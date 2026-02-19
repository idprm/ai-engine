# CLAUDE.md — AI Codebase Guide

This file provides context and implementation details for AI coding assistants (e.g., Claude Code) working in this repository. Read this before making changes.

---

## Project Overview

This is a **Python monorepo** implementing a scalable AI processing platform using **Domain-Driven Design (DDD)** architecture. The services include:

- **`services/gateway/`** — FastAPI service that handles ALL REST requests (including CRM routes) and enqueues jobs.
- **`services/llm-worker/`** — Worker service that consumes jobs, runs LangGraph pipelines, and writes results.
- **`services/messenger/`** — WhatsApp message sender service via WAHA API.
- **`services/commerce-agent/`** — **Background worker only** - processes CRM tasks from queue, NO HTTP endpoints.

They share code through **`shared/`**, the shared kernel containing cross-cutting concerns.

### Important: Gateway-CRM Architecture

> The Commerce Agent service has been refactored to a pure background worker. All HTTP routes (`/v1/crm/*`) are now served by the Gateway service. The Gateway imports CRM's domain, application, and infrastructure layers directly and publishes tasks to the `crm_tasks` queue for the CRM Worker to process.

---

## DDD Architecture

This codebase follows classic 4-layer DDD with isolated bounded contexts:

```
┌─────────────────────────────────────────────────────────────┐
│                     INTERFACE LAYER                          │
│  HTTP Controllers, Message Handlers, Pydantic Schemas       │
├─────────────────────────────────────────────────────────────┤
│                    APPLICATION LAYER                         │
│  Services, DTOs, Use Case Orchestration                      │
├─────────────────────────────────────────────────────────────┤
│                      DOMAIN LAYER                            │
│  Entities, Value Objects, Domain Events, Repository IFaces  │
├─────────────────────────────────────────────────────────────┤
│                   INFRASTRUCTURE LAYER                       │
│  Repository Impl, External Adapters, DB, Messaging, Cache   │
└─────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Domain Layer** contains NO infrastructure dependencies
2. **Repository interfaces** live in Domain; implementations in Infrastructure
3. **Value Objects** are immutable and self-validating
4. **Entities** contain business logic and emit domain events
5. **Application services** orchestrate use cases without business logic

---

## Bounded Contexts

### Gateway Context

**Aggregate Root:** `Job`

The Gateway service handles ALL HTTP endpoints, including CRM routes migrated from the Commerce Agent service.

```
services/gateway/src/gateway/
├── domain/
│   ├── entities/job.py          # Job aggregate with status transitions
│   ├── value_objects/           # JobId, JobStatus, Prompt
│   ├── events/job_events.py     # JobCreated, JobCompleted, JobFailed
│   └── repositories/            # JobRepository (abstract)
├── application/
│   ├── services/job_service.py  # Orchestrates job submission/status
│   └── dto/job_dto.py           # Data transfer objects
├── infrastructure/
│   ├── persistence/             # SQLAlchemy repository impl
│   ├── messaging/               # RabbitMQ publisher
│   │   ├── rabbitmq_publisher.py
│   │   └── delayed_publisher.py # Delayed retry scheduling
│   └── cache/                   # Redis client
├── crm/                         # CRM context module (NEW)
│   ├── __init__.py
│   ├── dependencies.py          # DI factories for CRM repos/services
│   └── publishers.py            # CRMTaskPublisher for webhook queue
└── interface/
    ├── controllers/
    │   ├── job_controller.py    # Job endpoints
    │   ├── wa_controller.py     # WhatsApp endpoints
    │   └── crm/                 # Migrated CRM controllers (NEW)
    │       ├── tenant_controller.py
    │       ├── product_controller.py
    │       ├── order_controller.py
    │       ├── webhook_controller.py
    │       ├── label_controller.py
    │       └── quick_reply_controller.py
    ├── routes/
    │   ├── api.py               # Main route definitions
    │   └── crm_routes.py        # CRM route aggregator (NEW)
    └── schemas/                 # Pydantic request/response
