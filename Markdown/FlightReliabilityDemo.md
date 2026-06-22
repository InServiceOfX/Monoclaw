# Flight Reliability AI Agent Dashboard — Demo Plan
**For:** SpaceX Sr. SWE (Flight Reliability) application  
**Timeline:** Wed–Fri morning, 2026-05-06 to 2026-05-09  
**Repo:** Create `Monoclaw/JavaScript/flight-reliability-demo`

---

## What We're Building

A React SPA + FastAPI + PostgreSQL application that demonstrates exactly what the Flight Reliability team builds:

> Engineers submit engineering changes (ECR analog). An LLM agent analyzes the change, identifies which vehicle systems are affected, what risks it introduces, and recommends mitigations. Results are stored in PostgreSQL and displayed in a real-time dashboard.

**Tech stack** (maps directly to JD requirements):
- Frontend: React + TypeScript + Tailwind (SPA)
- Backend: FastAPI (Python)
- Database: PostgreSQL
- AI: Anthropic Claude or Grok API as the risk agent
- Deployment: Docker Compose (single command to run)

---

## Why This Demo

The JD says explicitly:
- "manage engineering changes and mitigate risks affecting SpaceX's fleet"
- "building Agentic AI systems to further streamline operations"
- "build prototypes to prove out key design concepts"

This demo is a direct prototype of what they're building. It's not a toy. It's a point of discussion.

---

## Architecture

```
┌─────────────────────────────────────────┐
│            React SPA (Port 5173)        │
│  - ECR Submit Form                      │
│  - Risk Dashboard (table + risk badges) │
│  - AI Analysis Panel                    │
└──────────────┬──────────────────────────┘
               │ REST API
┌──────────────▼──────────────────────────┐
│           FastAPI (Port 8000)           │
│  POST /ecr         → submit change      │
│  GET  /ecr         → list all           │
│  GET  /ecr/{id}    → detail + analysis  │
│  POST /ecr/{id}/analyze → trigger agent │
└──────────────┬──────────────────────────┘
               │ SQLAlchemy
┌──────────────▼──────────────────────────┐
│           PostgreSQL (Port 5432)        │
│  engineering_changes                    │
│  risk_assessments                       │
│  affected_systems                       │
└─────────────────────────────────────────┘
               │ LLM API
┌──────────────▼──────────────────────────┐
│      Claude / Grok Risk Agent           │
│  - Reads ECR description                │
│  - Identifies affected vehicle systems  │
│  - Risk level: LOW / MED / HIGH / CRIT  │
│  - Generates mitigation recommendations │
└─────────────────────────────────────────┘
```

---

## Database Schema

```sql
CREATE TABLE engineering_changes (
    id SERIAL PRIMARY KEY,
    ecr_number VARCHAR(20) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    vehicle VARCHAR(50),          -- Falcon9, Starship, Starlink, Dragon
    subsystem VARCHAR(100),
    submitted_by VARCHAR(100),
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending'  -- pending, analyzed, approved, rejected
);

CREATE TABLE risk_assessments (
    id SERIAL PRIMARY KEY,
    ecr_id INTEGER REFERENCES engineering_changes(id),
    risk_level VARCHAR(20),       -- LOW, MEDIUM, HIGH, CRITICAL
    affected_systems TEXT[],
    analysis TEXT,
    mitigations TEXT,
    confidence FLOAT,
    model_used VARCHAR(100),
    analyzed_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## LLM Agent Design

**System prompt:**
```
You are a Flight Reliability engineer at a launch vehicle company.
You analyze Engineering Change Requests (ECRs) and assess their risk to vehicle reliability and mission success.

For each ECR you will:
1. Identify which vehicle systems are potentially affected (propulsion, avionics, structures, thermal, GNC, software, comms, power)
2. Assess risk level: LOW / MEDIUM / HIGH / CRITICAL
3. Provide a 2-3 sentence risk rationale
4. List 2-4 concrete mitigation recommendations
5. Estimate confidence in assessment (0.0-1.0)

