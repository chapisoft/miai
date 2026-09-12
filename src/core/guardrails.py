"""
AI Safety Guardrails: Prompt Injection Detection and PII Redaction.
"""

import re
from typing import Tuple, List
from core.exceptions import PromptInjectionException

# Patterns indicative of prompt injection / jailbreak attempts
INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|directives|rules)",
    r"(?i)system\s+override",
    r"(?i)you\s+are\s+now\s+(in\s+)?developer\s+mode",
    r"(?i)disregard\s+all\s+prior",
    r"(?i)bypass\s+safety\s+filters",
    r"(?i)reveal\s+(your\s+)?(system\s+prompt|hidden\s+instructions)",
    r"(?i)bỏ\s+qua\s+(toàn\s+bộ\s+)?(chỉ\s+dẫn|hướng\s+dẫn|quy\s+tắc)\s+trước",
    r"(?i)chế\s+độ\s+nhà\s+phát\s+triển",
]

# Sensitive PII Regex Patterns for Vietnam market
PII_PATTERNS = [
    (r"\b(0[3|5|7|8|9][0-9]{8})\b", "[REDACTED_PHONE]"),  # VN Mobile Phone
    (r"\b([0-9]{9}|[0-9]{12})\b", "[REDACTED_ID]"),        # CMND / CCCD
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[REDACTED_EMAIL]"), # Email
    (r"\b([0-9]{4}[- ]?){3}[0-9]{4}\b", "[REDACTED_CARD]"), # Credit Card
]


class Guardrails:
    """Prompt Guard & Content Safety Engine."""

    @staticmethod
    def inspect_prompt(text: str) -> bool:
        """
        Inspects text for prompt injection patterns.
        Raises PromptInjectionException if a malicious pattern is detected.
        """
        if not text:
            return True

        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, text):
                raise PromptInjectionException(
                    details={"matched_pattern": pattern}
                )
        return True

    @staticmethod
    def redact_pii(text: str) -> str:
        """
        Masks sensitive PII data (phone, ID, card, email) before sending to external LLMs.
        """
        if not text:
            return text

        redacted_text = text
        for pattern, replacement in PII_PATTERNS:
            redacted_text = re.sub(pattern, replacement, redacted_text)
        return redacted_text
