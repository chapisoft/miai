import re
import json
import unicodedata
from typing import List, Optional, Dict, Any
import redis
from schemas.chat_crm import DraftCustomerSchema, DraftOrderItemSchema
from core.config import settings
from core.telemetry import logger


def remove_accents(text: str) -> str:
    """Strip Vietnamese diacritics for flexible fuzzy matching."""
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.replace('đ', 'd').replace('Đ', 'D').lower()


# Default in-memory realistic CRM catalog fallback
MOCK_TENANT_CUSTOMERS: Dict[str, List[Dict[str, Any]]] = {
    "shop-default-01": [
        {
            "id": "cust-001",
            "name": "Nguyễn Văn Tuấn",
            "phone": "0912345678",
            "address": "Phòng 3006 Tòa B - Chung cư Sky Garden",
            "code": "3006B",
            "aliases": ["anh tuấn", "3006b", "a tuấn", "tuấn", "tuan"]
        },
        {
            "id": "cust-002",
            "name": "Trần Thị Mai",
            "phone": "0987654321",
            "address": "Số 45 Tràng Tiền, Hoàn Kiếm, Hà Nội",
            "code": "KH-002",
            "aliases": ["chị mai", "chị mai tràng tiền", "mai", "c mai"]
        },
        {
            "id": "cust-003",
            "name": "Lê Hoàng Long",
            "phone": "0905123456",
            "address": "Phòng 1204 Tòa A1",
            "code": "1204A1",
            "aliases": ["long 1204", "1204a1", "anh long", "long"]
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
            "unit": "suất",
            "stock": 50,
            "aliases": ["xôi", "xoi", "xoi lac", "xôi lạc", "xôi xéo"]
        },
        {
            "id": "prod-002",
            "sku": "BM-PATE-02",
            "name": "Bánh Mì Pate Cột Đèn",
            "price": 15000.0,
            "unit": "cái",
            "stock": 40,
            "aliases": ["bm", "banh mi", "bánh mì", "bm pate", "bánh mì pate", "bánh mỳ"]
        },
        {
            "id": "prod-003",
            "sku": "BM-TRUNG-03",
            "name": "Bánh Mì Trứng Ốp La",
            "price": 12000.0,
            "unit": "cái",
            "stock": 30,
            "aliases": ["bm trung", "bánh mì trứng", "bm trứng"]
        },
        {
            "id": "prod-004",
            "sku": "LAU-THAI-CAY",
            "name": "Combo Lẩu Thái Cay Đặc Biệt",
            "price": 250000.0,
            "unit": "nồi",
            "stock": 15,
            "aliases": ["lẩu thái cay", "lau thai cay", "combo lẩu thái", "lẩu thái", "lẩu"]
        },
        {
            "id": "prod-005",
            "sku": "COCA-LON-01",
            "name": "Coca Cola Lon 330ml",
            "price": 10000.0,
            "unit": "lon",
            "stock": 100,
            "aliases": ["coca", "co ca", "coca lon", "nước ngọt"]
        },
        {
            "id": "prod-006",
            "sku": "BIA-TIGER-THUNG",
            "name": "Bia Tiger Nâu (Thùng 24 lon)",
            "price": 320000.0,
            "unit": "thùng",
            "stock": 80,
            "aliases": ["bia tiger", "tiger", "bia", "thung bia tiger"]
        },
        {
            "id": "prod-007",
            "sku": "PHO-BO-TAI",
            "name": "Phở Bò Tái Lăn",
            "price": 45000.0,
            "unit": "bát",
            "stock": 60,
            "aliases": ["phở bò", "pho bo", "phở", "pho"]
        },
        {
            "id": "prod-008",
            "sku": "CF-SUA-DA",
            "name": "Cà Phê Sữa Đá Sài Gòn",
            "price": 25000.0,
            "unit": "ly",
            "stock": 90,
            "aliases": ["cà phê sữa", "cafe sữa", "cf sữa", "nâu đá", "cafe sua"]
        }
    ]
}


