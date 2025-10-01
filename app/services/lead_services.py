from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from datetime import datetime, timedelta
import json
from fastapi import HTTPException

from app.models import Lead, LeadSource, LeadAssignment, FollowUpTask, LeadConversionHistory, LeadActivity, LeadPropertyInterest
from app.schemas.lead import LeadCaptureRequest, LeadCaptureResponse, AssignedAgent
from app.schemas.lead_update import LeadUpdateRequest, LeadUpdateResponse
from app.services.lead_scoring import LeadScoringEngine
from app.services.lead_assignment import LeadAssignmentManager


class LeadServices:

    @staticmethod
    async def capture_lead_service(request: LeadCaptureRequest, db: AsyncSession, redis) -> LeadCaptureResponse:

        """
        Capture a new lead into the system.

        Workflow:
        1. Generate cache keys (phone/email) to check for duplicates in Redis.
        2. Verify lead uniqueness against both Redis cache and PostgreSQL database.
        3. Insert a new lead record into the `leads` table.
        4. Insert corresponding source details into the `lead_sources` table.
        5. Score the lead using `LeadScoringEngine`.
        6. Assign the lead to the most suitable agent via `LeadAssignmentManager`.
        7. Create an initial follow-up task for the assigned agent.
        8. Generate mock suggested property IDs for the lead.
        9. Commit all changes to the database.
        10. Cache the lead phone/email in Redis to prevent duplicates.

        Args:
            request (LeadCaptureRequest): The incoming lead request payload, including lead data and source details.
            db (AsyncSession): Active SQLAlchemy async database session.
            redis: Redis client instance for duplicate detection and caching.

        Returns:
            LeadCaptureResponse: Contains lead ID, assigned agent info, lead score, follow-up details, 
            and suggested property IDs.

        Raises:
            HTTPException:
                - 400 if a duplicate lead is detected (from Redis or DB).
                - 400 if no suitable agent is available for assignment.
        """

        cache_keys = []
        if request.lead_data.phone:
            cache_keys.append(f"lead:phone:{request.lead_data.phone}")
        if request.lead_data.email:
            cache_keys.append(f"lead:email:{request.lead_data.email}")

        # 1. --- Check Redis for duplicates ---
        for key in cache_keys:
            if await redis.get(key):
                raise HTTPException(status_code=400, detail="Duplicate lead detected (cache)")

        # 2. --- Check DB for duplicates (ORM) ---
        stmt = (
            select(Lead.lead_id)
            .join(LeadSource, Lead.lead_id == LeadSource.lead_id)
            .where(
                and_(
                    or_(
                        Lead.phone == request.lead_data.phone,
                        and_(Lead.email.isnot(None), Lead.email == request.lead_data.email),
                    ),
                    Lead.created_at >= datetime.utcnow() - timedelta(hours=24),
                )
            )
        )
        result = await db.execute(stmt)
        if result.first():
            raise HTTPException(status_code=400, detail="Duplicate lead detected (DB)")


        # 3. --- Insert Lead + Source ---
        new_lead = Lead(
            lead_id=uuid4(),
            source_type=request.source_type,
            **request.lead_data.dict(),
            status="new",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_lead)
        await db.flush()

        new_source = LeadSource(
            lead_id=new_lead.lead_id,
            source_type=request.source_type,
            **(request.source_details.dict() if request.source_details else {})
        )
        db.add(new_source)

        # 4. --- Score Lead ---
        scoring_engine = LeadScoringEngine()
        lead_score = await scoring_engine.calculate_lead_score(
            lead_data=request.lead_data.dict(),
            source_details={"source_type": request.source_type, **(request.source_details.dict() if request.source_details else {})}
        )
        new_lead.lead_score = lead_score

        # 5. --- Assign Agent ---
        assignment_manager = LeadAssignmentManager(db)
        agent_info = await assignment_manager.assign_lead(new_lead.lead_id, request.lead_data.dict())
        if not agent_info:
            raise HTTPException(status_code=400, detail="No suitable agent available")

        db.add(LeadAssignment(
            assignment_id=uuid4(),
            lead_id=new_lead.lead_id,
            agent_id=agent_info["agent_id"],
            reason="initial assignment"
        ))

        # 6. --- Create Follow-Up ---
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

        await db.commit()

        # 7. --- Cache prevention ---
        for key in cache_keys:
            await redis.set(key, json.dumps({"lead_id": str(new_lead.lead_id)}), ex=3600)

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
            suggested_properties=[uuid4(), uuid4(), uuid4()] # Mocing Property ID's
        )






    @staticmethod
    async def update_lead_service(lead_id: UUID, request: LeadUpdateRequest, db: AsyncSession) -> LeadUpdateResponse:
        """
        Update an existing lead with new status, activities, or property interests.

        Workflow:
        1. Fetch the lead from the database by ID.
        2. If status has changed, record the transition in `lead_conversion_history`
        and update the lead's current status.
        3. If an activity is provided:
        - Insert into `lead_activities`.
        - Optionally create a corresponding `follow_up_tasks` entry if `next_follow_up` is given.
        4. If property interests are provided, insert or update them in
        `lead_property_interests`.
        5. Recalculate the lead score using `LeadScoringEngine` based on new activity data.
        6. If the updated score exceeds a threshold (e.g., >90), reassign the lead
        to a more suitable agent via `LeadAssignmentManager`.
        7. Commit all changes to the database.
        8. Build and return a structured response with the updated lead state.

        Args:
            lead_id (UUID): Unique identifier of the lead being updated.
            request (LeadUpdateRequest): Incoming update payload (status, activities, property interests).
            db (AsyncSession): Active SQLAlchemy async database session.

        Returns:
            LeadUpdateResponse: Contains updated lead ID, status, recalculated lead score,
            last activity timestamp, next follow-up timestamp, and property interests.

        Raises:
            HTTPException:
                - 404 if the lead does not exist.
                - 400 if status progression violates business rules (trigger errors).
    """


        # 1. --- Fetch Lead ---
        result = await db.execute(select(Lead).where(Lead.lead_id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        last_activity_ts, next_follow_up_ts = None, None

        # 2. --- Status update In lead_conversion_history---
        if request.status and request.status != lead.status:
            try:
                # Add history
                history = LeadConversionHistory(
                    lead_id=lead_id,
                    previous_status=lead.status,
                    new_status=request.status,
                    notes="Updated via API",
                )
                db.add(history)

                # Update lead status
                lead.status = request.status
                lead.updated_at = datetime.utcnow()

            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
            
        # 3. --- Insert Activity if Provided ---
        if request.activity:
            act = request.activity
            activity = LeadActivity(
                lead_id=lead_id,
                agent_id=await LeadAssignmentManager.get_assigned_agent(db, lead_id),  # assumes helper
                activity_type=act.type,
                notes=act.notes,
                outcome=act.outcome,
                next_follow_up=act.next_follow_up,
            )
            db.add(activity)
            await db.flush()  # to get timestamps

            last_activity_ts, next_follow_up_ts = activity.created_at, activity.next_follow_up

            if act.next_follow_up:
                follow_up = FollowUpTask(
                    lead_id=lead_id,
                    agent_id=activity.agent_id,
                    task_type=act.type,
                    due_date=act.next_follow_up,
                    priority="high",
                    notes=act.notes or "Auto-generated follow-up",
                )
                db.add(follow_up)

        # 4. --- Update Property interests ---
        updated_interests = []
        if request.property_interests:
            for pi in request.property_interests:
                result = await db.execute(
                    select(LeadPropertyInterest).where(
                        LeadPropertyInterest.lead_id == lead_id,
                        LeadPropertyInterest.property_id == pi.property_id,
                    )
                )
                interest = result.scalar_one_or_none()
                if interest:
                    interest.interest_level = pi.interest_level
                else:
                    interest = LeadPropertyInterest(
                        lead_id=lead_id,
                        property_id=pi.property_id,
                        interest_level=pi.interest_level,
                    )
                    db.add(interest)
                updated_interests.append(pi)

        # 5. --- Recalculate score using LeadScoringEngine ---
        scoring_engine = LeadScoringEngine()
        new_score = await scoring_engine.update_lead_score(
            db, lead_id=lead_id, activity_data=request.activity.dict() if request.activity else {}
        )
        lead.lead_score = new_score

        # 6. --- Optional reassignment ---
        if new_score > 90:
            assignment_manager = LeadAssignmentManager(db)
            await assignment_manager.reassign_lead(lead_id=lead_id, reason="High potential lead (score > 90)")

        await db.commit()

        return LeadUpdateResponse(
            lead_id=lead_id,
            status=request.status or lead["status"],
            lead_score=new_score,
            last_activity=last_activity_ts.isoformat() if last_activity_ts else None,
            next_follow_up=next_follow_up_ts.isoformat() if next_follow_up_ts else None,
            updated_interests=updated_interests or None,
        )


    @staticmethod
    async def get_recent_leads_service(limit: int, db: AsyncSession):
        # 1. --- Recent Captures ---
        capture_stmt = (
            select(Lead)
            .order_by(Lead.created_at.desc())
            .limit(limit)
        )
        captures_result = await db.execute(capture_stmt)
        recent_captures = captures_result.scalars().all()

        # 2. --- Recent Updates ---
        update_stmt = (
            select(LeadConversionHistory)
            .order_by(LeadConversionHistory.changed_at.desc())
            .limit(limit)
        )
        updates_result = await db.execute(update_stmt)
        recent_updates = updates_result.scalars().all()

        return {
            "recent_captures": [
                {
                    "lead_id": str(lead.lead_id),
                    "status": lead.status,
                    "created_at": lead.created_at,
                }
                for lead in recent_captures
            ],
            "recent_updates": [
                {
                    "lead_id": str(update.lead_id),
                    "previous_status": update.previous_status,
                    "new_status": update.new_status,
                    "changed_at": update.changed_at,
                    "changed_by": str(update.changed_by) if update.changed_by else None,
                }
                for update in recent_updates
            ],
        }

