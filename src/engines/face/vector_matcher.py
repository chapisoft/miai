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
    def remove_identity(cls, identity_id: str) -> bool:
        """
        Removes an identity from either permanent or visitor cache.
        """
        removed = False
        if identity_id in cls._permanent_identities:
            del cls._permanent_identities[identity_id]
            removed = True
        if identity_id in cls._visitor_identities:
            del cls._visitor_identities[identity_id]
            removed = True
        return removed

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

    @classmethod
    def clear_all(cls) -> None:
        cls._permanent_identities.clear()
        cls._visitor_identities.clear()

    @classmethod
    def search(
        cls,
        query_embedding: Union[np.ndarray, list],
        top_k: int = 5,
        threshold: float = 0.60,
        include_visitors: bool = True,
    ) -> List[FaceSearchResultItemDto]:
        """
        Finds the closest matches across permanent identities and valid visitors.
        Returns matches sorted by similarity descending.
        """
        q_emb = np.asarray(query_embedding, dtype=np.float32).flatten()
        q_norm = np.linalg.norm(q_emb)
        if q_norm > 0:
            q_emb = q_emb / q_norm

        if not cls._permanent_identities and not cls._visitor_identities:
            return []

        # Auto-evict expired visitors before matching
        if include_visitors:
            cls.auto_evict_expired()

        now = datetime.now(timezone.utc)
        results = []

        # 1. Search Permanent Index
        for identity_id, data in cls._permanent_identities.items():
            db_emb = data["embedding"]
            sim = float(np.dot(q_emb, db_emb))
            sim = max(0.0, min(1.0, sim))

            if sim >= threshold:
                results.append(
                    FaceSearchResultItemDto(
                        identity_id=identity_id,
                        name=data.get("name"),
                        similarity=round(sim, 4),
                        metadata=data.get("metadata", {}),
                    )
                )

        # 2. Search Visitor Dynamic Index
        if include_visitors:
            for identity_id, data in cls._visitor_identities.items():
                valid_from = data.get("valid_from")
                valid_to = data.get("valid_to")
                
                # Check active validity window
                if valid_from and valid_from > now:
                    continue
                if valid_to and valid_to < now:
                    continue

                db_emb = data["embedding"]
                sim = float(np.dot(q_emb, db_emb))
                sim = max(0.0, min(1.0, sim))

                if sim >= threshold:
                    meta = dict(data.get("metadata", {}))
                    meta["is_visitor"] = True
                    results.append(
                        FaceSearchResultItemDto(
                            identity_id=identity_id,
                            name=data.get("name"),
                            similarity=round(sim, 4),
                            metadata=meta,
                        )
                    )

        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]