```

### LLM Worker Context

**Aggregate Roots:** `LLMConfig`, `PromptTemplate`, `AgentConfig`

```
services/llm-worker/src/llm_worker/
├── domain/
│   ├── entities/                # LLMConfig, PromptTemplate, AgentConfig
│   ├── value_objects/           # Provider, ModelName, Temperature
│   ├── services/llm_selector.py # Domain service for LLM selection
│   └── repositories/            # Repository interfaces
├── application/
│   ├── services/processing_service.py
│   └── dto/processing_dto.py
├── infrastructure/
│   ├── persistence/             # Repository implementations
│   ├── llm/                     # LLM infrastructure
│   │   ├── llm_factory.py       # Creates LangChain models
│   │   ├── langgraph_runner.py  # Executes AI pipelines
│   │   ├── agent_nodes.py       # Multi-agent node implementations
│   │   ├── agent_state.py       # AgentState TypedDict
│   │   ├── timeout.py           # Timeout wrapper
│   │   ├── response_validator.py # Response quality validation
│   │   ├── backoff.py           # Exponential backoff retry
│   │   └── circuit_breaker.py   # Circuit breaker pattern
│   ├── messaging/               # RabbitMQ consumer
│   └── cache/                   # Redis client
└── interface/
    └── handlers/                # Message handlers
```

### Commerce Agent Context (Background Worker)

**Aggregate Roots:** `Tenant`, `Customer`, `Product`, `Order`, `Conversation`, `Ticket`

> **Note:** The Commerce Agent is now a **background worker only**. All HTTP controllers and routes have been moved to the Gateway service. This service consumes messages from the `crm_tasks` queue and processes them using LLM agents.

```
services/commerce-agent/src/commerce_agent/
├── worker.py                    # Worker entry point (NEW - main entry)
├── main.py                      # DEPRECATED - use worker.py for production
├── domain/
│   ├── entities/                # Tenant, Customer, Product, Order, Conversation, Payment
│   │                            # Label, ConversationLabel, QuickReply, Ticket, TicketBoard, TicketTemplate
│   ├── value_objects/           # TenantId, CustomerId, OrderStatus, Money, ConversationState
│   │                            # LabelId, QuickReplyId, TicketId, TicketStatus, TicketPriority
│   ├── events/                  # Domain events
│   └── repositories/            # Repository interfaces (implemented in infrastructure/)
├── application/
│   ├── services/                # ChatbotOrchestrator, ConversationService, OrderService
│   │                            # LabelService, QuickReplyService (imported by Gateway)
│   ├── dto/                     # Data transfer objects (imported by Gateway)
│   └── handlers/                # WAMessageHandler
├── infrastructure/
│   ├── persistence/             # SQLAlchemy repository implementations (imported by Gateway)
│   ├── messaging/               # RabbitMQ consumer/publisher
│   ├── llm/                     # CRMLangGraphRunner, CRM agent tools
│   ├── payment/                 # MidtransClient, XenditClient (imported by Gateway)
│   └── cache/                   # ConversationCache (Redis)
└── interface/                   # DEPRECATED - controllers moved to Gateway
```

### Customer Service Tools (Cekat.ai-like Features)

The Commerce Agent includes customer service management tools inspired by Cekat.ai:

### Gateway-CRM Integration

The Gateway service imports from CRM's layers directly:

```python
# gateway/crm/dependencies.py
from commerce_agent.infrastructure.persistence import (
    TenantRepositoryImpl,
    CustomerRepositoryImpl,
    # ... other repositories
)
from commerce_agent.application.services import (
    CustomerService,
    OrderService,
    # ... other services
)

def get_tenant_repository() -> TenantRepositoryImpl:
    return TenantRepositoryImpl()

