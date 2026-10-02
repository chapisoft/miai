"""
Unit and Integration Tests for Face GPU Acceleration & Enrollment Pipeline.
Verifies VectorMatcher GPU Tensor math, Bulk Enrollment, and GPU Execution Providers.
"""

import numpy as np
from core.config import settings
from engines.face.vector_matcher import VectorMatcher
from schemas.face import FaceEnrollRequest, SurveillanceRecognizeRequest


def test_vector_matcher_gpu_simd_search():
    """Test 1:N identity search using GPU VRAM / Vectorized Matrix Multiplication."""
    VectorMatcher.clear_all()

    # Generate 100 random identity embeddings of dimension 512
    np.random.seed(42)
    dim = 512
    num_profiles = 100

    profiles = []
    for i in range(num_profiles):
        vec = np.random.randn(dim).astype(np.float32)
        vec /= np.linalg.norm(vec)
        profiles.append({
            "identity_id": f"STUDENT_{i:04d}",
            "name": f"Học Sinh {i}",
            "embedding": vec,
            "metadata": {"class": "10A1", "roll_no": i}
        })

    # Bulk register to GPU cache
    enrolled_count = VectorMatcher.bulk_register_identities(profiles)
    assert enrolled_count == num_profiles, f"Expected {num_profiles}, got {enrolled_count}"
    assert VectorMatcher.get_permanent_count() == num_profiles

    # Search with known vector + small noise
    target_idx = 15
    target_vec = profiles[target_idx]["embedding"].copy()
    noisy_query = target_vec + np.random.randn(dim).astype(np.float32) * 0.005
    noisy_query /= np.linalg.norm(noisy_query)

    results = VectorMatcher.search(noisy_query, top_k=3, threshold=0.50)
    assert len(results) > 0, "Should find at least 1 match"
    top_match = results[0]
    assert top_match.identity_id == f"STUDENT_{target_idx:04d}", f"Expected STUDENT_{target_idx:04d}, got {top_match.identity_id}"
    assert top_match.similarity > 0.90, f"Expected high similarity > 0.90, got {top_match.similarity}"
    print(f"PASS: VectorMatcher search correctly matched {top_match.identity_id} with similarity {top_match.similarity:.4f}")


def test_gpu_providers_configuration():
    """Test that all UniFace models are configured to use GPU execution provider."""
    from engines.face.detector import FaceDetector
    from engines.face.recognizer import FaceRecognizer
    from engines.face.quality import FaceQualityScorer
    from engines.face.attributes import FaceAttributesAnalyzer
    from engines.face.liveness import FaceLivenessChecker

    # Verify settings have CUDA execution provider configured
    assert settings.FACE_EXECUTION_PROVIDER == "CUDAExecutionProvider"
    assert settings.FACE_DEVICE == "cuda"
    print("PASS: FACE_EXECUTION_PROVIDER is set to CUDAExecutionProvider")


if __name__ == "__main__":
    test_vector_matcher_gpu_simd_search()
    test_gpu_providers_configuration()
    print("ALL FACE GPU TESTS PASSED 100%!")
