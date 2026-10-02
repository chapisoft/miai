"""
Utility functions for Face Analysis Engine.
Image decoding, encoding, format transformation and DTO mapping.
"""

import base64
import cv2
import numpy as np
from typing import Union, List, Optional
from schemas.face import (
    FaceBoxDto,
    LandmarkPointDto,
    FaceItemDto,
    HeadPoseDto,
    FaceStateDto,
)
from core.exceptions import FaceBiometricsException
from core.constants import ErrorCode


def decode_image(image_input: Union[str, bytes, np.ndarray]) -> np.ndarray:
    """
    Decodes an image from base64 string, raw bytes, or returns np.ndarray.
    Ensures the image is in BGR format with shape (H, W, 3).
    """
    if isinstance(image_input, np.ndarray):
        if len(image_input.shape) == 2:
            return cv2.cvtColor(image_input, cv2.COLOR_GRAY2BGR)
        return image_input

    if isinstance(image_input, str):
        if not image_input.strip():
            raise FaceBiometricsException(
                message="EMPTY_BASE64",
                error_code=ErrorCode.INVALID_PARAMETERS,
            )
        if "," in image_input:
            image_input = image_input.split(",", 1)[1]
        try:
            raw_bytes = base64.b64decode(image_input)
        except Exception as e:
            raise FaceBiometricsException(
                message=f"Base64 image decoding failed: {str(e)}",
                error_code=ErrorCode.INVALID_PARAMETERS,
            )
    elif isinstance(image_input, bytes):
        raw_bytes = image_input
    else:
        raise FaceBiometricsException(
            message=f"Invalid image input type: {type(image_input)}",
            error_code=ErrorCode.INVALID_PARAMETERS,
        )

    nparr = np.frombuffer(raw_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise FaceBiometricsException(
            message="DECODE_ERROR",
            error_code=ErrorCode.INVALID_PARAMETERS,
        )

    return image


def encode_image_base64(image_np: np.ndarray, format: str = ".jpg") -> str:
    """
    Encodes an image numpy array into a base64 string.
    """
    success, buffer = cv2.imencode(format, image_np)
    if not success:
        raise FaceBiometricsException(
            message="Failed to encode image to base64 format",
            error_code=ErrorCode.FACE_DETECTION_ERROR,
        )
    return base64.b64encode(buffer.tobytes()).decode("utf-8")


def map_uniface_to_dto(face) -> FaceItemDto:
    """
    Maps a UniFace Face object to standardized FaceItemDto.
    """
    bbox_raw = getattr(face, "bbox", [0, 0, 0, 0])
    conf = float(getattr(face, "confidence", 1.0))
    landmarks_raw = getattr(face, "landmarks", None)

    landmarks_dto: List[LandmarkPointDto] = []
    if landmarks_raw is not None and len(landmarks_raw) > 0:
        for pt in landmarks_raw:
            if len(pt) >= 2:
                landmarks_dto.append(LandmarkPointDto(x=float(pt[0]), y=float(pt[1])))

    # Embedding
    emb = getattr(face, "embedding", None)
    emb_list = emb.tolist() if isinstance(emb, np.ndarray) else None

    # HeadPose
    hp = getattr(face, "head_pose", None)
    head_pose_dto = None
    if hp is not None:
        head_pose_dto = HeadPoseDto(
            pitch=float(getattr(hp, "pitch", 0.0)),
            yaw=float(getattr(hp, "yaw", 0.0)),
            roll=float(getattr(hp, "roll", 0.0)),
        )

    # Face state
    fs = getattr(face, "face_state", None)
    state_dto = None
    if fs is not None:
        state_dto = FaceStateDto(
            has_mask=getattr(fs, "has_mask", None),
            has_glasses=getattr(fs, "has_glasses", None),
            has_sunglasses=getattr(fs, "has_sunglasses", None),
            is_left_eye_closed=getattr(fs, "is_left_eye_closed", None),
            is_right_eye_closed=getattr(fs, "is_right_eye_closed", None),
        )

    return FaceItemDto(
        bbox=FaceBoxDto(
            x1=float(bbox_raw[0]),
            y1=float(bbox_raw[1]),
            x2=float(bbox_raw[2]),
            y2=float(bbox_raw[3]),
            confidence=conf,
        ),
        landmarks=landmarks_dto,
        quality_score=getattr(face, "quality", None),
        is_live=getattr(face, "is_live", None),
        liveness_score=getattr(face, "liveness_confidence", None),
        embedding=emb_list,
        age=getattr(face, "age", None),
        gender=getattr(face, "gender", getattr(face, "sex", None)),
        race=getattr(face, "race", None),
        emotion=getattr(face, "emotion", None),
        head_pose=head_pose_dto,
        face_state=state_dto,
    )
