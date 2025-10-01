# crud/lead_assignment.py
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from datetime import datetime

from app.models.lead_assignment import LeadAssignment


# --- Create Assignment ---
async def create_assignment(
    db: AsyncSession,
    lead_id: UUID,
    agent_id: UUID,
    reason: Optional[str] = None
) -> LeadAssignment:
    assignment = LeadAssignment(
        lead_id=lead_id,
        agent_id=agent_id,
        reason=reason,
        assigned_at=datetime.utcnow(),
        reassigned=False
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


# --- Get Assignments by Lead ---
async def get_assignments_by_lead(
    db: AsyncSession,
    lead_id: UUID
) -> List[LeadAssignment]:
    stmt = select(LeadAssignment).where(LeadAssignment.lead_id == lead_id)
    result = await db.execute(stmt)
    return result.scalars().all()


# --- Get Assignments by Agent ---
async def get_assignments_by_agent(
    db: AsyncSession,
    agent_id: UUID
) -> List[LeadAssignment]:
    stmt = select(LeadAssignment).where(LeadAssignment.agent_id == agent_id)
    result = await db.execute(stmt)
    return result.scalars().all()


# --- Reassign Lead ---
async def reassign_lead(
    db: AsyncSession,
    lead_id: UUID,
    old_agent_id: UUID,
    new_agent_id: UUID,
    reason: Optional[str] = "Reassigned"
) -> LeadAssignment:
    # Mark old assignment as reassigned
    stmt = (
        update(LeadAssignment)
        .where(
            LeadAssignment.lead_id == lead_id,
            LeadAssignment.agent_id == old_agent_id,
            LeadAssignment.reassigned == False
        )
        .values(reassigned=True, reason=reason, assigned_at=datetime.utcnow())
    )
    await db.execute(stmt)

    # Create new assignment
    new_assignment = LeadAssignment(
        lead_id=lead_id,
        agent_id=new_agent_id,
        reason=reason,
        assigned_at=datetime.utcnow(),
        reassigned=False
    )
    db.add(new_assignment)
    await db.commit()
    await db.refresh(new_assignment)
    return new_assignment


# --- Delete Assignment ---
async def delete_assignment(
    db: AsyncSession,
    assignment_id: UUID
) -> None:
    stmt = delete(LeadAssignment).where(LeadAssignment.assignment_id == assignment_id)
    await db.execute(stmt)
    await db.commit()
