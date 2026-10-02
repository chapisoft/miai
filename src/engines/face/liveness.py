"""
Face Anti-Spoofing & Liveness Detection Adapter (MiniFASNet V2).
Detects presentation attacks: print photos, screens, video replay.
"""

from typing import Union, Dict, Any, Tuple
import numpy as np
from core.constants import LivenessDecision, ErrorCode
from core.exceptions import FaceBiometricsException
from engines.face.utils import decode_image


class FaceLivenessChecker:
    """
    Manages Face Anti-Spoofing models (MiniFASNet).
    """

    _instance: Any = None

    @classmethod
    def get_instance(cls):
        """
        Retrieves or initializes singleton MiniFASNet model.
        """
        if cls._instance is not None:
            return cls._instance

        try:
            from uniface.spoofing import MiniFASNet
            cls._instance = MiniFASNet()
            return cls._instance
        except Exception as e:
            raise FaceBiometricsException(
                message=f"Failed to initialize MiniFASNet anti-spoofing model: {str(e)}",
                error_code=ErrorCode.FACE_SPOOF_DETECTED,
                details={"error": str(e)},
            )

    @classmethod
    def check_liveness(
        cls,
        image_input: Union[str, bytes, np.ndarray],
        bbox: Union[list, np.ndarray],
        threshold: float = 0.80,
    ) -> Tuple[bool, float, LivenessDecision]:
        """
        Evaluates whether a detected face is live (real human) or a spoof attack.
        Returns:
            (is_live: bool, confidence: float, decision: LivenessDecision)
        """
        image_np = decode_image(image_input)
        spoofer = cls.get_instance()

        if isinstance(bbox, np.ndarray):
            bbox = bbox.tolist()

        try:
            result = spoofer.predict(image_np, bbox)
            is_real = bool(result.is_real)
            confidence = float(result.confidence)

            if is_real and confidence >= threshold:
                decision = LivenessDecision.REAL
                is_live = True
            elif not is_real and confidence >= threshold:
                decision = LivenessDecision.FAKE
                is_live = False
            else:
                decision = LivenessDecision.UNCERTAIN
                # If uncertain, require is_real to be True with reasonable confidence
                is_live = is_real and confidence >= 0.50

            return is_live, confidence, decision
        except Exception as e:
            raise FaceBiometricsException(
                message=f"Failed to execute face liveness verification: {str(e)}",
                error_code=ErrorCode.FACE_SPOOF_DETECTED,
                details={"error": str(e)},
            )
