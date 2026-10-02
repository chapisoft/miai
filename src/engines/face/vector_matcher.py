"""
Vector Matcher & Similarity Search for Face Embeddings.
Supports 2-tier In-Memory fast index (Permanent & Visitor TTL) and Postgres pgvector integration.
"""

import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional, Union
import numpy as np
from core.constants import VisitorStatus, SubjectType
from schemas.face import FaceSearchResultItemDto


class VectorMatcher:
    """
    Manages identity vector registry and similarity search (1:N matching).
    Supports 2 partitions:
    1. PERMANENT_INDEX: Students, Teachers, Staff (long-term).
    2. VISITOR_DYNAMIC_INDEX: Visitors, Parents with TTL (time-to-live expiration).
    """

    # Thread-safe in-memory vector caches for high-speed Campus & Kiosk search
    _permanent_identities: Dict[str, Dict[str, Any]] = {}
    _visitor_identities: Dict[str, Dict[str, Any]] = {}


    @classmethod
    def register_visitor(
        cls,
        visitor_id: str,
        embedding: Union[np.ndarray, list],
        name: Optional[str] = None,
        valid_from: Optional[str] = None,
        valid_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VisitorStatus:
        """
        Stores a temporary visitor embedding vector with TTL validity window.
        """
        emb = np.asarray(embedding, dtype=np.float32).flatten()
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm

        now = datetime.now(timezone.utc)
        
        # Parse expiration timestamps if provided
        from_dt = None
        to_dt = None
        if valid_from:
            try:
                from_dt = datetime.fromisoformat(valid_from.replace("Z", "+00:00"))
            except Exception:
                pass
        if valid_to:
            try:
                to_dt = datetime.fromisoformat(valid_to.replace("Z", "+00:00"))
            except Exception:
                pass

        cls._visitor_identities[visitor_id] = {
            "identity_id": visitor_id,
            "name": name or visitor_id,
            "embedding": emb,
            "valid_from": from_dt,
            "valid_to": to_dt,
            "metadata": metadata or {},
            "subject_type": SubjectType.VISITOR.value,
            "created_at": now,
        }
        return VisitorStatus.APPROVED


    @classmethod
    def remove_visitor(cls, visitor_id: str) -> bool:
        """
        Explicitly removes a visitor identity.
        """
        if visitor_id in cls._visitor_identities:
            del cls._visitor_identities[visitor_id]
            return True
        return False

    @classmethod
    def auto_evict_expired(cls) -> int:
        """
        Evicts expired visitor embeddings from memory. Returns number of evicted items.
        """
        now = datetime.now(timezone.utc)
        expired_keys = []
        for vid, data in cls._visitor_identities.items():
            valid_to = data.get("valid_to")
            if valid_to and valid_to < now:
                expired_keys.append(vid)

        for vid in expired_keys:
            del cls._visitor_identities[vid]

        return len(expired_keys)

    @classmethod
    def get_count(cls) -> int:
        return len(cls._permanent_identities) + len(cls._visitor_identities)

    @classmethod
    def get_permanent_count(cls) -> int:
        return len(cls._permanent_identities)

    @classmethod
    def get_visitor_count(cls) -> int:
        return len(cls._visitor_identities)

    # GPU Acceleration State
    _matrix_dirty: bool = True
    _cached_matrix: Optional[np.ndarray] = None
    _cached_keys: List[str] = []
    _cached_gpu_tensor: Any = None
    _gpu_device: Optional[str] = None

    @classmethod
    def _sync_matrix_cache(cls) -> None:
        """Đồng bộ ma trận embedding (N x 512) lên bộ nhớ RAM và VRAM GPU."""
        if not cls._matrix_dirty and cls._cached_matrix is not None:
            return

        cls._cached_keys = list(cls._permanent_identities.keys())
        if not cls._cached_keys:
            cls._cached_matrix = None
            cls._cached_gpu_tensor = None
            cls._matrix_dirty = False
            return

        # Nạp mảng 2D (N, 512)
        vectors = [cls._permanent_identities[k]["embedding"] for k in cls._cached_keys]
        cls._cached_matrix = np.vstack(vectors).astype(np.float32)

        # Chuyển đổi sang GPU VRAM Tensor nếu hệ thống có GPU
        try:
            import torch  # type: ignore
            if torch.cuda.is_available():
                cls._gpu_device = "cuda"
                cls._cached_gpu_tensor = torch.from_numpy(cls._cached_matrix).to("cuda")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                cls._gpu_device = "mps"
                cls._cached_gpu_tensor = torch.from_numpy(cls._cached_matrix).to("mps")
            else:
                cls._gpu_device = None
                cls._cached_gpu_tensor = None
        except Exception:
            cls._gpu_device = None
            cls._cached_gpu_tensor = None

        cls._matrix_dirty = False

    @classmethod
    def register_identity(
        cls,
        identity_id: str,
        embedding: Union[np.ndarray, list],
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Stores or updates a permanent identity embedding vector.
        """
        emb = np.asarray(embedding, dtype=np.float32).flatten()
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm

        cls._permanent_identities[identity_id] = {
            "identity_id": identity_id,
            "name": name or identity_id,
            "embedding": emb,
            "metadata": metadata or {},
            "subject_type": SubjectType.STUDENT.value,
        }
        cls._matrix_dirty = True

    @classmethod
    def bulk_register_identities(
        cls,
        identities: List[Dict[str, Any]],
    ) -> int:
        """
        Nạp hàng loạt hồ sơ nhận diện sinh trắc học trực tiếp vào GPU VRAM Cache.
        Chỉ kích hoạt đồng bộ GPU 1 lần duy nhất để tối ưu thông lượng PCIe.
        Mỗi phần tử trong identities chứa:
          - identity_id: str
          - embedding: np.ndarray | list (512D)
          - name: Optional[str]
          - metadata: Optional[Dict[str, Any]]
          - subject_type: Optional[str]
        """
        count = 0
        for item in identities:
            iid = item.get("identity_id")
            raw_emb = item.get("embedding")
            if not iid or raw_emb is None:
                continue
            emb = np.asarray(raw_emb, dtype=np.float32).flatten()
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            cls._permanent_identities[iid] = {
                "identity_id": iid,
                "name": item.get("name") or iid,
                "embedding": emb,
                "metadata": item.get("metadata") or {},
                "subject_type": item.get("subject_type", SubjectType.STUDENT.value),
            }
            count += 1

        if count > 0:
            cls._matrix_dirty = True
            cls._sync_matrix_cache()

        return count

    @classmethod
    def remove_identity(cls, identity_id: str) -> bool:
        """
        Removes an identity from either permanent or visitor cache.
        """
        removed = False
        if identity_id in cls._permanent_identities:
            del cls._permanent_identities[identity_id]
            cls._matrix_dirty = True
            removed = True
        if identity_id in cls._visitor_identities:
            del cls._visitor_identities[identity_id]
            removed = True
        return removed

    @classmethod
    def clear_all(cls) -> None:
        cls._permanent_identities.clear()
        cls._visitor_identities.clear()
        cls._cached_matrix = None
        cls._cached_gpu_tensor = None
        cls._cached_keys = []
        cls._matrix_dirty = True

    @classmethod
    def search(
        cls,
        query_embedding: Union[np.ndarray, list],
        top_k: int = 5,
        threshold: float = 0.60,
        include_visitors: bool = True,
    ) -> List[FaceSearchResultItemDto]:
        """
        So khớp 1:N siêu tốc trên GPU VRAM Tensor (hoặc Vectorized SIMD BLAS).
        Giải phóng 100% CPU khỏi vòng lặp tính toán độ tương đồng.
        """
        q_emb = np.asarray(query_embedding, dtype=np.float32).flatten()
        q_norm = np.linalg.norm(q_emb)
        if q_norm > 0:
            q_emb = q_emb / q_norm

        if not cls._permanent_identities and not cls._visitor_identities:
            return []

        # Tự động loại bỏ vector khách hết hạn
        if include_visitors:
            cls.auto_evict_expired()

        now = datetime.now(timezone.utc)
        results: List[FaceSearchResultItemDto] = []

        # 1. So khớp chỉ mục thường trú (Permanent Index) qua GPU Tensor
        cls._sync_matrix_cache()
        if cls._cached_matrix is not None and len(cls._cached_keys) > 0:
            # 1.1. Ưu tiên GPU CUDA nếu có sẵn VRAM
            if cls._cached_gpu_tensor is not None and cls._gpu_device is not None:
                try:
                    import torch  # type: ignore
                    with torch.no_grad():
                        q_tensor = torch.from_numpy(q_emb).to(cls._gpu_device)
                        sims_gpu = torch.matmul(cls._cached_gpu_tensor, q_tensor)
                        sims_np = sims_gpu.cpu().numpy()
                except Exception:
                    sims_np = np.dot(cls._cached_matrix, q_emb)
            else:
                # 1.2. Vectorized BLAS Matrix Multiplication (SIMD AVX-512)
                sims_np = np.dot(cls._cached_matrix, q_emb)

            # Lọc các ứng viên vượt ngưỡng
            valid_indices = np.where(sims_np >= threshold)[0]
            for idx in valid_indices:
                identity_id = cls._cached_keys[idx]
                sim = float(sims_np[idx])
                data = cls._permanent_identities.get(identity_id, {})
                results.append(
                    FaceSearchResultItemDto(
                        identity_id=identity_id,
                        name=data.get("name"),
                        similarity=round(min(1.0, max(0.0, sim)), 4),
                        metadata=data.get("metadata", {}),
                    )
                )

        # 2. So khớp chỉ mục khách thăm có thời hạn (Visitor Dynamic Index)
        if include_visitors and cls._visitor_identities:
            valid_visitors = []
            for vid, data in cls._visitor_identities.items():
                valid_from = data.get("valid_from")
                valid_to = data.get("valid_to")
                if valid_from and valid_from > now:
                    continue
                if valid_to and valid_to < now:
                    continue
                valid_visitors.append((vid, data))

            if valid_visitors:
                visitor_matrix = np.vstack([item[1]["embedding"] for item in valid_visitors])
                v_sims = np.dot(visitor_matrix, q_emb)
                v_valid_idx = np.where(v_sims >= threshold)[0]

                for idx in v_valid_idx:
                    vid, data = valid_visitors[idx]
                    sim = float(v_sims[idx])
                    meta = dict(data.get("metadata", {}))
                    meta["is_visitor"] = True
                    results.append(
                        FaceSearchResultItemDto(
                            identity_id=vid,
                            name=data.get("name"),
                            similarity=round(min(1.0, max(0.0, sim)), 4),
                            metadata=meta,
                        )
                    )

        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]

