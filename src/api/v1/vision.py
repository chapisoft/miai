"""
Vision, OCR, FDI Form Station, Identity Card, and Document Parsing API Endpoints.
"""

from fastapi import APIRouter, Depends
from schemas.vision import (
    OcrRequest,
    OcrGeneralResponse,
    InvoiceDto,
    BoqTableDto,
    IdentityCardRequest,
    IdentityCardResponse,
    FDIStationRequest,
    FdiExtractionResponse,
    FdiFormDto,
    FdiFieldDto,
)
from core.responses import ApiResponse
from engines.vision.ocr_reader import ocr_reader
from engines.vision.roi_extractor import roi_extractor, RoiExtractor
from engines.vision.invoice_parser import invoice_parser
from engines.vision.boq_parser import boq_parser
from engines.vision.identity_parser import identity_parser
from api.dependencies import get_current_user

router = APIRouter(prefix="/vision", tags=["Vision AI & Document OCR"])


@router.post("/ocr/extract", response_model=ApiResponse[OcrGeneralResponse], summary="OCR tổng quát nhận diện text và tọa độ")
@router.post("/ocr", response_model=ApiResponse[OcrGeneralResponse], summary="Nhận diện ký tự quang học (OCR)")
async def extract_ocr(
    request: OcrRequest,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[OcrGeneralResponse]:
    """Extracts raw text and bounding blocks from an image."""
    result = await ocr_reader.extract_general_ocr(request.image_base64 or "")
    return ApiResponse.success(data=result, message="OCR text extracted successfully")


@router.post("/identity/extract", response_model=ApiResponse[IdentityCardResponse], summary="Bóc tách giấy tờ tùy thân (CCCD / Hộ chiếu / GPLX)")
async def extract_identity_card(
    request: IdentityCardRequest,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[IdentityCardResponse]:
    """Parses Vietnamese CCCD, CMND, Passport, or Driver License with checksum validation."""
    result = await identity_parser.parse_identity_document(request)
    return ApiResponse.success(data=result, message="Identity document parsed successfully")


@router.post("/invoice/extract", response_model=ApiResponse[InvoiceDto], summary="Bóc tách hóa đơn điện tử GTGT (VAT Invoice)")
@router.post("/invoice", response_model=ApiResponse[InvoiceDto], summary="Bóc tách hóa đơn điện tử GTGT")
async def extract_vat_invoice(
    request: OcrRequest,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[InvoiceDto]:
    """Parses VAT invoice image into structured InvoiceDto with arithmetic validation."""
    raw_ocr = await ocr_reader.read_text_from_image(request.image_base64 or "")
    parsed_invoice = await invoice_parser.parse_text(raw_ocr)
    return ApiResponse.success(data=parsed_invoice, message="VAT invoice parsed successfully")


@router.post("/fdi/extract", response_model=ApiResponse[FdiFormDto], summary="Bóc tách biểu mẫu FDI Form Station rảnh tay")
@router.post("/fdi-form", response_model=ApiResponse[FdiFormDto], summary="Bóc tách biểu mẫu FDI")
async def extract_fdi_form(
    template_code: str = "FDI_INBOUND_DELIVERY_V1",
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[FdiFormDto]:
    """Simulates high-speed template ROI extraction for FDI factory receipt/scale station."""
    mock_detected_text = {
        "po_number": "PO-FDI-2026-9901",
        "delivery_date": "2026-09-12",
        "vendor_name": "Công ty TNHH Cơ Khí Chính Xác Precision Tech",
        "net_weight": "14250.5",
        "gross_weight": "15680.0",
        "driver_name": "Nguyễn Văn Tuấn",
        "vehicle_plate": "29C-889.23",
        "first_weight": "15680.0",
        "second_weight": "14250.5",
        "cargo_weight": "1429.5"
    }
    extracted_form = RoiExtractor.extract_from_mock_image(
        template_code=template_code,
        detected_text_map=mock_detected_text,
        execution_time_ms=115.0
    )
    return ApiResponse.success(data=extracted_form, message="FDI form parsed successfully")


@router.post("/boq/extract", response_model=ApiResponse[BoqTableDto], summary="Bóc tách bảng khối lượng dự toán đấu thầu (BoQ Table)")
@router.post("/boq", response_model=ApiResponse[BoqTableDto], summary="Bóc tách bảng BoQ")
async def extract_boq_table(
    request: OcrRequest,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[BoqTableDto]:
    """Parses BoQ document image into structured BoqTableDto."""
    raw_ocr = await ocr_reader.read_text_from_image(request.image_base64 or "")
    parsed_boq = await boq_parser.parse_text(raw_ocr)
    return ApiResponse.success(data=parsed_boq, message="BoQ table parsed successfully")
