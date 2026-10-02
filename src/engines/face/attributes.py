"""
Face Attributes & Pose Analysis Adapter.
Integrates FairFace (demographics), HeadPose (6D Euler angles), and FaceAttribNet (mask, glasses, eye state).
"""

from typing import Union, Dict, Any, Optional
import numpy as np
from schemas.face import HeadPoseDto, FaceStateDto
from engines.face.utils import decode_image


class FaceAttributesAnalyzer:
    """
    Manages Demographic, Pose, and State predictors for detected faces.
    """

    _headpose_instance: Any = None
    _fairface_instance: Any = None
    _attrib_instance: Any = None

    @classmethod
    def get_headpose(cls):
        if cls._headpose_instance is None:
            try:
                from uniface.headpose import HeadPose
                cls._headpose_instance = HeadPose()
            except Exception:
                cls._headpose_instance = None
        return cls._headpose_instance

    @classmethod
    def get_fairface(cls):
        if cls._fairface_instance is None:
            try:
                from uniface.attribute import FairFace
                cls._fairface_instance = FairFace()
            except Exception:
                cls._fairface_instance = None
        return cls._fairface_instance

    @classmethod
    def get_face_attrib(cls):
        if cls._attrib_instance is None:
            try:
                from uniface.attribute import FaceAttribNet
                cls._attrib_instance = FaceAttribNet()
            except Exception:
                cls._attrib_instance = None
        return cls._attrib_instance

    @classmethod
    def estimate_head_pose(
        cls,
        image_np: np.ndarray,
        bbox: Union[list, np.ndarray],
    ) -> Optional[HeadPoseDto]:
        """
        Estimates 6D head pose (Pitch, Yaw, Roll in degrees).
        """
        estimator = cls.get_headpose()
        if estimator is None:
            return None

        try:
            x1, y1, x2, y2 = map(int, bbox[:4])
            h, w = image_np.shape[:2]
            x1 = max(0, min(x1, w - 1))
            y1 = max(0, min(y1, h - 1))
            x2 = max(x1 + 1, min(x2, w))
            y2 = max(y1 + 1, min(y2, h))

            crop = image_np[y1:y2, x1:x2]
            if crop.size == 0:
                return None

            res = estimator.estimate(crop)
            return HeadPoseDto(
                pitch=float(res.pitch),
                yaw=float(res.yaw),
                roll=float(res.roll),
            )
        except Exception:
            return None

    @classmethod
    def analyze_demographics(cls, image_np: np.ndarray, face_obj: Any) -> Dict[str, Any]:
        """
        Predicts gender, age group, race via FairFace.
        """
        fairface = cls.get_fairface()
        if fairface is None or face_obj is None:
            return {}

        try:
            res = fairface.predict(image_np, face_obj)
            return {
                "gender": getattr(res, "sex", None),
                "age_group": getattr(res, "age_group", None),
                "race": getattr(res, "race", None),
            }
        except Exception:
            return {}

    @classmethod
    def analyze_state(cls, image_np: np.ndarray, face_obj: Any) -> Optional[FaceStateDto]:
        """
        Predicts mask, glasses, eyes openness via FaceAttribNet.
        """
        attrib_net = cls.get_face_attrib()
        if attrib_net is None or face_obj is None:
            return None

        try:
            res = attrib_net.predict(image_np, face_obj)
            return FaceStateDto(
                has_mask=bool(getattr(res, "has_mask", False)),
                has_glasses=bool(getattr(res, "has_glasses", False)),
                has_sunglasses=bool(getattr(res, "has_sunglasses", False)),
                is_left_eye_closed=bool(getattr(res, "is_left_eye_closed", False)),
                is_right_eye_closed=bool(getattr(res, "is_right_eye_closed", False)),
            )
        except Exception:
            return None
