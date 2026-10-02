"""
Face Recognizer & Feature Embedding Adapter for UniFace models (AdaFace, ArcFace, EdgeFace).
Extracts 512-dimensional L2-normalized vectors and computes Cosine Similarity.
"""

from typing import Dict, Any, Union, Tuple, Optional
import numpy as np
from core.constants import FaceRecognizerType, ErrorCode
from core.exceptions import FaceBiometricsException
from engines.face.utils import decode_image


class FaceRecognizer:
    """
    Manages Face Recognition models with cached instances and Cosine Similarity math.
    """

    _instances: Dict[str, Any] = {}

    @classmethod
    def get_recognizer(
        cls,
        recognizer_type: FaceRecognizerType = FaceRecognizerType.ADAFACE_IR50,
    ):
        """
        Retrieves or initializes a face recognizer instance.
        """
        key = recognizer_type.value
        if key in cls._instances:
            return cls._instances[key]

        try:
            from core.config import settings
            providers = [settings.FACE_EXECUTION_PROVIDER, "TensorrtExecutionProvider", "CPUExecutionProvider"]

            if recognizer_type == FaceRecognizerType.ADAFACE_IR50:
                from uniface.recognition import AdaFace
                recognizer = AdaFace(providers=providers)
            elif recognizer_type == FaceRecognizerType.ARCFACE_RESNET50:
                from uniface.recognition import ArcFace
                from uniface.constants import ArcFaceWeights
                recognizer = ArcFace(model_name=ArcFaceWeights.RESNET, providers=providers)
            elif recognizer_type == FaceRecognizerType.ARCFACE_MOBILENET:
                from uniface.recognition import ArcFace
                from uniface.constants import ArcFaceWeights
                recognizer = ArcFace(model_name=ArcFaceWeights.MNET, providers=providers)
            elif recognizer_type == FaceRecognizerType.EDGEFACE_XXS:
                from uniface.recognition import EdgeFace
                from uniface.constants import EdgeFaceWeights
                recognizer = EdgeFace(model_name=EdgeFaceWeights.XXS, providers=providers)
            else:
                from uniface.recognition import AdaFace
                recognizer = AdaFace(providers=providers)

            cls._instances[key] = recognizer
            return recognizer
        except Exception as e:
            raise FaceBiometricsException(
                message=f"Failed to initialize face recognizer model {recognizer_type.value}: {str(e)}",
                error_code=ErrorCode.FACE_RECOGNITION_ERROR,
                details={"recognizer_type": recognizer_type.value, "error": str(e)},
            )

    @classmethod
    def extract_embedding(
        cls,
        image_input: Union[str, bytes, np.ndarray],
        landmarks: Union[np.ndarray, list],
        recognizer_type: FaceRecognizerType = FaceRecognizerType.ADAFACE_IR50,
    ) -> np.ndarray:
        """
        Extracts L2-normalized 512-dimension embedding vector from face crop.
        """
        image_np = decode_image(image_input)
        if isinstance(landmarks, list):
            landmarks = np.array(landmarks, dtype=np.float32)

        recognizer = cls.get_recognizer(recognizer_type)
        try:
            embedding = recognizer.get_normalized_embedding(image_np, landmarks)
            # Ensure it is a 1D float32 numpy array
            embedding = np.asarray(embedding, dtype=np.float32).flatten()
            # Double check L2 normalization
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            return embedding
        except Exception as e:
            raise FaceBiometricsException(
                message=f"Failed to extract face embedding vector: {str(e)}",
                error_code=ErrorCode.FACE_RECOGNITION_ERROR,
                details={"error": str(e)},
            )

    @staticmethod
    def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Computes Cosine Similarity between two L2-normalized embeddings.
        Returns float in range [0.0, 1.0] (clamped for distance safety).
        """
        from uniface.face_utils import compute_similarity as uniface_sim
        try:
            score = float(uniface_sim(embedding1, embedding2, normalized=True))
            # Clamp between 0.0 and 1.0 for cosine similarity
            return max(0.0, min(1.0, score))
        except Exception:
            # Fallback pure numpy dot product
            dot = float(np.dot(embedding1, embedding2))
            norm1 = float(np.linalg.norm(embedding1))
            norm2 = float(np.linalg.norm(embedding2))
            if norm1 > 0 and norm2 > 0:
                sim = dot / (norm1 * norm2)
            else:
                sim = 0.0
            return max(0.0, min(1.0, sim))

    @classmethod
    def compare(
        cls,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
        threshold: float = 0.60,
    ) -> Tuple[bool, float]:
        """
        Checks if two embeddings belong to the same person.
        Returns (is_same_person, similarity_score).
        """
        similarity = cls.compute_similarity(embedding1, embedding2)
        is_same = similarity >= threshold
        return is_same, similarity
