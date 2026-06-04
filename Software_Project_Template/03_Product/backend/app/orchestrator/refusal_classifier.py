from __future__ import annotations

from dataclasses import dataclass
import re


PROMPT_EXTRACTION_RE = re.compile(r"\b(?:reveal|show|print|override|ignore)\b.*\b(?:system prompt|hidden instructions|developer message|guardrails)\b")
EXECUTION_RE = re.compile(r"^(?:please\s+|can you\s+|could you\s+)?(?:buy|sell|short|trade|place an order|execute)\b")
GUARANTEE_RE = re.compile(r"\b(?:guarantee|guaranteed|definitely|certainly)\b.*\b(?:profit|return|gain|outperform|rise|fall)\b")
PERSONAL_DIRECTIVE_RE = re.compile(r"\b(?:tell me exactly|what should i buy|should i buy|should i sell|invest all|put all)\b")
ILLICIT_RE = re.compile(r"\b(?:insider information|manipulate the market|pump and dump|hide a trade)\b")


@dataclass(frozen=True, slots=True)
class RefusalClassification:
    allowed: bool
    intent: str = "allowed"
    confidence: float = 0.0
    prohibited_reason: str | None = None


def _blocked(intent: str, reason: str) -> RefusalClassification:
    return RefusalClassification(
        allowed=False,
        intent=intent,
        confidence=0.96,
        prohibited_reason=reason,
    )


def classify_refusal_intent(message: str) -> RefusalClassification:
    lowered = " ".join(message.strip().lower().split())
    if PROMPT_EXTRACTION_RE.search(lowered):
        return _blocked("prompt_extraction", "Caishen cannot reveal or override its system instructions.")
    if ILLICIT_RE.search(lowered):
        return _blocked("market_abuse", "Caishen cannot assist with market abuse or illicit trading activity.")
    if EXECUTION_RE.search(lowered):
        return _blocked("trade_execution", "Caishen is read-only and cannot place, execute, or manage trades.")
    if GUARANTEE_RE.search(lowered) or PERSONAL_DIRECTIVE_RE.search(lowered):
        return _blocked(
            "personalized_investment_directive",
            "Caishen cannot guarantee outcomes or issue personalized buy or sell directives.",
        )
    return RefusalClassification(allowed=True, confidence=0.8)
