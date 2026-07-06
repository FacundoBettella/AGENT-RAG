"""Pre-OpenAI validation layer: 3 checks run before any API call.

Layer 1 — Sensitive data: credit cards, SSN, CUIT/CUIL.
Layer 2 — Prompt injection: adversarial framing trying to override system prompt.
Layer 3 — Abusive language: hate speech, violence, self-harm, cyber abuse.

Stateless classifier (ModerationEvaluator) is separated from the service that
handles logging (ModerationService) so each can be tested independently.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from domain.moderation import ModerationAction

if TYPE_CHECKING:
    from ports.log_repository import LogRepository

# --- Regex patterns for sensitive data (Layer 1) ---
_CREDIT_CARD_RE = re.compile(
    r"\b(?:"
    r"4[0-9]{12}(?:[0-9]{3})?"        # Visa
    r"|5[1-5][0-9]{14}"               # Mastercard
    r"|3[47][0-9]{13}"                # Amex
    r")\b"
)
_CUIT_CUIL_RE = re.compile(r"\b\d{2}-\d{7,8}-\d\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


class ModerationEvaluator:
    """Stateless classifier. No I/O — fully testable without mocks."""

    def __init__(self, salt: str) -> None:
        self._salt = salt

        # Layer 3 — Abusive language keywords
        self._risk_keywords: dict[str, set[str]] = {
            "hate_speech": {"racial slur", "nazi", "matar"},
            "self_harm": {"suicidio", "auto lesion", "cortarme"},
            "violence": {"bomb", "disparar", "asesinar", "asesino"},
            "cyber_abuse": {
                "sql injection",
                "bypass authentication",
                "robo de credenciales",
                "phishing",
            },
        }

        # Layer 2 — Prompt injection: adversarial framing markers
        self._injection_markers = {
            "fingiendo",
            "ficticio",
            "roleplay",
            "hace de cuenta",
            "para una investigacion",
            "para fines educativos",
            "ignora las instrucciones",
            "ignore previous instructions",
            "forget your instructions",
            "act as",
            "jailbreak",
            "dan mode",
        }
        # Sensitive tokens that escalate injection markers to a BLOCK
        self._injection_sensitive_tokens = {
            "credenciales",
            "password",
            "contrasena",
            "documento",
            "dni",
            "user id",
            "bypass",
            "token",
            "secret",
        }

    def hash_value(self, value: str) -> str:
        return hashlib.sha256(f"{self._salt}:{value}".encode()).hexdigest()

    def _normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text.lower())
        normalized = re.sub(r"[\W_]+", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def evaluate(self, text: str) -> tuple[list[str], ModerationAction, str]:
        """Return (detected_risks, action, reason)."""
        # Layer 1 — Sensitive data (regex)
        if _CREDIT_CARD_RE.search(text):
            return ["sensitive_data:credit_card"], ModerationAction.BLOCK, "Datos de tarjeta de crédito detectados. No se procesan datos financieros."
        if _CUIT_CUIL_RE.search(text):
            return ["sensitive_data:cuit_cuil"], ModerationAction.BLOCK, "CUIT/CUIL detectado. No se procesan datos fiscales personales."
        if _SSN_RE.search(text):
            return ["sensitive_data:ssn"], ModerationAction.BLOCK, "Número de seguro social detectado. No se procesan datos personales sensibles."

        normalized = self._normalize(text)

        # Layer 3 — Abusive language (keywords)
        risks: list[str] = []
        for category, keywords in self._risk_keywords.items():
            if any(kw in normalized for kw in keywords):
                risks.append(category)
        if risks:
            return risks, ModerationAction.BLOCK, "Contenido riesgoso detectado por política de palabras clave."

        # Layer 2 — Prompt injection (framing + sensitive token)
        has_injection_marker = any(m in normalized for m in self._injection_markers)
        has_sensitive_token = any(t in normalized for t in self._injection_sensitive_tokens)
        if has_injection_marker and has_sensitive_token:
            return ["prompt_injection"], ModerationAction.BLOCK, "Posible intento de prompt injection detectado."
        if has_injection_marker:
            return ["prompt_evasion"], ModerationAction.FLAG, "Framing adversarial detectado. Solicitud marcada para revisión."

        return [], ModerationAction.ALLOW, "Sin riesgos detectados."


class ModerationService:
    """Orchestrates evaluation + audit logging."""

    def __init__(self, evaluator: ModerationEvaluator, log_repository: LogRepository) -> None:
        self._evaluator = evaluator
        self._log_repository = log_repository

    def check(self, text: str) -> tuple[list[str], ModerationAction, str]:
        """Evaluate text and write an audit log entry. Returns (risks, action, reason)."""
        risks, action, reason = self._evaluator.evaluate(text)
        self._write_audit(text, risks, action)
        return risks, action, reason

    def _write_audit(self, text: str, risks: list[str], action: ModerationAction) -> None:
        retention = {
            ModerationAction.ALLOW: "clean_30d",
            ModerationAction.FLAG: "flagged_event_90d",
            ModerationAction.BLOCK: "incident_365d",
        }
        record = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "request_id": str(uuid4()),
            "input_hash": self._evaluator.hash_value(text),
            "detected_risks": risks,
            "moderation_action": action.value,
            "retention_tag": retention[action],
        }
        self._log_repository.write_log(record)
