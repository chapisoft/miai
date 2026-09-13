"""
Pydantic Schemas for CRM Quick Order Chat Assistant.
100% Pydantic V2 Type-Safe Schemas for Multi-App, Multi-Partner & Multi-Tenant Conversational Slot-Filling.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from core.constants import OrderIntent, PaymentMethod


class DraftOrderItemSchema(BaseModel):
    raw_text: str = Field(description="Cụm từ gốc chỉ sản phẩm trong câu chat")
    product_id: Optional[str] = Field(default=None, description="ID sản phẩm trong CRM nếu khớp")
    product_name: str = Field(description="Tên sản phẩm chuẩn hóa")
    sku: Optional[str] = Field(default=None, description="Mã SKU")
    quantity: int = Field(default=1, description="Số lượng đặt")
    unit_name: Optional[str] = Field(default=None, description="Đơn vị tính / Quy cách (thùng, lon, ly, suất, cái)")
    unit_price: Optional[float] = Field(default=None, description="Đơn giá")
    total_amount: Optional[float] = Field(default=None, description="Thành tiền")
    notes: Optional[str] = Field(default=None, description="Ghi chú định lượng theo số tiền hoặc quy cách")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="Độ tin cậy khớp sản phẩm")


class DraftCustomerSchema(BaseModel):
    customer_id: Optional[str] = Field(default=None, description="ID khách hàng trong CRM nếu khớp")
    full_name: Optional[str] = Field(default=None, description="Tên khách hàng")
    phone: Optional[str] = Field(default=None, description="Số điện thoại")
    delivery_address: Optional[str] = Field(default=None, description="Địa chỉ giao hàng / Mã phòng")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="Độ tin cậy khớp khách hàng")


class DraftOrderResponse(BaseModel):
    session_id: str = Field(description="ID phiên hội thoại")
    app_id: str = Field(default="chapi", description="Định danh ứng dụng phát sinh request")
    partner_id: Optional[str] = Field(default=None, description="Định danh đối tác kết nối")
    tenant_id: str = Field(default="shop-default-01", description="ID gian hàng / Shop")
    domain_code: Optional[str] = Field(default="FNB", description="Mã ngành nghề kinh doanh")
    intent: OrderIntent = Field(default=OrderIntent.ORDER, description="Ý định nhận diện: ORDER | PURCHASE | INQUIRY")
    overall_confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="Độ tin cậy tổng thể")
    customer: DraftCustomerSchema = Field(default_factory=DraftCustomerSchema, description="Thông tin khách hàng")
    items: List[DraftOrderItemSchema] = Field(default_factory=list, description="Danh sách mặt hàng")
    total_order_amount: Optional[float] = Field(default=None, description="Tổng tiền đơn hàng")
    payment_method: PaymentMethod = Field(default=PaymentMethod.CASH, description="Phương thức thanh toán")
    shipping_note: Optional[str] = Field(default=None, description="Ghi chú giao hàng")
    needs_clarification: bool = Field(default=False, description="Có cần hỏi lại Saler để làm rõ không")
    clarification_question: Optional[str] = Field(default=None, description="Câu hỏi làm rõ nếu có điểm mơ hồ")
    quick_options: Optional[List[str]] = Field(default=None, description="Các nút chọn nhanh gợi ý cho Saler")
    processing_time_ms: float = Field(default=0.0, description="Thời gian xử lý")


class ChatParseRequest(BaseModel):
    message: str = Field(description="Nội dung câu chat của Saler (ví dụ: '3006B 10k xoi lac 2 bm gv')")
    app_id: str = Field(default="chapi", description="Định danh ứng dụng: chapi | nexaflow | pos_kiosk")
    partner_id: Optional[str] = Field(default=None, description="Định danh đối tác / cổng kết nối")
    tenant_id: str = Field(default="shop-default-01", description="ID gian hàng / Shop")
    domain_code: Optional[str] = Field(default="FNB", description="Mã phân loại ngành nghề: FNB | RETAIL | FASHION")
    saler_id: Optional[str] = Field(default="saler-01", description="ID nhân viên bán hàng")


class CorrectionItemDto(BaseModel):
    raw_token: str = Field(description="Cụm từ gốc gõ tắt")
    corrected_product_id: Optional[str] = Field(default=None, description="ID sản phẩm thực tế chọn")
    corrected_customer_id: Optional[str] = Field(default=None, description="ID khách hàng thực tế chọn")


class ChatConfirmRequest(BaseModel):
    session_id: str = Field(description="ID phiên chat")
    app_id: str = Field(default="chapi", description="Định danh ứng dụng")
    partner_id: Optional[str] = Field(default=None, description="Định danh đối tác")
    tenant_id: str = Field(default="shop-default-01", description="ID gian hàng")
    order_id: Optional[str] = Field(default=None, description="ID đơn hàng được lưu trong CRM")
    corrections: List[CorrectionItemDto] = Field(default_factory=list, description="Danh sách chỉnh sửa của Saler")
    is_confirmed: bool = Field(default=True, description="Xác nhận tạo đơn thành công")


class AliasCreateRequest(BaseModel):
    app_id: str = Field(default="chapi", description="Định danh ứng dụng")
    tenant_id: str = Field(description="ID gian hàng")
    raw_token: str = Field(description="Từ lóng / từ viết tắt (ví dụ: 'bm', 'xoi')")
    target_type: str = Field(default="PRODUCT", description="Loại ánh xạ: PRODUCT | CUSTOMER")
    target_id: str = Field(description="ID sản phẩm hoặc ID khách hàng trong CRM")
    target_name: str = Field(description="Tên hiển thị chuẩn hóa")


class AliasItemDto(BaseModel):
    raw_token: str
    target_type: str
    target_id: str
    target_name: str
    usage_count: int = 1


class AliasListResponse(BaseModel):
    app_id: str = "chapi"
    tenant_id: str
    aliases: List[AliasItemDto] = Field(default_factory=list)