def get_order_service() -> OrderService:
    return OrderService(
        order_repository=get_order_repository(),
        product_repository=get_product_repository(),
        payment_repository=get_payment_repository(),
        payment_client=get_payment_client(),
    )
```

The webhook controller publishes to the CRM queue:

```python
# gateway/interface/controllers/crm/webhook_controller.py
@router.post("/whatsapp/{tenant_id}")
async def whatsapp_webhook(tenant_id: str, request: Request):
    payload = await request.json()
    payload["tenant_id"] = tenant_id

    # Publish to CRM worker queue
    publisher = get_crm_publisher()
    await publisher.publish_webhook_task(payload)

    return {"status": "queued", "tenant_id": tenant_id}
```

#### Labels/Tagging System
- **Label entity** — Categorize conversations with color-coded labels
- **ConversationLabel** — Many-to-many association between conversations and labels
- **AI Integration** — `label_conversation`, `get_available_labels`, `remove_label` tools
- **Use cases** — Follow-up tracking, topic categorization, priority marking

#### Quick Reply System
- **QuickReply entity** — Template responses triggered by shortcuts (e.g., `/hello`)
- **Category organization** — Group quick replies by category
- **Shortcut expansion** — Expand shortcuts in messages automatically

#### Ticket System
- **Ticket aggregate** — Support ticket management with status workflow
- **TicketStatus** — open → in_progress → pending → resolved → closed
- **TicketPriority** — none, low, medium, high, urgent (with SLA implications)
- **TicketBoard** — Organize tickets into boards/queues
- **TicketTemplate** — Predefined templates for quick ticket creation

```python
# Example: Creating and labeling a conversation
label = Label.create(
    tenant_id=tenant_id,
    name="Follow Up",
    color="#e74c3c",
    description="Needs follow-up"
)

conversation_label = ConversationLabel.create(
    conversation_id=conversation_id,
    label_id=label.id,
    tenant_id=tenant_id,
    applied_by="ai"
)
```

---

## Key Implementation Patterns

### Value Object Pattern

```python
# domain/value_objects/temperature.py
@dataclass(frozen=True)
class Temperature:
    value: float

    def __post_init__(self):
        if not 0.0 <= self.value <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
```

### Entity with Domain Events

```python
# domain/entities/job.py
@dataclass
class Job:
    _events: list[DomainEvent] = field(default_factory=list)

    def complete(self, result: str) -> None:
        if not self._status.can_transition_to(JobStatus.COMPLETED):
            raise ValueError(f"Invalid transition")
        self._status = JobStatus.COMPLETED
        self._result = result
        self._add_event(JobCompleted(self._id, result))

    def pull_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events
```

### Repository Interface (Domain)

```python
# domain/repositories/job_repository.py
class JobRepository(ABC):
    @abstractmethod
    async def get_by_id(self, job_id: JobId) -> Job | None:
        pass

    @abstractmethod
    async def save(self, job: Job) -> Job:
        pass
```

### Repository Implementation (Infrastructure)

```python
# infrastructure/persistence/job_repository_impl.py
class JobRepositoryImpl(JobRepository):
    async def get_by_id(self, job_id: JobId) -> Job | None:
        async with get_db_session() as session:
            model = await session.get(JobModel, str(job_id))
            return self._to_entity(model) if model else None
```

### Application Service

```python
# application/services/job_service.py
class JobService:
    def __init__(
        self,
        job_repository: JobRepository,
        message_publisher: MessagePublisher,
        cache_client: CacheClient,
    ):
        self._job_repository = job_repository
        self._message_publisher = message_publisher
        self._cache_client = cache_client

    async def submit_job(self, dto: JobDTO) -> JobStatusDTO:
        # Create domain objects
        prompt = Prompt(content=dto.prompt)
        job = Job.create(prompt=prompt, config_name=dto.config_name, ...)

        # Persist
        await self._cache_client.set(str(job.id), json.dumps(job.to_dict()))

        # Publish event
        await self._message_publisher.publish_task(...)

        return JobStatusDTO(job_id=str(job.id), status=job.status.value)
