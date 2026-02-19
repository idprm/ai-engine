# AI Platform Engine: DDD Architecture with LangGraph & RabbitMQ

A scalable AI processing platform built with **Domain-Driven Design (DDD)** architecture, featuring microservices, asynchronous job processing, and LangGraph-powered agentic workflows.

---

## Key Features

- **Domain-Driven Design** — Classic 4-layer architecture (Domain, Application, Infrastructure, Interface) with isolated bounded contexts
- **Microservices Architecture** — Decoupled Gateway and AI Engine services
- **Asynchronous Processing** — RabbitMQ message broker for long-running AI tasks
- **Dynamic Configuration** — LLM configs and prompt templates stored in PostgreSQL for runtime changes
- **LangGraph Integration** — Stateful, multi-step agent workflows
- **Multi-Agent Architecture** — Specialized agents (Main, Fallback, Followup, Moderation) with intelligent routing
- **High Performance** — SQLAlchemy 2.0 with asyncpg, Redis caching, connection pooling

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        GATEWAY SERVICE                          │
├─────────────────────────────────────────────────────────────────┤
│  Interface/        │  Application/      │  Domain/             │
│  - controllers/    │  - services/       │  - entities/         │
│  - routes/         │  - dto/            │  - value_objects/    │
│  - schemas/        │                    │  - repositories/     │
│                    │                    │  - events/           │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure/                                                 │
│  - persistence/ (SQLAlchemy repos)    - cache/ (Redis)         │
│  - messaging/   (RabbitMQ publishers)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                         RabbitMQ
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        AI ENGINE SERVICE                        │
├─────────────────────────────────────────────────────────────────┤
│  Interface/        │  Application/      │  Domain/             │
│  - handlers/      │  - services/       │  - entities/         │
│    (MQ consumer)  │  - dto/            │  - value_objects/    │
│                   │                    │  - services/         │
│                   │                    │  - events/           │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure/                                                 │
│  - persistence/ (SQLAlchemy repos)    - cache/ (Redis)         │
│  - llm/   (LangChain/LangGraph)       - messaging/ (Consumer)  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
ai-platform/
├── docker-compose.yml
├── pyproject.toml
├── .env.example
│
├── .github/
│   └── workflows/
│       └── docker.yml              # CI/CD pipeline
│
├── shared/                         # Shared kernel
│   ├── config/settings.py          # Pydantic settings
│   ├── events/base_event.py        # Domain event base
│   └── exceptions/                 # Domain exceptions
│
├── services/
│   ├── gateway/                    # FastAPI REST API
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── src/gateway/
│   │       ├── domain/
│   │       │   ├── entities/job.py
│   │       │   ├── value_objects/  # JobId, JobStatus, Prompt
│   │       │   ├── events/         # JobCreated, JobCompleted
│   │       │   └── repositories/   # JobRepository (interface)
│   │       ├── application/
│   │       │   ├── services/job_service.py
│   │       │   └── dto/job_dto.py
│   │       ├── infrastructure/
│   │       │   ├── persistence/    # SQLAlchemy repos
│   │       │   ├── messaging/      # RabbitMQ publisher
│   │       │   └── cache/          # Redis client
│   │       └── interface/
│   │           ├── controllers/job_controller.py
│   │           ├── routes/api.py
│   │           └── schemas/job_schemas.py
│   │
│   └── ai_engine/                  # Worker service
│       ├── Dockerfile
│       ├── pyproject.toml
│       └── src/ai_engine/
│           ├── domain/
│           │   ├── entities/       # LLMConfig, PromptTemplate, AgentConfig
│           │   ├── value_objects/  # Provider, ModelName, Temperature
│           │   ├── services/       # LLMSelector
│           │   └── repositories/   # Repository interfaces
│           ├── application/
│           │   ├── services/processing_service.py
│           │   └── dto/processing_dto.py
│           ├── infrastructure/
│           │   ├── persistence/    # Repository implementations
│           │   ├── llm/            # LLMFactory, LangGraphRunner, AgentNodes, AgentState
│           │   ├── messaging/      # RabbitMQ consumer
│           │   └── cache/          # Redis client
│           └── interface/
│               └── handlers/message_handler.py
│
└── infra/
    └── docker/
        ├── postgres/init.sql
        └── rabbitmq/definitions.json
```

---

## Tech Stack

| Category | Technology |
|---|---|
| Language | Python 3.12+ |
| Web Framework | FastAPI |
| Task Queue | RabbitMQ (aio-pika) |
| Database | PostgreSQL + asyncpg |
| Cache / State | Redis |
| AI Framework | LangChain, LangGraph |
| ORM | SQLAlchemy 2.0 (Async) |
| Validation | Pydantic v2 |
| Containerization | Docker & Docker Compose |

---

## Setup & Installation

### 1. Prerequisites

- Docker and Docker Compose
- API Keys for LLM providers (OpenAI, Anthropic)

### 2. Configuration

```bash
# Copy environment file
cp .env.example .env

# Add your API keys
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run Services

```bash
docker-compose up --build
```

---

## API Endpoints

### Submit a Job

