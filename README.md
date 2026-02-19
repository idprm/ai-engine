# AI Platform Engine: DDD Architecture with LangGraph & RabbitMQ

A scalable AI processing platform built with **Domain-Driven Design (DDD)** architecture, featuring microservices, asynchronous job processing, and LangGraph-powered agentic workflows.

---

## Key Features

- **Domain-Driven Design** — Classic 4-layer architecture (Domain, Application, Infrastructure, Interface) with isolated bounded contexts
- **Microservices Architecture** — Decoupled Gateway, LLM Worker, Messenger, and Commerce Agent services
- **Asynchronous Processing** — RabbitMQ message broker for long-running AI tasks
- **Dynamic Configuration** — LLM configs and prompt templates stored in PostgreSQL for runtime changes
- **LangGraph Integration** — Stateful, multi-step agent workflows with tool-calling
- **Multi-Agent Architecture** — Specialized agents (Main, Fallback, Followup, Moderation) with intelligent routing
- **WhatsApp Commerce Agent** — Multi-tenant customer service with product catalog, orders, and payments
- **Payment Integration** — Midtrans and Xendit payment gateway support
- **Customer Service Tools** — Labels/Tagging, Quick Replies, Ticket System for support management
- **High Performance** — SQLAlchemy 2.0 with asyncpg, Redis caching, connection pooling
- **LLM Resilience** — Timeout handling, exponential backoff, circuit breaker, job-level retry

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           GATEWAY SERVICE                                │
│                    (All HTTP Endpoints - No Business Logic)             │
├─────────────────────────────────────────────────────────────────────────┤
│  Interface/                    │  CRM Context/                          │
│  - controllers/job_controller  │  - crm/dependencies.py (DI)            │
│  - controllers/wa_controller   │  - crm/publishers.py (Queue)           │
│  - controllers/crm/*           │                                        │
│  - routes/api.py               │  Imports from CRM:                     │
│  - routes/crm_routes.py        │  - domain/entities, value_objects      │
│                                │  - application/services, dto           │
│                                │  - infrastructure/persistence          │
├─────────────────────────────────────────────────────────────────────────┤
│  Infrastructure/                                                         │
│  - persistence/ (SQLAlchemy repos)    - cache/ (Redis)                  │
│  - messaging/   (RabbitMQ publishers)                                    │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                         RabbitMQ
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│   LLM WORKER      │ │   MESSENGER       │ │ COMMERCE AGENT    │
│   SERVICE         │ │   SERVICE         │ │   (Background)    │
├───────────────────┤ ├───────────────────┤ ├───────────────────┤
│  - LLM Pipeline   │ │  - WhatsApp API   │ │  - Multi-tenant   │
│  - Multi-agent    │ │  - Message send   │ │  - Product catalog│
│  - LangGraph      │ │  - WAHA client    │ │  - Order mgmt     │
└───────────────────┘ └───────────────────┘ │  - Payments       │
                                          │  - LLM Processing │
                                          │  - NO HTTP        │
                                          └───────────────────┘
```

### Message Flow

```
[WhatsApp] --webhook--> [Gateway] --RabbitMQ (crm_tasks)--> [CRM Worker]
     │                     │                                    │
     │              All HTTP APIs                              LLM Processing
     │              /v1/crm/*                                   │
     │                                                          │
[WhatsApp] <--send-- [Messenger] <--RabbitMQ (wa_messages)--┘
```

**Note:** Commerce Agent is now a **background worker only** - all HTTP routes have been moved to Gateway.

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
│   ├── gateway/                    # FastAPI REST API (All HTTP endpoints)
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
│   │       │   ├── messaging/      # RabbitMQ publisher, DelayedTaskPublisher
│   │       │   └── cache/          # Redis client
│   │       ├── crm/                # CRM context (DI, publishers)
│   │       │   ├── dependencies.py # DI factories for CRM repos/services
│   │       │   └── publishers.py   # CRM task queue publisher
│   │       └── interface/
│   │           ├── controllers/
│   │           │   ├── job_controller.py
│   │           │   ├── wa_controller.py
│   │           │   └── crm/        # Migrated CRM controllers
│   │           │       ├── tenant_controller.py
│   │           │       ├── product_controller.py
│   │           │       ├── order_controller.py
│   │           │       ├── webhook_controller.py
│   │           │       ├── label_controller.py
│   │           │       └── quick_reply_controller.py
│   │           ├── routes/
│   │           │   ├── api.py
│   │           │   └── crm_routes.py
│   │           └── schemas/
│   │
│   ├── llm-worker/                 # Worker service
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── src/llm_worker/
│   │       ├── domain/
│   │       │   ├── entities/       # LLMConfig, PromptTemplate, AgentConfig
│   │       │   ├── value_objects/  # Provider, ModelName, Temperature
│   │       │   ├── services/       # LLMSelector
│   │       │   └── repositories/   # Repository interfaces
│   │       ├── application/
│   │       │   ├── services/processing_service.py
│   │       │   └── dto/processing_dto.py
│   │       ├── infrastructure/
│   │       │   ├── persistence/    # Repository implementations
│   │       │   ├── llm/            # LLMFactory, LangGraphRunner, AgentNodes, AgentState
│   │       │   │   ├── timeout.py           # Timeout wrapper
│   │       │   │   ├── response_validator.py # Response validation
│   │       │   │   ├── backoff.py           # Exponential backoff
│   │       │   │   ├── circuit_breaker.py   # Circuit breaker pattern
│   │       │   │   └── ...
│   │       │   ├── messaging/      # RabbitMQ consumer
│   │       │   └── cache/          # Redis client
│   │       └── interface/
│   │           └── handlers/message_handler.py
│   │
│   ├── messenger/                  # WhatsApp message sender
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── src/messenger/
│   │       ├── infrastructure/
│   │       │   ├── waha/           # WAHA API client
│   │       │   └── messaging/      # RabbitMQ consumer
│   │       └── main.py
│   │
│   └── commerce-agent/             # Commerce Agent WORKER (background only)
│       ├── Dockerfile              # Runs worker.py, not uvicorn
│       ├── pyproject.toml
│       └── src/commerce_agent/
│           ├── worker.py           # Worker entry point (NO HTTP)
│           ├── main.py             # Deprecated (for dev only)
│           ├── domain/
│           │   ├── entities/       # Tenant, Customer, Product, Order, Conversation, Payment
│           │   ├── value_objects/  # TenantId, OrderStatus, Money, ConversationState
│           │   ├── events/         # Domain events
│           │   └── repositories/   # Repository interfaces
│           ├── application/
│           │   ├── services/       # ChatbotOrchestrator, OrderService, CustomerService
│           │   ├── dto/            # Data transfer objects
│           │   └── handlers/       # WAMessageHandler
│           ├── infrastructure/
│           │   ├── persistence/    # SQLAlchemy repositories
│           │   ├── messaging/      # RabbitMQ consumer/publisher
│           │   ├── llm/            # CRMLangGraphRunner, tools
│           │   ├── payment/        # Midtrans, Xendit clients
│           │   └── cache/          # Conversation cache
│           └── interface/          # (DEPRECATED - routes moved to Gateway)
│
└── infra/
    └── docker/
        ├── postgres/
        │   ├── init.sql
        │   └── migrations/
        │       └── 002_add_resilience_columns.sql
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
- `JobStatus` — QUEUED → PROCESSING → COMPLETED | FAILED | RETRYING
- `max_retries` — Maximum retry attempts (default: 3)
- `retry_count` — Current retry attempt
- `next_retry_at` — Scheduled time for next retry
- Events: `JobCreated`, `JobStatusChanged`, `JobCompleted`, `JobFailed`

### LLM Worker Bounded Context

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

The LLM Worker supports a sophisticated multi-agent system with intelligent routing:

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

## LLM Worker Resilience

The LLM Worker implements comprehensive resilience patterns to handle LLM failures gracefully:

```
                    ┌──────────────────────────────────────┐
                    │           LLM WORKER                 │
                    │                                      │
Message ─────────>  │  ┌─────────────────────────────┐    │
(from queue)        │  │     Message Handler         │    │
                    │  │  - Receive message          │    │
                    │  │  - Check circuit breaker    │    │
                    │  └──────────┬──────────────────┘    │
                    │             │                        │
                    │  ┌──────────▼──────────┐            │
                    │  │  Processing Service  │            │
                    │  │  - Orchestrate flow  │            │
                    │  │  - Handle retries    │            │
                    │  └──────────┬──────────┘            │
                    │             │                        │
                    │  ┌──────────▼──────────┐            │
                    │  │   LangGraph Runner   │            │
                    │  │  - Multi-agent flow  │            │
                    │  │  - Backoff retry     │            │
                    │  └──────────┬──────────┘            │
                    │             │                        │
                    │  ┌──────────▼──────────┐            │
                    │  │    Agent Nodes      │            │
                    │  │  ┌──────────────┐   │            │
                    │  │  │   TIMEOUT    │   │            │
                    │  │  │   WRAPPER    │   │            │
                    │  │  └──────┬───────┘   │            │
                    │  │         │           │            │
                    │  │  ┌──────▼───────┐   │            │
                    │  │  │   CIRCUIT    │   │            │
                    │  │  │   BREAKER    │   │            │
                    │  │  └──────┬───────┘   │            │
                    │  │         │           │            │
                    │  │  ┌──────▼───────┐   │            │
                    │  │  │    LLM       │   │            │
                    │  │  │   ainvoke()  │   │            │
                    │  │  └──────────────┘   │            │
                    │  │  - Validate response│            │
                    │  └─────────────────────┘            │
                    └──────────────────────────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │           RESULT                 │
                    │  - Success → Cache result        │
                    │  - Retryable → Schedule retry    │
                    │  - Failed → Mark job FAILED      │
                    └─────────────────────────────────┘
```

### Resilience Features

| Feature | Description |
|---------|-------------|
| **Timeout Wrapper** | Wraps LLM calls with `asyncio.wait_for()` to prevent hanging |
| **Response Validation** | Validates responses for empty/whitespace/error indicators |
| **Exponential Backoff** | Retry delays with jitter to prevent thundering herd |
| **Circuit Breaker** | Prevents cascading failures during LLM outages |
| **Job-Level Retry** | Automatic retry with delayed re-queue via RabbitMQ DLX |

### Configuration

Configure resilience settings via environment variables:

```bash
# LLM Resilience Settings
LLM_DEFAULT_TIMEOUT_SECONDS=120    # Default timeout for LLM calls
LLM_MAX_RETRIES=3                  # Max retry attempts per call
LLM_RETRY_INITIAL_DELAY=1.0        # Initial delay in seconds
LLM_RETRY_MAX_DELAY=60.0           # Maximum delay cap

# Circuit Breaker Settings
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5  # Failures before opening
CIRCUIT_BREAKER_SUCCESS_THRESHOLD=2  # Successes to close
CIRCUIT_BREAKER_TIMEOUT_SECONDS=60.0  # Time before half-open

# Job Retry Settings
JOB_DEFAULT_MAX_RETRIES=3          # Max job-level retries
JOB_RETRY_DELAY_MIN=5.0            # Minimum retry delay
JOB_RETRY_DELAY_MAX=300.0          # Maximum retry delay (5 min)
```

### Circuit Breaker States

```
     ┌──────────────────────────────────────────┐
     │                                          │
     ▼                                          │
  CLOSED ────(5 failures)───> OPEN ────(60s)───> HALF_OPEN
     │                          │                    │
     │                          │                    │
     │<──────(2 successes)──────┘<───(failure)──────┘
     │
   Normal
  Operation
```

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Requests rejected immediately, prevents cascading failures
- **HALF_OPEN**: Testing recovery, limited requests allowed

### Job Retry Flow

```
QUEUED → PROCESSING → RETRYING → QUEUED (retry) → PROCESSING → ...
                        │
                        └──(max retries)──> FAILED
```

### Response Validation

The validator checks for:
- `None` or empty responses
- Whitespace-only responses
- Responses below minimum length threshold
- Error indicator patterns (e.g., "I cannot", "error occurred")

---

## Commerce Agent Service

The Commerce Agent is a **background worker service** that processes WhatsApp messages and payment callbacks. All HTTP endpoints have been moved to the Gateway service.

### Architecture Note

> **Important:** The Commerce Agent no longer exposes HTTP endpoints. All API routes (`/v1/crm/*`) are handled by the Gateway service. The Commerce Worker consumes messages from the `crm_tasks` queue and processes them asynchronously.

```
Gateway Service                      Commerce Agent Service
─────────────                        ─────────────────────
HTTP /v1/crm/tenants/*               Consumes crm_tasks queue
HTTP /v1/crm/products/*      ──>     LLM Processing
HTTP /v1/crm/orders/*               Message Handling
HTTP /v1/crm/webhook/*               Payment Processing
HTTP /v1/crm/labels/*
HTTP /v1/crm/quick-replies/*
```

### Features

- **Multi-tenant Architecture** — Each business has isolated products, customers, and configurations
- **WhatsApp Integration** — Via WAHA (WhatsApp HTTP API) for sending/receiving messages
- **Product Catalog** — Search products, check stock, get details
- **Order Management** — Create orders, add items, track status, cancel
- **Payment Integration** — Midtrans and Xendit payment gateways
- **AI-Powered Responses** — LangGraph agent with domain tools

### CRM Agent Tools

| Tool | Description |
|------|-------------|
| `search_products` | Search product catalog by query |
| `get_product_details` | Get full product info with variants |
| `check_stock` | Check variant availability |
| `create_order` | Create new empty order |
| `add_to_order` | Add item to current order |
| `get_order_status` | Check order status |
| `confirm_order` | Confirm order for payment |
| `initiate_payment` | Generate payment link |
| `get_customer_profile` | Get customer info |
| `update_customer_profile` | Update customer details |
| `label_conversation` | Apply label to conversation for categorization |
| `get_available_labels` | Get all available labels for tenant |
| `remove_label` | Remove label from conversation |

### Conversation States

```
GREETING → BROWSING → ORDERING → CHECKOUT → PAYMENT → COMPLETED
                ↑__________|___________|          |
                           |______________________|
```

### API Endpoints (Gateway Service)

All CRM endpoints are now served by the **Gateway service** at `http://localhost:8000`:
|----------|-------------|
| `POST /v1/crm/tenants` | Create tenant |
| `GET /v1/crm/tenants/{id}` | Get tenant |
| `PUT /v1/crm/tenants/{id}/prompt` | Update AI prompt |
| `POST /v1/crm/tenants/{id}/products` | Add product |
| `GET /v1/crm/tenants/{id}/products` | List products |
| `GET /v1/crm/orders/{id}` | Get order |
| `PUT /v1/crm/orders/{id}/status` | Update status |
| `POST /v1/crm/webhook/{tenant_id}` | WhatsApp webhook |
| `POST /v1/crm/payments/callback/{provider}` | Payment callback |
| **Labels** | |
| `POST /v1/crm/tenants/{id}/labels` | Create label |
| `GET /v1/crm/tenants/{id}/labels` | List labels |
| `PUT /v1/crm/tenants/{id}/labels/{label_id}` | Update label |
| `DELETE /v1/crm/tenants/{id}/labels/{label_id}` | Delete label |
| `POST /v1/crm/conversations/{id}/labels` | Apply label to conversation |
| `GET /v1/crm/conversations/{id}/labels` | Get conversation labels |
| **Quick Replies** | |
| `POST /v1/crm/tenants/{id}/quick-replies` | Create quick reply |
| `GET /v1/crm/tenants/{id}/quick-replies` | List quick replies |
| `PUT /v1/crm/tenants/{id}/quick-replies/{id}` | Update quick reply |
| `DELETE /v1/crm/tenants/{id}/quick-replies/{id}` | Delete quick reply |

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
    timeout_seconds INTEGER DEFAULT 120,  -- LLM call timeout
    is_active BOOLEAN DEFAULT TRUE
);

-- Jobs (with retry support)
CREATE TABLE jobs (
    id VARCHAR(36) PRIMARY KEY,
    prompt TEXT NOT NULL,
    config_name VARCHAR(255) NOT NULL,
    template_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'QUEUED',  -- QUEUED, PROCESSING, COMPLETED, FAILED, RETRYING
    result TEXT,
    error TEXT,
    max_retries INTEGER DEFAULT 3,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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

-- Labels for conversation tagging
CREATE TABLE labels (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    name VARCHAR(100) NOT NULL,
    color VARCHAR(7) DEFAULT '#3498db',
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(tenant_id, name)
);

-- Conversation Labels association
CREATE TABLE conversation_labels (
    conversation_id VARCHAR(100),
    label_id UUID REFERENCES labels(id),
    tenant_id UUID REFERENCES tenants(id),
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_by VARCHAR(50),
    PRIMARY KEY (conversation_id, label_id)
);

-- Quick Replies for template responses
CREATE TABLE quick_replies (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    shortcut VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100) DEFAULT 'general',
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(tenant_id, shortcut)
);

-- Ticket Boards
CREATE TABLE ticket_boards (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE
);

-- Tickets
CREATE TABLE tickets (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    board_id UUID REFERENCES ticket_boards(id),
    conversation_id VARCHAR(100),
    customer_id UUID REFERENCES customers(id),
    subject VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(30) DEFAULT 'open',
    priority VARCHAR(20) DEFAULT 'none',
    assignee_id VARCHAR(100),
    resolution TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    closed_at TIMESTAMP
);

-- Ticket Templates
CREATE TABLE ticket_templates (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    name VARCHAR(200) NOT NULL,
    subject_template TEXT,
    description_template TEXT,
    default_priority VARCHAR(20) DEFAULT 'none'
);
```

---

## Scaling

Scale workers horizontally:

```bash
docker-compose up --scale llm-worker=4
```

RabbitMQ distributes messages across all worker instances automatically.

---

## Development

### Local Development (without Docker)

```bash
# Install dependencies
pip install -e .
pip install -e ./services/gateway
pip install -e ./services/llm-worker
pip install -e ./services/commerce-agent

# Run Gateway (all HTTP endpoints)
uvicorn gateway.main:app --reload --port 8000

# Run LLM Worker (background worker)
python -m llm_worker.main

# Run Commerce Agent Worker (background worker)
python -m commerce_agent.worker
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

1. **Builds** Docker images for all services on every push/PR
2. **Pushes** images to Docker Hub on `main`/`master` branch

### Services

- `ai-platform-gateway` — Gateway service
- `ai-platform-llm-worker` — LLM Worker
- `ai-platform-messenger` — WhatsApp Messenger
- `ai-platform-commerce-agent` — Commerce Agent

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
docker build -f services/llm-worker/Dockerfile -t your-username/ai-platform-llm-worker:latest .
docker build -f services/messenger/Dockerfile -t your-username/ai-platform-messenger:latest .
docker build -f services/commerce-agent/Dockerfile -t your-username/ai-platform-commerce-agent:latest .  # Worker, not HTTP
docker push your-username/ai-platform-gateway:latest
docker push your-username/ai-platform-llm-worker:latest
docker push your-username/ai-platform-messenger:latest
docker push your-username/ai-platform-commerce-agent:latest
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
| `RABBITMQ_TASK_QUEUE` | Task queue name (default: `ai_tasks`) |
| `RABBITMQ_CRM_QUEUE` | CRM queue name (default: `crm_tasks`) |
| `RABBITMQ_WA_QUEUE` | WhatsApp message queue (default: `wa_messages`) |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `WAHA_SERVER_URL` | WAHA server URL |
| `WAHA_API_KEY` | WAHA API key |
| `MIDTRANS_SERVER_KEY` | Midtrans server key |
| `MIDTRANS_IS_PRODUCTION` | Use Midtrans production mode |
| `CONVERSATION_TTL` | Conversation cache TTL (seconds) |
| **LLM Resilience** | |
| `LLM_DEFAULT_TIMEOUT_SECONDS` | Default timeout for LLM calls (default: 120) |
| `LLM_MAX_RETRIES` | Max retry attempts per LLM call (default: 3) |
| `LLM_RETRY_INITIAL_DELAY` | Initial backoff delay in seconds (default: 1.0) |
| `LLM_RETRY_MAX_DELAY` | Maximum backoff delay cap (default: 60.0) |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | Failures before circuit opens (default: 5) |
| `CIRCUIT_BREAKER_SUCCESS_THRESHOLD` | Successes to close circuit (default: 2) |
| `CIRCUIT_BREAKER_TIMEOUT_SECONDS` | Circuit open duration (default: 60.0) |
| `JOB_DEFAULT_MAX_RETRIES` | Max job-level retries (default: 3) |