```

---

## LLM Integration

### LLMFactory

Creates LangChain model instances from domain configuration:

```python
# infrastructure/llm/llm_factory.py
class LLMFactory:
    @staticmethod
    def create(config: LLMConfig) -> BaseChatModel:
        api_key = os.getenv(config.api_key_env)

        if config.provider.is_openai:
            return ChatOpenAI(
                model=str(config.model_name),
                api_key=api_key,
                temperature=float(config.temperature),
            )
        elif config.provider.is_anthropic:
            return ChatAnthropic(...)
```

### LangGraphRunner

Executes AI pipelines with LangGraph:

```python
# infrastructure/llm/langgraph_runner.py
class LangGraphRunner:
    async def run(self, config: LLMConfig, system_prompt: str, user_prompt: str) -> tuple[str, int]:
        llm = LLMFactory.create(config)

        async def agent_node(state: AgentState) -> dict:
            messages = [SystemMessage(content=system_prompt)] + state["messages"]
            response = await llm.ainvoke(messages)
            return {"messages": [response]}

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent_node)
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)

        graph = workflow.compile()
        result = await graph.ainvoke({"messages": [HumanMessage(content=user_prompt)]})

        return result["messages"][-1].content, tokens_used
```

---

## Multi-Agent Architecture

The LLM Worker supports a multi-agent system with specialized agents and intelligent routing:

### Agent Types

| Type | Purpose | Template Name |
|------|---------|---------------|
| `MAIN` | Primary response handler | `main-agent` |
| `FALLBACK` | Error recovery and moderation violations | `fallback-agent` |
| `FOLLOWUP` | Conversation continuity | `followup-agent` |
| `MODERATION` | Content policy validation | `moderation-agent` |

### AgentState

Extended state for multi-agent workflows:

```python
# infrastructure/llm/agent_state.py
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    agent_type: Literal["main", "fallback", "followup", "moderation"]
    context: dict[str, Any]
    needs_moderation: bool
    moderation_result: dict[str, Any] | None
    retry_count: int
    final_response: str | None
    error: str | None
```

### Agent Workflow

```
START → moderation_node → router_node
         ↓
    [Conditional routing]
         ↓
    ┌────┴────┬────────────┐
    ↓         ↓            ↓
main_agent  followup  fallback_agent
    ↓         ↓            ↓
 [success?]   END          END
    ↓
 fallback (on failure)
    ↓
   END
```

### Multi-Agent Processing

```python
# application/services/processing_service.py
class ProcessingService:
    async def process_multi_agent(
        self,
        request: ProcessingRequest,
        context: dict[str, Any] | None = None,
        needs_moderation: bool = True,
    ) -> ProcessingResult:
        # Load agent configurations
        agent_configs = await self._load_agent_configs(request.config_name)

        # Execute multi-agent pipeline
        result, tokens, agent_type = await self._llm_runner.run_multi_agent(
            config=config,
            agent_configs=agent_configs,
            user_prompt=request.prompt,
            context=context,
            needs_moderation=needs_moderation,
        )
        return ProcessingResult(...)
```

### Agent Nodes

Individual agent implementations in `infrastructure/llm/agent_nodes.py`:

- `moderation_node()` — Content policy checking
- `router_node()` — Intelligent agent routing
- `main_agent_node()` — Primary processing
- `fallback_agent_node()` — Error recovery
- `followup_agent_node()` — Conversation continuation

---

## LLM Worker Resilience

The LLM Worker implements comprehensive resilience patterns to handle LLM failures gracefully:

### Resilience Architecture

```
Message Handler ──> Processing Service ──> LangGraph Runner
        │                   │                    │
        │                   │                    │
        ▼                   ▼                    ▼
  Circuit Check      Retry Coordination    Backoff Retry
        │                   │                    │
        │                   │                    ▼
        │                   │              Agent Nodes
        │                   │                    │
        │                   │              ┌─────┴─────┐
        │                   │              ▼           ▼
        │                   │         Timeout     Circuit
        │                   │         Wrapper    Breaker
        │                   │              │           │
        │                   │              └─────┬─────┘
        │                   │                    ▼
        │                   │               LLM Call
        │                   │                    │
        │                   │              Response
        │                   │              Validator
        │                   │                    │
        ▼                   ▼                    ▼
   Schedule Retry <───── Result ────────────> Success/Retry/Fail
