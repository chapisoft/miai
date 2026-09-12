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
        if any(k in lower for k in ["nhập", "nhap", "mua từ", "mua tu", "lấy hàng từ", "lay hang tu"]):
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
        """Convert '10k', '15.000', '1.5tr' to numeric float value."""
        token = token.lower().strip()
        k_match = re.match(r"^(\d+(?:\.\d+)?)\s*k$", token)
        if k_match:
            return float(k_match.group(1)) * 1000.0

        tr_match = re.match(r"^(\d+(?:\.\d+)?)\s*(?:tr|trieu)$", token)
        if tr_match:
            return float(tr_match.group(1)) * 1000000.0

        clean_num = re.sub(r"[^\d]", "", token)
        if clean_num:
            val = float(clean_num)
            # If plain number like '10' before a product name, it might be 10k or quantity 10
            return val
        return None

    def extract_raw_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract basic regex entities: Phone, Room/Building code, Prices, Notes.
        """
        intent = self.detect_intent(text)
        payment = self.extract_payment_method(text)

        # 1. Phone number (10 digits starting with 03, 05, 07, 08, 09)
        phone_match = re.search(r"\b(0[35789]\d{8})\b", text)
        phone = phone_match.group(1) if phone_match else None

        # 2. Room/Apartment code (e.g. 3006B, P1204, A102, T3-12)
        room_match = re.search(r"\b([A-Za-z]?\d{3,4}[A-Za-z]?|[A-Za-z]\d{1,3})\b", text)
        room_code = room_match.group(1) if room_match and not (phone and room_match.group(1) in phone) else None

        # 3. Shipping notes
        notes = []
        lower = text.lower()
        if "free ship" in lower or "freeship" in lower:
            notes.append("Freeship")
        if "gv" in lower or "giao gap" in lower or "giao ngay" in lower:
            notes.append("Giao việc/Giao ngay")
        if "kem da" in lower or "kèm đá" in lower:
            notes.append("Kèm đá")

        shipping_note = ", ".join(notes) if notes else None

        return {
            "intent": intent,
            "payment_method": payment,
            "phone": phone,
            "room_code": room_code,
            "shipping_note": shipping_note,
            "normalized_text": self.remove_accent(text)
        }


nlu_preprocessor = NluPreprocessor()
