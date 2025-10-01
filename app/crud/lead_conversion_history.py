# crud/lead_conversion_history.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List, Optional
from uuid import UUID

from app.models.lead_conversion_history import LeadConversionHistory


# ---------------- CREATE ----------------
async def create_history_entry(
    db: AsyncSession,
    lead_id: UUID,
    previous_status: Optional[str],
    new_status: str,
    changed_by: Optional[UUID] = None,
    notes: Optional[str] = None,
) -> LeadConversionHistory:
    history = LeadConversionHistory(
        lead_id=lead_id,
        previous_status=previous_status,
        new_status=new_status,
        changed_by=changed_by,
        notes=notes,
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)
    return history


# ---------------- READ ----------------
async def get_history_by_id(db: AsyncSession, history_id: UUID) -> Optional[LeadConversionHistory]:
    result = await db.execute(
        select(LeadConversionHistory).where(LeadConversionHistory.history_id == history_id)
    )
    return result.scalar_one_or_none()


async def get_history_by_lead(db: AsyncSession, lead_id: UUID) -> List[LeadConversionHistory]:
    result = await db.execute(
        select(LeadConversionHistory)
        .where(LeadConversionHistory.lead_id == lead_id)
        .order_by(LeadConversionHistory.changed_at.desc())
    )
    return result.scalars().all()


# ---------------- UPDATE ----------------
async def update_history_entry(
    db: AsyncSession,
    history_id: UUID,
    **kwargs
) -> Optional[LeadConversionHistory]:
    """
    kwargs can include: previous_status, new_status, notes, changed_by
    """
    result = await db.execute(
        update(LeadConversionHistory)
        .where(LeadConversionHistory.history_id == history_id)
        .values(**kwargs)
        .returning(LeadConversionHistory)
    )
    await db.commit()
    return result.scalar_one_or_none()


# ---------------- DELETE ----------------
async def delete_history_entry(db: AsyncSession, history_id: UUID) -> bool:
    result = await db.execute(
        delete(LeadConversionHistory).where(LeadConversionHistory.history_id == history_id)
    )
    await db.commit()
    return result.rowcount > 0
