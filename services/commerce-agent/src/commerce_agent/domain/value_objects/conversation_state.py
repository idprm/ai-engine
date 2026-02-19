"""ConversationState value object."""
from enum import Enum


class ConversationState(str, Enum):
    """State of a customer conversation in the chatbot."""

    GREETING = "greeting"           # Initial greeting/exchange
    BROWSING = "browsing"           # Customer browsing products
    ORDERING = "ordering"           # Building an order
    CHECKOUT = "checkout"           # Order confirmation/checkout
    PAYMENT = "payment"             # Payment processing
    SUPPORT = "support"             # Customer support mode
    COMPLETED = "completed"         # Conversation ended

    def can_transition_to(self, target: "ConversationState") -> bool:
        """Check if transition to target state is valid.

        Flexible transition rules allow returning to previous states
        to handle customer changing their mind.
        """
        transitions = {
            ConversationState.GREETING: {
                ConversationState.BROWSING,
                ConversationState.SUPPORT,
                ConversationState.COMPLETED,
            },
            ConversationState.BROWSING: {
                ConversationState.ORDERING,
                ConversationState.SUPPORT,
                ConversationState.COMPLETED,
            },
            ConversationState.ORDERING: {
                ConversationState.CHECKOUT,
                ConversationState.BROWSING,  # Can go back to browsing
                ConversationState.SUPPORT,
                ConversationState.COMPLETED,
            },
            ConversationState.CHECKOUT: {
                ConversationState.PAYMENT,
                ConversationState.ORDERING,  # Can modify order
                ConversationState.BROWSING,
                ConversationState.COMPLETED,
            },
            ConversationState.PAYMENT: {
                ConversationState.COMPLETED,
                ConversationState.SUPPORT,
                ConversationState.CHECKOUT,  # Payment failed, retry
            },
            ConversationState.SUPPORT: {
                ConversationState.GREETING,
                ConversationState.BROWSING,
                ConversationState.COMPLETED,
            },
            ConversationState.COMPLETED: set(),
        }
        return target in transitions.get(self, set())
