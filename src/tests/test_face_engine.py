"""
Unit & Integration Tests for Face Analysis Engine (UniFace Integration).
Covers detection, recognition, similarity calculation, liveness, quality, anonymization, and API endpoints.
"""

import base64
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from main import app
from core.constants import FaceDetectorType, FaceRecognizerType, FaceAnonymizeMethod, ErrorCode
from core.guardrails import Guardrails
from core.exceptions import FaceBiometricsException
from schemas.face import (
    FaceBoxDto,
    FaceDetectRequest,
    FaceCompareRequest,
    FaceAnonymizeRequest,
    FaceSearchRequest,
    FaceLivenessRequest,
)
from engines.face.utils import decode_image, encode_image_base64, map_uniface_to_dto
from engines.face.detector import FaceDetector
from engines.face.recognizer import FaceRecognizer
from engines.face.quality import FaceQualityScorer
from engines.face.liveness import FaceLivenessChecker
from engines.face.anonymizer import FaceAnonymizer
from engines.face.vector_matcher import VectorMatcher
from engines.face.pipeline import FaceEngineFacade


@pytest.fixture
def sample_face_image_b64() -> str:
    """Creates a synthetic 200x200 BGR image with a face-like pattern."""
    img = np.ones((200, 200, 3), dtype=np.uint8) * 120
    # Draw oval face
    cv2.ellipse(img, (100, 100), (60, 80), 0, 0, 360, (200, 180, 160), -1)
    # Eyes
    cv2.circle(img, (75, 80), 8, (50, 50, 50), -1)
    cv2.circle(img, (125, 80), 8, (50, 50, 50), -1)
    # Nose
    cv2.line(img, (100, 90), (100, 110), (100, 100, 100), 3)
    # Mouth
    cv2.ellipse(img, (100, 135), (25, 10), 0, 0, 180, (80, 80, 180), 3)

    return encode_image_base64(img)


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)


# ── 1. Image Utils & Format Tests ───────────────────────────────────────────

def test_decode_and_encode_image(sample_face_image_b64):
    decoded = decode_image(sample_face_image_b64)
    assert isinstance(decoded, np.ndarray)
    assert decoded.shape == (200, 200, 3)

    re_encoded = encode_image_base64(decoded)
    assert isinstance(re_encoded, str)
    assert len(re_encoded) > 0


def test_decode_invalid_image():
    with pytest.raises(FaceBiometricsException) as exc_info:
        decode_image("invalid_base64_garbage!@#$")
    assert exc_info.value.error_code == ErrorCode.INVALID_PARAMETERS

    with pytest.raises(FaceBiometricsException):
        decode_image("")


# ── 2. Face Detector & Recognition Tests ────────────────────────────────────

def test_face_detector_initialization():
    detector = FaceDetector.get_detector(FaceDetectorType.SCRFD, confidence_threshold=0.5)
    assert detector is not None


def test_cosine_similarity_computation():
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    sim_identical = FaceRecognizer.compute_similarity(v1, v2)
    assert pytest.approx(sim_identical, 0.001) == 1.0

    sim_orthogonal = FaceRecognizer.compute_similarity(v1, v3)
    assert pytest.approx(sim_orthogonal, 0.001) == 0.0

    is_same, score = FaceRecognizer.compare(v1, v2, threshold=0.60)
    assert is_same is True
    assert pytest.approx(score, 0.001) == 1.0

    is_same_diff, score_diff = FaceRecognizer.compare(v1, v3, threshold=0.60)
    assert is_same_diff is False


# ── 3. Vector Matcher (1:N Search) Tests ────────────────────────────────────

