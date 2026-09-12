"""
Document Chunker Module.
Splits long documents into overlapping passages preserving context boundaries.
"""

import re
import uuid
from typing import List, Dict, Any, Optional
from schemas.rag import DocumentChunk


class DocumentChunker:
    """Intelligent text splitter supporting recursive sentence and paragraph boundaries."""

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]

    @classmethod
    def split_text(
        cls,
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None
    ) -> List[str]:
        """Recursive character text splitting."""
        if not text:
            return []

        seps = separators or cls.DEFAULT_SEPARATORS
        
        # Base case
        if len(text) <= chunk_size:
            return [text.strip()] if text.strip() else []

        # Find appropriate separator
        chosen_sep = ""
        for sep in seps:
            if sep in text:
                chosen_sep = sep
                break

        splits = text.split(chosen_sep) if chosen_sep else list(text)
        
        chunks: List[str] = []
        current_chunk = []
        current_length = 0

        for piece in splits:
            piece_len = len(piece) + len(chosen_sep)
            if current_length + piece_len > chunk_size and current_chunk:
                combined = chosen_sep.join(current_chunk).strip()
                if combined:
                    chunks.append(combined)
                
                # Keep overlap pieces
                overlap_accum = []
                overlap_len = 0
                for back_piece in reversed(current_chunk):
                    if overlap_len + len(back_piece) <= chunk_overlap:
                        overlap_accum.insert(0, back_piece)
                        overlap_len += len(back_piece)
                    else:
                        break
                current_chunk = overlap_accum
                current_length = sum(len(p) for p in current_chunk) + len(chosen_sep) * max(0, len(current_chunk) - 1)

            current_chunk.append(piece)
            current_length += piece_len

        if current_chunk:
            combined = chosen_sep.join(current_chunk).strip()
            if combined:
                chunks.append(combined)

        return chunks

    @classmethod
    def chunk_document(
        cls,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[DocumentChunk]:
        """Generates a list of structured DocumentChunk objects from raw document text."""
        raw_chunks = cls.split_text(content, chunk_size, chunk_overlap)
        meta = metadata or {}
        
        results: List[DocumentChunk] = []
        for idx, text in enumerate(raw_chunks):
            chunk_id = f"{document_id}_chunk_{idx}"
            chunk_meta = meta.copy()
            chunk_meta["chunk_index"] = idx
            results.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    content=text,
                    metadata=chunk_meta
                )
            )
        return results
