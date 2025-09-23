from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import json

from app.schemas.lead import LeadCaptureRequest, LeadCaptureResponse, AssignedAgent
from app.models import Lead, LeadSource, LeadAssignment, FollowUpTask
from app.services.lead_scoring import LeadScoringEngine
from app.services.lead_assignment import LeadAssignmentManager
from app.db.session import get_db
from app.db.redis_client import get_redis  # Redis client

router = APIRouter(prefix="/api/v1/leads", tags=["Leads"])


@router.post("/capture", response_model=LeadCaptureResponse)
async def capture_lead(
    request: LeadCaptureRequest,
    db: AsyncSession = Depends(get_db)
):
    redis = await get_redis()
    cache_keys = []
    
    # 1--- Prepare cache keys ---
    if request.lead_data.phone:
        cache_keys.append(f"lead:phone:{request.lead_data.phone}")
    if request.lead_data.email:
        cache_keys.append(f"lead:email:{request.lead_data.email}")

    # 2--- Check Redis cache for duplicates ---
    for key in cache_keys:
        cached = await redis.get(key)
        if cached:
            raise HTTPException(status_code=400, detail="Duplicate lead detected (cache)")

    # 3--- Check DB for duplicates (fallback) ---
    existing = await db.execute(
        text("""
        SELECT 1
        FROM leads l
        JOIN lead_sources ls ON l.lead_id = ls.lead_id
        WHERE l.phone = :phone
           OR (l.email IS NOT NULL AND l.email = :email)
        """),
        {"phone": request.lead_data.phone, "email": request.lead_data.email}
    )
    if existing.first():
        raise HTTPException(status_code=400, detail="Duplicate lead detected (DB)")

    # 4--- Insert new lead ---
    new_lead = Lead(
        lead_id=uuid4(),
        **request.lead_data.dict(),
        status="new",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(new_lead)
    await db.flush()  # lead_id now available

    # 5--- Insert source details ---
    new_source = LeadSource(
        lead_id=new_lead.lead_id,
        source_type=request.source_type,
        **(request.source_details.dict() if request.source_details else {})
    )
    db.add(new_source)

    # 6--- Score lead ---
    scoring_engine = LeadScoringEngine()
    lead_score = await scoring_engine.calculate_lead_score(
        lead_data=request.lead_data.dict(),
        source_details={"source_type": request.source_type, **(request.source_details.dict() if request.source_details else {})}
    )
    new_lead.lead_score = lead_score

    # 7--- Assign agent ---
    assignment_manager = LeadAssignmentManager(db)
    agent_info = await assignment_manager.assign_lead(
        lead_id=new_lead.lead_id,
        lead_data=request.lead_data.dict()
    )
    if not agent_info:
        raise HTTPException(status_code=400, detail="No suitable agent available")

    new_assignment = LeadAssignment(
        assignment_id=uuid4(),
        lead_id=new_lead.lead_id,
        agent_id=agent_info["agent_id"],
        reason="initial assignment"
    )
    db.add(new_assignment)

    # 8--- Create initial follow-up ---
    follow_up = FollowUpTask(
        task_id=uuid4(),
        lead_id=new_lead.lead_id,
        agent_id=agent_info["agent_id"],
        task_type="call",
        due_date=datetime.utcnow() + timedelta(days=1),
        priority="high",
        notes="Initial follow-up"
    )
    db.add(follow_up)

    # 9--- Suggested properties (mock UUIDs) ---
    suggested_properties = [uuid4(), uuid4(), uuid4()]

    await db.commit()

    # 10--- Set Redis cache for phone/email to prevent duplicates ---
    for key in cache_keys:
        await redis.set(key, json.dumps({"lead_id": str(new_lead.lead_id)}), ex=3600)  # 1 hour expiration

    # 11--- Build response ---
    return LeadCaptureResponse(
        success=True,
        lead_id=new_lead.lead_id,
        assigned_agent=AssignedAgent(
            agent_id=agent_info["agent_id"],
            name=agent_info["full_name"],
            phone=agent_info["phone"]
        ),
        source_type=request.source_type,
        lead_data=request.lead_data,
        source_details=request.source_details,
        lead_score=lead_score,
        next_follow_up=follow_up.due_date.isoformat(),
        suggested_properties=suggested_properties
    )


# ----------------- FOR TESTING Lead cature -------------
# {
#   "source_type": "bayut",
#   "lead_data": {
#     "first_name": "Ali",
#     "last_name": "Khan",
#     "email": "ali.khan@example.com",
#     "phone": "971501234567",
#     "nationality": "UAE",
#     "language_preference": "english",
#     "budget_min": 500000,
#     "budget_max": 1500000,
#     "property_type": "apartment",
#     "preferred_areas": ["Downtown", "Marina"]
#   },
#   "source_details": {
#     "campaign_id": "summer2024",
#     "referrer_agent_id": "6e0b655b-edc1-4229-9d08-4af6e09a4548",
#     "property_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
#     "utm_source": "google",
#     "utm_medium": "cpc",
#     "utm_campaign": "dubai_apartments"
#   }
# }









# --------- Lead Update ---------

from app.schemas.lead_update import (
    LeadUpdateRequest,
    LeadUpdateResponse,
    LeadActivityUpdate,
    LeadPropertyInterestUpdate,
)

@router.put("/{lead_id}/update", response_model=LeadUpdateResponse)
async def update_lead(
    lead_id: UUID,
    request: LeadUpdateRequest,
    db: AsyncSession = Depends(get_db),
):

    # --- 1. Fetch lead ---
    lead_res = await db.execute(text("SELECT * FROM leads WHERE lead_id = :id"), {"id": str(lead_id)})
    lead = lead_res.mappings().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    last_activity_ts = None
    next_follow_up_ts = None

    # --- 2. Insert status change into lead_conversion_history ---
    if request.status and request.status != lead["status"]:
        try:
            await db.execute(
                text("""
                    INSERT INTO lead_conversion_history (lead_id, previous_status, new_status, notes)
                    VALUES (:lead_id, :prev_status, :new_status, :notes)
                """),
                {
                    "lead_id": str(lead_id),
                    "prev_status": lead["status"],
                    "new_status": request.status,
                    "notes": "Updated via API"
                }
            )

            # After trigger validation, update the main leads table
            await db.execute(
                text("UPDATE leads SET status = :status, updated_at = :ts WHERE lead_id = :id"),
                {"status": request.status, "ts": datetime.utcnow(), "id": str(lead_id)},
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # --- 3. Insert activity if provided ---
    last_activity_ts = None
    next_follow_up_ts = None
    if request.activity:
        act = request.activity
        result = await db.execute(
            text("""
                INSERT INTO lead_activities (lead_id, agent_id, activity_type, notes, outcome, next_follow_up)
                VALUES (:lead_id, (SELECT agent_id FROM lead_assignments WHERE lead_id = :lead_id AND reassigned = FALSE LIMIT 1),
                        :type, :notes, :outcome, :next_follow_up)
                RETURNING created_at, next_follow_up
            """),
            {
                "lead_id": str(lead_id),
                "type": act.type,
                "notes": act.notes,
                "outcome": act.outcome,
                "next_follow_up": act.next_follow_up,
            },
        )
        row = result.mappings().first()
        last_activity_ts = row["created_at"]
        next_follow_up_ts = row["next_follow_up"]

        # Also create follow-up task if next_follow_up provided
        if act.next_follow_up:
            await db.execute(
                text("""
                    INSERT INTO follow_up_tasks (lead_id, agent_id, task_type, due_date, priority, notes)
                    VALUES (:lead_id,
                           (SELECT agent_id FROM lead_assignments WHERE lead_id = :lead_id AND reassigned = FALSE LIMIT 1),
                           :task_type, :due_date, 'high', :notes)
                """),
                {
                    "lead_id": str(lead_id),
                    "task_type": act.type,
                    "due_date": act.next_follow_up,
                    "notes": act.notes or "Auto-generated follow-up",
                },
            )

    # --- 4. Update property interests ---
    updated_interests = []
    if request.property_interests:
        for pi in request.property_interests:
            await db.execute(
                text("""
                    INSERT INTO lead_property_interests (lead_id, property_id, interest_level)
                    VALUES (:lead_id, :property_id, :level)
                    ON CONFLICT (lead_id, property_id)
                    DO UPDATE SET interest_level = EXCLUDED.interest_level
                """),
                {"lead_id": str(lead_id), "property_id": str(pi.property_id), "level": pi.interest_level},
            )
            updated_interests.append(pi)

    # --- 5. Recalculate score using LeadScoringEngine ---
    scoring_engine = LeadScoringEngine()
    new_score = await scoring_engine.update_lead_score(
        db,
        lead_id=lead_id,
        activity_data=request.activity.dict() if request.activity else {}
    )
    await db.execute(
        text("UPDATE leads SET lead_score = :score WHERE lead_id = :id"),
        {"score": new_score, "id": str(lead_id)},
    )

    # --- 6. Reassignment check (example: if score > 90 reassign to senior agent) ---
    if new_score > 90:
        assignment_manager = LeadAssignmentManager(db)
        await assignment_manager.reassign_lead(
            lead_id=lead_id,
            reason="High potential lead (score > 90)"
        )

    await db.commit()

    # --- 7. Build response ---
    return LeadUpdateResponse(
        lead_id=lead_id,
        status=request.status or lead["status"],
        lead_score=new_score,
        last_activity=last_activity_ts.isoformat() if last_activity_ts else None,
        next_follow_up=next_follow_up_ts.isoformat() if next_follow_up_ts else None,
        updated_interests=updated_interests or None,
    )


# -----------FOR TESTING Update Lead JSON Example----------
# lead_id:"21c677a2-9fe6-4da4-b634-19351d695124"
# {
#   "status": "viewing_scheduled",
#   "activity": {
#     "type": "call",
#     "notes": "Discussed property details, client interested.",
#     "outcome": "positive",
#     "next_follow_up": "2025-09-23T05:40:37.334"
#   },
#   "property_interests": [
#     {
#       "property_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
#       "interest_level": "high"
#     }
#   ]
# }