```bash
curl -X POST "http://localhost:8000/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a haiku about programming",
    "config_name": "default-smart",
    "template_name": "default-assistant"
  }'
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "QUEUED"
}
```

### Check Job Status

```bash
curl "http://localhost:8000/v1/jobs/550e8400-e29b-41d4-a716-446655440000"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "result": "Code flows like water\nBugs hide in the logic streams\nDebug brings clarity",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:05"
}
```

### Health Check

```bash
curl "http://localhost:8000/health"
```

---

## Domain Models

### Gateway Bounded Context

**Job Aggregate:**
- `JobId` — Unique identifier (UUID)
- `Prompt` — User input with validation
- `JobStatus` — QUEUED → PROCESSING → COMPLETED | FAILED
- Events: `JobCreated`, `JobStatusChanged`, `JobCompleted`, `JobFailed`

### AI Engine Bounded Context

**LLMConfig Aggregate:**
- `Provider` — openai | anthropic
- `ModelName` — gpt-4-turbo, claude-3-opus, etc.
- `Temperature` — 0.0 to 2.0 (validated)

**PromptTemplate Aggregate:**
- Name and content with optional variables

**AgentConfig Entity:**
- `AgentType` — main | fallback | followup | moderation
- System prompt and LLM configuration per agent
- Temperature, max_tokens, retry settings

---

## Multi-Agent Architecture

The AI Engine supports a sophisticated multi-agent system with intelligent routing:

```
                    ┌─────────────────┐
                    │  START          │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ moderation_node │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   router_node   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
     │ main_agent  │ │followup_    │ │ fallback_   │
     │             │ │agent        │ │ agent       │
     └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
            │               │               │
            └───────────────┼───────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │      END        │
                    └─────────────────┘
```

### Agent Types

| Agent | Purpose |
|-------|---------|
| **Main** | Primary response handler for standard queries |
| **Fallback** | Handles errors and moderation violations |
| **Followup** | Manages conversation continuity and depth |
| **Moderation** | Content filtering and policy validation |

### Usage

```python
# Single-agent (backward compatible)
result = await processing_service.process(request)

# Multi-agent pipeline
result = await processing_service.process_multi_agent(
    request=request,
    context={"is_followup": False},
    needs_moderation=True,
)
```

---

## Database Schema

```sql
-- LLM Configurations
CREATE TABLE llm_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    provider VARCHAR(100) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    api_key_env VARCHAR(255) NOT NULL,
    temperature REAL DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 4096,
    is_active BOOLEAN DEFAULT TRUE
);

-- Prompt Templates
CREATE TABLE prompt_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    description TEXT
);

-- Agent Prompt Templates (multi-agent system)
INSERT INTO prompt_templates (name, content, description) VALUES
    ('main-agent', 'Primary agent system prompt...', 'Primary agent for handling user requests'),
    ('fallback-agent', 'Fallback agent system prompt...', 'Fallback agent for error recovery'),
    ('followup-agent', 'Followup agent system prompt...', 'Agent for conversation continuity'),
    ('moderation-agent', 'Moderation agent system prompt...', 'Agent for content moderation');
```

---

## Scaling

Scale workers horizontally:

```bash
docker-compose up --scale ai-engine=4
```

RabbitMQ distributes messages across all worker instances automatically.

---

## Development

### Local Development (without Docker)

```bash
# Install dependencies
pip install -e .
pip install -e ./services/gateway
pip install -e ./services/ai_engine

# Run Gateway
uvicorn gateway.main:app --reload

# Run AI Engine
python -m ai_engine.main
```

### Running Tests

```bash
pytest tests/
```

---

## CI/CD

This project uses GitHub Actions for continuous integration and deployment.

### Workflow

The CI/CD pipeline (`.github/workflows/docker.yml`) automatically:

1. **Builds** Docker images for both services on every push/PR
2. **Pushes** images to Docker Hub on `main`/`master` branch

### Image Tags

| Trigger | Tag Format |
|---------|------------|
| Main branch | `latest`, `sha-<commit>` |
| Version tag | `v1.0.0`, `v1.0` |
| Pull request | `pr-<number>` (build only, no push) |

### Required Secrets

Configure these in your GitHub repository settings:

| Secret | Description |
|--------|-------------|
| `DOCKER_USERNAME` | Docker Hub username |
| `DOCKER_PASSWORD` | Docker Hub access token |

### Manual Deploy

```bash
# Build and push manually
docker build -f services/gateway/Dockerfile -t your-username/ai-platform-gateway:latest .
docker build -f services/ai_engine/Dockerfile -t your-username/ai-platform-ai-engine:latest .
docker push your-username/ai-platform-gateway:latest
docker push your-username/ai-platform-ai-engine:latest
```

---

## DDD Layer Responsibilities

| Layer | Responsibility |
|-------|---------------|
| **Domain** | Business logic, entities, value objects, domain events, repository interfaces |
| **Application** | Use case orchestration, DTOs, application services |
| **Infrastructure** | External adapters, repository implementations, messaging |
| **Interface** | HTTP controllers, message handlers, API schemas |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) |
| `REDIS_URL` | Redis connection string |
| `RABBITMQ_URL` | RabbitMQ AMQP connection string |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
