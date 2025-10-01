from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from uuid import UUID
import logging
import traceback

from app.schemas.agent import AgentDashboardParams, AgentDashboardResponse
from app.db.session import get_db
from app.db.redis_client import get_redis
from app.services.agent_services import AgentServices

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agents", tags=["Agents"])


@router.get("/{agent_id}/dashboard", response_model=AgentDashboardResponse)
async def get_agent_dashboard(
    agent_id: UUID,
    params: AgentDashboardParams = Depends(),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    try:
        return await AgentServices.get_agent_dashboard(agent_id, params, db, redis)
    except Exception as e:
        logger.error("Error in capture_lead: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=404, detail=str(e))
