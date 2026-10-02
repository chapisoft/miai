"""
Face Biometrics, eKYC, Liveness, and Privacy API Endpoints (V1).
Powered by UniFace Engine.
"""

from fastapi import APIRouter, Depends
from core.constants import ErrorCode, FaceFeedbackCode
from core.responses import ApiResponse
from api.dependencies import get_current_user
from schemas.face import (
    FaceDetectRequest,
    FaceDetectResponse,
    FaceCompareRequest,
    FaceCompareResponse,
    FaceSearchRequest,
    FaceSearchResponse,
    FaceLivenessRequest,
    FaceLivenessResponse,
    FaceAnalyzeRequest,
    FaceAnalyzeResponse,
    FaceAnonymizeRequest,
    FaceAnonymizeResponse,
    ClassroomDetectRequest,
    ClassroomDetectResponse,
    VisitorRegisterRequest,
    VisitorRegisterResponse,
    VisitorRemoveResponse,
    FaceEnrollRequest,
    FaceEnrollResponse,
    SurveillanceRecognizeRequest,
    SurveillanceRecognizeResponse,
)
from engines.face.pipeline import FaceEngineFacade

router = APIRouter(prefix="/face", tags=["Face Biometrics & Identity (UniFace)"])


@router.post(
    "/detect",
    response_model=ApiResponse[FaceDetectResponse],
    summary="Face and 5-point landmark detection",
)
async def detect_faces(
    request: FaceDetectRequest,
    current_user: dict = Depends(get_current_user),
) -> ApiResponse[FaceDetectResponse]:
    """Detect faces in image with bounding boxes and 5 canonical facial landmarks."""
    result = FaceEngineFacade.detect_faces(request)
    return ApiResponse.success(data=result, message=ErrorCode.SUCCESS.value)


@router.post(
    "/compare",
    response_model=ApiResponse[FaceCompareResponse],
    summary="1:1 eKYC face identity verification",
)
async def compare_faces(
    request: FaceCompareRequest,
    current_user: dict = Depends(get_current_user),
) -> ApiResponse[FaceCompareResponse]:
    """1:1 face verification between ID card/passport photo and selfie image."""
    result = FaceEngineFacade.compare_faces(request)
    msg = "VERIFICATION_MATCHED" if result.is_same_person else "VERIFICATION_MISMATCH"
    return ApiResponse.success(data=result, message=msg)


@router.post(
    "/search",
    response_model=ApiResponse[FaceSearchResponse],
    summary="1:N face search and attendance identification",
)
async def search_face(
    request: FaceSearchRequest,
    current_user: dict = Depends(get_current_user),
) -> ApiResponse[FaceSearchResponse]:
    """1:N face identification for attendance and VIP recognition."""
    result = FaceEngineFacade.search_face(request)
    return ApiResponse.success(data=result, message=ErrorCode.SUCCESS.value)


@router.post(
    "/liveness",
    response_model=ApiResponse[FaceLivenessResponse],
    summary="Anti-spoofing and presentation attack detection",
)
async def check_liveness(
    request: FaceLivenessRequest,
    current_user: dict = Depends(get_current_user),
) -> ApiResponse[FaceLivenessResponse]:
    """Evaluates whether face is live or a presentation attack (print, screen, replay)."""
    result = FaceEngineFacade.check_liveness(request)
    msg = "LIVENESS_CONFIRMED" if result.is_live else "SPOOF_ATTACK_DETECTED"
    return ApiResponse.success(data=result, message=msg)


@router.post(
    "/analyze",
    response_model=ApiResponse[FaceAnalyzeResponse],
    summary="Comprehensive face attributes, demographics and pose analysis",
)
async def analyze_face(
    request: FaceAnalyzeRequest,
    current_user: dict = Depends(get_current_user),
) -> ApiResponse[FaceAnalyzeResponse]:
    """Analyzes face quality, 3D head pose, age, gender, emotion, and occlusion state."""
    result = FaceEngineFacade.analyze_face(request)
    return ApiResponse.success(data=result, message=ErrorCode.SUCCESS.value)


@router.post(
    "/anonymize",
    response_model=ApiResponse[FaceAnonymizeResponse],
    summary="Privacy anonymization and face blurring (PII Protection)",
)
async def anonymize_faces(
    request: FaceAnonymizeRequest,
    current_user: dict = Depends(get_current_user),
) -> ApiResponse[FaceAnonymizeResponse]:
    """Anonymizes faces in image for privacy protection compliance."""
    result = FaceEngineFacade.anonymize_faces(request)
    return ApiResponse.success(data=result, message=ErrorCode.SUCCESS.value)


@router.post(
    "/classroom-detect",
    response_model=ApiResponse[ClassroomDetectResponse],
    summary="Panoramic classroom attendance detection and spatial partitioning",
)
async def detect_classroom_attendance(
    request: ClassroomDetectRequest,
    current_user: dict = Depends(get_current_user),
) -> ApiResponse[ClassroomDetectResponse]:
    """Automated attendance verification from classroom panoramic camera with ROI spatial analysis."""
    result = FaceEngineFacade.detect_classroom_faces(request)
    return ApiResponse.success(data=result, message=ErrorCode.SUCCESS.value)


@router.post(
    "/visitor/register",
    response_model=ApiResponse[VisitorRegisterResponse],
    summary="Temporary visitor registration with TTL validity",
)
async def register_visitor(
    request: VisitorRegisterRequest,
    current_user: dict = Depends(get_current_user),
) -> ApiResponse[VisitorRegisterResponse]:
    """Registers visitor face embedding in memory with time-to-live expiration."""
    result = FaceEngineFacade.register_visitor(request)
    return ApiResponse.success(data=result, message=ErrorCode.SUCCESS.value)


@router.delete(
    "/visitor/{visitor_id}",
    response_model=ApiResponse[VisitorRemoveResponse],
    summary="Remove temporary visitor from in-memory cache",
)
async def remove_visitor(
    visitor_id: str,
    current_user: dict = Depends(get_current_user),
) -> ApiResponse[VisitorRemoveResponse]:
    """Removes visitor face embedding from in-memory cache."""
    result = FaceEngineFacade.remove_visitor(visitor_id)
    return ApiResponse.success(data=result, message=ErrorCode.SUCCESS.value)


@router.post(
    "/enroll",
    response_model=ApiResponse[FaceEnrollResponse],
    summary="Multi-angle eDifFIQA verification and 512-D embedding extraction for biometric enrollment",
)
async def enroll_face(
    request: FaceEnrollRequest,
    current_user: dict = Depends(get_current_user),
) -> ApiResponse[FaceEnrollResponse]:
    """
    Evaluates face image quality (eDifFIQA ISO/IEC 29794-5), head pose angle, occlusion,
    and extracts L2-normalized 512-D embedding for biometric profile registration.
    """
    result = FaceEngineFacade.enroll_face(request)
    return ApiResponse.success(data=result, message=result.feedback_code.value)


@router.post(
    "/surveillance",
    response_model=ApiResponse[SurveillanceRecognizeResponse],
    summary="CCTV surveillance stream face recognition and embedding extraction on GPU",
)
async def recognize_surveillance(
    request: SurveillanceRecognizeRequest,
    current_user: dict = Depends(get_current_user),
) -> ApiResponse[SurveillanceRecognizeResponse]:
    """Extracts faces, quality, pose, and 512-D embeddings from CCTV frame on GPU."""
    result = FaceEngineFacade.recognize_surveillance(request)
    return ApiResponse.success(data=result, message=ErrorCode.SUCCESS.value)