```

### Resilience Utilities

Located in `infrastructure/llm/`:

| File | Purpose |
|------|---------|
| `timeout.py` | `with_timeout()` wrapper using `asyncio.wait_for()` |
| `response_validator.py` | `validate_response()` for quality checks |
| `backoff.py` | `retry_with_backoff()` with exponential delay and jitter |
| `circuit_breaker.py` | `CircuitBreaker` pattern with CLOSED/OPEN/HALF_OPEN states |

### Timeout Implementation

```python
# infrastructure/llm/timeout.py
async def with_timeout(coro, timeout_seconds, operation="LLM call"):
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise LLMTimeoutError(timeout_seconds, operation)
```

### Response Validation

```python
# infrastructure/llm/response_validator.py
class ResponseQuality(Enum):
    VALID = "valid"
    EMPTY = "empty"
    WHITESPACE_ONLY = "whitespace_only"
    TOO_SHORT = "too_short"
    ERROR_INDICATOR = "error_indicator"

def validate_response(response: str | None, min_length: int = 10) -> ValidationResult:
    # Checks for None, empty, whitespace, too short, error patterns
```

### Exponential Backoff

```python
# infrastructure/llm/backoff.py
@dataclass(frozen=True)
class BackoffConfig:
    initial_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter_factor: float = 0.1

async def retry_with_backoff(
    coro_factory,  # Callable that returns awaitable
    max_retries: int = 3,
    backoff_config: BackoffConfig | None = None,
    retryable_exceptions: tuple | None = None,
) -> T:
    # Retries with exponential backoff + jitter
```

### Circuit Breaker

```python
# infrastructure/llm/circuit_breaker.py
class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    async def call(self, coro: Awaitable[T]) -> T:
        # Executes through circuit breaker

class CircuitBreakerRegistry:
    # Global registry for circuit breakers by LLM config name
    def get_or_create(self, name: str, config: CircuitBreakerConfig | None = None) -> CircuitBreaker
```

### Job-Level Retry

Jobs can be retried at the message queue level:

```python
# domain/entities/job.py
class Job:
    _max_retries: int = 3
    _retry_count: int = 0
    _next_retry_at: datetime | None = None

    @property
    def can_retry(self) -> bool:
        return self._retry_count < self._max_retries

    def mark_for_retry(self, delay_seconds: float) -> None:
        self._status = JobStatus.RETRYING
        self._retry_count += 1
        self._next_retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)

# domain/value_objects/job_status.py
class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"  # NEW: Intermediate state for retry scheduling
```

### Delayed Task Publisher

Uses RabbitMQ dead-letter exchange for delayed retries:

```python
# gateway/infrastructure/messaging/delayed_publisher.py
class DelayedTaskPublisher:
    async def schedule_retry(self, job_id: str, message: dict, delay_seconds: float):
        # Creates delay queue with TTL that dead-letters to main task queue
        delay_queue_name = f"{self._task_queue}.delay.{delay_ms}ms"
        await self._channel.declare_queue(
            delay_queue_name,
            durable=True,
            arguments={
                "x-message-ttl": delay_ms,
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": self._task_queue,
            },
        )
```

### Retry Flow

```
QUEUED → PROCESSING → RETRYING → QUEUED (retry) → PROCESSING → ...
                        │
                        └──(max retries exceeded)──> FAILED
