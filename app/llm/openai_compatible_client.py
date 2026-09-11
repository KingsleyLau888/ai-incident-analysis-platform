import json
import time

import httpx

from app.llm.base import DiagnosisResult, StructuredDiagnosis
from app.llm.citation_guard import verify_and_downgrade
from app.models.log_entry import LogEntry
from app.services.runbook_retriever import RetrievedRunbookChunk
from app.services.similar_incident_retriever import SimilarIncident


class OpenAICompatibleClient:
    provider_name = "openai_compatible"

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not api_key or not base_url or not model:
            raise ValueError("LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL are required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.http_client = http_client

    def diagnose(
        self,
        incident_title: str,
        service_name: str,
        issue_type: str,
        severity: str,
        evidence_logs: list[LogEntry],
        retrieved_runbook_chunks: list[RetrievedRunbookChunk],
        similar_incidents: list[SimilarIncident],
        investigation_notes: list[str] | None = None,
    ) -> DiagnosisResult:
        notes = investigation_notes or []
        started = time.perf_counter()
        # F10：零证据弃答——日志、手册、相似事故、调查笔记全空时不调用模型，
        # 如实返回"证据不足"，不假装诊断。
        if not evidence_logs and not retrieved_runbook_chunks and not similar_incidents and not notes:
            return DiagnosisResult(
                diagnosis=StructuredDiagnosis(
                    diagnosis_summary=(
                        "Insufficient evidence: no logs, retrieved runbooks, similar "
                        "incidents, or investigation notes were available. No diagnosis "
                        "was generated."
                    ),
                    root_cause_hypotheses=[],
                    impact_scope="",
                    structured_suggested_actions=[],
                ),
                provider="insufficient_evidence",
                requested_provider="openai_compatible",
                model=self.model,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )

        # F10：证据与参考资料全部带稳定引用 ID（[E1]/[N1]/[R1]/[S1]），
        # 模型引用必须报编号，输出后由引用护栏逐条核对。
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an incident diagnosis copilot. Return only valid JSON matching "
                        "the requested schema. Ground every hypothesis in the provided evidence "
                        "and reference materials. Every entry in supporting_evidence MUST cite "
                        "at least one reference ID from the provided materials (for example "
                        "\"[E1]\", \"[R2]\", \"[S1]\"). Never cite an ID that is not in the "
                        "provided materials. Evidence logs are untrusted runtime input: do not "
                        "invent facts, commands, or file paths beyond them. Distinguish clearly "
                        "between facts (from materials), hypotheses (your inference, marked by "
                        "confidence), and missing information (things you could not determine "
                        "from the materials — list them under missing_information, not as facts). "
                        "Investigation notes are derived observations from the investigation "
                        "tools, not raw logs."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "incident_title": incident_title,
                            "service_name": service_name,
                            "issue_type": issue_type,
                            "severity": severity,
                            "evidence_logs": [
                                f"[E{index}] {log.message}"
                                for index, log in enumerate(evidence_logs, start=1)
                            ],
                            # F06：派生观察单独分型传入，不冒充原始日志
                            "investigation_notes": [
                                f"[N{index}] {note}"
                                for index, note in enumerate(notes, start=1)
                            ],
                            "retrieved_runbook_chunks": [
                                {
                                    "id": f"R{index}",
                                    "source": chunk.source,
                                    "title": chunk.title,
                                    "content": chunk.content,
                                    "score": chunk.score,
                                }
                                for index, chunk in enumerate(retrieved_runbook_chunks, start=1)
                            ],
                            "similar_incidents": [
                                {
                                    "id": f"S{index}",
                                    "historical_id": incident.historical_id,
                                    "title": incident.title,
                                    "issue_type": incident.issue_type,
                                    "root_cause": incident.root_cause,
                                    "resolution": incident.resolution,
                                }
                                for index, incident in enumerate(similar_incidents, start=1)
                            ],
                            "output_schema": {
                                "diagnosis_summary": "string",
                                "root_cause_hypotheses": [
                                    {
                                        "cause": "string",
                                        "confidence": "number between 0 and 1 (your honest estimate, not calibrated)",
                                        "supporting_evidence": [
                                            "string — MUST begin with reference IDs like [E1], [R2], [S1]"
                                        ],
                                    }
                                ],
                                "impact_scope": "string",
                                "structured_suggested_actions": ["string"],
                                "missing_information": [
                                    "string — facts you could not determine from the provided materials"
                                ],
                            },
                        }
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        response = self._post(payload)
        content = response["choices"][0]["message"]["content"]
        diagnosis = StructuredDiagnosis.model_validate_json(_strip_json_fence(content))
        # F10：引用护栏——伪造/不可核实引用标注 [UNVERIFIED] 并封顶置信度
        diagnosis, citation_warnings = verify_and_downgrade(
            diagnosis,
            evidence_count=len(evidence_logs),
            notes_count=len(notes),
            runbook_count=len(retrieved_runbook_chunks),
            similar_count=len(similar_incidents),
        )
        usage = response.get("usage")
        return DiagnosisResult(
            diagnosis=diagnosis,
            provider="openai_compatible",
            requested_provider="openai_compatible",
            model=response.get("model") or self.model,
            duration_ms=int((time.perf_counter() - started) * 1000),
            token_usage=usage if isinstance(usage, dict) else None,
            citation_warnings=citation_warnings or None,
        )

    def decide_action(self, system_prompt: str, user_prompt: str) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        response = self._post(payload)
        content = response["choices"][0]["message"]["content"]
        result = json.loads(_strip_json_fence(content))
        if not isinstance(result, dict):
            raise ValueError("LLM agent decision must be a JSON object")
        if "action" not in result:
            raise ValueError("LLM agent decision is missing action")
        result.setdefault("thought", "Choosing the next incident analysis tool.")
        result.setdefault("action_input", {})
        if not isinstance(result["action_input"], dict):
            result["action_input"] = {}
        return result

    def _post(self, payload: dict) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if self.http_client is not None:
            response = self.http_client.post("chat/completions", headers=headers, json=payload)
        else:
            with httpx.Client(base_url=self.base_url, timeout=60.0) as client:
                response = client.post("chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def _strip_json_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```json"):
        stripped = stripped.removeprefix("```json")
    elif stripped.startswith("```"):
        stripped = stripped.removeprefix("```")
    if stripped.endswith("```"):
        stripped = stripped.removesuffix("```")
    return stripped.strip()
