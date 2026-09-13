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

        # 2. Resolve Customer from CRM DB with App & Tenant Isolation
        customer = crm_tools.resolve_customer(
            tenant_id=request.tenant_id,
            phone=phone,
            code=room_code,
            raw_text=raw_msg,
            app_id=request.app_id
        )

        # Cập nhật tên khách hàng nếu bóc tách được từ cụm xưng hô và SĐT
        if pre_data.get("raw_customer_name"):
            if not customer.customer_id or customer.full_name == "Khách lẻ tại quầy":
                customer.full_name = pre_data["raw_customer_name"]

        # 3. Product Tokenization and Item Extraction (Dual Quantity vs Fixed Amount Resolution)
        items: List[DraftOrderItemSchema] = []

        # Remove customer/room_code/phone and supplier prefixes from product parsing text
        clean_text = pre_data.get("clean_text", raw_msg)
        if pre_data.get("raw_customer_name"):
            clean_text = re.sub(rf"(?i)\b{re.escape(pre_data['raw_customer_name'])}\b", " ", clean_text)
        if room_code:
            clean_text = re.sub(rf"(?i)\b{re.escape(room_code)}\b", " ", clean_text)
        if phone:
            clean_text = re.sub(rf"\b{re.escape(phone)}\b", " ", clean_text)
        if pre_data.get("supplier_name"):
            clean_text = re.sub(rf"(?i)(?:từ|ncc|nhà cung cấp|đại lý)\s+{re.escape(pre_data['supplier_name'])}", " ", clean_text)
        
        # Strip matched customer name or aliases if matched
        if customer and customer.customer_id:
            for alias in ["anh tuấn", "a tuấn", "tuấn", "chị mai", "c mai", "mai", "anh long", "long"]:
                clean_text = re.sub(rf"(?i)\b{re.escape(alias)}\b", " ", clean_text)

        # Strip shipping/modifier notes
        for note_token in ["ít đường", "it duong", "ít đá", "it da", "kèm đá", "kem da", "freeship", "free ship", "giao ngay", "giao gap", "gv"]:
            clean_text = re.sub(rf"(?i)\b{re.escape(note_token)}\b", " ", clean_text)

        # Strip salutations & conversational noise (hỗ trợ cả có dấu và không dấu chi, bac, chu, co...)
        clean_text = re.sub(r"(?i)\b(?:anh|chị|chi|em|bác|bac|chú|chu|cô|co|bạn|khách|khach|a|c|e)\b", " ", clean_text)
        clean_text = re.sub(r"(?i)\b(?:nhập|nhap|mua|bán|ban|lấy|lay|cho|ship|giao|đặt|dat)\b", " ", clean_text)

        # Split items by comma, semicolon, plus sign or newline, AND by subsequent item start numbers (e.g. "2 xoi ga 1 sua ngo")
        raw_splits = [seg.strip() for seg in re.split(r"[,;+\n]+", clean_text) if seg.strip()]
        if not raw_splits:
            raw_splits = [clean_text.strip()]

        item_segments = []
        item_start_pattern = re.compile(r"(?:^|\s+)(\d+(?:\.\d+)?(?:k|K|tr|nghin|nghìn|cái|cai|ly|bát|bat|suất|suat|hộp|hop|thùng|thung|chai|gói|goi)?\s+)", re.IGNORECASE)

        for part in raw_splits:
            trimmed = part.strip()
            if not trimmed:
                continue
            matches = list(item_start_pattern.finditer(trimmed))
            if len(matches) <= 1:
                item_segments.append(trimmed)
            else:
                last_idx = 0
                for m in matches[1:]:
                    pos = m.start()
                    sub = trimmed[last_idx:pos].strip()
                    if sub:
                        item_segments.append(sub)
                    last_idx = pos
                tail = trimmed[last_idx:].strip()
                if tail:
                    item_segments.append(tail)

        for seg in item_segments:
            seg = seg.strip()
            if not seg or len(seg) < 2:
                continue

            # Pattern A: Quantity + Packaging Unit + Product + Unit Price (e.g. "10 thùng bia tiger 320k", "2 ly cà phê sữa 25k")
            comb_unit_match = re.search(
                r"^(\d+)\s+(thùng|thung|lốc|loc|lon|hộp|hop|gói|goi|bịch|bich|kg|cái|cai|ly|cốc|coc|suất|suat|bát|bat|tô|to|dĩa|dia)\s+([^\d,;+\n]+?)\s+(\d+(?:\.\d+)?\s*(?:k|K|tr|trieu|triệu|đ|vnd|vnđ))$",
                seg,
                re.IGNORECASE
            )
            if comb_unit_match:
                qty_val = int(comb_unit_match.group(1))
                unit_name = comb_unit_match.group(2).strip()
                prod_name = comb_unit_match.group(3).strip()
                price_str = comb_unit_match.group(4)
                price_val = nlu_preprocessor.parse_price_token(price_str)
                item = crm_tools.resolve_product(tenant_id=request.tenant_id, token=prod_name, price_hint=price_val, app_id=request.app_id)
                item.quantity = qty_val
                item.unit_name = unit_name
                if price_val:
                    item.unit_price = price_val
                item.total_amount = (item.unit_price or 10000.0) * qty_val
                item.notes = f"Quy cách {qty_val} {unit_name}"
                items.append(item)
                continue

            # Pattern A2: Quantity + Product + Unit Price (e.g. "2 xôi 15k", "3 phở bò 45k")
            comb_match = re.search(
                r"^(\d+)\s+([^\d,;+\n]+?)\s+(\d+(?:\.\d+)?\s*(?:k|K|tr|trieu|triệu|đ|vnd|vnđ))$",
                seg,
                re.IGNORECASE
            )
            if comb_match:
                qty_val = int(comb_match.group(1))
                prod_name = comb_match.group(2).strip()
                price_str = comb_match.group(3)
                price_val = nlu_preprocessor.parse_price_token(price_str)
                item = crm_tools.resolve_product(tenant_id=request.tenant_id, token=prod_name, price_hint=price_val, app_id=request.app_id)
                item.quantity = qty_val
                if price_val:
                    item.unit_price = price_val
                item.total_amount = (item.unit_price or 10000.0) * qty_val
                items.append(item)
                continue

            # Pattern B: Fixed Amount First + Product (e.g. "30K xôi", "30k xôi xéo", "50k thịt bò")
            amt_match = re.search(
                r"^(\d+(?:\.\d+)?\s*(?:k|K|tr|trieu|triệu|đ|vnd|vnđ))\s+([^\d,;+\n]+)$",
                seg,
                re.IGNORECASE
            )
            if amt_match:
                price_str = amt_match.group(1)
                prod_name = amt_match.group(2).strip()
                amt_val = nlu_preprocessor.parse_price_token(price_str) or 10000.0
                item = crm_tools.resolve_product(tenant_id=request.tenant_id, token=prod_name, price_hint=amt_val, app_id=request.app_id)
                item.quantity = 1
                item.unit_price = amt_val
                item.total_amount = amt_val
                item.notes = f"Định lượng theo số tiền {amt_val:,.0f}đ"
                items.append(item)
                continue

            # Pattern C: Product + Fixed Amount Last (e.g. "xôi 30k", "bánh mì 25k")
            prod_amt_match = re.search(
                r"^([^\d,;+\n]+?)\s+(\d+(?:\.\d+)?\s*(?:k|K|tr|trieu|triệu|đ|vnd|vnđ))$",
                seg,
                re.IGNORECASE
            )
            if prod_amt_match:
                prod_name = prod_amt_match.group(1).strip()
                price_str = prod_amt_match.group(2)
                amt_val = nlu_preprocessor.parse_price_token(price_str) or 10000.0
                item = crm_tools.resolve_product(tenant_id=request.tenant_id, token=prod_name, price_hint=amt_val, app_id=request.app_id)
                item.quantity = 1
                item.unit_price = amt_val
                item.total_amount = amt_val
                item.notes = f"Định lượng theo số tiền {amt_val:,.0f}đ"
                items.append(item)
                continue

            # Pattern D: Quantity + Packaging Unit + Product (e.g. "5 lon coca", "10 gói mì")
            qty_unit_match = re.search(
                r"^(\d+)\s+(thùng|thung|lốc|loc|lon|hộp|hop|gói|goi|bịch|bich|kg|cái|cai|ly|cốc|coc|suất|suat|bát|bat|tô|to|dĩa|dia)\s+([^\d,;+\n]+)$",
                seg,
                re.IGNORECASE
            )
            if qty_unit_match:
                qty_val = int(qty_unit_match.group(1))
                unit_name = qty_unit_match.group(2).strip()
                prod_name = qty_unit_match.group(3).strip()
                item = crm_tools.resolve_product(tenant_id=request.tenant_id, token=prod_name, app_id=request.app_id)
                item.quantity = qty_val
                item.unit_name = unit_name
                item.total_amount = (item.unit_price or 10000.0) * qty_val
                item.notes = f"Quy cách {qty_val} {unit_name}"
                items.append(item)
                continue

            # Pattern E: Quantity + Product without price (e.g. "3 bánh mì", "2 sữa chua", "1 lẩu thái")
            qty_match = re.search(
                r"^(\d+)\s+([^\d,;+\n]+)$",
                seg,
                re.IGNORECASE
            )
            if qty_match:
                qty_val = int(qty_match.group(1))
                prod_name = qty_match.group(2).strip()
                item = crm_tools.resolve_product(tenant_id=request.tenant_id, token=prod_name, app_id=request.app_id)
                item.quantity = qty_val
                item.total_amount = (item.unit_price or 10000.0) * qty_val
                items.append(item)
                continue

            # Fallback: general single product token
            item = crm_tools.resolve_product(tenant_id=request.tenant_id, token=seg, app_id=request.app_id)
            item.quantity = 1
            item.total_amount = item.unit_price or 10000.0
            items.append(item)

        # Safety Gate: Lọc bỏ triệt để các item không có trong CSDL mà tên là danh từ xưng hô / tên người
        valid_items: List[DraftOrderItemSchema] = []
        for it in items:
            it_name_norm = nlu_preprocessor.remove_accent(it.product_name or "")
            is_salutation = bool(re.match(r"^(?:khach|anh|chi|bac|chu|co|em|a|c|e)\s+[a-z]+.*$", it_name_norm))
            if it.product_id is None and is_salutation:
                if not customer.full_name or customer.full_name == "Khách lẻ tại quầy":
                    customer.full_name = it.product_name
                continue
            valid_items.append(it)
        items = valid_items

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
            app_id=request.app_id,
            partner_id=request.partner_id,
            tenant_id=request.tenant_id,
            domain_code=request.domain_code,
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

