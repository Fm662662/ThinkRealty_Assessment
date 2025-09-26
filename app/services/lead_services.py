from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timedelta
import json
from fastapi import HTTPException

from app.models import Lead, LeadSource, LeadAssignment, FollowUpTask
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

        # 2. --- Check DB for duplicates ---
        existing = await db.execute(
            text("""
                SELECT 1 FROM leads l
                JOIN lead_sources ls ON l.lead_id = ls.lead_id
                WHERE (l.phone = :phone OR (l.email IS NOT NULL AND l.email = :email))
                AND l.created_at >= NOW() - INTERVAL '24 hours'

            """),
            {"phone": request.lead_data.phone, "email": request.lead_data.email}
        )
        if existing.first():
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
        lead_res = await db.execute(text("SELECT * FROM leads WHERE lead_id = :id"), {"id": str(lead_id)})
        lead = lead_res.mappings().first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        last_activity_ts, next_follow_up_ts = None, None

        # 2. --- Status update In lead_conversion_history---
        if request.status and request.status != lead["status"]:
            try:
                await db.execute(
                    text("""INSERT INTO lead_conversion_history (lead_id, previous_status, new_status, notes) 
                            VALUES (:lead_id, :prev, :new, :notes)"""),
                    {"lead_id": str(lead_id), 
                    "prev": lead["status"], 
                    "new": request.status, 
                    "notes": "Updated via API"}
                )

                await db.execute(
                    text("UPDATE leads SET status = :status, updated_at = :ts WHERE lead_id = :id"),
                    {"status": request.status, 
                    "ts": datetime.utcnow(), 
                    "id": str(lead_id)}
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
            
        # 3. ---Insert  Activity if Provided---
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
                    "next_follow_up": act.next_follow_up
                }
            )
            row = result.mappings().first()
            last_activity_ts, next_follow_up_ts = row["created_at"], row["next_follow_up"]

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
                        "notes": act.notes or "Auto-generated follow-up"
                    }
                )

        # 4. --- Update Property interests ---
        updated_interests = []
        if request.property_interests:
            for pi in request.property_interests:
                await db.execute(
                    text("""INSERT INTO lead_property_interests (lead_id, property_id, interest_level)
                            VALUES (:lead_id, :property_id, :level)
                            ON CONFLICT (lead_id, property_id) DO UPDATE SET interest_level = EXCLUDED.interest_level"""),
                    {
                        "lead_id": str(lead_id), 
                        "property_id": str(pi.property_id), 
                        "level": pi.interest_level
                    }
                )
                updated_interests.append(pi)

        # 5. --- Recalculate score using LeadScoringEngine ---
        scoring_engine = LeadScoringEngine()
        new_score = await scoring_engine.update_lead_score(db, lead_id=lead_id, activity_data=request.activity.dict() if request.activity else {})
        await db.execute(text("UPDATE leads SET lead_score = :score WHERE lead_id = :id"), {"score": new_score, "id": str(lead_id)})

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
