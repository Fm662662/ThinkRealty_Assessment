from typing import Dict, Any
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

class LeadScoringEngine:

    async def calculate_lead_score(
        self,
        lead_data: Dict[str, Any],
        source_details: Dict[str, Any]
    ) -> int:
        """
        Calculate score for a new lead based on profile + source.
        """
        score = 0

        # --- Budget ---
        budget_max = lead_data.get("budget_max", 0)
        if budget_max > 1500000:
            score += 15
        elif budget_max > 1000000:
            score += 8
        elif budget_max < 500000:
            score -= 5

        # --- Source quality ---
        source = source_details.get("source_type")
        source_weights = {
            "bayut": 90,
            "propertyFinder": 85,
            "website": 80,
            "dubizzle": 70,
            "walk_in": 75,
            "referral": 82
        }
        score += source_weights.get(source, 50) // 10  # scale down

        # --- Nationality ---
        nationality = lead_data.get("nationality")
        if nationality == "UAE":
            score += 10
        elif nationality in ["KSA", "Kuwait", "Oman", "Bahrain", "Qatar"]:
            score += 5

        # --- Property type preference ---
        property_type = lead_data.get("property_type")
        if property_type == "villa":
            score += 5
        elif property_type == "apartment":
            score += 3
        elif property_type == "commercial":
            score -= 3
        # townhouse → neutral (no bonus/penalty)

        # --- Response time to initial contact ---
        # expects "response_time_minutes" key in source_details
        response_time = source_details.get("response_time_minutes")
        if response_time is not None:
            if response_time < 60:          # within 1 hour
                score += 10
            elif response_time < 1440:      # within a day
                score += 5

        # --- Referral bonus ---
        if source_details.get("referrer_agent_id"):
            score += 5

        # Clamp between 0–100
        return max(0, min(score, 100))


    async def update_lead_score(
        self,
        db: AsyncSession,
        lead_id: UUID,
        activity_data: Dict[str, Any]
    ) -> int:
        """
        Compute delta from activity, add to current score, persist and return new score.
        """
        score_delta = 0
        activity_type = activity_data.get("type")
        outcome = activity_data.get("outcome")
        last_activity_at = activity_data.get("last_activity_at")

        # Outcome effects 
        if outcome == "positive":
            score_delta += 5
        elif outcome == "negative":
            score_delta -= 5

        # Activity type effects
        if activity_type == "viewing":
            score_delta += 10
        if activity_type == "offer_made":
            score_delta += 20

        # Inactivity penalty
        if last_activity_at and last_activity_at < datetime.utcnow() - timedelta(days=7):
            score_delta -= 10

        # fetch current score
        res = await db.execute(
            text("SELECT lead_score FROM leads WHERE lead_id = :id"), {"id": str(lead_id)})
        row = res.mappings().first()
        current = int(row["lead_score"]) if row and row["lead_score"] is not None else 0

        new_score = max(0, min(100, current + score_delta))

        await db.execute(
            text("UPDATE leads SET lead_score = :score, updated_at = now() WHERE lead_id = :id"),
            {"score": new_score, "id": str(lead_id)}
        )
        await db.commit()

        return new_score