def test_vector_matcher_registry_and_search():
    VectorMatcher.clear_all()
    assert VectorMatcher.get_count() == 0

    emb_alice = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    emb_bob = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    emb_charlie = np.array([0.8, 0.6, 0.0, 0.0], dtype=np.float32)

    VectorMatcher.register_identity("USER_01", emb_alice, name="Alice", metadata={"role": "ADMIN"})
    VectorMatcher.register_identity("USER_02", emb_bob, name="Bob", metadata={"role": "STAFF"})
    VectorMatcher.register_identity("USER_03", emb_charlie, name="Charlie", metadata={"role": "VIP"})

    assert VectorMatcher.get_count() == 3

    # Query with Alice-like embedding
    query_emb = np.array([0.99, 0.01, 0.0, 0.0], dtype=np.float32)
    matches = VectorMatcher.search(query_emb, top_k=2, threshold=0.50)

    assert len(matches) > 0
    assert matches[0].identity_id == "USER_01"
    assert matches[0].similarity > 0.90
    assert matches[0].name == "Alice"

    # Remove Bob
    assert VectorMatcher.remove_identity("USER_02") is True
    assert VectorMatcher.get_count() == 2


# ── 4. Quality & Liveness Tests ─────────────────────────────────────────────

def test_face_quality_assessment():
    dummy_img = np.zeros((112, 112, 3), dtype=np.uint8)
    dummy_landmarks = np.array([[38, 51], [73, 51], [56, 71], [41, 92], [70, 92]], dtype=np.float32)

    score = FaceQualityScorer.assess_quality(dummy_img, dummy_landmarks)
    assert 0.0 <= score <= 1.0


def test_face_liveness_assessment():
    dummy_img = np.zeros((150, 150, 3), dtype=np.uint8)
    dummy_bbox = [10, 10, 140, 140]

    is_live, conf, decision = FaceLivenessChecker.check_liveness(dummy_img, dummy_bbox)
    assert isinstance(is_live, bool)
    assert 0.0 <= conf <= 1.0
    assert decision in ["REAL", "FAKE", "UNCERTAIN"]


# ── 5. Anonymization & Privacy Tests ────────────────────────────────────────

def test_face_anonymization_methods():
    img = np.ones((100, 100, 3), dtype=np.uint8) * 150
    # Custom mock face box
    bbox = [10, 10, 80, 80]

    # Pixelate
    anon_np, b64_str, count = FaceAnonymizer.anonymize_image(
        img,
        faces=[{"bbox": bbox}],
        method=FaceAnonymizeMethod.PIXELATE,
    )
    assert anon_np.shape == (100, 100, 3)
    assert count == 1
    assert len(b64_str) > 0

    # Gaussian
    anon_gauss, _, _ = FaceAnonymizer.anonymize_image(
        img,
        faces=[{"bbox": bbox}],
        method=FaceAnonymizeMethod.GAUSSIAN,
    )
    assert anon_gauss.shape == (100, 100, 3)

    # Blackout
    anon_black, _, _ = FaceAnonymizer.anonymize_image(
        img,
        faces=[{"bbox": bbox}],
        method=FaceAnonymizeMethod.BLACKOUT,
    )
    # Target region should be black (0)
    assert np.all(anon_black[20:70, 20:70] == 0)


def test_guardrails_face_redaction_integration():
    img = np.ones((80, 80, 3), dtype=np.uint8) * 200
    redacted = Guardrails.redact_face_pii(img, faces=[[10, 10, 50, 50]], method="pixelate")
    assert redacted is not None
    assert redacted.shape == (80, 80, 3)


# ── 6. FastAPI Endpoints Integration Tests ──────────────────────────────────

