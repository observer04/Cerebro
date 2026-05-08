from fastapi import APIRouter

from app.api.analytics import router as analytics_router
from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.rca import router as rca_router
from app.api.signals import router as signals_router
from app.api.signals_query import router as signals_query_router
from app.api.system_health import router as system_health_router
from app.api.timeline import router as timeline_router
from app.api.work_items import router as work_items_router

api_router = APIRouter()
api_router.include_router(signals_router)
api_router.include_router(work_items_router)
api_router.include_router(rca_router)
api_router.include_router(dashboard_router)
api_router.include_router(health_router)
api_router.include_router(signals_query_router)
api_router.include_router(analytics_router)
api_router.include_router(system_health_router)
api_router.include_router(timeline_router)
