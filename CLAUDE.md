# CLAUDE.md — AI Codebase Guide

This file provides context and implementation details for AI coding assistants (e.g., Claude Code) working in this repository. Read this before making changes.

---

## Project Overview

This is a **Python monorepo** implementing a scalable AI processing platform using **Domain-Driven Design (DDD)** architecture. The services include:

- **`services/gateway/`** — FastAPI service that accepts REST requests and enqueues jobs.
- **`services/ai_engine/`** — Worker service that consumes jobs, runs LangGraph pipelines, and writes results.
- **`services/waha_sender/`** — WhatsApp message sender service via WAHA API.
- **`services/crm_chatbot/`** — Multi-tenant CRM chatbot for WhatsApp customer interactions.

They share code through **`shared/`**, the shared kernel containing cross-cutting concerns.

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
│   └── cache/                   # Redis client
└── interface/
    ├── controllers/             # FastAPI route handlers
    ├── routes/api.py            # Route definitions
    └── schemas/                 # Pydantic request/response
```

### AI Engine Context

**Aggregate Roots:** `LLMConfig`, `PromptTemplate`, `AgentConfig`

```
services/ai_engine/src/ai_engine/
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
│   ├── llm/                     # LLMFactory, LangGraphRunner, AgentNodes, AgentState
│   ├── messaging/               # RabbitMQ consumer
│   └── cache/                   # Redis client
└── interface/
    └── handlers/                # Message handlers
```

### CRM Chatbot Context

**Aggregate Roots:** `Tenant`, `Customer`, `Product`, `Order`, `Conversation`, `Ticket`

```
services/crm_chatbot/src/crm_chatbot/
├── domain/
│   ├── entities/                # Tenant, Customer, Product, Order, Conversation, Payment
│   │                            # Label, ConversationLabel, QuickReply, Ticket, TicketBoard, TicketTemplate
│   ├── value_objects/           # TenantId, CustomerId, OrderStatus, Money, ConversationState
│   │                            # LabelId, QuickReplyId, TicketId, TicketStatus, TicketPriority
│   ├── events/                  # Domain events
│   └── repositories/            # Repository interfaces
├── application/
│   ├── services/                # ChatbotOrchestrator, ConversationService, OrderService
│   │                            # LabelService, QuickReplyService
│   ├── dto/                     # Data transfer objects
│   └── handlers/                # WAMessageHandler
├── infrastructure/
│   ├── persistence/             # SQLAlchemy repository implementations
│   ├── messaging/               # RabbitMQ consumer/publisher
│   ├── llm/                     # CRMLangGraphRunner, CRM agent tools (including label tools)
│   ├── payment/                 # MidtransClient, XenditClient
│   └── cache/                   # ConversationCache (Redis)
└── interface/
    ├── controllers/             # Tenant, Product, Order, Webhook, Label, QuickReply controllers
    └── routes/api.py
```

### Customer Service Tools (Cekat.ai-like Features)

The CRM Chatbot includes customer service management tools inspired by Cekat.ai:

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

The AI Engine supports a multi-agent system with specialized agents and intelligent routing:

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
- `ai-platform-ai-engine` — AI Engine worker image
- `ai-platform-waha-sender` — WhatsApp sender service image
- `ai-platform-crm-chatbot` — CRM Chatbot service image

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
| `OPENAI_API_KEY` | AI Engine | OpenAI API key |
| `ANTHROPIC_API_KEY` | AI Engine | Anthropic API key |
| `WAHA_SERVER_URL` | WAHA/CRM | WAHA server URL |
| `WAHA_API_KEY` | WAHA/CRM | WAHA API key |
| `MIDTRANS_SERVER_KEY` | CRM | Midtrans server key |
| `MIDTRANS_IS_PRODUCTION` | CRM | Midtrans production mode |
| `CONVERSATION_TTL` | CRM | Conversation cache TTL (seconds) |

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
docker-compose up --scale ai-engine=4
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
3. Add webhook handler in `WebhookController`
4. Update `Tenant.payment_provider` validation

---

## Notes & Gotchas

- **Dependency Direction**: Domain → nothing; Infrastructure → Domain; Application → Domain; Interface → Application
- **No business logic in Application layer** — use Domain services instead
- **Value Objects are immutable** — always use `frozen=True` in dataclass
- **Repository interfaces in Domain** — implementations in Infrastructure
- **Shared kernel is minimal** — only truly cross-cutting concerns (events, exceptions, config)
- **Redis is ephemeral** — job results may expire based on TTL
- **Pydantic v2** — use `model_config` instead of `Config` class

---

## File Locations Quick Reference

| What | Where |
|------|-------|
| CI/CD workflow | `.github/workflows/docker.yml` |
| Job entity | `services/gateway/src/gateway/domain/entities/job.py` |
| Job service | `services/gateway/src/gateway/application/services/job_service.py` |
| API routes | `services/gateway/src/gateway/interface/routes/api.py` |
| LLM config entity | `services/ai_engine/src/ai_engine/domain/entities/llm_config.py` |
| Agent config entity | `services/ai_engine/src/ai_engine/domain/entities/agent_config.py` |
| LLM factory | `services/ai_engine/src/ai_engine/infrastructure/llm/llm_factory.py` |
| LangGraph runner | `services/ai_engine/src/ai_engine/infrastructure/llm/langgraph_runner.py` |
| Agent state | `services/ai_engine/src/ai_engine/infrastructure/llm/agent_state.py` |
| Agent nodes | `services/ai_engine/src/ai_engine/infrastructure/llm/agent_nodes.py` |
| Processing service | `services/ai_engine/src/ai_engine/application/services/processing_service.py` |
| Processing DTOs | `services/ai_engine/src/ai_engine/application/dto/processing_dto.py` |
| Shared settings | `shared/config/settings.py` |
| Database init | `infra/docker/postgres/init.sql` |
| **CRM Chatbot** | |
| Tenant entity | `services/crm_chatbot/src/crm_chatbot/domain/entities/tenant.py` |
| Customer entity | `services/crm_chatbot/src/crm_chatbot/domain/entities/customer.py` |
| Order entity | `services/crm_chatbot/src/crm_chatbot/domain/entities/order.py` |
| Product entity | `services/crm_chatbot/src/crm_chatbot/domain/entities/product.py` |
| Conversation entity | `services/crm_chatbot/src/crm_chatbot/domain/entities/conversation.py` |
| Label entity | `services/crm_chatbot/src/crm_chatbot/domain/entities/label.py` |
| QuickReply entity | `services/crm_chatbot/src/crm_chatbot/domain/entities/quick_reply.py` |
| Ticket entity | `services/crm_chatbot/src/crm_chatbot/domain/entities/ticket.py` |
| Chatbot orchestrator | `services/crm_chatbot/src/crm_chatbot/application/services/chatbot_orchestrator.py` |
| Label service | `services/crm_chatbot/src/crm_chatbot/application/services/label_service.py` |
| QuickReply service | `services/crm_chatbot/src/crm_chatbot/application/services/quick_reply_service.py` |
| CRM LangGraph runner | `services/crm_chatbot/src/crm_chatbot/infrastructure/llm/crm_langgraph_runner.py` |
| CRM agent tools | `services/crm_chatbot/src/crm_chatbot/infrastructure/llm/tools/` |
| Label tools | `services/crm_chatbot/src/crm_chatbot/infrastructure/llm/tools/label_tools.py` |
| Midtrans client | `services/crm_chatbot/src/crm_chatbot/infrastructure/payment/midtrans_client.py` |
| WA message handler | `services/crm_chatbot/src/crm_chatbot/application/handlers/wa_message_handler.py` |
