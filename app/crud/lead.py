# app/crud/lead.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from app.models.lead import (
    Lead,
    LeadSource,
    LeadAssignment,
    FollowUpTask,
    LeadConversionHistory,
    LeadActivity,
    LeadPropertyInterest,
)


# --- Duplicate check ---
async def get_recent_duplicate_lead(db: AsyncSession, phone: str, email: str | None):
    stmt = (
        select(Lead.lead_id)
        .join(LeadSource, Lead.lead_id == LeadSource.lead_id)
        .where(
            and_(
                or_(
                    Lead.phone == phone,
                    and_(Lead.email.isnot(None), Lead.email == email),
                ),
                Lead.created_at >= datetime.utcnow() - timedelta(hours=24),
            )
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# --- Insert Lead ---
async def create_lead(db: AsyncSession, lead_data: dict, source_type: str) -> Lead:
    new_lead = Lead(
        lead_id=uuid4(),
        **lead_data,
        status="new",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(new_lead)
    await db.flush()
    return new_lead


# --- Insert Lead Source ---
async def create_lead_source(db: AsyncSession, lead_id: UUID, source_type: str, source_details: dict | None):
    new_source = LeadSource(
        lead_id=lead_id,
        source_type=source_type,
        **(source_details or {}),
    )
    db.add(new_source)
    return new_source


# --- Insert Assignment ---
async def create_assignment(db: AsyncSession, lead_id: UUID, agent_id: UUID, reason: str):
    assignment = LeadAssignment(
        assignment_id=uuid4(),
        lead_id=lead_id,
        agent_id=agent_id,
        reason=reason,
    )
    db.add(assignment)
    return assignment


# --- Insert Follow-Up ---
async def create_follow_up(db: AsyncSession, lead_id: UUID, agent_id: UUID, task_type: str, due_date: datetime, notes: str):
    follow_up = FollowUpTask(
        task_id=uuid4(),
        lead_id=lead_id,
        agent_id=agent_id,
        task_type=task_type,
        due_date=due_date,
        priority="high",
        notes=notes,
    )
    db.add(follow_up)
    return follow_up


# --- Fetch Lead by ID ---
async def get_lead_by_id(db: AsyncSession, lead_id: UUID) -> Lead | None:
    result = await db.execute(select(Lead).where(Lead.lead_id == lead_id))
    return result.scalar_one_or_none()


# --- Update Lead Status + History ---
async def update_lead_status(db: AsyncSession, lead: Lead, new_status: str):
    history = LeadConversionHistory(
        lead_id=lead.lead_id,
        previous_status=lead.status,
        new_status=new_status,
        notes="Updated via API",
    )
    db.add(history)

    lead.status = new_status
    lead.updated_at = datetime.utcnow()
    return lead


# --- Insert Activity ---
async def create_activity(db: AsyncSession, lead_id: UUID, agent_id: UUID, activity_data: dict) -> LeadActivity:
    activity = LeadActivity(
        lead_id=lead_id,
        agent_id=agent_id,
        activity_type=activity_data.get("type"),
        notes=activity_data.get("notes"),
        outcome=activity_data.get("outcome"),
        next_follow_up=activity_data.get("next_follow_up"),
    )
    db.add(activity)
    await db.flush()
    return activity


# --- Insert or Update Property Interest ---
async def upsert_property_interest(db: AsyncSession, lead_id: UUID, property_id: UUID, interest_level: str):
    result = await db.execute(
        select(LeadPropertyInterest).where(
            LeadPropertyInterest.lead_id == lead_id,
            LeadPropertyInterest.property_id == property_id,
        )
    )
    interest = result.scalar_one_or_none()
    if interest:
        interest.interest_level = interest_level
    else:
        interest = LeadPropertyInterest(
            lead_id=lead_id,
            property_id=property_id,
            interest_level=interest_level,
        )
        db.add(interest)
    return interest
