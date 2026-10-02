"""
Face Image Quality Assessment Adapter (eDifFIQA).
Evaluates face image quality for enrollment and verification (NIST FATE-Quality top performer).
"""

from typing import Union, Optional, Any
import numpy as np
from core.exceptions import FaceBiometricsException
from core.constants import ErrorCode
from engines.face.utils import decode_image


class FaceQualityScorer:
    """
    Manages Face Quality Assessment models (eDifFIQA).
    """

    _instance: Any = None

    @classmethod
    def get_instance(cls):
        """
        Retrieves or initializes singleton EDifFIQA model.
        """
        if cls._instance is not None:
            return cls._instance

        try:
            from core.config import settings
            from uniface.quality import EDifFIQA
            providers = [settings.FACE_EXECUTION_PROVIDER, "TensorrtExecutionProvider", "CPUExecutionProvider"]
            cls._instance = EDifFIQA(providers=providers)
            return cls._instance
        except Exception as e:
            raise FaceBiometricsException(
                message=f"Failed to initialize eDifFIQA face quality assessment model: {str(e)}",
                error_code=ErrorCode.FACE_QUALITY_TOO_LOW,
                details={"error": str(e)},
            )

    @classmethod
    def assess_quality(
        cls,
        image_input: Union[str, bytes, np.ndarray],
        landmarks: Union[np.ndarray, list],
    ) -> float:
        """
        Calculates a scalar quality score roughly in [0.0 - 1.0].
        Higher means clearer, better aligned, more suitable for recognition.
        """
        image_np = decode_image(image_input)
        if isinstance(landmarks, list):
            landmarks = np.array(landmarks, dtype=np.float32)

        try:
            scorer = cls.get_instance()
            result = scorer.predict(image_np, landmarks)
            score = float(result.score)
            return max(0.0, min(1.0, score))
        except Exception:
            # Fallback estimation using Laplacian variance (blur detection)
            try:
                import cv2
                gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
                variance = cv2.Laplacian(gray, cv2.CV_64F).var()
                # Map variance (typically 0-500) to 0.0 - 1.0
                fallback_score = min(1.0, max(0.1, variance / 200.0))
                return round(fallback_score, 3)
            except Exception:
                return 0.75