def test_api_face_detect_empty_image(test_client):
    blank_img = np.zeros((100, 100, 3), dtype=np.uint8)
    b64 = encode_image_base64(blank_img)

    response = test_client.post(
        "/api/v1/face/detect",
        json={"image_base64": b64, "detector": "SCRFD", "min_confidence": 0.5},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["status"] == "SUCCESS"
    assert payload["data"]["total_faces"] == 0


def test_api_face_anonymize_endpoint(test_client):
    blank_img = np.zeros((100, 100, 3), dtype=np.uint8)
    b64 = encode_image_base64(blank_img)

    response = test_client.post(
        "/api/v1/face/anonymize",
        json={"image_base64": b64, "method": "pixelate"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["status"] == "SUCCESS"
    assert "anonymized_image_base64" in payload["data"]


def test_api_face_compare_no_face_fails(test_client):
    blank_img = np.zeros((100, 100, 3), dtype=np.uint8)
    b64 = encode_image_base64(blank_img)

    response = test_client.post(
        "/api/v1/face/compare",
        json={
            "image_base64_target": b64,
            "image_base64_source": b64,
            "detector": "SCRFD",
        },
    )
    # Should catch FaceBiometricsException and return 400
    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == 400
    assert payload["status"] == "ERROR"
    assert payload["errorCode"] == ErrorCode.FACE_DETECTION_ERROR.value


# ── 7. Classroom & Visitor TTL Tests ─────────────────────────────────────────

def test_visitor_ttl_and_auto_eviction():
    VectorMatcher.clear_all()
    assert VectorMatcher.get_count() == 0

    emb_perm = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    VectorMatcher.register_identity("STU_001", emb_perm, name="Hoc Sinh A")

    # Register visitor with expired TTL
    emb_vis_expired = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    VectorMatcher.register_visitor(
        visitor_id="VIS_EXP",
        embedding=emb_vis_expired,
        name="Khach Het Han",
        valid_from="2020-01-01T00:00:00Z",
        valid_to="2020-01-02T00:00:00Z",
    )

    # Register visitor with valid TTL
    emb_vis_valid = np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32)
    VectorMatcher.register_visitor(
        visitor_id="VIS_VAL",
        embedding=emb_vis_valid,
        name="Phu Huynh Dang Den",
        valid_from="2020-01-01T00:00:00Z",
        valid_to="2099-01-01T00:00:00Z",
    )

    assert VectorMatcher.get_permanent_count() == 1
    assert VectorMatcher.get_visitor_count() == 2

    # Evict expired explicitly
    evicted = VectorMatcher.auto_evict_expired()
    assert evicted >= 1
    assert VectorMatcher.get_visitor_count() == 1

    # Query with valid visitor embedding
    query_vis = np.array([0.0, 0.0, 0.99, 0.0], dtype=np.float32)
    matches = VectorMatcher.search(query_vis, top_k=2, threshold=0.50)
    assert len(matches) > 0
    assert matches[0].identity_id == "VIS_VAL"
    assert matches[0].metadata.get("is_visitor") is True

    # Remove visitor
    assert VectorMatcher.remove_visitor("VIS_VAL") is True
    assert VectorMatcher.get_visitor_count() == 0


def test_api_classroom_detect_endpoint(test_client):
    # Blank image with no face
    blank_img = np.zeros((400, 600, 3), dtype=np.uint8)
    b64 = encode_image_base64(blank_img)

    response = test_client.post(
        "/api/v1/face/classroom-detect",
        json={
            "image_base64": b64,
            "teacher_roi_boundary_y": 0.35,
            "min_confidence": 0.45,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["status"] == "SUCCESS"
    assert payload["data"]["total_detected"] == 0
    assert isinstance(payload["data"]["teacher_faces"], list)
    assert isinstance(payload["data"]["student_faces"], list)


def test_api_visitor_crud_endpoints(test_client):
    VectorMatcher.clear_all()

    # 1. Register visitor with raw embedding
    reg_response = test_client.post(
        "/api/v1/face/visitor/register",
        json={
            "visitor_id": "PARENT_101",
            "name": "Nguyen Van Phu Huynh",
            "embedding": [0.1] * 512,
            "valid_from": "2026-01-01T00:00:00Z",
            "valid_to": "2026-12-31T23:59:59Z",
            "metadata": {"student_id": "HS_001"},
        },
    )
    assert reg_response.status_code == 200
    reg_data = reg_response.json()
    assert reg_data["code"] == 200
    assert reg_data["data"]["visitor_id"] == "PARENT_101"
    assert reg_data["data"]["status"] == "APPROVED"

    # 2. Remove visitor
    del_response = test_client.delete("/api/v1/face/visitor/PARENT_101")
    assert del_response.status_code == 200
    del_data = del_response.json()
    assert del_data["code"] == 200
    assert del_data["data"]["removed"] is True

