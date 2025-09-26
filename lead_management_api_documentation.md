# 📘 Lead Management API Documentation

This document provides **cURL commands** for testing the Lead Management API along with example request payloads and responses.

---

## 🔹 1. Capture Lead  
**Endpoint:** `POST /api/v1/leads/capture`  

### Request
```bash
curl -X POST "http://localhost:8000/api/v1/leads/capture"   
-H "Content-Type: application/json"   
-d '{
    "source_type": "bayut",
    "lead_data": {
      "first_name": "Ali",
      "last_name": "Khan",
      "email": "ali.khan@example.com",
      "phone": "971501234567",
      "nationality": "UAE",
      "language_preference": "english",
      "budget_min": 500000,
      "budget_max": 1500000,
      "property_type": "apartment",
      "preferred_areas": ["Downtown", "Marina"]
    },
    "source_details": {
      "campaign_id": "summer2024",
      "referrer_agent_id": "6e0b655b-edc1-4229-9d08-4af6e09a4548",
      "property_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "utm_source": "google",
      "utm_medium": "cpc",
      "utm_campaign": "dubai_apartments"
    }
  }'
```

### ✅ Success Response
```json
{
  "success": true,
  "lead_id": "e5d93a91-47a3-4f8a-91bc-7e9a12d7c59f",
  "assigned_agent": {
    "agent_id": "5a77d8c3-b52a-4a8f-ae6d-8b2cb5c72c5f",
    "name": "Sarah Ali",
    "phone": "+971502223344"
  },
  "source_type": "bayut",
  "lead_data": {
    "first_name": "Ali",
    "last_name": "Khan",
    "phone": "971501234567",
    "email": "ali.khan@example.com"
  },
  "lead_score": 72,
  "next_follow_up": "2025-09-27T14:22:15.321Z",
  "suggested_properties": [
    "f933c229-1c36-437f-a02a-b421f182ae90",
    "a4b67b8c-6e13-44cb-b2fa-bc50fcb6cb3e",
    "d26de7d7-9936-4b38-82f0-3d79256989cb"
  ]
}
```

### ❌ Error Responses
```json
{ "detail": "Duplicate lead detected (DB)" }
{ "detail": "No suitable agent available" }
{ "detail": "Invalid lead data" }
```

---

## 🔹 2. Update Lead  
**Endpoint:** `PUT /api/v1/leads/{lead_id}/update`  

**lead_id**
21c677a2-9fe6-4da4-b634-19351d695124

### Request
```bash
curl -X PUT "http://localhost:8000/api/v1/leads/{lead_id}/update"   
-H "Content-Type: application/json"   
-d '{
    "status": "viewing_scheduled",
    "activity": {
      "type": "call",
      "notes": "Discussed property details, client interested.",
      "outcome": "positive",
      "next_follow_up": "2025-09-23T05:40:37.334"
    },
    "property_interests": [
      {
        "property_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "interest_level": "high"
      }
    ]
  }'
```

### ✅ Success Response
```json
{
  "lead_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "viewing_scheduled",
  "lead_score": 88,
  "last_activity": "2025-09-26T14:55:20.000Z",
  "next_follow_up": "2025-09-23T05:40:37.334",
  "updated_interests": [
    { "property_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "interest_level": "high" }
  ]
}
```

### ❌ Error Responses
```json
{ "detail": "Lead not found" }
{ "detail": "Invalid status transition from contacted to converted" }
```

---

## 🔹 3. Agent Dashboard  
**Endpoint:** `GET /api/v1/agents/{agent_id}/dashboard`  

**agent_id**
ee1b4f86-183d-4f4b-9ad6-8a032be4fc99

### Request
```bash
curl -X GET "http://localhost:8000/api/v1/agents/{agent_id}/dashboard?date_range=30d&status_filter=all&source_filter=all&start_date=2025-09-01&end_date=2025-09-26"
```

### ✅ Success Response
```json
{
  "agent_summary": {
    "total_active_leads": 32,
    "overdue_follow_ups": 3,
    "this_month_conversions": 4,
    "average_response_time": "5.2 hours",
    "lead_score_average": 74.5
  },
  "recent_leads": [
    {
      "lead_id": "e5d93a91-47a3-4f8a-91bc-7e9a12d7c59f",
      "name": "Ali Khan",
      "phone": "971501234567",
      "source": "bayut",
      "status": "qualified",
      "score": 72,
      "last_activity": "2025-09-26T13:44:10Z",
      "next_follow_up": "2025-09-28T10:00:00Z"
    }
  ],
  "pending_tasks": [
    {
      "task_id": "7d57c7b9-5e55-463f-8084-36a69f6a1e8a",
      "lead_name": "Jane Smith",
      "task_type": "call",
      "due_date": "2025-09-28T09:00:00Z",
      "priority": "high"
    }
  ],
  "performance_metrics": {
    "conversion_rate": 0.21,
    "average_deal_size": 1250000.0,
    "response_time_rank": 3
  }
}
```

### ❌ Error Responses
```json
{ "detail": "No metrics found for this agent" }
```

---

## Notes
- Replace `{lead_id}` and `{agent_id}` with actual UUIDs.  
- **Query params** for dashboard endpoint:  
  - `agent_id`: Agent UUID  
  - `date_range`: `7d | 30d | 90d | custom`  
  - `status_filter`: `all | active | converted | lost`  
  - `source_filter`: `all | bayut | propertyFinder | dubizzle | website`  
  - `start_date`, `end_date`: required only when `date_range=custom`.  
