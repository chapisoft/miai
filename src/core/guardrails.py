"""
AI Safety Guardrails: Prompt Injection Detection and PII Redaction.
"""

import re
from typing import Tuple, List, Optional
import numpy as np
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

    @staticmethod
    def redact_face_pii(
        image_np: np.ndarray,
        faces: Optional[list] = None,
        method: str = "pixelate",
        blur_strength: float = 3.0,
    ) -> np.ndarray:
        """
        Masks / blurs human faces in images to protect PII privacy (Decree 13/2023/ND-CP).
        Uses UniFace BlurFace utility.
        """
        if image_np is None or image_np.size == 0:
            return image_np

        from uniface.privacy import BlurFace
        from uniface.types import Face

        blurrer = BlurFace(method=method, blur_strength=blur_strength)
        if faces is None or len(faces) == 0:
            # Fallback: if no faces provided, return image unmodified
            return image_np

        face_objs = []
        for f in faces:
            if isinstance(f, Face):
                face_objs.append(f)
            elif isinstance(f, (list, tuple)) and len(f) >= 4:
                face_objs.append(Face(
                    bbox=np.array([float(f[0]), float(f[1]), float(f[2]), float(f[3])], dtype=np.float32),
                    confidence=1.0,
                    landmarks=np.zeros((5, 2), dtype=np.float32)
                ))
            elif isinstance(f, dict) and "bbox" in f:
                b = f["bbox"]
                face_objs.append(Face(
                    bbox=np.array([float(b[0]), float(b[1]), float(b[2]), float(b[3])], dtype=np.float32),
                    confidence=float(f.get("confidence", 1.0)),
                    landmarks=np.array(f.get("landmarks", np.zeros((5, 2))), dtype=np.float32)
                ))

        if not face_objs:
            return image_np

        result = blurrer.anonymize(image_np, face_objs)
        return result if result is not None else image_np