class CrmTools:
    """CRM Database Tool Adapter for Customer & Product Entity Grounding with Multi-App & Multi-Tenant Redis Grounding Store."""

    def __init__(self):
        self._redis_client = None

    def _get_redis(self) -> Optional[redis.Redis]:
        if self._redis_client is None:
            try:
                self._redis_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD or None,
                    db=settings.REDIS_DB,
                    decode_responses=True,
                    socket_timeout=0.3,
                    socket_connect_timeout=0.3
                )
            except Exception as e:
                logger.warning(f"Could not connect to Redis: {e}")
                self._redis_client = None
        return self._redis_client

    def get_products_for_tenant(self, app_id: str = "chapi", tenant_id: str = "shop-default-01") -> List[Dict[str, Any]]:
        """Fetch active products for app and tenant from Redis with fallback to in-memory catalog."""
        r = self._get_redis()
        if r:
            try:
                # 1. Try standardized hierarchical key: miai:knowledge:{app_id}:{tenant_id}:catalog
                raw_json = r.get(f"miai:knowledge:{app_id}:{tenant_id}:catalog")
                if not raw_json:
                    # 2. Fallback to legacy key: crm:catalog:{tenant_id}
                    raw_json = r.get(f"crm:catalog:{tenant_id}")

                if raw_json:
                    parsed = json.loads(raw_json)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        return parsed
            except Exception as e:
                logger.debug(f"Redis catalog lookup failed for app={app_id}, tenant={tenant_id}: {e}")

        # Fallback to in-memory mock catalog
        mock_key = tenant_id
        return MOCK_TENANT_PRODUCTS.get(mock_key, MOCK_TENANT_PRODUCTS.get("shop-default-01", []))

    def get_customers_for_tenant(self, app_id: str = "chapi", tenant_id: str = "shop-default-01") -> List[Dict[str, Any]]:
        """Fetch active customers for app and tenant from Redis with fallback to in-memory catalog."""
        r = self._get_redis()
        if r:
            try:
                # 1. Try standardized hierarchical key: miai:knowledge:{app_id}:{tenant_id}:customers
                raw_json = r.get(f"miai:knowledge:{app_id}:{tenant_id}:customers")
                if not raw_json:
                    # 2. Fallback to legacy key: crm:customers:{tenant_id}
                    raw_json = r.get(f"crm:customers:{tenant_id}")

                if raw_json:
                    parsed = json.loads(raw_json)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        return parsed
            except Exception as e:
                logger.debug(f"Redis customer lookup failed for app={app_id}, tenant={tenant_id}: {e}")

        mock_key = tenant_id
        return MOCK_TENANT_CUSTOMERS.get(mock_key, MOCK_TENANT_CUSTOMERS.get("shop-default-01", []))

    def resolve_customer(
        self,
        tenant_id: str,
        phone: Optional[str] = None,
        code: Optional[str] = None,
        raw_text: Optional[str] = None,
        app_id: str = "chapi"
    ) -> DraftCustomerSchema:
        """
        Lookup customer in CRM DB by phone, room code, or name alias with App and Tenant isolation.
        """
        customers = self.get_customers_for_tenant(app_id=app_id, tenant_id=tenant_id)
        raw_norm = remove_accents(raw_text or "")

        # 1. Match exact phone
        if phone:
            for c in customers:
                if c.get("phone") == phone:
                    return DraftCustomerSchema(
                        customer_id=c.get("id"),
                        full_name=c.get("name"),
                        phone=c.get("phone"),
                        delivery_address=c.get("address"),
                        confidence=0.98
                    )

        # 2. Match exact code (e.g. 3006B, 1204A1)
        if code:
            code_norm = remove_accents(code)
            for c in customers:
                if remove_accents(c.get("code") or "") == code_norm:
                    return DraftCustomerSchema(
                        customer_id=c.get("id"),
                        full_name=c.get("name"),
                        phone=c.get("phone"),
                        delivery_address=c.get("address"),
                        confidence=0.96
                    )

        # 3. Match aliases and name fragments in raw text
        best_match = None
        best_score = 0.0

        for c in customers:
            # Check full name match
            cust_name_norm = remove_accents(c.get("name") or "")
            if cust_name_norm and cust_name_norm in raw_norm:
                return DraftCustomerSchema(
                    customer_id=c.get("id"),
                    full_name=c.get("name"),
                    phone=c.get("phone"),
                    delivery_address=c.get("address"),
                    confidence=0.95
                )

            # Check individual aliases
            for alias in c.get("aliases", []):
                alias_norm = remove_accents(alias)
                if not alias_norm:
                    continue
                # Word boundary search
                if re.search(rf"\b{re.escape(alias_norm)}\b", raw_norm):
                    score = 0.93 if len(alias_norm) > 3 else 0.88
                    if score > best_score:
                        best_score = score
                        best_match = c

        if best_match:
            return DraftCustomerSchema(
                customer_id=best_match.get("id"),
                full_name=best_match.get("name"),
                phone=best_match.get("phone"),
                delivery_address=best_match.get("address"),
                confidence=best_score
            )

        # Fallback customer from raw token
        return DraftCustomerSchema(
            customer_id=None,
            full_name=code or "Khách lẻ tại quầy",
            phone=phone,
            delivery_address=code,
            confidence=0.75
        )

    def resolve_product(
        self,
        tenant_id: str,
        token: str,
        price_hint: Optional[float] = None,
        app_id: str = "chapi"
    ) -> DraftOrderItemSchema:
        """
        Lookup product in CRM catalog by SKU, name, or alias with App and Tenant isolation.
        """
        products = self.get_products_for_tenant(app_id=app_id, tenant_id=tenant_id)
        token_clean = token.strip().lower()
        token_norm = remove_accents(token_clean)

        best_prod = None
        best_score = 0.0

        for p in products:
            sku_norm = remove_accents(p.get("sku") or "")
            name_norm = remove_accents(p.get("name") or "")
            prod_price = float(p.get("price") or 0.0)

            # 1. Exact SKU match
            if sku_norm and sku_norm == token_norm:
                best_prod = p
                best_score = 0.99
                break

            # 2. Exact or near-exact Name match
            if name_norm and name_norm == token_norm:
                best_prod = p
                best_score = 0.98
                break

            # 3. Alias exact match
            for alias in p.get("aliases", []):
                alias_norm = remove_accents(alias)
                if not alias_norm:
                    continue
                if alias_norm == token_norm:
                    # If price hint is provided and matches this product's price exactly, boost score
                    if price_hint and abs(price_hint - prod_price) < 1.0:
                        best_prod = p
                        best_score = 0.98
                        break
                    elif 0.95 > best_score:
                        best_prod = p
                        best_score = 0.95
                elif alias_norm in token_norm or token_norm in alias_norm:
                    # Substring match
                    match_score = 0.88 if len(token_norm) > 2 else 0.80
                    if price_hint and abs(price_hint - prod_price) < 1.0:
                        match_score += 0.08
                    if match_score > best_score:
                        best_prod = p
                        best_score = match_score

            # 4. Partial SKU prefix match
            if sku_norm and token_norm in sku_norm and len(token_norm) >= 3:
                if 0.90 > best_score:
                    best_prod = p
                    best_score = 0.90

        if best_prod:
            prod_price = float(best_prod.get("price") or 0.0)
            final_price = price_hint if (price_hint and price_hint > 0) else prod_price
            return DraftOrderItemSchema(
                raw_text=token,
                product_id=best_prod.get("id"),
                product_name=best_prod.get("name"),
                sku=best_prod.get("sku"),
                quantity=1,
                unit_name=best_prod.get("unit"),
                unit_price=final_price,
                total_amount=final_price,
                confidence=best_score
            )

        # Fallback product item
        fallback_price = price_hint or 10000.0
        return DraftOrderItemSchema(
            raw_text=token,
            product_id=None,
            product_name=token.strip().capitalize(),
            sku=None,
            quantity=1,
            unit_name="cái",
            unit_price=fallback_price,
            total_amount=fallback_price,
            confidence=0.70
        )


crm_tools = CrmTools()
