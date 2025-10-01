# crud/lead_property_interests.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from uuid import UUID
from typing import List, Optional

from app.models.lead_property_interests import LeadPropertyInterest


# ---------------- CREATE ----------------
async def create_interest(
    db: AsyncSession,
    lead_id: UUID,
    property_id: UUID,
    interest_level: str,
) -> LeadPropertyInterest:
    interest = LeadPropertyInterest(
        lead_id=lead_id,
        property_id=property_id,
        interest_level=interest_level,
    )
    db.add(interest)
    await db.commit()
    await db.refresh(interest)
    return interest


# ---------------- READ ----------------
async def get_interest(db: AsyncSession, interest_id: UUID) -> Optional[LeadPropertyInterest]:
    result = await db.execute(
        select(LeadPropertyInterest).where(LeadPropertyInterest.interest_id == interest_id)
    )
    return result.scalar_one_or_none()


async def get_interests_by_lead(db: AsyncSession, lead_id: UUID) -> List[LeadPropertyInterest]:
    result = await db.execute(
        select(LeadPropertyInterest).where(LeadPropertyInterest.lead_id == lead_id)
    )
    return result.scalars().all()


# ---------------- UPDATE ----------------
async def update_interest(
    db: AsyncSession,
    interest_id: UUID,
    new_level: str,
) -> Optional[LeadPropertyInterest]:
    result = await db.execute(
        update(LeadPropertyInterest)
        .where(LeadPropertyInterest.interest_id == interest_id)
        .values(interest_level=new_level)
        .returning(LeadPropertyInterest)
    )
    await db.commit()
    return result.scalar_one_or_none()


# ---------------- DELETE ----------------
async def delete_interest(db: AsyncSession, interest_id: UUID) -> bool:
    result = await db.execute(
        delete(LeadPropertyInterest).where(LeadPropertyInterest.interest_id == interest_id)
    )
    await db.commit()
    return result.rowcount > 0
