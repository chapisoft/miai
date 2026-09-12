"""
Adaptive Feedback and In-Context Self-Learning Module for CRM Chat Assistant.
Stores learned aliases per tenant and builds dynamic Few-Shot contexts for System Prompts.
"""

from typing import Dict, List, Any, Optional
from schemas.chat_crm import AliasItemDto, CorrectionItemDto
from core.telemetry import logger


class FeedbackLearner:
    """Manages tenant-specific token mappings and few-shot memory."""

    def __init__(self):
        # In-memory dictionary: tenant_id -> list of AliasItemDto
        self._tenant_aliases: Dict[str, Dict[str, AliasItemDto]] = {
            "shop-default-01": {
                "bm": AliasItemDto(
                    raw_token="bm",
                    target_type="PRODUCT",
                    target_id="prod-002",
                    target_name="Bánh Mì Pate Cột Đèn",
                    usage_count=12
                ),
                "xoi lac": AliasItemDto(
                    raw_token="xoi lac",
                    target_type="PRODUCT",
                    target_id="prod-001",
                    target_name="Xôi Lạc Ruốc Hành",
                    usage_count=8
                ),
                "3006b": AliasItemDto(
                    raw_token="3006b",
                    target_type="CUSTOMER",
                    target_id="cust-001",
                    target_name="Nguyễn Văn Tuấn (3006B)",
                    usage_count=15
                )
            }
        }
        self._session_history: List[Dict[str, Any]] = []

    def get_aliases(self, tenant_id: str) -> List[AliasItemDto]:
        """Return all learned aliases for a tenant."""
        aliases_map = self._tenant_aliases.get(tenant_id, {})
        return list(aliases_map.values())

    def record_alias(
        self,
        tenant_id: str,
        raw_token: str,
        target_type: str,
        target_id: str,
        target_name: str
    ) -> AliasItemDto:
        """Store or increment usage count of an alias for a tenant."""
        if tenant_id not in self._tenant_aliases:
            self._tenant_aliases[tenant_id] = {}

        token_key = raw_token.strip().lower()
        if token_key in self._tenant_aliases[tenant_id]:
            item = self._tenant_aliases[tenant_id][token_key]
            item.usage_count += 1
            item.target_id = target_id
            item.target_name = target_name
            return item

        new_item = AliasItemDto(
            raw_token=token_key,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            usage_count=1
        )
        self._tenant_aliases[tenant_id][token_key] = new_item
        logger.info("Learned new alias for tenant %s: '%s' -> %s (%s)", tenant_id, token_key, target_name, target_id)
        return new_item

    def process_confirmation(
        self,
        session_id: str,
        tenant_id: str,
        order_id: Optional[str],
        corrections: List[CorrectionItemDto]
    ) -> None:
        """Process saler confirmation and correction feedback."""
        for corr in corrections:
            if corr.corrected_product_id:
                self.record_alias(
                    tenant_id=tenant_id,
                    raw_token=corr.raw_token,
                    target_type="PRODUCT",
                    target_id=corr.corrected_product_id,
                    target_name=f"Sản phẩm {corr.corrected_product_id}"
                )
            elif corr.corrected_customer_id:
                self.record_alias(
                    tenant_id=tenant_id,
                    raw_token=corr.raw_token,
                    target_type="CUSTOMER",
                    target_id=corr.corrected_customer_id,
                    target_name=f"Khách hàng {corr.corrected_customer_id}"
                )

        self._session_history.append({
            "session_id": session_id,
            "tenant_id": tenant_id,
            "order_id": order_id,
            "corrections_count": len(corrections)
        })

    def build_few_shot_prompt(self, tenant_id: str) -> str:
        """Generate dynamic few-shot in-context learning string for System Prompt."""
        aliases = self.get_aliases(tenant_id)
        if not aliases:
            return ""

        lines = ["=== TỪ ĐIỂN TỪ LÓNG & VIẾT TẮT ĐÃ HỌC CỦA GIAN HÀNG ==="]
        for a in aliases[:10]:
            lines.append(f'- "{a.raw_token}" -> {a.target_type}: "{a.target_name}" (ID: {a.target_id})')

        lines.append("\n=== CÁC VÍ DỤ TẠO ĐƠN THÀNH CÔNG GẦN ĐÂY ===")
        lines.append('Saler: "3006B 10k xoi lac 2 bm gv"')
        lines.append('-> Khách: 3006B (Nguyễn Văn Tuấn), Món: [Xôi Lạc Ruốc Hành x 1 (10.000đ), Bánh Mì Pate x 2 (30.000đ)], Ghi chú: "Giao việc/Giao ngay"')

        return "\n".join(lines)


feedback_learner = FeedbackLearner()
