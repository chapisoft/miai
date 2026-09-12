"""
End-to-End Test Data Generator & Results Demonstration Runner.
Demonstrates realistic test datasets and extraction results for:
1. Unified Vision OCR (CCCD 12-digit, Passport MRZ, VAT Invoice, BoQ Table, FDI Form)
2. CRM Quick Order AI Chat (Rapid Sales Message, Entity Grounding, Dynamic Learning)
"""

import asyncio
import json
import time
from typing import Dict, Any

from engines.vision.identity_parser import IdentityParser, identity_parser
from engines.vision.invoice_parser import InvoiceParser
from engines.vision.boq_parser import BoqParser
from engines.vision.roi_extractor import RoiExtractor
from schemas.vision import (
    IdentityCardRequest,
    InvoiceDto,
    InvoiceItemDto,
    BoqTableDto,
)
from engines.chat_crm.nlu_preprocessor import nlu_preprocessor
from engines.chat_crm.crm_tools import crm_tools
from engines.chat_crm.feedback_learner import feedback_learner
from engines.chat_crm.conversation_graph import conversation_graph
from schemas.chat_crm import ChatParseRequest, ChatConfirmRequest, CorrectionItemDto


def print_section(title: str):
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)


def print_json(data: Any):
    if hasattr(data, "model_dump"):
        print(json.dumps(data.model_dump(), indent=2, ensure_ascii=False))
    elif isinstance(data, dict):
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(str(data))


async def run_vision_test_dataset():
    print_section("1. KIỂM THỬ DỮ LIỆU THỰC TẾ: BỘ MÁY THỊ GIÁC & OCR (VISION OCR)")

    # ── Test Dataset 1.1: CCCD 12 Số gắn chip ──────────────────────────────────
    print("\n[TEST DATASET 1.1] Bóc tách và kiểm tra hợp lệ CCCD 12 số")
    raw_cccd_sample = {
        "cccd_number": "001095012345",
        "raw_ocr_text": (
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
            "Độc lập - Tự do - Hạnh phúc\n"
            "CĂN CƯỚC CÔNG DÂN / Citizen Identity Card\n"
            "Số / No.: 001095012345\n"
            "Họ và tên / Full name: NGUYỄN VĂN AN\n"
            "Ngày sinh / Date of birth: 15/08/1995\n"
            "Giới tính / Sex: Nam\n"
            "Quốc tịch / Nationality: Việt Nam\n"
            "Quê quán: Đan Phượng, Hà Nội\n"
            "Nơi thường trú: Số 12 Phố Huế, Hoàn Kiếm, Hà Nội\n"
            "Có giá trị đến / Date of expiry: 15/08/2035"
        )
    }
    print("-> Dữ liệu đầu vào (Input):")
    print(raw_cccd_sample["raw_ocr_text"])

    cccd_res = await identity_parser.parse_identity_document(
        IdentityCardRequest(image_base64=raw_cccd_sample["raw_ocr_text"])
    )
    print("\n-> Kết quả bóc tách & Giải mã cấu trúc định danh (Output):")
    print_json(cccd_res)

    # ── Test Dataset 1.2: Hộ chiếu ICAO Doc 9303 MRZ ────────────────────────────
    print("\n[TEST DATASET 1.2] Giải mã vùng đọc máy MRZ Hộ chiếu quốc tế (2 dòng)")
    passport_mrz_sample = {
        "line1": "P<VNMNGUYEN<<VAN<AN<<<<<<<<<<<<<<<<<<<<<<<<<",
        "line2": "B1234567<8VNM9508154M3008158<<<<<<<<<<<<<<02"
    }
    print(f"-> Dòng 1: {passport_mrz_sample['line1']}")
    print(f"-> Dòng 2: {passport_mrz_sample['line2']}")

    mrz_res = IdentityParser.parse_mrz_td3(passport_mrz_sample["line1"], passport_mrz_sample["line2"])
    print("\n-> Kết quả giải mã chuẩn quốc tế (Output):")
    print_json(mrz_res)

    # ── Test Dataset 1.3: Hóa đơn điện tử VAT & Đối soát số học ───────────────
    print("\n[TEST DATASET 1.3] Hóa đơn điện tử GTGT (VAT) kèm kiểm tra số học")
    invoice_sample_text = (
        "HÓA ĐƠN GIÁ TRỊ GIA TĂNG (VAT INVOICE)\n"
        "Ký hiệu (Serial): 1C26TAA - Số (No): 0012345\n"
        "Ngày lập: 12/09/2026\n"
        "Đơn vị bán: CÔNG TY TNHH PHẦN MỀM CÔNG NGHỆ CAO\n"
        "Mã số thuế: 0101234567\n"
        "Đơn vị mua: CÔNG TY CỔ PHẦN THƯƠNG MẠI DỊCH VỤ\n"
        "Mã số thuế: 0309876543\n"
        "Danh mục hàng hóa:\n"
        "1. Dịch vụ AI OCR Platform Engine | SL: 1 | Đơn giá: 20,000,000 | Thành tiền: 20,000,000 | Thuế VAT: 10%\n"
        "Cộng tiền hàng: 20,000,000 VNĐ\n"
        "Tiền thuế GTGT (10%): 2,000,000 VNĐ\n"
        "Tổng tiền thanh toán: 22,000,000 VNĐ"
    )
    print("-> Dữ liệu hóa đơn đầu vào (Input):")
    print(invoice_sample_text)

    invoice_res = await InvoiceParser.parse_text(invoice_sample_text)
    print("\n-> Kết quả trích xuất hóa đơn có cấu trúc & Kiểm tra đối soát (Output):")
    print_json(invoice_res)

    # ── Test Dataset 1.4: Bảng khối lượng dự toán BoQ ───────────────────────────
    print("\n[TEST DATASET 1.4] Bảng khối lượng mời thầu dự toán (BoQ)")
    boq_sample_text = (
        "DỰ ÁN: NÂNG CẤP NHÀ MÁY THÔNG MINH FDI CÔNG NGHỆ CAO\n"
        "GÓI THẦU SỐ 03: HỆ THỐNG TRẠM QUÉT BIỂU MẪU RẢNH TAY\n"
        "STT | Mã hiệu | Mô tả công tác | ĐVT | Khối lượng | Đơn giá | Thành tiền\n"
        "1   | CV-001  | Cung cấp lắp đặt camera 4K Overhead | Bộ | 4 | 15,000,000 | 60,000,000\n"
        "2   | CV-002  | Bản quyền phần mềm FDI Vision Homography | License | 4 | 25,000,000 | 100,000,000\n"
        "3   | CV-003  | Triển khai vi dịch vụ AI Gateway On-Premise | Hệ thống | 1 | 50,000,000 | 50,000,000"
    )
    print("-> Dữ liệu BoQ đầu vào (Input):")
    print(boq_sample_text)

    boq_res = await BoqParser.parse_text(boq_sample_text)
    print("\n-> Kết quả trích xuất bảng BoQ (Output):")
    print_json(boq_res)


