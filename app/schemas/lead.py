from typing import List, Optional, Annotated
from pydantic import BaseModel, EmailStr, StringConstraints
from uuid import UUID

# --- Nested Schemas ---
class LeadData(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr]
    phone: Annotated[str, StringConstraints(min_length=7, max_length=20)]
    nationality: Optional[str]
    language_preference: Optional[str]
    budget_min: Optional[int]
    budget_max: Optional[int]
    property_type: Optional[str]
    preferred_areas: Optional[List[str]]

class SourceDetails(BaseModel):
    campaign_id: Optional[str]
    referrer_agent_id: Optional[UUID]
    property_id: Optional[UUID]
    utm_source: Optional[str]
    utm_medium: Optional[str]
    utm_campaign: Optional[str]

# --- Main Request ---
class LeadCaptureRequest(BaseModel):
    source_type: str  # bayut|propertyFinder|dubizzle|website|walk_in|referral
    lead_data: LeadData
    source_details: Optional[SourceDetails]

# --- Assigned Agent ---
class AssignedAgent(BaseModel):
    agent_id: UUID
    name: str
    phone: str

# --- Main Response ---
class LeadCaptureResponse(BaseModel):
    success: bool
    lead_id: UUID
    assigned_agent: AssignedAgent
    source_type: str
    lead_data: LeadData
    source_details: Optional[SourceDetails]
    lead_score: int
    next_follow_up: Optional[str]  # ISO 8601 datetime string
    suggested_properties: List[UUID]

