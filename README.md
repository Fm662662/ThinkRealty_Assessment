# ThinkRealty Lead Management System

## Introduction & Overview
The **ThinkRealty Lead Management System** is a FastAPI-based application designed to manage real estate leads and Agents.  
It provides functionality for:
- Lead capturing, scoring, and assignment  
- Agent workload balancing  
- Performance tracking and analytics  
- Business rules enforcement with PostgreSQL triggers  

The system can run **locally without Docker** or **inside Docker containers**.  
In both cases, the database schema is created in **pgAdmin 4 (PostgreSQL)** using provided `.sql` files.

---

## Tech Stack
- **Backend Framework**: FastAPI (Python 3.11)  
- **Database**: PostgreSQL (via pgAdmin 4 for management)  
- **ORM**: SQLAlchemy (async with asyncpg)  
- **Caching**: Redis  
- **Containerization**: Docker & Docker Compose  

---

## Required Software
Before running the project, install the following:
- [Python 3.11+](https://www.python.org/downloads/)  
- [PostgreSQL](https://www.postgresql.org/download/) & [pgAdmin 4](https://www.pgadmin.org/download/)  
- [Redis](https://redis.io/download/)  
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for containerized setup)  

---

## Project Structure
TR (root)/
│── app/
│ ├── routers/      # FastAPI routes (agents, leads, etc.)
│ ├── services/     # Business logic (lead scoring, assignment, etc.)
│ ├── db/           # Database session, base_class, redis client
│ ├── schemas/      # Pydantic schemas
│ ├── models/       # SQLAlchemy ORM models
│ └── main.py       # FastAPI entry point
│
│── databse_design/
│ ├── db_schema.sql     # Create all tables
│ ├── db_triggers.sql   # Enforce business rules
│ └── db_seed.sql       # Insert sample data
│
│── requirements.txt    # Python dependencies
│── Dockerfile          # Docker build instructions
│── docker-compose.yml  # Multi-container setup (app + postgres + redis)
│── README.md           # Project documentation
│──queries/
  ├── 4.1_query.sql     # All queries in queries folder 
  ├── 4.2_query.sql
  ├── 4.3_query.sql

---

## Database Setup (Required for Both Modes)
1. Open **pgAdmin 4**.  
2. Create a new database named `thinkrealty_leads`.  
3. Run the SQL scripts in order:
   - `db_schema.sql` → creates tables  
   - `db_triggers.sql` → adds business rule triggers  
   - `db_seed.sql` → seeds with initial data  

---

## Running Without Docker (Local Development)
1. **Clone the repository**  
   ```bash
   git clone https://github.com/Fm662662/ThinkRealty_Assessment.git
   cd ThinkRealty_Assessment

2. **Create virtual environment**  
   ```bash
    python -m venv venv
    source venv/bin/activate   # Mac/Linux
    venv\Scripts\activate      # Windows

3. **Install dependencies**  
   ```bash
    pip install -r requirements.txt

4. **Set environment variables (in .env or system)**  
DATABASE_URL=postgresql+asyncpg://user:password@localhost/thinkrealty_leads
REDIS_URL=redis://localhost:6379/1

5. **Run FastAPI app with Uvicorn**  
   ```bash
    uvicorn app.main:app --reloa

6. **Access the API**
API Base: http://127.0.0.1:8000
Swagger Docs: http://127.0.0.1:8000/docs

---

## Running With Docker

1. **Create and initialize the database in pgAdmin 4**  
   - Create a database named `thinkrealty_leads`.  
   - Run the SQL scripts in order:  
     - `db_schema.sql`  
     - `db_triggers.sql`  
     - `db_seed.sql`  

2. **Build the Docker image and start the containers**  
   ```bash
   docker-compose up --build

3. **Services started by docker-compose**
FastAPI application → available at http://localhost:8000
PostgreSQL database → available at postgres:5432 (inside Docker network)
Redis cache → available at redis:6379 (inside Docker network)

4. **Environment configuration inside Docker**
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/thinkrealty_leads
REDIS_URL=redis://redis:6379/1

5. **Access the API**
Base URL: http://localhost:8000
Swagger UI: http://localhost:8000/docs

---

| Service     | Without Docker   | With Docker                         |
| ----------- | ---------------- | ----------------------------------- |
| FastAPI App | `127.0.0.1:8000` | `localhost:8000`                    |
| PostgreSQL  | `localhost:5432` | `postgres:5432` (container network) |
| Redis       | `localhost:6379` | `redis:6379` (container network)    |








