"""
Face Detector Adapter for UniFace models (SCRFD, RetinaFace, CenterFace, YOLOv8Face).
"""

from typing import List, Optional, Union, Dict, Any
import numpy as np
from core.constants import FaceDetectorType, ErrorCode
from core.exceptions import FaceBiometricsException
from schemas.face import FaceItemDto
from engines.face.utils import decode_image, map_uniface_to_dto


class FaceDetector:
    """
    Manages Face Detection models with cached instances and provider acceleration.
    """

    _instances: Dict[str, Any] = {}

    @classmethod
    def get_detector(
        cls,
        detector_type: FaceDetectorType = FaceDetectorType.SCRFD,
        confidence_threshold: float = 0.5,
    ):
        """
        Retrieves or initializes a detector instance (singleton per detector type).
        """
        key = f"{detector_type.value}_{confidence_threshold:.2f}"
        if key in cls._instances:
            return cls._instances[key]

        try:
            if detector_type == FaceDetectorType.SCRFD:
                from uniface.detection import SCRFD
                detector = SCRFD(confidence_threshold=confidence_threshold)
            elif detector_type == FaceDetectorType.RETINAFACE:
                from uniface.detection import RetinaFace
                detector = RetinaFace(confidence_threshold=confidence_threshold)
            elif detector_type == FaceDetectorType.CENTERFACE:
                from uniface.detection import CenterFace
                detector = CenterFace(confidence_threshold=confidence_threshold)
            elif detector_type == FaceDetectorType.YOLOV8_FACE:
                from uniface.detection import YOLOv8Face
                detector = YOLOv8Face(confidence_threshold=confidence_threshold)
            else:
                from uniface.detection import SCRFD
                detector = SCRFD(confidence_threshold=confidence_threshold)

            cls._instances[key] = detector
            return detector
        except Exception as e:
            raise FaceBiometricsException(
                message=f"Failed to initialize face detector model {detector_type.value}: {str(e)}",
                error_code=ErrorCode.FACE_DETECTION_ERROR,
                details={"detector_type": detector_type.value, "error": str(e)},
            )

    @classmethod
    def detect(
        cls,
        image_input: Union[str, bytes, np.ndarray],
        detector_type: FaceDetectorType = FaceDetectorType.SCRFD,
        min_confidence: float = 0.5,
    ) -> List[Any]:
        """
        Detects faces in the given image. Returns list of UniFace Face objects.
        """
        image_np = decode_image(image_input)
        detector = cls.get_detector(detector_type, min_confidence)
        try:
            faces = detector.detect(image_np)
            return faces or []
        except Exception as e:
            raise FaceBiometricsException(
                message=f"Failed to execute face detection: {str(e)}",
                error_code=ErrorCode.FACE_DETECTION_ERROR,
                details={"error": str(e)},
            )

    @classmethod
    def detect_dtos(
        cls,
        image_input: Union[str, bytes, np.ndarray],
        detector_type: FaceDetectorType = FaceDetectorType.SCRFD,
        min_confidence: float = 0.5,
    ) -> List[FaceItemDto]:
        """
        Detects faces and converts output to standardized FaceItemDto list.
        """
        faces = cls.detect(image_input, detector_type, min_confidence)
        return [map_uniface_to_dto(f) for f in faces]
