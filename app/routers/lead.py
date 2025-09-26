from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.schemas.lead import LeadCaptureRequest, LeadCaptureResponse
from app.schemas.lead_update import LeadUpdateRequest, LeadUpdateResponse
from app.db.session import get_db
from app.db.redis_client import get_redis
from app.services.lead_services import LeadServices

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
    except Exception:
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
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")
