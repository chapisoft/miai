"""
Unit Tests for Vision OCR Parsers: CCCD/Passport, VAT Invoice, and BoQ Tables.
Enforces validation rules, arithmetic checks, and MRZ parsing.
"""

import pytest
from engines.vision.identity_parser import IdentityParser, identity_parser
from engines.vision.invoice_parser import InvoiceParser
from engines.vision.boq_parser import BoqParser
from schemas.vision import (
    IdentityCardRequest,
    IdentityCardResponse,
    InvoiceDto,
    InvoiceItemDto,
    BoqTableDto,
    BoqRowDto,
)
from core.constants import IdentityDocumentType


# ── 1. Identity & CCCD Tests ──────────────────────────────────────────────────

def test_cccd_12_digit_validation_valid():
    """Tests CCCD 12-digit parser with valid structure and province code mapping."""
    # 001 (Hà Nội), 0 (Nam, sinh năm 1995), 012345 (Số ngẫu nhiên)
    valid_cccd = "001095012345"
    meta = IdentityParser.validate_cccd_number(valid_cccd)
    
    assert meta["is_valid"] is True
    assert meta["province_code"] == "001"
    assert meta["province"] == "Hà Nội"
    assert meta["gender"] == "Nam"
    assert meta["birth_year"] == 1995


def test_cccd_female_21st_century():
    """Tests CCCD century and gender decoding (century 2000s, female = 3)."""
    # 079 (TP. HCM), 3 (Nữ, sinh năm 2002)
    cccd = "079302009988"
    meta = IdentityParser.validate_cccd_number(cccd)
    
    assert meta["is_valid"] is True
    assert meta["province_code"] == "079"
    assert meta["province"] == "TP. Hồ Chí Minh"
    assert meta["gender"] == "Nữ"
    assert meta["birth_year"] == 2002


def test_cccd_invalid_length():
    """Tests CCCD validator flags invalid ID numbers."""
    meta = IdentityParser.validate_cccd_number("12345")
    assert meta["is_valid"] is False


def test_mrz_passport_decoding():
    """Tests ICAO Doc 9303 TD3 MRZ decoding for international passports."""
    # Standard 2 lines x 44 chars
    line1 = "P<VNMNGUYEN<<VAN<AN<<<<<<<<<<<<<<<<<<<<<<<<<"
    line2 = "B1234567<8VNM9508154M3008158<<<<<<<<<<<<<<02"

    parsed = IdentityParser.parse_mrz_td3(line1, line2)
    assert parsed["passport_number"] == "B1234567"
    assert parsed["full_name"] == "NGUYEN VAN AN"
    assert parsed["date_of_birth"] == "1995-08-15"
    assert parsed["gender"] == "Nam"
    assert parsed["expiry_date"] == "2030-08-15"
    assert parsed["nationality"] == "VNM"


@pytest.mark.asyncio
async def test_identity_parser_end_to_end():
    """Tests end-to-end identity parsing request."""
    req = IdentityCardRequest(image_base64="CCCD Số: 001095012345")
    res = await identity_parser.parse_identity_document(req)
    assert res.document_type == IdentityDocumentType.CCCD_CHIP
    assert res.id_number == "001095012345"
    assert res.province_code == "001"
    assert res.is_valid_checksum is True


# ── 2. VAT Invoice Tests ──────────────────────────────────────────────────────

def test_invoice_arithmetic_validation_pass():
    """Tests VAT Invoice arithmetic cross-check validation pass."""
    invoice = InvoiceDto(
        invoice_number="0001234",
        invoice_series="1C26TAA",
        invoice_date="2026-09-12",
        seller_name="Công ty TNHH AI Solutions",
        seller_tax_code="0109876543",
        items=[
            InvoiceItemDto(
                item_name="License AI OCR Platform",
                quantity=1.0,
                unit_price=10000000.0,
                total_amount=10000000.0,
                tax_rate="10%"
            ),
            InvoiceItemDto(
                item_name="Hardware FDI Station",
                quantity=2.0,
                unit_price=5000000.0,
                total_amount=10000000.0,
                tax_rate="10%"
            )
        ],
        subtotal_amount=20000000.0,
        tax_amount=2000000.0,
        total_payment=22000000.0,
        currency="VND"
    )

    is_valid = InvoiceParser.validate_arithmetic(invoice)
    assert is_valid is True


def test_invoice_arithmetic_validation_fail_flag():
    """Tests VAT Invoice validator flags arithmetic discrepancies."""
    invoice = InvoiceDto(
        invoice_number="0009999",
        seller_name="Công ty ABC",
        items=[
            InvoiceItemDto(
                item_name="Sản phẩm A",
                quantity=1.0,
                unit_price=100000.0,
                total_amount=100000.0
            )
        ],
        subtotal_amount=100000.0,
        tax_amount=10000.0,
        total_payment=150000.0,  # 100k + 10k != 150k
        currency="VND"
    )

    is_valid = InvoiceParser.validate_arithmetic(invoice)
    assert is_valid is False


@pytest.mark.asyncio
async def test_invoice_text_parse_fallback():
    """Tests invoice text parsing fallback with regex extraction."""
    raw_ocr = "HÓA ĐƠN GIÁ TRỊ GIA TĂNG\nSố: 0012345\nMST: 0101234567\nNgày: 12/09/2026\nTổng tiền: 5000000"
    invoice = await InvoiceParser.parse_text(raw_ocr)
    assert invoice.invoice_number == "0012345"
    assert invoice.seller_tax_code == "0101234567"
    assert invoice.invoice_date == "2026-09-12"


# ── 3. BoQ Bidding Table Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_boq_table_parsing():
    """Tests BoQ parser creates structured rows and handles estimates."""
    ocr_table = """
    STT | Mô tả công việc | Khối lượng | Đơn giá
    1   | Cung cấp lắp đặt trạm FDI Vision | 4 | 25000000
    2   | Tích hợp mô hình AI Qwen2.5-VL  | 1 | 50000000
    """
    boq = await BoqParser.parse_text(ocr_table)
    assert len(boq.rows) > 0
    assert boq.rows[0].item_code is not None