```

---

## Database Configuration

PostgreSQL with asyncpg driver:

```python
# infrastructure/persistence/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(
    settings.database_url,  # postgresql+asyncpg://...
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@asynccontextmanager
async def get_db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

## CI/CD Pipeline

GitHub Actions workflow at `.github/workflows/docker.yml`:

### Triggers
- Push to `main`/`master` branch
- Version tags (`v*`)
- Pull requests to `main`/`master`

### Services Built
- `ai-platform-gateway` — Gateway service image
- `ai-platform-llm-worker` — LLM Worker worker image
- `ai-platform-messenger` — WhatsApp sender service image
- `ai-platform-commerce-agent` — Commerce Agent service image

### Image Tagging Strategy
- `latest` — Default branch builds
- `sha-<commit>` — Commit SHA prefix
- `v1.0.0`, `v1.0` — Semantic version tags
- `pr-<number>` — Pull request builds (not pushed)

### Required GitHub Secrets
- `DOCKER_USERNAME` — Docker Hub username
- `DOCKER_PASSWORD` — Docker Hub access token (not password)

---

## Environment Variables

| Variable | Used By | Description |
|----------|---------|-------------|
| `DATABASE_URL` | Both | PostgreSQL connection (asyncpg driver) |
| `REDIS_URL` | Both | Redis connection string |
| `RABBITMQ_URL` | Both | RabbitMQ AMQP connection |
| `RABBITMQ_TASK_QUEUE` | Both | Queue name (default: `ai_tasks`) |
| `RABBITMQ_CRM_QUEUE` | CRM | CRM queue name (default: `crm_tasks`) |
| `RABBITMQ_WA_QUEUE` | WAHA/CRM | WhatsApp message queue (default: `wa_messages`) |
| `OPENAI_API_KEY` | LLM Worker | OpenAI API key |
| `ANTHROPIC_API_KEY` | LLM Worker | Anthropic API key |
| `WAHA_SERVER_URL` | WAHA/CRM | WAHA server URL |
| `WAHA_API_KEY` | WAHA/CRM | WAHA API key |
| `MIDTRANS_SERVER_KEY` | CRM | Midtrans server key |
| `MIDTRANS_IS_PRODUCTION` | CRM | Midtrans production mode |
| `CONVERSATION_TTL` | CRM | Conversation cache TTL (seconds) |
| **LLM Resilience** | | |
| `LLM_DEFAULT_TIMEOUT_SECONDS` | LLM Worker | Default timeout for LLM calls (default: 120) |
| `LLM_MAX_RETRIES` | LLM Worker | Max retry attempts per call (default: 3) |
| `LLM_RETRY_INITIAL_DELAY` | LLM Worker | Initial backoff delay in seconds (default: 1.0) |
| `LLM_RETRY_MAX_DELAY` | LLM Worker | Maximum backoff delay cap (default: 60.0) |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | LLM Worker | Failures before circuit opens (default: 5) |
| `CIRCUIT_BREAKER_SUCCESS_THRESHOLD` | LLM Worker | Successes to close circuit (default: 2) |
| `CIRCUIT_BREAKER_TIMEOUT_SECONDS` | LLM Worker | Circuit open duration (default: 60.0) |
| `JOB_DEFAULT_MAX_RETRIES` | Gateway | Max job-level retries (default: 3) |

API keys are referenced by name in `llm_configs.api_key_env` and resolved at runtime.

---

## Common Tasks

### Add a new LLM provider

1. Add provider to `ProviderType` enum in `domain/value_objects/provider.py`
2. Extend `LLMFactory.create()` in `infrastructure/llm/llm_factory.py`
3. Add a row to `llm_configs` table in PostgreSQL

### Add a new prompt template

Insert a row into `prompt_templates` table. No code change needed.

### Add a new agent node

