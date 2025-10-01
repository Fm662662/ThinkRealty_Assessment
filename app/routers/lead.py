from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging
import traceback


from app.schemas.lead import LeadCaptureRequest, LeadCaptureResponse
from app.schemas.lead_update import LeadUpdateRequest, LeadUpdateResponse
from app.db.session import get_db
from app.db.redis_client import get_redis
from app.services.lead_services import LeadServices

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/leads", tags=["Leads"])


@router.post(
    "/capture",
    response_model=LeadCaptureResponse,
    status_code=201,
    summary="Capture a new lead",
    description="Captures a new lead, assigns it to the best available agent, applies scoring, and generates an initial follow-up task."
)
async def capture_lead(
    request: LeadCaptureRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    try:
        return await LeadServices.capture_lead_service(request, db, redis)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error in capture_lead: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.put(
    "/{lead_id}/update",
    response_model=LeadUpdateResponse,
    summary="Update lead details",
    description="Updates a lead’s status, activities, property interests, and follow-ups."
)
async def update_lead(
    lead_id: UUID,
    request: LeadUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await LeadServices.update_lead_service(lead_id, request, db)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error in capture_lead: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get(
    "/recent",
    summary="Get recent lead capture and update events",
    description="Returns the most recent leads captured and their latest update events.",
)
async def get_recent_leads(
    limit: int = Query(1, description="Number of recent records to fetch"),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await LeadServices.get_recent_leads_service(limit, db)
    except Exception as e:
        logger.error("Error in capture_lead: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error")

