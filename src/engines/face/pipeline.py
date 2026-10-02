"""
Face Engine Facade Pipeline.
Unified high-level orchestrator coordinating detection, recognition, quality, liveness, attributes and privacy.
"""

import time
from typing import List, Optional, Tuple, Any
import numpy as np
from core.constants import (
    FaceDetectorType,
    FaceRecognizerType,
    FaceAnonymizeMethod,
    LivenessDecision,
    ErrorCode,
    ClassroomROIType,
    VisitorStatus,
    FaceFeedbackCode,
)
from core.exceptions import FaceBiometricsException
from core.config import settings
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
    ClassroomFaceItemDto,
    VisitorRegisterRequest,
    VisitorRegisterResponse,
    VisitorRemoveResponse,
    FaceEnrollRequest,
    FaceEnrollResponse,
    FaceItemDto,
    FaceBoxDto,
)
from engines.face.utils import decode_image, encode_image_base64, map_uniface_to_dto
from core.i18n import get_message
from engines.face.detector import FaceDetector
from engines.face.recognizer import FaceRecognizer
from engines.face.liveness import FaceLivenessChecker
from engines.face.quality import FaceQualityScorer
from engines.face.attributes import FaceAttributesAnalyzer
from engines.face.anonymizer import FaceAnonymizer
from engines.face.vector_matcher import VectorMatcher


