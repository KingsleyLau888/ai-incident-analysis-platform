"""F10 引用护栏：校验诊断假设的支持证据引用，伪造引用明确降级。

诊断提示词要求每条 supporting_evidence 携带引用 ID（[E1] 证据日志、
[N1] 调查笔记、[R1] 手册 chunk、[S1] 相似事故）。模型输出后由本模块
逐条核对 ID 是否在本次请求实际提供的材料集合内：

- 引用全部真实 → 原样保留；
- 引用不存在的 ID、整条没有任何引用 ID，或假设一条支持证据都没有
  （supporting_evidence 为空）→ 该条目/假设标注 [UNVERIFIED]，
  且所在假设的置信度封顶 0.35（明确降级，不静默删除）；
- 降级逐条记录为警告，随 DiagnosisResult 进入 Trace（可观测）。

注意：本护栏只针对真实 LLM 客户端（openai_compatible）。Mock 客户端是
确定性模板，不存在编造引用问题，不经过本模块。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.llm.base import StructuredDiagnosis

# 引用 ID 形如 [E1] / [N2] / [R3] / [S4]
_CITATION_RE = re.compile(r"\[([ENRS])(\d+)\]")

# 存在伪造/不可核实引用的假设置信度上限——低于"中等"，明确降级
UNVERIFIED_CONFIDENCE_CAP = 0.35


def valid_reference_ids(
    evidence_count: int,
    notes_count: int = 0,
    runbook_count: int = 0,
    similar_count: int = 0,
) -> set[str]:
    """本次请求实际提供的材料 ID 集合（只包含真实存在的编号）。"""
    valid: set[str] = set()
    valid.update(f"E{i}" for i in range(1, evidence_count + 1))
    valid.update(f"N{i}" for i in range(1, notes_count + 1))
    valid.update(f"R{i}" for i in range(1, runbook_count + 1))
    valid.update(f"S{i}" for i in range(1, similar_count + 1))
    return valid


def verify_and_downgrade(
    diagnosis: StructuredDiagnosis,
    *,
    evidence_count: int,
    notes_count: int = 0,
    runbook_count: int = 0,
    similar_count: int = 0,
) -> tuple[StructuredDiagnosis, list[str]]:
    """校验假设引用；伪引用的条目标注 [UNVERIFIED] 并封顶置信度。

    返回 (处理后的诊断, 警告列表)。警告逐条记录降级的假设与原因，
    无问题时空列表。
    """
    valid = valid_reference_ids(
        evidence_count=evidence_count,
        notes_count=notes_count,
        runbook_count=runbook_count,
        similar_count=similar_count,
    )
    warnings: list[str] = []
    hypotheses = []
    for index, hypothesis in enumerate(diagnosis.root_cause_hypotheses, start=1):
        entries = []
        unverified_reasons = []
        if not hypothesis.supporting_evidence:
            # R02（2026-09-11 复核）：有根因但一条证据都不引用——原实现
            # 循环直接跳过空列表，0.99 置信度原样保留；现在同样降级。
            unverified_reasons.append("no supporting evidence")
            entries.append("[UNVERIFIED] (no supporting evidence)")
        else:
            for entry in hypothesis.supporting_evidence:
                cited = {f"{kind}{num}" for kind, num in _CITATION_RE.findall(entry)}
                unknown = cited - valid
                if not cited:
                    unverified_reasons.append("no citation id")
                    entries.append(f"[UNVERIFIED] {entry}")
                elif unknown:
                    unverified_reasons.append("unknown id " + ", ".join(sorted(unknown)))
                    entries.append(f"[UNVERIFIED] {entry}")
                else:
                    entries.append(entry)

        confidence = hypothesis.confidence
        if unverified_reasons:
            confidence = min(confidence, UNVERIFIED_CONFIDENCE_CAP)
            warnings.append(
                f"hypothesis#{index} confidence capped at "
                f"{UNVERIFIED_CONFIDENCE_CAP}: {', '.join(unverified_reasons)}"
            )
        hypotheses.append(
            hypothesis.model_copy(
                update={
                    "supporting_evidence": entries,
                    "confidence": round(confidence, 2),
                }
            )
        )

    return (
        diagnosis.model_copy(update={"root_cause_hypotheses": hypotheses}),
        warnings,
    )
