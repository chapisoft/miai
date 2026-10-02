"""
Face Analysis, Biometrics, eKYC and Privacy Schemas (Pydantic V2).
100% Zero-Hardcode with Enums.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from core.constants import (
    FaceDetectorType,
    FaceRecognizerType,
    FaceAnonymizeMethod,
    LivenessDecision,
    ClassroomROIType,
    VisitorStatus,
    SubjectType,
    FaceFeedbackCode,
)


class FaceBoxDto(BaseModel):
    """Bounding box coordinates and detection confidence."""
    x1: float = Field(description="Top-left X coordinate")
    y1: float = Field(description="Top-left Y coordinate")
    x2: float = Field(description="Bottom-right X coordinate")
    y2: float = Field(description="Bottom-right Y coordinate")
    confidence: float = Field(default=1.0, description="Detection confidence score [0.0 - 1.0]")


class LandmarkPointDto(BaseModel):
    """2D landmark point."""
    x: float
    y: float


class HeadPoseDto(BaseModel):
    """Head pose Euler angles in degrees."""
    pitch: float = Field(description="Pitch angle (-up, +down)")
    yaw: float = Field(description="Yaw angle (-left, +right)")
    roll: float = Field(description="Roll tilt angle")


class FaceStateDto(BaseModel):
    """Facial state and occlusion attributes."""
    has_mask: Optional[bool] = Field(default=None, description="Face mask detected")
    has_glasses: Optional[bool] = Field(default=None, description="Eyeglasses detected")
    has_sunglasses: Optional[bool] = Field(default=None, description="Sunglasses detected")
    is_left_eye_closed: Optional[bool] = Field(default=None, description="Left eye closed")
    is_right_eye_closed: Optional[bool] = Field(default=None, description="Right eye closed")


class FaceItemDto(BaseModel):
    """Comprehensive Face representation."""
    bbox: FaceBoxDto
    landmarks: List[LandmarkPointDto] = Field(default_factory=list, description="5-point canonical landmarks")
    quality_score: Optional[float] = Field(default=None, description="eDifFIQA quality score [0.0 - 1.0]")
    is_live: Optional[bool] = Field(default=None, description="Liveness verification verdict")
    liveness_score: Optional[float] = Field(default=None, description="Liveness confidence score")
    embedding: Optional[List[float]] = Field(default=None, description="512-D L2-normalized feature embedding vector")
    age: Optional[int] = Field(default=None, description="Estimated age")
    gender: Optional[str] = Field(default=None, description="Gender (Male, Female)")
    race: Optional[str] = Field(default=None, description="Demographic classification")
    emotion: Optional[str] = Field(default=None, description="Emotion classification")
    head_pose: Optional[HeadPoseDto] = Field(default=None, description="3D head pose angles")
    face_state: Optional[FaceStateDto] = Field(default=None, description="Occlusion and eye states")


# ── 1. Detection Schemas ─────────────────────────────────────────────────────

class FaceDetectRequest(BaseModel):
    image_base64: str = Field(description="Input image as Base64 string")
    detector: FaceDetectorType = Field(default=FaceDetectorType.SCRFD, description="Face detector model")
    min_confidence: float = Field(default=0.5, description="Minimum confidence threshold")


class FaceDetectResponse(BaseModel):
    faces: List[FaceItemDto] = Field(default_factory=list, description="List of detected faces")
    total_faces: int = Field(description="Total face count")
    processing_time_ms: float = Field(description="Processing latency in milliseconds")


# ── 2. 1:1 Verification / eKYC Schemas ───────────────────────────────────────

class FaceCompareRequest(BaseModel):
    image_base64_target: str = Field(description="Target portrait image (ID card or Passport)")
    image_base64_source: str = Field(description="Source selfie or camera image")
    detector: FaceDetectorType = Field(default=FaceDetectorType.SCRFD, description="Face detector model")
    recognizer: FaceRecognizerType = Field(default=FaceRecognizerType.ADAFACE_IR50, description="Feature extractor model")
    check_liveness: bool = Field(default=True, description="Enable anti-spoofing check on source image")
    min_quality: float = Field(default=0.50, description="Minimum quality score threshold")


class FaceCompareResponse(BaseModel):
    is_same_person: bool = Field(description="Identity match verdict")
    similarity: float = Field(description="Cosine similarity score [0.0 - 1.0]")
    threshold: float = Field(description="Decision threshold applied")
    target_quality: Optional[float] = Field(default=None, description="Target image quality score")
    source_quality: Optional[float] = Field(default=None, description="Source image quality score")
    source_is_live: Optional[bool] = Field(default=None, description="Source image liveness verdict")
    source_liveness_score: Optional[float] = Field(default=None, description="Source liveness confidence")
    processing_time_ms: float = Field(description="Processing latency in milliseconds")


# ── 3. 1:N Search Schemas ────────────────────────────────────────────────────

class FaceSearchResultItemDto(BaseModel):
    identity_id: str = Field(description="Unique identity ID")
    name: Optional[str] = Field(default=None, description="Full name of person")
    similarity: float = Field(description="Cosine similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary")


class FaceSearchRequest(BaseModel):
    image_base64: str = Field(description="Query face image as Base64 string")
    top_k: int = Field(default=5, description="Number of top candidates to return")
    threshold: float = Field(default=0.60, description="Minimum similarity threshold")
    detector: FaceDetectorType = Field(default=FaceDetectorType.SCRFD)
    recognizer: FaceRecognizerType = Field(default=FaceRecognizerType.ADAFACE_IR50)


class FaceSearchResponse(BaseModel):
    matches: List[FaceSearchResultItemDto] = Field(default_factory=list, description="Ranked list of matching candidates")
    top_match: Optional[FaceSearchResultItemDto] = Field(default=None, description="Top matching candidate if above threshold")
    query_face: Optional[FaceItemDto] = Field(default=None, description="Query face metadata")
    processing_time_ms: float = Field(description="Processing latency in milliseconds")


# ── 4. Liveness Detection Schemas ───────────────────────────────────────────

class FaceLivenessRequest(BaseModel):
    image_base64: str = Field(description="Camera face image for anti-spoofing analysis")
    detector: FaceDetectorType = Field(default=FaceDetectorType.SCRFD)


class FaceLivenessResponse(BaseModel):
    is_live: bool = Field(description="Real human face verification verdict")
    confidence: float = Field(description="Confidence score [0.0 - 1.0]")
    decision: LivenessDecision = Field(description="Decision: REAL, FAKE, UNCERTAIN")
    detected_box: Optional[FaceBoxDto] = Field(default=None)
    processing_time_ms: float = Field(description="Processing latency in milliseconds")


# ── 5. Full Attribute Analysis Schemas ───────────────────────────────────────

class FaceAnalyzeRequest(BaseModel):
    image_base64: str = Field(description="Face image for comprehensive analysis")
    detector: FaceDetectorType = Field(default=FaceDetectorType.SCRFD)
    include_attributes: bool = Field(default=True, description="Analyze demographics, age, gender, emotion")
    include_headpose: bool = Field(default=True, description="Estimate 3D head pose angles")
    include_liveness: bool = Field(default=False, description="Evaluate anti-spoofing")
    include_quality: bool = Field(default=True, description="Evaluate eDifFIQA quality score")


class FaceAnalyzeResponse(BaseModel):
    faces: List[FaceItemDto] = Field(default_factory=list)
    total_faces: int = Field(description="Total detected face count")
    processing_time_ms: float = Field(description="Processing latency in milliseconds")


# ── 6. Anonymization / Privacy Schemas ──────────────────────────────────────

class FaceAnonymizeRequest(BaseModel):
    image_base64: str = Field(description="Input image containing human faces to blur")
    method: FaceAnonymizeMethod = Field(default=FaceAnonymizeMethod.PIXELATE, description="Anonymization blurring method")
    blur_strength: float = Field(default=3.0, description="Blur strength or pixel block size")
    detector: FaceDetectorType = Field(default=FaceDetectorType.SCRFD)


class FaceAnonymizeResponse(BaseModel):
    anonymized_image_base64: str = Field(description="Anonymized output image as Base64 string")
    faces_anonymized: int = Field(description="Count of anonymized faces")
    method: FaceAnonymizeMethod = Field(description="Applied anonymization method")
    processing_time_ms: float = Field(description="Processing latency in milliseconds")


# ── 7. Classroom Wide-Angle Detection Schemas ────────────────────────────────

class ClassroomFaceItemDto(BaseModel):
    """Face representation within a classroom spatial zone."""
    face: FaceItemDto
    roi_type: ClassroomROIType = Field(default=ClassroomROIType.STUDENT, description="Spatial zone: TEACHER or STUDENT")
    matched_identity_id: Optional[str] = Field(default=None, description="Matched student or teacher ID")
    matched_name: Optional[str] = Field(default=None, description="Full name of person")
    similarity: Optional[float] = Field(default=None, description="Cosine similarity with enrolled profile")
    is_registered: bool = Field(default=False, description="Whether face matched enrolled database")


class ClassroomDetectRequest(BaseModel):
    """Classroom attendance request for panoramic 40+ faces photo."""
    image_base64: str = Field(description="Wide-angle panoramic classroom image")
    teacher_roi_boundary_y: float = Field(
        default=0.35,
        description="Y-ratio boundary separating Podium (top) from Student desks (bottom) [0.0 - 1.0]"
    )
    detector: FaceDetectorType = Field(default=FaceDetectorType.SCRFD)
    recognizer: FaceRecognizerType = Field(default=FaceRecognizerType.ADAFACE_IR50)
    min_confidence: float = Field(default=0.45, description="Face confidence threshold for crowded scenes")
    min_quality: float = Field(default=0.30, description="Minimum quality score threshold")
    top_k: int = Field(default=1, description="Max matches per face")
    threshold: float = Field(default=0.60, description="Recognition decision threshold")


class ClassroomDetectResponse(BaseModel):
    """Classroom attendance response."""
    total_detected: int = Field(description="Total face count detected")
    teacher_faces: List[ClassroomFaceItemDto] = Field(default_factory=list, description="Faces detected in Podium zone")
    student_faces: List[ClassroomFaceItemDto] = Field(default_factory=list, description="Faces detected in Student zone")
    processing_time_ms: float = Field(description="Processing latency in milliseconds")


# ── 8. Visitor Dynamic TTL Schemas ──────────────────────────────────────────

class VisitorRegisterRequest(BaseModel):
    """Register temporary visitor embedding with TTL."""
    visitor_id: str = Field(description="Unique visitor ID")
    name: str = Field(description="Visitor full name")
    image_base64: Optional[str] = Field(default=None, description="Face image for embedding extraction")
    embedding: Optional[List[float]] = Field(default=None, description="Direct 512-D embedding vector")
    valid_from: Optional[str] = Field(default=None, description="Validity start time (ISO 8601)")
    valid_to: Optional[str] = Field(default=None, description="Validity expiration time (ISO 8601)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Visitor metadata dictionary")


class VisitorRegisterResponse(BaseModel):
    visitor_id: str
    status: VisitorStatus
    registered_at: str
    expires_at: Optional[str] = None
    message: str


class VisitorRemoveResponse(BaseModel):
    visitor_id: str
    removed: bool
    message: str


# ── 9. Face Enrollment & Verification Schemas ───────────────────────────────

class FaceEnrollRequest(BaseModel):
    """Enrollment face quality evaluation and 512D embedding extraction."""
    image_base64: str = Field(description="Face image as Base64 string")
    angle_type: str = Field(default="straight", description="Required pose angle: straight, left, right")
    min_quality: float = Field(default=0.80, description="Minimum eDifFIQA quality score threshold")


class FaceEnrollResponse(BaseModel):
    """Enrollment evaluation result with 512-D embedding."""
    is_valid: bool = Field(description="Whether face meets quality and pose angle criteria")
    quality_score: float = Field(description="eDifFIQA quality score [0.0 - 1.0]")
    angle_matched: bool = Field(description="Whether head pose yaw matches requested turn")
    feedback_code: FaceFeedbackCode = Field(description="Standardized Enum Feedback Code from AI Engine")
    feedback_message: str = Field(default="", description="Localized feedback message based on client language")
    head_pose: Optional[HeadPoseDto] = Field(default=None, description="3D head pose angles (Pitch, Yaw, Roll)")
    face_state: Optional[FaceStateDto] = Field(default=None, description="Occlusion attributes (mask, glasses)")
    bbox: Optional[FaceBoxDto] = Field(default=None, description="Bounding box coordinates")
    landmarks: List[LandmarkPointDto] = Field(default_factory=list, description="5 canonical facial landmarks")
    embedding: Optional[List[float]] = Field(default=None, description="512-D L2-normalized embedding vector")
    processing_time_ms: float = Field(default=0.0, description="Processing latency in milliseconds")


# ── 10. Surveillance Stream Schemas ──────────────────────────────────────────

class SurveillanceRecognizeRequest(BaseModel):
    """CCTV Surveillance face recognition and feature extraction."""
    image_base64: str = Field(description="CCTV frame image as Base64 string")
    min_confidence: float = Field(default=0.30, description="Minimum detection confidence threshold")
    min_quality: float = Field(default=0.20, description="Minimum quality score threshold")
    max_faces: int = Field(default=5, description="Maximum faces to process")
    select_largest: bool = Field(default=True, description="Prioritize largest face in frame")


class SurveillanceFaceItemDto(BaseModel):
    bbox: Dict[str, float] = Field(description="Bounding box dict x1, y1, x2, y2")
    norm_x1: float = Field(default=0.0)
    norm_y1: float = Field(default=0.0)
    norm_x2: float = Field(default=0.0)
    norm_y2: float = Field(default=0.0)
    norm_w: float = Field(default=0.0)
    norm_h: float = Field(default=0.0)
    confidence: float = Field(default=1.0)
    quality_score: float = Field(default=0.0)
    yaw: float = Field(default=0.0)
    pitch: float = Field(default=0.0)
    roll: float = Field(default=0.0)
    landmarks: List[Dict[str, float]] = Field(default_factory=list)
    embedding: Optional[List[float]] = Field(default=None)


class SurveillanceRecognizeResponse(BaseModel):
    faces: List[SurveillanceFaceItemDto] = Field(default_factory=list)
    total_faces: int = Field(default=0)
    image_width: int = Field(default=0)
    image_height: int = Field(default=0)
    processing_time_ms: float = Field(default=0.0)