class FaceEngineFacade:
    """
    Unified entrypoint for all Face Analysis and Biometrics operations.
    """

    @classmethod
    def detect_faces(cls, request: FaceDetectRequest) -> FaceDetectResponse:
        """
        Executes face detection and returns bounding boxes with landmarks.
        """
        start_time = time.perf_counter()
        image_np = decode_image(request.image_base64)
        faces = FaceDetector.detect(
            image_np,
            detector_type=request.detector,
            min_confidence=request.min_confidence,
        )

        dtos = [map_uniface_to_dto(f) for f in faces]
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return FaceDetectResponse(
            faces=dtos,
            total_faces=len(dtos),
            processing_time_ms=round(elapsed_ms, 2),
        )

    @classmethod
    def compare_faces(cls, request: FaceCompareRequest) -> FaceCompareResponse:
        """
        Executes 1:1 biometric identity comparison (eKYC).
        Validates quality, checks liveness, extracts embeddings and matches cosine similarity.
        """
        start_time = time.perf_counter()

        target_img = decode_image(request.image_base64_target)
        source_img = decode_image(request.image_base64_source)

        # 1. Detect faces in target (ID/Card)
        target_faces = FaceDetector.detect(target_img, detector_type=request.detector)
        if not target_faces:
            raise FaceBiometricsException(
                message="NO_FACE_TARGET",
                error_code=ErrorCode.FACE_DETECTION_ERROR,
            )
        target_face = target_faces[0]

        # 2. Detect faces in source (Camera/Selfie)
        source_faces = FaceDetector.detect(source_img, detector_type=request.detector)
        if not source_faces:
            raise FaceBiometricsException(
                message="NO_FACE_SOURCE",
                error_code=ErrorCode.FACE_DETECTION_ERROR,
            )
        source_face = source_faces[0]

        # 3. Assess Quality
        target_quality = FaceQualityScorer.assess_quality(target_img, target_face.landmarks)
        source_quality = FaceQualityScorer.assess_quality(source_img, source_face.landmarks)

        # 4. Anti-Spoofing Check
        source_is_live = True
        source_liveness_score = 1.0
        if request.check_liveness:
            source_is_live, source_liveness_score, decision = FaceLivenessChecker.check_liveness(
                source_img, source_face.bbox, threshold=settings.FACE_LIVENESS_THRESHOLD
            )
            if not source_is_live:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return FaceCompareResponse(
                    is_same_person=False,
                    similarity=0.0,
                    threshold=settings.FACE_SIMILARITY_THRESHOLD,
                    target_quality=target_quality,
                    source_quality=source_quality,
                    source_is_live=False,
                    source_liveness_score=source_liveness_score,
                    processing_time_ms=round(elapsed_ms, 2),
                )

        # 5. Extract Embeddings
        target_emb = FaceRecognizer.extract_embedding(
            target_img, target_face.landmarks, recognizer_type=request.recognizer
        )
        source_emb = FaceRecognizer.extract_embedding(
            source_img, source_face.landmarks, recognizer_type=request.recognizer
        )

        # 6. Compare
        threshold = settings.FACE_SIMILARITY_THRESHOLD
        is_same, similarity = FaceRecognizer.compare(target_emb, source_emb, threshold=threshold)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return FaceCompareResponse(
            is_same_person=is_same,
            similarity=round(similarity, 4),
            threshold=threshold,
            target_quality=round(target_quality, 4),
            source_quality=round(source_quality, 4),
            source_is_live=source_is_live,
            source_liveness_score=round(source_liveness_score, 4),
            processing_time_ms=round(elapsed_ms, 2),
        )

    @classmethod
    def search_face(cls, request: FaceSearchRequest) -> FaceSearchResponse:
        """
        Executes 1:N identity search across registered vectors.
        """
        start_time = time.perf_counter()
        image_np = decode_image(request.image_base64)

        faces = FaceDetector.detect(image_np, detector_type=request.detector)
        if not faces:
            raise FaceBiometricsException(
                message="NO_FACE_SEARCH",
                error_code=ErrorCode.FACE_DETECTION_ERROR,
            )

        query_face = faces[0]
        query_emb = FaceRecognizer.extract_embedding(
            image_np, query_face.landmarks, recognizer_type=request.recognizer
        )

        matches = VectorMatcher.search(
            query_emb,
            top_k=request.top_k,
            threshold=request.threshold,
        )

        top_match = matches[0] if matches else None
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return FaceSearchResponse(
            matches=matches,
            top_match=top_match,
            query_face=map_uniface_to_dto(query_face),
            processing_time_ms=round(elapsed_ms, 2),
        )

    @classmethod
    def check_liveness(cls, request: FaceLivenessRequest) -> FaceLivenessResponse:
        """
        Evaluates liveness / anti-spoofing for a face.
        """
        start_time = time.perf_counter()
        image_np = decode_image(request.image_base64)

        faces = FaceDetector.detect(image_np, detector_type=request.detector)
        if not faces:
            raise FaceBiometricsException(
                message="NO_FACE_LIVENESS",
                error_code=ErrorCode.FACE_DETECTION_ERROR,
            )

        face = faces[0]
        is_live, confidence, decision = FaceLivenessChecker.check_liveness(
            image_np, face.bbox, threshold=settings.FACE_LIVENESS_THRESHOLD
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        b = face.bbox
        bbox_dto = FaceBoxDto(
            x1=float(b[0]), y1=float(b[1]), x2=float(b[2]), y2=float(b[3]),
            confidence=float(face.confidence)
        )

        return FaceLivenessResponse(
            is_live=is_live,
            confidence=round(confidence, 4),
            decision=decision,
            detected_box=bbox_dto,
            processing_time_ms=round(elapsed_ms, 2),
        )

    @classmethod
    def analyze_face(cls, request: FaceAnalyzeRequest) -> FaceAnalyzeResponse:
        """
        Performs full multidimensional analysis (quality, liveness, demographics, pose, states).
        """
        start_time = time.perf_counter()
        image_np = decode_image(request.image_base64)

        faces = FaceDetector.detect(image_np, detector_type=request.detector)
        results: List[FaceItemDto] = []

        for face in faces:
            dto = map_uniface_to_dto(face)

            if request.include_quality:
                dto.quality_score = FaceQualityScorer.assess_quality(image_np, face.landmarks)

            if request.include_liveness:
                is_live, conf, _ = FaceLivenessChecker.check_liveness(image_np, face.bbox)
                dto.is_live = is_live
                dto.liveness_score = conf

            if request.include_headpose:
                dto.head_pose = FaceAttributesAnalyzer.estimate_head_pose(image_np, face.bbox)

            if request.include_attributes:
                demo = FaceAttributesAnalyzer.analyze_demographics(image_np, face)
                if demo:
                    dto.gender = demo.get("gender")
                    dto.race = demo.get("race")
                state = FaceAttributesAnalyzer.analyze_state(image_np, face)
                if state:
                    dto.face_state = state

            results.append(dto)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return FaceAnalyzeResponse(
            faces=results,
            total_faces=len(results),
            processing_time_ms=round(elapsed_ms, 2),
        )

    @classmethod
    def anonymize_faces(cls, request: FaceAnonymizeRequest) -> FaceAnonymizeResponse:
        """
        Anonymizes human faces to protect personal identity.
        """
        start_time = time.perf_counter()
        image_np = decode_image(request.image_base64)

        faces = FaceDetector.detect(image_np, detector_type=request.detector)
        _, anonymized_b64, count = FaceAnonymizer.anonymize_image(
            image_np,
            faces=faces,
            method=request.method,
            blur_strength=request.blur_strength,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return FaceAnonymizeResponse(
            anonymized_image_base64=anonymized_b64,
            faces_anonymized=count,
            method=request.method,
            processing_time_ms=round(elapsed_ms, 2),
        )

    @classmethod
    def detect_classroom_faces(cls, request: ClassroomDetectRequest) -> ClassroomDetectResponse:
        """
        Executes wide-angle classroom face detection (40+ faces) and spatial ROI segregation.
        Splits detections into Teacher ROI (Podium area) vs Student ROI (Desk rows).
        Matches embeddings against registered roster in memory.
        """
        start_time = time.perf_counter()
        image_np = decode_image(request.image_base64)
        img_h, img_w = image_np.shape[:2]

        # 1. Detect all faces in wide-angle classroom photo
        faces = FaceDetector.detect(
            image_np,
            detector_type=request.detector,
            min_confidence=request.min_confidence,
        )

        teacher_items: List[ClassroomFaceItemDto] = []
        student_items: List[ClassroomFaceItemDto] = []

        boundary_y_pixels = img_h * request.teacher_roi_boundary_y

        for face in faces:
            dto = map_uniface_to_dto(face)

            # Compute quality score
            dto.quality_score = FaceQualityScorer.assess_quality(image_np, face.landmarks)

            # Extract embedding if quality is acceptable
            matched_id = None
            matched_name = None
            similarity = None
            is_registered = False

            if dto.quality_score >= request.min_quality:
                try:
                    emb = FaceRecognizer.extract_embedding(
                        image_np, face.landmarks, recognizer_type=request.recognizer
                    )
                    dto.embedding = emb.tolist() if hasattr(emb, "tolist") else list(emb)

                    # Match against roster
                    matches = VectorMatcher.search(
                        emb, top_k=request.top_k, threshold=request.threshold
                    )
                    if matches:
                        top = matches[0]
                        matched_id = top.identity_id
                        matched_name = top.name
                        similarity = top.similarity
                        is_registered = True
                except Exception:
                    pass

            # Classify ROI based on vertical center coordinate
            bbox = face.bbox
            center_y = (bbox[1] + bbox[3]) / 2.0

            if center_y <= boundary_y_pixels:
                roi_type = ClassroomROIType.TEACHER
                item = ClassroomFaceItemDto(
                    face=dto,
                    roi_type=roi_type,
                    matched_identity_id=matched_id,
                    matched_name=matched_name,
                    similarity=similarity,
                    is_registered=is_registered,
                )
                teacher_items.append(item)
            else:
                roi_type = ClassroomROIType.STUDENT
                item = ClassroomFaceItemDto(
                    face=dto,
                    roi_type=roi_type,
                    matched_identity_id=matched_id,
                    matched_name=matched_name,
                    similarity=similarity,
                    is_registered=is_registered,
                )
                student_items.append(item)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return ClassroomDetectResponse(
            total_detected=len(faces),
            teacher_faces=teacher_items,
            student_faces=student_items,
            processing_time_ms=round(elapsed_ms, 2),
        )

    @classmethod
    def register_visitor(cls, request: VisitorRegisterRequest) -> VisitorRegisterResponse:
        """
        Registers a temporary visitor embedding into the in-memory dynamic index with TTL.
        """
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # If embedding is provided directly
        if request.embedding:
            emb = np.array(request.embedding, dtype=np.float32)
        elif request.image_base64:
            image_np = decode_image(request.image_base64)
            faces = FaceDetector.detect(image_np)
            if not faces:
                raise FaceBiometricsException(
                    message="No face detected in visitor registration image",
                    error_code=ErrorCode.FACE_DETECTION_ERROR,
                )
            emb = FaceRecognizer.extract_embedding(image_np, faces[0].landmarks)
        else:
            raise FaceBiometricsException(
                message="Either image_base64 or embedding vector must be provided",
                error_code=ErrorCode.INVALID_PARAMETERS,
            )

        status = VectorMatcher.register_visitor(
            visitor_id=request.visitor_id,
            embedding=emb,
            name=request.name,
            valid_from=request.valid_from,
            valid_to=request.valid_to,
            metadata=request.metadata,
        )

        return VisitorRegisterResponse(
            visitor_id=request.visitor_id,
            status=status,
            registered_at=now_str,
            expires_at=request.valid_to,
            message=get_message("VISITOR_REGISTERED"),
        )

    @classmethod
    def remove_visitor(cls, visitor_id: str) -> VisitorRemoveResponse:
        """
        Removes a temporary visitor from the in-memory dynamic index.
        """
        removed = VectorMatcher.remove_visitor(visitor_id)
        msg = get_message("VISITOR_REMOVED") if removed else get_message("VISITOR_NOT_FOUND")
        return VisitorRemoveResponse(
            visitor_id=visitor_id,
            removed=removed,
            message=msg,
        )

    @classmethod
    def enroll_face(cls, request: FaceEnrollRequest) -> FaceEnrollResponse:
        """
        Evaluates face quality (eDifFIQA), verifies head pose angle, checks occlusion,
        and extracts 512-D L2-normalized embedding for registration.
        100% Multilingual Zero-Hardcode with FaceFeedbackCode.
        """
        start_time = time.perf_counter()
        image_np = decode_image(request.image_base64)

        faces = FaceDetector.detect(image_np)
        if not faces:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            fb_code = FaceFeedbackCode.FACE_NOT_DETECTED
            return FaceEnrollResponse(
                is_valid=False,
                quality_score=0.0,
                angle_matched=False,
                feedback_code=fb_code,
                feedback_message=get_message(fb_code.value),
                processing_time_ms=round(elapsed_ms, 2),
            )

        if len(faces) > 1:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            fb_code = FaceFeedbackCode.MULTIPLE_FACES_DETECTED
            return FaceEnrollResponse(
                is_valid=False,
                quality_score=0.0,
                angle_matched=False,
                feedback_code=fb_code,
                feedback_message=get_message(fb_code.value),
                processing_time_ms=round(elapsed_ms, 2),
            )

        face = faces[0]
        dto = map_uniface_to_dto(face)

        # 1. Quality Assessment with eDifFIQA
        quality_score = FaceQualityScorer.assess_quality(image_np, face.landmarks)

        # 2. Estimate 3D Head Pose (Pitch, Yaw, Roll)
        head_pose = FaceAttributesAnalyzer.estimate_head_pose(image_np, face.bbox)

        # 3. Analyze face occlusions (mask, glasses)
        face_state = FaceAttributesAnalyzer.analyze_state(image_np, face)

        # 4. Check occlusions
        if face_state and getattr(face_state, "has_mask", False):
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            fb_code = FaceFeedbackCode.MASK_DETECTED
            return FaceEnrollResponse(
                is_valid=False,
                quality_score=round(quality_score, 3),
                angle_matched=False,
                feedback_code=fb_code,
                feedback_message=get_message(fb_code.value),
                head_pose=head_pose,
                face_state=face_state,
                bbox=dto.bbox,
                landmarks=dto.landmarks,
                processing_time_ms=round(elapsed_ms, 2),
            )

        # 5. Validate Head Pose Yaw / Pitch matching enrollment stage
        angle_type = (request.angle_type or "straight").lower()
        angle_matched = True
        feedback_code = FaceFeedbackCode.ENROLL_SUCCESS

        if head_pose:
            yaw = head_pose.yaw
            pitch = head_pose.pitch

            if abs(pitch) > 22.0:
                angle_matched = False
                feedback_code = FaceFeedbackCode.HEAD_PITCH_UNBALANCED
            elif angle_type == "straight":
                if abs(yaw) > 14.0:
                    angle_matched = False
                    feedback_code = FaceFeedbackCode.HEAD_TURN_STRAIGHT_REQUIRED
            elif angle_type == "left":
                if yaw > -8.0:
                    angle_matched = False
                    feedback_code = FaceFeedbackCode.HEAD_TURN_LEFT_REQUIRED
                elif yaw < -35.0:
                    angle_matched = False
                    feedback_code = FaceFeedbackCode.HEAD_TURN_LEFT_TOO_DEEP
            elif angle_type == "right":
                if yaw < 8.0:
                    angle_matched = False
                    feedback_code = FaceFeedbackCode.HEAD_TURN_RIGHT_REQUIRED
                elif yaw > 35.0:
                    angle_matched = False
                    feedback_code = FaceFeedbackCode.HEAD_TURN_RIGHT_TOO_DEEP

        # 6. Quality threshold check
        is_quality_pass = quality_score >= request.min_quality
        is_valid = is_quality_pass and angle_matched

        if not is_quality_pass and angle_matched:
            feedback_code = FaceFeedbackCode.QUALITY_SCORE_TOO_LOW

        embedding_list = None
        if is_valid:
            try:
                emb = FaceRecognizer.extract_embedding(image_np, face.landmarks)
                embedding_list = emb.tolist()
                feedback_code = FaceFeedbackCode.ENROLL_SUCCESS
            except Exception:
                is_valid = False
                feedback_code = FaceFeedbackCode.EXTRACTION_ERROR

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return FaceEnrollResponse(
            is_valid=is_valid,
            quality_score=round(quality_score, 3),
            angle_matched=angle_matched,
            feedback_code=feedback_code,
            feedback_message=get_message(feedback_code.value),
            head_pose=head_pose,
            face_state=face_state,
            bbox=dto.bbox,
            landmarks=dto.landmarks,
            embedding=embedding_list,
            processing_time_ms=round(elapsed_ms, 2),
        )