Respond in JSON format.
```

**Tool use (optional stretch)**: Give the agent a `lookup_similar_changes` tool that queries the DB for historical ECRs with similar subsystem + risk level — demonstrates RAG/context retrieval from the JD.

---

## Demo Data (Seed)

Pre-load 5-10 realistic ECRs to make the demo non-empty:

| ECR | Vehicle | Subsystem | Change | Expected Risk |
|-----|---------|-----------|--------|---------------|
| ECR-0001 | Falcon 9 | Propulsion | Replace Merlin LOX pump seal material from Inconel to Ti-6Al-4V | HIGH |
| ECR-0002 | Starship | Avionics | Upgrade flight computer OS from VxWorks 6.9 to 7.0 | MEDIUM |
| ECR-0003 | Starlink | Software | Increase beam steering update rate from 100Hz to 500Hz | LOW |
| ECR-0004 | Dragon | Structures | Reduce heat shield panel overlap by 2mm for mass savings | CRITICAL |
| ECR-0005 | Falcon 9 | GNC | Modify roll control authority limits during max-Q | HIGH |

---

## Build Plan

### Wednesday (today) — Backend + AI core

- [ ] `cd Monoclaw/JavaScript && npx create-vite@latest flight-reliability-demo --template react-ts`
- [ ] Create `backend/` directory: FastAPI + SQLAlchemy + asyncpg
- [ ] `docker-compose.yml`: postgres + backend + frontend services
- [ ] Database schema + Alembic migration
- [ ] `POST /ecr` and `GET /ecr` endpoints (no AI yet)
- [ ] LLM agent: system prompt + structured JSON output
- [ ] `POST /ecr/{id}/analyze` → calls LLM → stores risk_assessment
- [ ] Seed script with 5 demo ECRs + run analysis on all

### Thursday — Frontend + polish

- [ ] ECR Submit form (title, description, vehicle, subsystem)
- [ ] Dashboard table with risk level badges (color-coded)
- [ ] ECR detail view with AI analysis panel
- [ ] "Analyze" button that triggers agent and shows streaming response or spinner
- [ ] Simple risk summary stats at top (X critical, Y high, etc.)
- [ ] README with one-command Docker setup
- [ ] Screenshot / demo GIF

### Friday morning — Wrap

- [ ] Clean up code, add minimal comments on non-obvious decisions
- [ ] Push to GitHub public repo
- [ ] Link in resume and/or application materials
- [ ] Done by 10am

---

## What This Demonstrates to SpaceX

| JD Requirement | Demo Shows |
|----------------|-----------|
| 5+ yr SPA | React + TypeScript SPA with routing, state management |
| PostgreSQL | Schema design, migrations, async queries |
| Agentic AI systems | LLM agent with structured output, stored results |
| LLM prompting | System prompt engineering for domain-specific task |
| Context retrieval | (stretch) RAG over historical ECRs |
| Docker | docker-compose, one-command deploy |
| Python backend | FastAPI, SQLAlchemy, async |
| Risk mitigation tooling | Literally what they build |

---

## Alternatives Considered and Rejected

**OpenFoam + OpenClaw**: CFD ≠ flight reliability ops tooling. Wrong domain for this role.

**Improved grokicad + NSpice**: Electronics CAD schematic review ≠ engineering change risk management. grokicad already exists — unclear what "improved" means in 2 days.

**Cosmos orbit simulation**: Physics/math demo. Doesn't show SPA, PostgreSQL, agentic AI, or any of the preferred skills. The WASM demo is cool for a different role.

---

## Notes

- Keep scope ruthlessly minimal. MVP = submit form + analysis + dashboard. No auth, no pagination, no multi-user.
- The seed data + pre-run analyses mean the demo looks complete even before a live analysis runs.
- Use streaming if time permits (makes the AI feel alive in the demo).
