"""
Vision, OCR, FDI Form Station and Document Parsing Schemas.
100% Pydantic V2 Type-Safe Schemas.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from core.constants import FDIProfileType, IdentityDocumentType


class Point2D(BaseModel):
    x: float
    y: float


class BoundingBox(BaseModel):
    top_left: Point2D
    bottom_right: Point2D


class OcrRequest(BaseModel):
    """Generic OCR request payload."""
    image_base64: Optional[str] = Field(default=None, description="Base64 encoded image string")
    image_url: Optional[str] = Field(default=None, description="URL of the image")
    lang_profile: FDIProfileType = Field(default=FDIProfileType.VIET_ENGLISH, description="Language profile")
    extract_structured: bool = Field(default=True, description="Parse into structured JSON")


class OcrTextBlock(BaseModel):
    text: str = Field(description="Văn bản bóc tách được")
    confidence: float = Field(ge=0.0, le=1.0, description="Độ tin cậy nhận diện")
    bounding_box: Optional[List[float]] = Field(default=None, description="Tọa độ [x_min, y_min, x_max, y_max]")


class OcrGeneralResponse(BaseModel):
    raw_text: str = Field(description="Toàn bộ nội dung văn bản trích xuất")
    blocks: List[OcrTextBlock] = Field(default_factory=list, description="Danh sách các đoạn văn bản kèm tọa độ")
    language: str = Field(default="vi", description="Ngôn ngữ chính phát hiện được")
    processing_time_ms: float = Field(default=0.0, description="Thời gian xử lý")


# ── 1. VAT Invoice Schemas ───────────────────────────────────────────────────

class InvoiceItemDto(BaseModel):
    item_name: str = Field(description="Tên hàng hóa, dịch vụ")
    unit: Optional[str] = Field(default=None, description="Đơn vị tính")
    quantity: float = Field(default=1.0, description="Số lượng")
    unit_price: float = Field(default=0.0, description="Đơn giá")
    total_amount: float = Field(default=0.0, description="Thành tiền chưa thuế")
    tax_rate: Optional[str] = Field(default=None, description="Thuế suất VAT (8%, 10%)")


class InvoiceDto(BaseModel):
    invoice_number: Optional[str] = Field(default=None, description="Số hóa đơn")
    invoice_series: Optional[str] = Field(default=None, description="Ký hiệu mẫu số/ký hiệu hóa đơn")
    invoice_date: Optional[str] = Field(default=None, description="Ngày lập hóa đơn (YYYY-MM-DD)")
    seller_name: Optional[str] = Field(default=None, description="Tên đơn vị bán hàng")
    seller_tax_code: Optional[str] = Field(default=None, description="Mã số thuế bên bán")
    seller_address: Optional[str] = Field(default=None, description="Địa chỉ bên bán")
    buyer_name: Optional[str] = Field(default=None, description="Tên đơn vị mua hàng")
    buyer_tax_code: Optional[str] = Field(default=None, description="Mã số thuế bên mua")
    buyer_address: Optional[str] = Field(default=None, description="Địa chỉ bên mua")
    items: List[InvoiceItemDto] = Field(default_factory=list, description="Danh mục hàng hóa")
    subtotal_amount: float = Field(default=0.0, description="Tổng tiền hàng chưa thuế")
    tax_amount: float = Field(default=0.0, description="Tiền thuế GTGT")
    total_payment: float = Field(default=0.0, description="Tổng tiền thanh toán bằng số")
    currency: str = Field(default="VND", description="Đơn vị tiền tệ")
    is_arithmetic_valid: bool = Field(default=True, description="Kiểm tra đối soát số học hợp lệ")


# ── 2. BoQ Bidding Table Schemas ─────────────────────────────────────────────

class BoqRowDto(BaseModel):
    stt: Optional[str] = Field(default=None, description="Số thứ tự")
    item_code: Optional[str] = Field(default=None, description="Mã hiệu công việc/vật tư")
    description: str = Field(description="Mô tả công việc, quy cách vật tư")
    unit: Optional[str] = Field(default=None, description="Đơn vị tính")
    quantity: float = Field(default=0.0, description="Khối lượng mời thầu")
    unit_price: float = Field(default=0.0, description="Đơn giá dự thầu")
    total_price: float = Field(default=0.0, description="Thành tiền dự thầu")


class BoqTableDto(BaseModel):
    project_name: Optional[str] = Field(default=None, description="Tên dự án/gói thầu")
    package_name: Optional[str] = Field(default=None, description="Tên hạng mục")
    rows: List[BoqRowDto] = Field(default_factory=list, description="Danh sách các dòng công tác BoQ")
    total_estimated_cost: float = Field(default=0.0, description="Tổng giá trị dự toán")


# ── 3. Identity Document (CCCD / Passport / Driver License) Schemas ──────────

class IdentityCardRequest(BaseModel):
    image_base64: Optional[str] = Field(default=None, description="Base64 ảnh mặt trước hoặc 2 mặt")
    image_url: Optional[str] = Field(default=None, description="URL ảnh giấy tờ")
    back_image_base64: Optional[str] = Field(default=None, description="Base64 ảnh mặt sau nếu có")


class IdentityCardResponse(BaseModel):
    document_type: IdentityDocumentType = Field(default=IdentityDocumentType.CCCD_CHIP, description="Loại giấy tờ")
    id_number: str = Field(description="Số định danh cá nhân / Số hộ chiếu / Số GPLX")
    full_name: str = Field(description="Họ và tên đầy đủ")
    date_of_birth: Optional[str] = Field(default=None, description="Ngày sinh (YYYY-MM-DD)")
    gender: Optional[str] = Field(default=None, description="Giới tính (Nam/Nữ/Khác)")
    nationality: str = Field(default="Việt Nam", description="Quốc tịch")
    origin_place: Optional[str] = Field(default=None, description="Quê quán")
    residence_place: Optional[str] = Field(default=None, description="Nơi thường trú / Địa chỉ cư trú")
    issue_date: Optional[str] = Field(default=None, description="Ngày cấp (YYYY-MM-DD)")
    expiry_date: Optional[str] = Field(default=None, description="Ngày hết hạn (YYYY-MM-DD)")
    issue_place: Optional[str] = Field(default=None, description="Nơi cấp")
    mrz_code: Optional[str] = Field(default=None, description="Chuỗi ký tự đọc máy MRZ nếu có")
    is_valid_checksum: bool = Field(default=True, description="Kiểm tra tính hợp lệ số định danh")
    province_code: Optional[str] = Field(default=None, description="Mã tỉnh/thành phố khai sinh")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="Độ tin cậy tổng thể")


# ── 4. FDI Form Station Schemas ──────────────────────────────────────────────

class FDIStationRequest(BaseModel):
    """Payload for hand-free FDI Form Station."""
    station_id: str = Field(default="STATION-01", description="Station hardware identifier")
    qr_code_metadata: Optional[str] = Field(default=None, description="Fast-scanned QR identifier")
    four_corner_points: Optional[List[Point2D]] = Field(default=None, description="Detected 4 corners for homography")
    image_base64: str = Field(description="High-res raw image captured from overhead camera")
    lang_profile: FDIProfileType = Field(default=FDIProfileType.VIET_ENGLISH)


class RoiFieldDefinition(BaseModel):
    field_name: str = Field(description="Tên trường dữ liệu chuẩn hóa")
    bbox: List[float] = Field(description="Tọa độ [x_min, y_min, x_max, y_max] chuẩn hóa (0.0 - 1.0)")
    data_type: str = Field(default="STRING", description="Kiểu dữ liệu: STRING, NUMBER, DATE, SIGNATURE")
    language: str = Field(default="VI", description="Ngôn ngữ trường: VI, EN, ZH, KO, JA")


class FdiFieldDto(BaseModel):
    field_key: str = Field(description="Mã định danh trường")
    field_label: str = Field(description="Nhãn hiển thị trường")
    extracted_value: str = Field(description="Giá trị bóc tách được")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Độ tin cậy nhận diện")
    is_valid: bool = Field(default=True, description="Hợp lệ theo schema validation")


class FdiFormDto(BaseModel):
    template_code: str = Field(description="Mã mẫu biểu mẫu")
    partner_profile: FDIProfileType = Field(default=FDIProfileType.VIET_ENGLISH, description="Hồ sơ ngôn ngữ FDI")
    document_code: Optional[str] = Field(default=None, description="Mã chứng từ")
    fields: List[FdiFieldDto] = Field(default_factory=list, description="Danh sách các trường bóc tách")
    has_signature: bool = Field(default=False, description="Có chữ ký tại hiện trường")
    processing_time_ms: float = Field(default=0.0, description="Thời gian xử lý tính bằng ms")


class FdiExtractionResponse(BaseModel):
    template_code: Optional[str] = Field(default=None, description="Mã mẫu biểu mẫu")
    document_code: Optional[str] = Field(default=None, description="Mã chứng từ bóc tách")
    extracted_fields: Dict[str, Any] = Field(default_factory=dict, description="Các trường dữ liệu trích xuất")
    confidence_scores: Dict[str, float] = Field(default_factory=dict, description="Độ tin cậy từng trường")
    has_signature: bool = Field(default=False, description="Xác nhận có chữ ký tại hiện trường")
    processing_time_ms: float = Field(default=0.0, description="Thời gian xử lý")

