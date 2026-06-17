import json

import httpx

from app.llm.base import DiagnosisResult, StructuredDiagnosis
from app.models.log_entry import LogEntry
from app.services.runbook_retriever import RetrievedRunbookChunk
from app.services.similar_incident_retriever import SimilarIncident


class OpenAICompatibleClient:
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
    ) -> DiagnosisResult:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an incident diagnosis copilot. Return only valid JSON matching "
                        "the requested schema. Ground hypotheses in the provided evidence."
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
                            "evidence_logs": [log.message for log in evidence_logs],
                            "retrieved_runbook_chunks": [
                                {
                                    "source": chunk.source,
                                    "title": chunk.title,
                                    "content": chunk.content,
                                    "score": chunk.score,
                                }
                                for chunk in retrieved_runbook_chunks
                            ],
                            "similar_incidents": [
                                {
                                    "historical_id": incident.historical_id,
                                    "title": incident.title,
                                    "issue_type": incident.issue_type,
                                    "root_cause": incident.root_cause,
                                    "resolution": incident.resolution,
                                }
                                for incident in similar_incidents
                            ],
                            "output_schema": {
                                "diagnosis_summary": "string",
                                "root_cause_hypotheses": [
                                    {
                                        "cause": "string",
                                        "confidence": "number between 0 and 1",
                                        "supporting_evidence": ["string"],
                                    }
                                ],
                                "impact_scope": "string",
                                "structured_suggested_actions": ["string"],
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
        return DiagnosisResult(diagnosis=diagnosis, provider="openai_compatible")

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