1. Define agent type in `AgentType` enum (`domain/entities/agent_config.py`)
2. Create node function in `infrastructure/llm/agent_nodes.py`
3. Add prompt template to `prompt_templates` table
4. Update `LangGraphRunner._build_multi_agent_workflow()` to include the node
5. Add routing logic in `_route_after_router()` or `_route_after_main()`

### Add a new agent node

Extend `AgentState` and modify `LangGraphRunner.run()` to add nodes/edges.

### Scale workers

```bash
docker-compose up --scale llm-worker=4
```

### Add a new CRM agent tool

1. Create tool function in `infrastructure/llm/tools/` (e.g., `new_tools.py`)
2. Use `@tool` decorator from `langchain_core.tools`
3. Add executor function (receives repositories as parameters)
4. Register executor in `ChatbotOrchestrator._register_tool_executors()`
5. Add tool to `get_tools_for_conversation_state()` in `tool_registry.py`

### Add a new payment provider

1. Create client in `infrastructure/payment/` (e.g., `new_payment_client.py`)
2. Implement `create_transaction()` and `check_transaction_status()` methods
3. Add webhook handler in Gateway's `WebhookController`
4. Update `Tenant.payment_provider` validation

### Add a new CRM HTTP endpoint

1. Create controller in `services/gateway/src/gateway/interface/controllers/crm/`
2. Import domain/application from `commerce_agent.*`
3. Use dependency injection from `gateway.crm.dependencies`
4. Register router in `services/gateway/src/gateway/interface/routes/crm_routes.py`

### Run CRM worker locally

```bash
# The CRM service is a background worker (no HTTP)
python -m commerce_agent.worker
```

### Troubleshoot LLM worker resilience issues

1. **Check circuit breaker state** — If jobs are failing with `CircuitOpenError`, the circuit breaker is protecting against cascading failures
2. **Check timeout settings** — Increase `LLM_DEFAULT_TIMEOUT_SECONDS` if jobs are timing out
3. **Check retry logs** — Look for "Scheduling retry" messages in logs
4. **Check job retry count** — Query `jobs` table for `retry_count` and `next_retry_at`
5. **Reset circuit breaker** — Restart the LLM worker service to reset circuit breaker state

```sql
-- Check jobs with retry status
SELECT id, status, retry_count, next_retry_at, error
FROM jobs
WHERE status IN ('RETRYING', 'FAILED')
ORDER BY created_at DESC;

-- Check jobs scheduled for retry
SELECT id, retry_count, next_retry_at
FROM jobs
WHERE next_retry_at IS NOT NULL
ORDER BY next_retry_at;
```

---

## Notes & Gotchas

- **Dependency Direction**: Domain → nothing; Infrastructure → Domain; Application → Domain; Interface → Application
- **No business logic in Application layer** — use Domain services instead
- **Value Objects are immutable** — always use `frozen=True` in dataclass
- **Repository interfaces in Domain** — implementations in Infrastructure
- **Shared kernel is minimal** — only truly cross-cutting concerns (events, exceptions, config)
- **Redis is ephemeral** — job results may expire based on TTL
- **Pydantic v2** — use `model_config` instead of `Config` class
- **Circuit breaker is in-memory** — state is lost on worker restart (by design)
- **Retry delays use RabbitMQ DLX** — DelayedTaskPublisher creates delay queues with TTL
- **Job RETRYING status** — Jobs in RETRYING state should transition to QUEUED or FAILED

---

## File Locations Quick Reference

