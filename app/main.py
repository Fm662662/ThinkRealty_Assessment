from fastapi import FastAPI
from app.routers import lead, agent

app = FastAPI(
    title="ThinkRealty Lead Management",
    version="1.0.0"
)

# --- Register Routers ---
app.include_router(lead.router)     # /api/v1/leads/*
app.include_router(agent.router)    # /api/v1/agents/*


# --- Root health check ---
@app.get("/")
async def root():
    return {"message": "ThinkRealty Backend API is running"}
