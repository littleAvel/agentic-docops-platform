# Agentic Document Ops Platform

A production-oriented agentic document processing platform built with FastAPI and LLM-driven workflows, focused on determinism, observability, and safety.

The system executes document processing as a controlled agent workflow (not a chatbot), with a strict job lifecycle, policy-guarded tool execution, structured audit logs, and artifact persistence.

This project demonstrates how to build reliable, inspectable LLM systems suitable for real-world automation.

---

## What this project demonstrates

- Designing agentic systems as deterministic workflows, not chats
- Enforcing explicit state machines for long-running LLM jobs
- Treating LLMs as untrusted components
- Guarding tool usage with deny-by-default policies
- Building auditable, replayable LLM pipelines
- Separating planning, execution, verification, and actions
- Production-grade FastAPI architecture with async SQLAlchemy


## Core Concepts

**Agent ≠ Chatbot**

This system is **not conversational**.
An agent here is **a workflow executor** that:
- Receives a job
- Plans steps
- Executes tools under constraints
- Verifies results
- Produces side effects (artifacts, exports, actions)

All steps are explicit, logged, and bounded.


## Features
- Job-based execution model
- Strict job state machine
- Deterministic planner + bounded executor
- Policy-guarded tool registry
- Structured audit events
- Artifacts persistence
- Signals store for inter-step communication
- FastAPI REST API
- Server-rendered UI (Jinja2) for inspection
- OpenAPI documentation
- Health & readiness probes


## Job Lifecycle

Each job progresses through a strict finite state machine:
```
    RECEIVED
    ↓
    PREPROCESSED
    ↓
    ROUTED
    ↓
    PLANNED
    ↓
    EXECUTING
    ↓
    VERIFIED
    ↓
    ACTED
    ↓
    SUCCEEDED / FAILED / NEEDS_REVIEW
```
Invalid transitions are explicitly blocked.


## Architecture
High-level system flow
```
User / API / UI
      ↓
 Job Created
      ↓
 Planner (deterministic)
      ↓
 Bounded Executor
   (max steps, max tools, max cost)
      ↓
 Tool Calls (policy-guarded)
      ↓
 Verification
      ↓
 Actions
      ↓
 Artifacts + Audit Log
```

## Core components

- **Planner**
    - Generates deterministic execution plans
    - No free-form reasoning loops

- **Executor**
    - Enforces:
        - max steps
        - max tool calls
        - cost limits
    - Stops execution on violations
- **Tool Registry**
    - Explicit schemas (Pydantic)
    - Deny-by-default
    - Policy evaluation before every call
- **Verification Layer**
    - Confirms correctness of outputs
    - Can reject or flag results

- **Audit Log**
    - Every meaningful event is recorded:
        - job created
        - state changes
        - tool calls
        - policy denials
        - errors

- Artifacts
    - Persisted outputs:
        - extracted JSON
        - reports
        - exports
        - rafts


## API Overview

`POST /jobs` — create a job

`GET /jobs/{job_id}` — job details

`POST /jobs/{job_id}/run` — run job

`GET /jobs/{job_id}/events` — audit events

`GET /jobs/{job_id}/artifacts` — artifacts

`GET /health` — liveness

`GET /ready` — readiness

`GET /docs` — OpenAPI



## UI (Optional Inspection Layer)

The UI is **server-rendered (Jinja2)** and intentionally minimal.

It allows you to:
- Create jobs
- Run jobs
- Inspect:
    - job state
    - signals
    - audit events
    - artifacts

UI is **not core logic** — it is an **inspection/debugging surface**.

---

## Quickstart
### 1) Setup

Create `.env`:

```
OPENAI_API_KEY=your_key_here
LOG_LEVEL=INFO
```

Install dependencies:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Run the service
```
uvicorn app.main:app --reload
```
- UI: http://127.0.0.1:8000/
- API docs: http://127.0.0.1:8000/docs

### 3) Create & run a job

Via UI or API:

```
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{ "text": "Invoice #123. Total 50 USD." }'
```

Then:
```
POST /jobs/{job_id}/run
```


## Reliability & Guardrails

- Deterministic planning
- Explicit state transitions
- Tool schema validation
- Policy enforcement
- Bounded execution
- Explicit failures instead of hallucinations
- Full audit trail
- No hidden agent memory


## Notes
This project is designed as a reference implementation for:
- Agentic systems
- LLM orchestration
- Safe automation pipelines

It intentionally prioritizes clarity and control over raw model capability.


## Future Improvements

- Multi-agent orchestration
- Queue-based execution (Celery / Temporal)
- Retry & compensation strategies
- Artifact versioning
- RBAC & auth
- Streaming execution logs
- Cost tracking per job
- Pluggable planners