| What | Where |
|------|-------|
| CI/CD workflow | `.github/workflows/docker.yml` |
| **Gateway Service** | |
| Job entity | `services/gateway/src/gateway/domain/entities/job.py` |
| Job status | `services/gateway/src/gateway/domain/value_objects/job_status.py` |
| Job service | `services/gateway/src/gateway/application/services/job_service.py` |
| API routes | `services/gateway/src/gateway/interface/routes/api.py` |
| CRM routes | `services/gateway/src/gateway/interface/routes/crm_routes.py` |
| CRM dependencies | `services/gateway/src/gateway/crm/dependencies.py` |
| CRM publisher | `services/gateway/src/gateway/crm/publishers.py` |
| CRM controllers | `services/gateway/src/gateway/interface/controllers/crm/` |
| Delayed task publisher | `services/gateway/src/gateway/infrastructure/messaging/delayed_publisher.py` |
| **LLM Worker Service** | |
| LLM config entity | `services/llm-worker/src/llm_worker/domain/entities/llm_config.py` |
| Agent config entity | `services/llm-worker/src/llm_worker/domain/entities/agent_config.py` |
| LLM factory | `services/llm-worker/src/llm_worker/infrastructure/llm/llm_factory.py` |
| LangGraph runner | `services/llm-worker/src/llm_worker/infrastructure/llm/langgraph_runner.py` |
| Agent state | `services/llm-worker/src/llm_worker/infrastructure/llm/agent_state.py` |
| Agent nodes | `services/llm-worker/src/llm_worker/infrastructure/llm/agent_nodes.py` |
| Processing service | `services/llm-worker/src/llm_worker/application/services/processing_service.py` |
| Processing DTOs | `services/llm-worker/src/llm_worker/application/dto/processing_dto.py` |
| Message handler | `services/llm-worker/src/llm_worker/interface/handlers/message_handler.py` |
| **Resilience Utilities** | |
| Timeout wrapper | `services/llm-worker/src/llm_worker/infrastructure/llm/timeout.py` |
| Response validator | `services/llm-worker/src/llm_worker/infrastructure/llm/response_validator.py` |
| Backoff retry | `services/llm-worker/src/llm_worker/infrastructure/llm/backoff.py` |
| Circuit breaker | `services/llm-worker/src/llm_worker/infrastructure/llm/circuit_breaker.py` |
| **Commerce Agent Worker** | |
| Worker entry point | `services/commerce-agent/src/commerce_agent/worker.py` |
| Tenant entity | `services/commerce-agent/src/commerce_agent/domain/entities/tenant.py` |
| Customer entity | `services/commerce-agent/src/commerce_agent/domain/entities/customer.py` |
| Order entity | `services/commerce-agent/src/commerce_agent/domain/entities/order.py` |
| Product entity | `services/commerce-agent/src/commerce_agent/domain/entities/product.py` |
| Conversation entity | `services/commerce-agent/src/commerce_agent/domain/entities/conversation.py` |
| Label entity | `services/commerce-agent/src/commerce_agent/domain/entities/label.py` |
| QuickReply entity | `services/commerce-agent/src/commerce_agent/domain/entities/quick_reply.py` |
| Ticket entity | `services/commerce-agent/src/commerce_agent/domain/entities/ticket.py` |
| Chatbot orchestrator | `services/commerce-agent/src/commerce_agent/application/services/chatbot_orchestrator.py` |
| Label service | `services/commerce-agent/src/commerce_agent/application/services/label_service.py` |
| QuickReply service | `services/commerce-agent/src/commerce_agent/application/services/quick_reply_service.py` |
| CRM LangGraph runner | `services/commerce-agent/src/commerce_agent/infrastructure/llm/crm_langgraph_runner.py` |
| CRM agent tools | `services/commerce-agent/src/commerce_agent/infrastructure/llm/tools/` |
| Label tools | `services/commerce-agent/src/commerce_agent/infrastructure/llm/tools/label_tools.py` |
| Midtrans client | `services/commerce-agent/src/commerce_agent/infrastructure/payment/midtrans_client.py` |
| WA message handler | `services/commerce-agent/src/commerce_agent/application/handlers/wa_message_handler.py` |
| **Shared** | |
| Shared settings | `shared/config/settings.py` |
| Database init | `infra/docker/postgres/init.sql` |
| Resilience migration | `infra/docker/postgres/migrations/002_add_resilience_columns.sql` |
