"""
Unit Tests for CRM AI Chat Quick Order Engine.
Tests NLU Preprocessor, CRM Entity Matcher, Feedback Learner, and State Graph Orchestrator.
"""

import pytest
from engines.chat_crm.nlu_preprocessor import nlu_preprocessor
from engines.chat_crm.crm_tools import crm_tools
from engines.chat_crm.feedback_learner import feedback_learner, FeedbackLearner
from engines.chat_crm.structured_extractor import structured_extractor
from engines.chat_crm.conversation_graph import conversation_graph
from schemas.chat_crm import (
    ChatParseRequest,
    ChatConfirmRequest,
    CorrectionItemDto,
)
from core.constants import OrderIntent, PaymentMethod


# ── 1. NLU Preprocessor Unit Tests ───────────────────────────────────────────

def test_nlu_parse_price_token():
    """Tests Vietnamese price normalization across diverse slang patterns."""
    assert nlu_preprocessor.parse_price_token("10k") == 10000.0
    assert nlu_preprocessor.parse_price_token("25k") == 25000.0
    assert nlu_preprocessor.parse_price_token("1.5tr") == 1500000.0
    assert nlu_preprocessor.parse_price_token("50tr") == 50000000.0


def test_nlu_extract_raw_entities():
    """Tests raw regex entity extraction from sales chat message."""
    text = "3006B 10k xoi lac 2 bm gv ck"
    entities = nlu_preprocessor.extract_raw_entities(text)
    
    assert entities["intent"] == OrderIntent.ORDER
    assert entities["payment_method"] == PaymentMethod.BANK_TRANSFER
    assert entities["room_code"] == "3006B"
    assert "Giao việc/Giao ngay" in entities["shipping_note"]


def test_nlu_extract_phone_number():
    """Tests Vietnamese 10-digit mobile phone extraction."""
    text = "giao cho chị Mai 0987654321 ở Tràng Tiền"
    entities = nlu_preprocessor.extract_raw_entities(text)
    assert entities["phone"] == "0987654321"


def test_nlu_detect_intent():
    """Tests intent classification for ORDER vs PURCHASE vs INQUIRY."""
    assert nlu_preprocessor.detect_intent("chốt đơn 2 bm cho chị Lan") == OrderIntent.ORDER
    assert nlu_preprocessor.detect_intent("nhập 50 thùng bia từ nhà cung cấp") == OrderIntent.PURCHASE
    assert nlu_preprocessor.detect_intent("sản phẩm này giá bao nhiêu còn hàng không") == OrderIntent.INQUIRY


def test_nlu_extract_payment_method():
    """Tests payment method detection."""
    assert nlu_preprocessor.extract_payment_method("khách ck qua vietcombank") == PaymentMethod.BANK_TRANSFER
    assert nlu_preprocessor.extract_payment_method("thu cod giúp e nhé") == PaymentMethod.COD
    assert nlu_preprocessor.extract_payment_method("khách đưa tiền mặt") == PaymentMethod.CASH


# ── 2. CRM Tools & Entity Resolution Tests ───────────────────────────────────

def test_crm_tools_resolve_customer_by_phone():
    """Tests customer lookup by phone."""
    cust = crm_tools.resolve_customer(
        tenant_id="shop-default-01",
        phone="0912345678"
    )
    assert cust.customer_id == "cust-001"
    assert cust.full_name == "Nguyễn Văn Tuấn"


def test_crm_tools_resolve_customer_by_code():
    """Tests customer lookup by room code."""
    cust = crm_tools.resolve_customer(
        tenant_id="shop-default-01",
        code="3006B"
    )
    assert cust.customer_id == "cust-001"
    assert cust.full_name == "Nguyễn Văn Tuấn"


def test_crm_tools_resolve_product_token():
    """Tests product lookup by alias or code."""
    prod_item = crm_tools.resolve_product(
        tenant_id="shop-default-01",
        token="xoi lac",
        price_hint=10000.0
    )
    assert prod_item is not None
    assert prod_item.product_id == "prod-001"
    assert prod_item.unit_price == 10000.0
    assert prod_item.total_amount == 10000.0


# ── 3. Feedback Learner & Slang Memory Tests ──────────────────────────────────

def test_feedback_learner_alias_registration():
    """Tests tenant-isolated slang alias recording and retrieval."""
    learner = FeedbackLearner()
    tenant = "shop_test_99"
    
    learner.record_alias(
        tenant_id=tenant,
        raw_token="xl",
        target_type="PRODUCT",
        target_id="prod-001",
        target_name="Xôi Lạc Ruốc Hành"
    )
    
    aliases = learner.get_aliases(tenant)
    assert len(aliases) == 1
    assert aliases[0].raw_token == "xl"
    assert aliases[0].target_name == "Xôi Lạc Ruốc Hành"


def test_feedback_learner_process_confirmation():
    """Tests processing confirmation and corrections into alias memory."""
    learner = FeedbackLearner()
    tenant = "shop_test_99"
    
    learner.process_confirmation(
        session_id="sess-001",
        tenant_id=tenant,
        order_id="ord-100",
        corrections=[
            CorrectionItemDto(
                raw_token="bm trứng",
                corrected_product_id="prod-003"
            )
        ]
    )
    
    aliases = learner.get_aliases(tenant)
    assert any(a.raw_token == "bm trứng" for a in aliases)


def test_feedback_learner_build_few_shot_prompt():
    """Tests dynamic few-shot prompt generation."""
    prompt = feedback_learner.build_few_shot_prompt("shop-default-01")
    assert "TỪ ĐIỂN TỪ LÓNG & VIẾT TẮT" in prompt
    assert "3006b" in prompt


# ── 4. End-to-End Structured Extractor & State Graph Tests ───────────────────

@pytest.mark.asyncio
async def test_structured_extractor_pipeline():
    """Tests full extraction pipeline from rapid salesperson text to draft order."""
    req = ChatParseRequest(
        message="3006B 10k xoi lac 2 bm gv ck",
        tenant_id="shop-default-01",
        saler_id="saler-01"
    )
    
    draft = await structured_extractor.parse_message(req)
    
    assert draft.intent == OrderIntent.ORDER
    assert draft.payment_method == PaymentMethod.BANK_TRANSFER
    assert draft.customer.full_name == "Nguyễn Văn Tuấn"
    assert len(draft.items) >= 1
    assert draft.total_order_amount is not None
    assert draft.total_order_amount > 0.0


@pytest.mark.asyncio
async def test_conversation_graph_process_and_confirm_turn():
    """Tests complete turn cycle: parse message -> draft order -> confirm -> auto-learn."""
    # 1. User turn: Parse message
    parse_req = ChatParseRequest(
        message="3006B 10k xoi lac 2 bm gv ck",
        tenant_id="shop-default-01",
        saler_id="saler-01"
    )
    draft = await conversation_graph.process_user_turn(parse_req)
    assert draft.session_id is not None
    assert draft.customer.customer_id == "cust-001"
    
    # 2. Confirmation turn: User confirms draft
    confirm_req = ChatConfirmRequest(
        session_id=draft.session_id,
        tenant_id="shop-default-01",
        order_id="ord-99881",
        corrections=[]
    )
    confirm_res = await conversation_graph.confirm_order_turn(confirm_req)
    assert confirm_res["status"] == "ORDER_CREATED_AND_LEARNED"
    assert confirm_res["session_id"] == draft.session_id
