"""Chatbot orchestrator service - main entry point for chatbot processing."""
import logging
from typing import Any

from commerce_agent.application.dto import (
    WhatsAppMessageDTO,
    WhatsAppResponseDTO,
    ChatbotResponseDTO,
)
from commerce_agent.application.services.customer_service import CustomerService
from commerce_agent.application.services.conversation_service import ConversationService
from commerce_agent.application.services.order_service import OrderService
from commerce_agent.domain.repositories import TenantRepository
from commerce_agent.domain.value_objects import ConversationState
from commerce_agent.infrastructure.llm import CRMLangGraphRunner
from commerce_agent.infrastructure.llm.tools.tool_registry import register_tool_executor
from commerce_agent.infrastructure.llm.tools import (
    product_tools,
    order_tools,
    customer_tools,
    payment_tools,
)
from commerce_agent.infrastructure.messaging import WAResponsePublisher
from llm_worker.domain.repositories import LLMConfigRepository

logger = logging.getLogger(__name__)


class ChatbotOrchestrator:
    """Main orchestrator for CRM chatbot processing.

    Coordinates between:
    - WhatsApp message handling
    - Customer/Conversation/Order management
    - AI agent execution
    - Response publishing
    """

    def __init__(
        self,
        tenant_repository: TenantRepository,
        customer_service: CustomerService,
        conversation_service: ConversationService,
        order_service: OrderService,
        llm_config_repository: LLMConfigRepository,
        product_repository,
        order_repository,
        payment_repository,
        payment_client,
        llm_runner: CRMLangGraphRunner,
        response_publisher: WAResponsePublisher,
    ):
        self._tenant_repository = tenant_repository
        self._customer_service = customer_service
        self._conversation_service = conversation_service
        self._order_service = order_service
        self._llm_config_repository = llm_config_repository
        self._product_repository = product_repository
        self._order_repository = order_repository
        self._payment_repository = payment_repository
        self._payment_client = payment_client
        self._llm_runner = llm_runner
        self._response_publisher = response_publisher

        # Register tool executors
        self._register_tool_executors()

    def _register_tool_executors(self) -> None:
        """Register tool executor functions."""
        # Product tools
        async def exec_search_products(**kwargs):
            return await product_tools.execute_search_products(
                self._product_repository, kwargs["tenant_id"],
                kwargs["query"], kwargs.get("category"),
                kwargs.get("min_price"), kwargs.get("max_price"),
            )

        async def exec_get_product_details(**kwargs):
            return await product_tools.execute_get_product_details(
                self._product_repository, kwargs["product_id"],
            )

        async def exec_check_stock(**kwargs):
            return await product_tools.execute_check_stock(
                self._product_repository, kwargs["tenant_id"], kwargs["sku"],
            )

        # Order tools
        async def exec_create_order(**kwargs):
            return await order_tools.execute_create_order(
                self._order_repository, kwargs["tenant_id"], kwargs["customer_id"],
            )

        async def exec_add_to_order(**kwargs):
            return await order_tools.execute_add_to_order(
                self._order_repository, self._product_repository,
                kwargs["tenant_id"], kwargs["customer_id"],
                kwargs["product_id"], kwargs["quantity"], kwargs.get("variant_sku"),
            )

        async def exec_get_order_status(**kwargs):
            return await order_tools.execute_get_order_status(
                self._order_repository, kwargs["order_id"],
            )

        async def exec_get_customer_orders(**kwargs):
            return await order_tools.execute_get_customer_orders(
                self._order_repository, kwargs["customer_id"], kwargs.get("status"),
            )

        async def exec_confirm_order(**kwargs):
            return await order_tools.execute_confirm_order(
                self._order_repository, kwargs["order_id"], kwargs.get("shipping_address"),
            )

        async def exec_cancel_order(**kwargs):
            return await order_tools.execute_cancel_order(
                self._order_repository, kwargs["order_id"], kwargs.get("reason"),
            )

        # Customer tools
        async def exec_get_customer_profile(**kwargs):
            return await customer_tools.execute_get_customer_profile(
                self._customer_service._customer_repository, kwargs["customer_id"],
            )

        async def exec_update_customer_profile(**kwargs):
            return await customer_tools.execute_update_customer_profile(
                self._customer_service._customer_repository, kwargs["customer_id"],
                kwargs.get("name"), kwargs.get("email"), kwargs.get("address"),
            )

        # Payment tools
        async def exec_initiate_payment(**kwargs):
            return await payment_tools.execute_initiate_payment(
                self._payment_repository, self._order_repository,
                self._tenant_repository, self._payment_client,
                kwargs["order_id"], kwargs["payment_method"],
            )

        async def exec_check_payment_status(**kwargs):
            return await payment_tools.execute_check_payment_status(
                self._payment_repository, self._order_repository,
                self._payment_client, kwargs["payment_id"],
            )

        # Register all executors
        register_tool_executor("search_products", exec_search_products)
        register_tool_executor("get_product_details", exec_get_product_details)
        register_tool_executor("check_stock", exec_check_stock)
        register_tool_executor("create_order", exec_create_order)
        register_tool_executor("add_to_order", exec_add_to_order)
        register_tool_executor("get_order_status", exec_get_order_status)
        register_tool_executor("get_customer_orders", exec_get_customer_orders)
        register_tool_executor("confirm_order", exec_confirm_order)
        register_tool_executor("cancel_order", exec_cancel_order)
        register_tool_executor("get_customer_profile", exec_get_customer_profile)
        register_tool_executor("update_customer_profile", exec_update_customer_profile)
        register_tool_executor("initiate_payment", exec_initiate_payment)
        register_tool_executor("check_payment_status", exec_check_payment_status)

    async def process_message(self, message: WhatsAppMessageDTO) -> ChatbotResponseDTO:
        """Process an incoming WhatsApp message.

        This is the main entry point for message processing.

        Args:
            message: The incoming WhatsApp message.

        Returns:
            ChatbotResponseDTO with the response.
        """
        logger.info(f"Processing message from {message.chat_id}: {message.text[:50]}...")

        try:
            # 1. Get tenant by WA session
            tenant = await self._tenant_repository.get_by_wa_session(message.wa_session)

            if not tenant:
                logger.error(f"Tenant not found for session: {message.wa_session}")
                return ChatbotResponseDTO(
                    response_text="Sorry, this service is not configured.",
                    conversation_id="",
                    conversation_state="error",
                )

            if not tenant.is_active:
                logger.warning(f"Tenant inactive: {tenant.id}")
                return ChatbotResponseDTO(
                    response_text="Sorry, this service is currently unavailable.",
                    conversation_id="",
                    conversation_state="error",
                )

            # 2. Get or create customer
            customer = await self._customer_service.get_or_create_customer(
                tenant_id=str(tenant.id),
                phone_number=message.phone_number or "",
                wa_chat_id=message.chat_id,
            )

            # 3. Get or create conversation
            conversation = await self._conversation_service.get_or_create_conversation(
                tenant_id=str(tenant.id),
                customer_id=customer.id,
                wa_chat_id=message.chat_id,
            )

            # 4. Add user message to conversation
            await self._conversation_service.add_message(
                conversation_id=conversation.id,
                role="user",
                content=message.text,
                metadata={"message_id": message.message_id},
            )

            # 5. Get conversation history for context
            history = await self._conversation_service.get_message_history(conversation.id)

            # 6. Get customer context
            customer_context = await self._customer_service.get_customer_context(customer.id)

            # 7. Get LLM config
            llm_config = await self._llm_config_repository.get_by_name(tenant.llm_config_name)

            if not llm_config:
                logger.error(f"LLM config not found: {tenant.llm_config_name}")
                return ChatbotResponseDTO(
                    response_text="Sorry, there's a configuration error.",
                    conversation_id=conversation.id,
                    conversation_state=conversation.state.value,
                )

            # 8. Run AI agent
            response_text, tokens_used, metadata = await self._llm_runner.run(
                config=llm_config,
                system_prompt=tenant.agent_prompt,
                tenant_id=str(tenant.id),
                customer_id=customer.id,
                conversation_id=conversation.id,
                user_message=message.text,
                customer_context=customer_context,
                conversation_state=conversation.state.value,
                conversation_history=history,
            )

            # 9. Update conversation state if changed
            new_state = metadata.get("conversation_state")
            if new_state and new_state != conversation.state.value:
                await self._conversation_service.update_state(conversation.id, new_state)

            # 10. Add assistant response to conversation
            await self._conversation_service.add_message(
                conversation_id=conversation.id,
                role="assistant",
                content=response_text,
                metadata={"tokens": tokens_used},
            )

            # 11. Return response
            return ChatbotResponseDTO(
                response_text=response_text,
                conversation_id=conversation.id,
                conversation_state=new_state or conversation.state.value,
                intent=metadata.get("intent"),
                tokens_used=tokens_used,
                tools_used=metadata.get("tools_used", []),
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return ChatbotResponseDTO(
                response_text="Sorry, I encountered an error. Please try again.",
                conversation_id="",
                conversation_state="error",
                metadata={"error": str(e)},
            )

    async def handle_incoming_message(self, message_data: dict[str, Any]) -> None:
        """Handle incoming message from RabbitMQ.

        This is called by the consumer for each incoming message.

        Args:
            message_data: Message data from queue.
        """
        # Parse message
        message = WhatsAppMessageDTO(
            message_id=message_data.get("message_id", ""),
            wa_session=message_data.get("wa_session", ""),
            chat_id=message_data.get("chat_id", ""),
            phone_number=message_data.get("phone_number"),
            text=message_data.get("text", ""),
            metadata=message_data.get("metadata", {}),
        )

        # Process message
        response = await self.process_message(message)

        # Publish response if we have a valid conversation
        if response.conversation_id:
            await self._response_publisher.publish_split_message(
                wa_session=message.wa_session,
                chat_id=message.chat_id,
                text=response.response_text,
                metadata={
                    "conversation_id": response.conversation_id,
                    "intent": response.intent,
                    "tools_used": response.tools_used,
                },
            )

    async def start(self) -> None:
        """Start the orchestrator (initialize connections)."""
        await self._response_publisher.start()
        logger.info("Chatbot orchestrator started")

    async def stop(self) -> None:
        """Stop the orchestrator (cleanup connections)."""
        await self._response_publisher.stop()
        logger.info("Chatbot orchestrator stopped")