async def run_chat_crm_test_dataset():
    print_section("2. KIỂM THỬ DỮ LIỆU THỰC TẾ: TRỢ LÝ CHAT AI TẠO ĐƠN CRM")

    tenant_id = "shop-default-01"

    # ── Case 2.1: Tin nhắn bán hàng siêu ngắn ──────────────────────────────────
    print("\n[TEST CASE 2.1] Saler gõ lệnh bán hàng viết tắt siêu ngắn tại hiện trường")
    msg_1 = "3006B 10k xoi lac 2 bm gv ck"
    print(f'-> Tin nhắn của Saler: "{msg_1}"')

    parse_req_1 = ChatParseRequest(
        message=msg_1,
        tenant_id=tenant_id,
        saler_id="saler-01"
    )
    draft_1 = await conversation_graph.process_user_turn(parse_req_1)
    print("\n-> AI Đọc hiểu và tạo Đơn Hàng Nháp (Draft Order Output):")
    print_json(draft_1)

    # ── Case 2.2: Tin nhắn có SĐT, tên và địa chỉ chi tiết ────────────────────
    print("\n[TEST CASE 2.2] Saler gõ tin nhắn có số điện thoại, địa chỉ và món combo")
    msg_2 = "giao chị Mai 0987654321 45 Tràng Tiền 1 lẩu thái cay 2 coca freeship"
    print(f'-> Tin nhắn của Saler: "{msg_2}"')

    parse_req_2 = ChatParseRequest(
        message=msg_2,
        tenant_id=tenant_id,
        saler_id="saler-01"
    )
    draft_2 = await conversation_graph.process_user_turn(parse_req_2)
    print("\n-> AI Đọc hiểu và tạo Đơn Hàng Nháp (Draft Order Output):")
    print_json(draft_2)

    # ── Case 2.3: Cơ chế tự học thích ứng (Dynamic Self-Learning) ─────────────
    print("\n[TEST CASE 2.3] Tự học từ lóng mới thông qua lượt xác nhận của Saler")
    print("Bước 1: Saler dùng từ lóng hoàn toàn mới 'bmc' (Bánh mì chả)")
    new_slang_msg = "1204A1 3 bmc"
    print(f'-> Saler gõ: "{new_slang_msg}"')

    parse_req_3 = ChatParseRequest(
        message=new_slang_msg,
        tenant_id=tenant_id,
        saler_id="saler-01"
    )
    draft_3 = await conversation_graph.process_user_turn(parse_req_3)
    print(f"-> AI phát hiện từ 'bmc' với độ tin cậy thấp: {draft_3.items[0].product_name} (Confidence: {draft_3.items[0].confidence})")

    print("\nBước 2: Saler xác nhận và chọn đúng sản phẩm trong CRM (Bánh Mì Pate Cột Đèn - ID: prod-002)")
    confirm_req = ChatConfirmRequest(
        session_id=draft_3.session_id,
        tenant_id=tenant_id,
        order_id="ORD-2026-9901",
        corrections=[
            CorrectionItemDto(
                raw_token="bmc",
                corrected_product_id="prod-002"
            )
        ]
    )
    confirm_res = await conversation_graph.confirm_order_turn(confirm_req)
    print(f"-> Kết quả ghi nhận phản hồi: {confirm_res['message']}")

    print("\nBước 3: Kiểm tra từ điển từ lóng đã được học tự động của gian hàng:")
    learned_aliases = feedback_learner.get_aliases(tenant_id)
    for idx, a in enumerate(learned_aliases, 1):
        print(f"   {idx}. Từ lóng: '{a.raw_token}' -> {a.target_type}: {a.target_name} (Sử dụng: {a.usage_count} lần)")

    print("\nBước 4: Kiểm tra System Prompt được nạp Few-Shot động:")
    few_shot_prompt = feedback_learner.build_few_shot_prompt(tenant_id)
    print(few_shot_prompt)


async def main():
    start = time.time()
    await run_vision_test_dataset()
    await run_chat_crm_test_dataset()
    duration = time.time() - start
    print_section(f"HOÀN TẤT CHẠY TOÀN BỘ DỮ LIỆU KIỂM THỬ THỰC TẾ TRONG {duration:.2f} GIÂY")


if __name__ == "__main__":
    asyncio.run(main())
