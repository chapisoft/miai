"""
Homography Perspective Transformation Module.
Aligns skewed, rotated, or angled camera photos to a 1:1 rectangular document template.
"""

from typing import List, Tuple
import numpy as np


class HomographyTransformer:
    """Calculates perspective transform matrix and rectifies angled document photos."""

    @staticmethod
    def get_perspective_matrix(
        source_points: List[Tuple[float, float]],
        target_points: List[Tuple[float, float]]
    ) -> np.ndarray:
        """
        Calculates 3x3 homography perspective transform matrix H
        such that: target = H * source
        """
        if len(source_points) != 4 or len(target_points) != 4:
            raise ValueError("Bắt buộc phải có đúng 4 điểm góc (Top-Left, Top-Right, Bottom-Right, Bottom-Left)")

        # Direct linear transformation (DLT) or OpenCV getPerspectiveTransform
        a_matrix = []
        b_vector = []

        for (x, y), (u, v) in zip(source_points, target_points):
            a_matrix.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
            b_vector.append(u)
            a_matrix.append([0, 0, 0, x, y, 1, -v * x, -v * y])
            b_vector.append(v)

        a_mat = np.array(a_matrix, dtype=np.float32)
        b_vec = np.array(b_vector, dtype=np.float32)

        # Solve Ah = b
        h_vec = np.linalg.lstsq(a_mat, b_vec, rcond=None)[0]
        h_matrix = np.append(h_vec, 1.0).reshape(3, 3)
        return h_matrix

    @classmethod
    def transform_point(cls, point: Tuple[float, float], matrix: np.ndarray) -> Tuple[float, float]:
        """Applies homography transformation to a single 2D point."""
        x, y = point
        vec = np.array([x, y, 1.0], dtype=np.float32)
        res = np.dot(matrix, vec)
        if res[2] != 0:
            return float(res[0] / res[2]), float(res[1] / res[2])
        return float(res[0]), float(res[1])
