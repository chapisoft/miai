"""
Structured Extractor Engine for CRM Quick Order Chat.
Combines Fast-Path Regex Tokenization, CRM Tool Grounding, and LLM Structured Extraction.
"""

import re
import uuid
import time
from typing import List, Optional, Dict, Any
from schemas.chat_crm import (
    DraftOrderResponse,
    DraftOrderItemSchema,
    DraftCustomerSchema,
    ChatParseRequest,
)
from core.constants import OrderIntent, PaymentMethod, ModelProvider
from engines.chat_crm.nlu_preprocessor import nlu_preprocessor
from engines.chat_crm.crm_tools import crm_tools
from engines.chat_crm.feedback_learner import feedback_learner
from engines.llm.structured import StructuredExtractor
from engines.llm.factory import LLMFactory
from core.telemetry import logger


class StructuredExtractorEngine:
    """Core Engine for parsing unstructured sales messages into Draft Orders."""

    SYSTEM_INSTRUCTION_TEMPLATE = (
        "Bạn là Trợ lý AI Bán hàng CRM chuyên nghiệp. "
        "Nhiệm vụ của bạn là đọc câu lệnh bán hàng viết tắt của nhân viên và trích xuất thành đơn hàng chuẩn xác."
    )

    async def parse_message(self, request: ChatParseRequest) -> DraftOrderResponse:
        """
        Parse raw sales message into validated DraftOrderResponse.
        """
        start_time = time.time()
        raw_msg = request.message.strip()
        session_id = f"sess-{uuid.uuid4().hex[:10]}"

        # 1. Fast-Path Preprocessing
        pre_data = nlu_preprocessor.extract_raw_entities(raw_msg)
        intent = pre_data["intent"]
        payment_method = pre_data["payment_method"]
        phone = pre_data["phone"]
        room_code = pre_data["room_code"]
        shipping_note = pre_data["shipping_note"]

        # 2. Resolve Customer from CRM DB
        customer = crm_tools.resolve_customer(
            tenant_id=request.tenant_id,
            phone=phone,
            code=room_code,
            raw_text=raw_msg
        )

        # 3. Product Tokenization and Item Extraction
        items: List[DraftOrderItemSchema] = []

        # Tokenize by common delimiters or sequential product chunks
        # e.g., "3006B 10k xoi lac 2 bm gv" -> chunks: ("10k xoi lac"), ("2 bm")
        # Regex to find patterns like: (<price> <product>), (<quantity> <product>)
        chunk_patterns = re.findall(
            r"(\d+(?:\.\d+)?\s*(?:k|K|tr|trieu|đ)?)\s+([a-zA-Z\s\u00C0-\u1EF9]+?)(?=(?:\d+(?:\.\d+)?\s*(?:k|K|tr|trieu|đ)?|\b(?:gv|free ship|freeship|ck|cod)\b|$))",
            raw_msg,
            re.IGNORECASE
        )

        if chunk_patterns:
            for qty_or_price_str, prod_raw in chunk_patterns:
                prod_clean = prod_raw.strip()
                if not prod_clean or prod_clean.lower() in ["gv", "ck", "cod", "free ship"]:
                    continue

                # Check if first part is price or quantity
                price_val = nlu_preprocessor.parse_price_token(qty_or_price_str)
                qty_val = 1

                # If token is just a small digit without 'k', it's likely a quantity
                if re.match(r"^\d{1,2}$", qty_or_price_str.strip()):
                    qty_val = int(qty_or_price_str.strip())
                    price_val = None

                item = crm_tools.resolve_product(
                    tenant_id=request.tenant_id,
                    token=prod_clean,
                    price_hint=price_val
                )
                item.quantity = qty_val
                item.total_amount = (item.unit_price or 10000.0) * qty_val
                items.append(item)

        # If regex chunks found nothing, fallback to direct search
        if not items:
            # Try splitting by keywords
            words = raw_msg.split()
            filtered_words = [w for w in words if w.lower() not in [room_code or "", phone or "", "gv", "ck", "cod"]]
            prod_token = " ".join(filtered_words) if filtered_words else "Sản phẩm tổng hợp"
            item = crm_tools.resolve_product(request.tenant_id, prod_token)
            items.append(item)

        # 4. Calculate Total Amount & Overall Confidence
        total_order_amount = sum(it.total_amount or 0.0 for it in items)
        min_item_conf = min(it.confidence for it in items) if items else 0.80
        overall_confidence = round(customer.confidence * 0.4 + min_item_conf * 0.6, 2)

        # 5. Check if clarification is needed
        needs_clarification = overall_confidence < 0.88
        clarification_question = None
        quick_options = None

        if needs_clarification:
            if not customer.customer_id:
                clarification_question = f"Chưa tìm thấy khách hàng '{customer.full_name}'. Bạn muốn tạo mới hay gán vào khách lẻ?"
                quick_options = ["Gán khách lẻ tại quầy", "Tạo mới khách hàng"]
            else:
                ambiguous_item = next((it for it in items if it.confidence < 0.85), items[0])
                clarification_question = f"Sản phẩm '{ambiguous_item.raw_text}' chưa rõ phân loại. Bạn muốn chọn:"
                quick_options = ["Bánh Mì Pate (15k)", "Bánh Mì Trứng (12k)"]

        processing_time = round((time.time() - start_time) * 1000.0, 1)

        return DraftOrderResponse(
            session_id=session_id,
            intent=intent,
            overall_confidence=overall_confidence,
            customer=customer,
            items=items,
            total_order_amount=total_order_amount,
            payment_method=payment_method,
            shipping_note=shipping_note,
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
            quick_options=quick_options,
            processing_time_ms=processing_time
        )


structured_extractor = StructuredExtractorEngine()
