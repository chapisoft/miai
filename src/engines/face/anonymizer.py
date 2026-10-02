"""
Face Anonymization & Privacy Protection Adapter (BlurFace).
Compliant with Vietnam Personal Data Protection Decree 13/2023/ND-CP and GDPR.
"""

from typing import Union, List, Tuple, Optional, Any
import numpy as np
from core.constants import FaceAnonymizeMethod, ErrorCode
from core.exceptions import FaceBiometricsException
from engines.face.utils import decode_image, encode_image_base64
from engines.face.detector import FaceDetector


class FaceAnonymizer:
    """
    Manages Face Anonymization and Blurring strategies.
    """

    @classmethod
    def anonymize_image(
        cls,
        image_input: Union[str, bytes, np.ndarray],
        faces: Optional[List[Any]] = None,
        method: FaceAnonymizeMethod = FaceAnonymizeMethod.PIXELATE,
        blur_strength: float = 3.0,
    ) -> Tuple[np.ndarray, str, int]:
        """
        Anonymizes human faces in an image.
        Returns:
            (anonymized_np: np.ndarray, anonymized_base64: str, faces_count: int)
        """
        image_np = decode_image(image_input)

        if faces is None:
            # Auto-detect faces
            faces = FaceDetector.detect(image_np)

        if not faces:
            return image_np, encode_image_base64(image_np), 0

        from uniface.privacy import BlurFace
        from uniface.types import Face

        normalized_faces = []
        for f in faces:
            if isinstance(f, Face):
                normalized_faces.append(f)
            elif isinstance(f, (list, tuple)) and len(f) >= 4:
                normalized_faces.append(Face(
                    bbox=np.array([float(f[0]), float(f[1]), float(f[2]), float(f[3])], dtype=np.float32),
                    confidence=1.0,
                    landmarks=np.zeros((5, 2), dtype=np.float32),
                ))
            elif isinstance(f, dict) and "bbox" in f:
                b = f["bbox"]
                normalized_faces.append(Face(
                    bbox=np.array([float(b[0]), float(b[1]), float(b[2]), float(b[3])], dtype=np.float32),
                    confidence=float(f.get("confidence", 1.0)),
                    landmarks=np.array(f.get("landmarks", np.zeros((5, 2))), dtype=np.float32),
                ))
            elif hasattr(f, "bbox"):
                normalized_faces.append(f)

        if not normalized_faces:
            return image_np, encode_image_base64(image_np), 0

        try:
            blurrer = BlurFace(
                method=method.value if isinstance(method, FaceAnonymizeMethod) else str(method),
                blur_strength=blur_strength,
            )
            anonymized_np = blurrer.anonymize(image_np, normalized_faces)
            anonymized_b64 = encode_image_base64(anonymized_np)
            return anonymized_np, anonymized_b64, len(normalized_faces)
        except Exception as e:
            raise FaceBiometricsException(
                message=f"Failed to execute face anonymization: {str(e)}",
                error_code=ErrorCode.FACE_DETECTION_ERROR,
                details={"error": str(e)},
            )
