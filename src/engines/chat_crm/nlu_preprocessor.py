"""
NLU Preprocessor Module for Vietnamese Sales Chat.
Extracts entities using regex patterns and normalizes abbreviations, telex, and currency tokens.
"""

import re
import unicodedata
from typing import Dict, Any, List, Optional
from core.constants import OrderIntent, PaymentMethod


class NluPreprocessor:
    """Fast-path Vietnamese text preprocessor and regex entity extractor."""

    @staticmethod
    def remove_accent(text: str) -> str:
        """Remove Vietnamese accents and diacritics for normalization."""
        if not text:
            return ""
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        return text.replace('đ', 'd').replace('Đ', 'D').lower()

    @staticmethod
    def detect_intent(text: str) -> OrderIntent:
        """Detect intent (ORDER vs PURCHASE vs INQUIRY)."""
        lower = text.lower()
        if any(k in lower for k in ["nhập", "nhap", "mua từ", "mua tu", "lấy hàng từ", "lay hang tu", "ncc", "nhà cung cấp", "nha cung cap", "đại lý", "dai ly"]):
            return OrderIntent.PURCHASE
        if any(k in lower for k in ["còn hàng không", "con hang khong", "giá bao nhiêu", "gia bao nhieu", "check tồn"]):
            return OrderIntent.INQUIRY
        return OrderIntent.ORDER

    @staticmethod
    def extract_payment_method(text: str) -> PaymentMethod:
        """Detect payment method from slang/tokens."""
        lower = text.lower()
        if any(k in lower for k in ["ck", "chuyển khoản", "chuyen khoan", "banking", "qr"]):
            return PaymentMethod.BANK_TRANSFER
        if any(k in lower for k in ["cod", "thu hộ", "thu ho", "nhận hàng trả tiền"]):
            return PaymentMethod.COD
        return PaymentMethod.CASH

    @staticmethod
    def parse_price_token(token: str) -> Optional[float]:
        """Convert '10k', '15.000', '1.5tr', '30K', '320k' to numeric float value in VND."""
        if not token:
            return None
        token = token.lower().strip()
        k_match = re.match(r"^(\d+(?:\.\d+)?)\s*(?:k|nghìn|ngàn)$", token)
        if k_match:
            return float(k_match.group(1)) * 1000.0

        tr_match = re.match(r"^(\d+(?:\.\d+)?)\s*(?:tr|trieu|triệu)$", token)
        if tr_match:
            return float(tr_match.group(1)) * 1000000.0

        d_match = re.match(r"^(\d+(?:[.,]\d+)?)\s*(?:đ|d|vnd|vnđ)$", token)
        if d_match:
            clean = re.sub(r"[^\d]", "", d_match.group(1))
            return float(clean) if clean else None

        # Plain number >= 1000 is likely an amount in VND (e.g. '30000', '15000')
        clean_num = re.sub(r"[^\d]", "", token)
        if clean_num:
            val = float(clean_num)
            if val >= 1000:
                return val
        return None

    @staticmethod
    def is_currency_token(token: str) -> bool:
        """Check if token contains currency indicators (k, K, đ, vnđ, nghìn, tr)."""
        if not token:
            return False
        lower = token.lower().strip()
        return bool(re.search(r"(?:k|nghìn|ngàn|tr|trieu|triệu|đ|vnd|vnđ)$", lower))

    def extract_raw_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract basic regex entities: Phone, Room/Building code, Supplier, Customer Name, Notes.
        """
        # Làm sạch tiền tố đơn hàng
        clean_input = re.sub(r"(?i)^(?:đơn hàng|don hang|đơn|don|order|đặt hàng|dat hang)\s*[:：\-–]?\s*", "", text).strip()

        intent = self.detect_intent(clean_input)
        payment = self.extract_payment_method(clean_input)

        # 1. Supplier Extraction for PURCHASE intent
        supplier_name = None
        if intent == OrderIntent.PURCHASE:
            sup_match = re.search(r"(?i)(?:từ|ncc|nhà cung cấp|dai ly|đại lý)\s+([^\d,;+\n]+?)(?=\s+\d|\s*,|\s*;|\s*$)", clean_input)
            if sup_match:
                supplier_name = sup_match.group(1).strip()

        # 2. Bóc tách khách hàng & Số điện thoại (combo danh xưng + tên + phone)
        raw_customer_name = None
        phone = None

        combo_match = re.search(r"(?i)\b(khách|khach|anh|chị|chi|bác|bac|chú|chu|cô|co|em|a|c|e)\s+([^\d,;+\n:]{2,20}?)\s*(?:-|:|,)?\s*(0[35789]\d{8})\b", clean_input)
        if combo_match:
            salutation = combo_match.group(1).capitalize()
            cname = combo_match.group(2).strip().title()
            raw_customer_name = f"{salutation} {cname}"
            phone = combo_match.group(3)
        else:
            combo_rev_match = re.search(r"(?i)\b(0[35789]\d{8})\s*(?:-|:|,)?\s*(khách|khach|anh|chị|chi|bác|bac|chú|chu|cô|co|em|a|c|e)\s+([^\d,;+\n:]{2,20}?)\b", clean_input)
            if combo_rev_match:
                phone = combo_rev_match.group(1)
                salutation = combo_rev_match.group(2).capitalize()
                cname = combo_rev_match.group(3).strip().title()
                raw_customer_name = f"{salutation} {cname}"
            else:
                # Phone number riêng lẻ (10 digits starting with 03, 05, 07, 08, 09)
                phone_match = re.search(r"\b(0[35789]\d{8})\b", clean_input)
                phone = phone_match.group(1) if phone_match else None

                name_standalone = re.search(r"(?i)\b(khách|khach|anh|chị|chi|bác|bac|chú|chu|cô|co|em|a|c|e)\s+([^\d,;+\n:]{2,20}?)(?=\s+\d|\s*,|\s*;|\s*$)", clean_input)
                if name_standalone:
                    raw_customer_name = f"{name_standalone.group(1).capitalize()} {name_standalone.group(2).strip().title()}"

        # 3. Room/Apartment/Table code (e.g. 3008B, P1204, Bàn 5, B02)
        room_match = re.search(r"(?i)\b(?:bàn\s*|ban\s*|phòng\s*|p\s*)?([A-Za-z]?\d{3,4}[A-Za-z]?|[A-Za-z]\d{1,3}|bàn\s*\d+|ban\s*\d+)\b", clean_input)
        room_code = room_match.group(1).strip() if room_match and not (phone and room_match.group(1) in phone) else None
        if room_code and (room_code.lower().endswith("k") or room_code.lower().endswith("tr") or room_code.lower().endswith("d")):
            room_code = None

        # 4. Shipping notes
        notes = []
        lower = clean_input.lower()
        if "free ship" in lower or "freeship" in lower:
            notes.append("Freeship")
        if "gv" in lower or "giao gap" in lower or "giao ngay" in lower:
            notes.append("Giao ngay")
        if "kem da" in lower or "kèm đá" in lower:
            notes.append("Kèm đá")
        if "it duong" in lower or "ít đường" in lower:
            notes.append("Ít đường")
        if "it da" in lower or "ít đá" in lower:
            notes.append("Ít đá")

        shipping_note = ", ".join(notes) if notes else None

        return {
            "intent": intent,
            "payment_method": payment,
            "phone": phone,
            "raw_customer_name": raw_customer_name,
            "room_code": room_code,
            "supplier_name": supplier_name,
            "shipping_note": shipping_note,
            "clean_text": clean_input,
            "normalized_text": self.remove_accent(clean_input)
        }


nlu_preprocessor = NluPreprocessor()

