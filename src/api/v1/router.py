"""
Master API V1 Router Aggregator.
"""

from fastapi import APIRouter
from api.v1.chat import router as chat_router
from api.v1.rag import router as rag_router
from api.v1.vision import router as vision_router
from api.v1.analytics import router as analytics_router
from api.v1.audio import router as audio_router
from api.v1.agent import router as agent_router
from api.v1.chat_crm import router as chat_crm_router

api_v1_router = APIRouter()

api_v1_router.include_router(chat_router)
api_v1_router.include_router(rag_router)
api_v1_router.include_router(vision_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(audio_router)
api_v1_router.include_router(agent_router)
api_v1_router.include_router(chat_crm_router)

