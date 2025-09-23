from typing import List, Optional, Literal
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


# --- Activity sub-schema ---
class LeadActivityUpdate(BaseModel):
    type: Literal["call", "email", "whatsapp", "viewing", "meeting", "offer_made"]
    notes: Optional[str]
    outcome: Optional[Literal["positive", "negative", "neutral"]]
    next_follow_up: Optional[datetime]


# --- Property interest sub-schema ---
class LeadPropertyInterestUpdate(BaseModel):
    property_id: UUID
    interest_level: Literal["high", "medium", "low"]


# --- Main request ---
class LeadUpdateRequest(BaseModel):
    status: Optional[
        Literal[
            "new",
            "contacted",
            "qualified",
            "viewing_scheduled",
            "negotiation",
            "converted",
            "lost",
        ]
    ]
    activity: Optional[LeadActivityUpdate]
    property_interests: Optional[List[LeadPropertyInterestUpdate]]


# --- Response ---
class LeadUpdateResponse(BaseModel):
    lead_id: UUID
    status: str
    lead_score: int
    last_activity: Optional[str]  # ISO datetime
    next_follow_up: Optional[str]  # ISO datetime
    updated_interests: Optional[List[LeadPropertyInterestUpdate]]
