"""
CRM Database Tools and Entity Resolver.
Simulates and connects to PostgreSQL / pgvector CRM database to resolve Customers, Products, and Stock.
"""

from typing import List, Optional, Dict, Any
from schemas.chat_crm import DraftCustomerSchema, DraftOrderItemSchema
from core.telemetry import logger


# In-memory realistic CRM mock catalog for instant demonstration & testing
MOCK_TENANT_CUSTOMERS: Dict[str, List[Dict[str, Any]]] = {
    "shop-default-01": [
        {
            "id": "cust-001",
            "name": "Nguyễn Văn Tuấn",
            "phone": "0912345678",
            "address": "Phòng 3006 Tòa B - Chung cư Sky Garden",
            "code": "3006B",
            "aliases": ["anh tuấn", "3006b", "a tuấn"]
        },
        {
            "id": "cust-002",
            "name": "Trần Thị Mai",
            "phone": "0987654321",
            "address": "Số 45 Tràng Tiền, Hoàn Kiếm, Hà Nội",
            "code": "KH-002",
            "aliases": ["chị mai", "chị mai tràng tiền"]
        },
        {
            "id": "cust-003",
            "name": "Lê Hoàng Long",
            "phone": "0905123456",
            "address": "Phòng 1204 Tòa A1",
            "code": "1204A1",
            "aliases": ["long 1204", "1204a1"]
        }
    ]
}

MOCK_TENANT_PRODUCTS: Dict[str, List[Dict[str, Any]]] = {
    "shop-default-01": [
        {
            "id": "prod-001",
            "sku": "XOI-LAC-01",
            "name": "Xôi Lạc Ruốc Hành",
            "price": 10000.0,
            "stock": 50,
            "aliases": ["xôi", "xoi", "xoi lac", "xôi lạc"]
        },
        {
            "id": "prod-002",
            "sku": "BM-PATE-02",
            "name": "Bánh Mì Pate Cột Đèn",
            "price": 15000.0,
            "stock": 40,
            "aliases": ["bm", "banh mi", "bánh mì", "bm pate"]
        },
        {
            "id": "prod-003",
            "sku": "BM-TRUNG-03",
            "name": "Bánh Mì Trứng Ốp La",
            "price": 12000.0,
            "stock": 30,
            "aliases": ["bm trung", "bánh mì trứng"]
        },
        {
            "id": "prod-004",
            "sku": "LAU-THAI-CAY",
            "name": "Combo Lẩu Thái Cay Đặc Biệt",
            "price": 250000.0,
            "stock": 15,
            "aliases": ["lẩu thái cay", "lau thai cay", "combo lẩu thái"]
        },
        {
            "id": "prod-005",
            "sku": "COCA-LON-01",
            "name": "Coca Cola Lon 330ml",
            "price": 10000.0,
            "stock": 100,
            "aliases": ["coca", "co ca", "nước ngọt"]
        }
    ]
}


class CrmTools:
    """CRM Database Tool Adapter for Customer & Product Entity Grounding."""

    @staticmethod
    def resolve_customer(
        tenant_id: str,
        phone: Optional[str] = None,
        code: Optional[str] = None,
        raw_text: Optional[str] = None
    ) -> DraftCustomerSchema:
        """
        Lookup customer in CRM DB by phone, room code, or name alias.
        """
        customers = MOCK_TENANT_CUSTOMERS.get(tenant_id, MOCK_TENANT_CUSTOMERS["shop-default-01"])
        lower_raw = (raw_text or "").lower()

        # 1. Match exact phone
        if phone:
            for c in customers:
                if c["phone"] == phone:
                    return DraftCustomerSchema(
                        customer_id=c["id"],
                        full_name=c["name"],
                        phone=c["phone"],
                        delivery_address=c["address"],
                        confidence=0.98
                    )

        # 2. Match exact code (e.g. 3006B, 1204A1)
        if code:
            for c in customers:
                if c["code"].lower() == code.lower():
                    return DraftCustomerSchema(
                        customer_id=c["id"],
                        full_name=c["name"],
                        phone=c["phone"],
                        delivery_address=c["address"],
                        confidence=0.96
                    )

        # 3. Match alias in raw text
        for c in customers:
            for alias in c["aliases"]:
                if alias in lower_raw:
                    return DraftCustomerSchema(
                        customer_id=c["id"],
                        full_name=c["name"],
                        phone=c["phone"],
                        delivery_address=c["address"],
                        confidence=0.92
                    )

        # Fallback customer from raw token
        return DraftCustomerSchema(
            customer_id=None,
            full_name=code or "Khách lẻ tại quầy",
            phone=phone,
            delivery_address=code,
            confidence=0.75
        )

    @staticmethod
    def resolve_product(
        tenant_id: str,
        token: str,
        price_hint: Optional[float] = None
    ) -> DraftOrderItemSchema:
        """
        Lookup product in CRM catalog by SKU or alias.
        """
        products = MOCK_TENANT_PRODUCTS.get(tenant_id, MOCK_TENANT_PRODUCTS["shop-default-01"])
        token_clean = token.strip().lower()

        best_prod = None
        best_score = 0.0

        for p in products:
            # Exact SKU match
            if p["sku"].lower() == token_clean:
                best_prod = p
                best_score = 0.99
                break

            # Alias match
            for alias in p["aliases"]:
                if alias == token_clean:
                    best_prod = p
                    best_score = 0.95
                    break
                elif alias in token_clean or token_clean in alias:
                    if 0.85 > best_score:
                        best_prod = p
                        best_score = 0.85

        if best_prod:
            final_price = price_hint if price_hint and price_hint > 0 else best_prod["price"]
            return DraftOrderItemSchema(
                raw_text=token,
                product_id=best_prod["id"],
                product_name=best_prod["name"],
                sku=best_prod["sku"],
                quantity=1,
                unit_price=final_price,
                total_amount=final_price,
                confidence=best_score
            )

        # Fallback product item
        fallback_price = price_hint or 10000.0
        return DraftOrderItemSchema(
            raw_text=token,
            product_id=None,
            product_name=token.capitalize(),
            sku=None,
            quantity=1,
            unit_price=fallback_price,
            total_amount=fallback_price,
            confidence=0.70
        )


crm_tools = CrmTools()
