"""
WebSocket event models and validation.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator


class EventType(str, Enum):
    """Inbound event types."""
    JOIN = "join"
    START = "start"
    PLAY = "play"
    PASS = "pass"
    GIFT_SELECT = "gift_select"
    DISCARD_SELECT = "discard_select"
    EXCHANGE_RETURN = "exchange_return"
    EXCHANGE_RETURN_VICE = "exchange_return_vice"
    REQUEST_STATE = "request_state"
    CHAT = "chat"


class OutboundEventType(str, Enum):
    """Outbound event types."""
    JOIN_SUCCESS = "join_success"
    STATE_FULL = "state_full"
    STATE_PATCH = "state_patch"
    EFFECT = "effect"
    ERROR = "error"
    CHAT = "chat"


class ErrorCode(str, Enum):
    """Error codes for client events."""
    INVALID_EVENT = "INVALID_EVENT"
    ROOM_FULL = "ROOM_FULL"
    NOT_YOUR_TURN = "NOT_YOUR_TURN"
    OWNERSHIP = "OWNERSHIP"
    PATTERN_MISMATCH = "PATTERN_MISMATCH"
    RANK_TOO_LOW = "RANK_TOO_LOW"
    EFFECT_PENDING = "EFFECT_PENDING"
    INVALID_GIFT_DISTRIBUTION = "INVALID_GIFT_DISTRIBUTION"
    INVALID_DISCARD_SELECTION = "INVALID_DISCARD_SELECTION"
    ALREADY_PASSED = "ALREADY_PASSED"
    ACTION_NOT_ALLOWED = "ACTION_NOT_ALLOWED"
    INTERNAL = "INTERNAL"


# Inbound event models
class BaseEvent(BaseModel):
    """Base event model."""
    type: EventType
    

class JoinEvent(BaseEvent):
    """Join room event."""
    type: EventType = EventType.JOIN
    room_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=30)
    is_bot: bool = False


class StartEvent(BaseEvent):
    """Start game event."""
    type: EventType = EventType.START
    seed: Optional[int] = None


class PlayEvent(BaseEvent):
    """Play cards event."""
    type: EventType = EventType.PLAY
    cards: List[str] = Field(..., min_items=1, max_items=4)


class PassEvent(BaseEvent):
    """Pass turn event."""
    type: EventType = EventType.PASS


class GiftAssignment(BaseModel):
    """Gift assignment for gift_select event."""
    to: str = Field(..., min_length=1)
    cards: List[str] = Field(..., min_items=1)


class GiftSelectEvent(BaseEvent):
    """Gift selection event."""
    type: EventType = EventType.GIFT_SELECT
    assignments: List[GiftAssignment] = Field(..., min_items=1)


class DiscardSelectEvent(BaseEvent):
    """Discard selection event."""
    type: EventType = EventType.DISCARD_SELECT
    cards: List[str] = Field(..., min_items=0, max_items=10)


class ExchangeReturnEvent(BaseEvent):
    """Exchange return event (President)."""
    type: EventType = EventType.EXCHANGE_RETURN
    cards: List[str] = Field(..., min_items=1, max_items=2)


class ExchangeReturnViceEvent(BaseEvent):
    """Exchange return event (Vice President)."""
    type: EventType = EventType.EXCHANGE_RETURN_VICE
    cards: List[str] = Field(..., min_items=1, max_items=1)


class RequestStateEvent(BaseEvent):
    """Request full state event."""
    type: EventType = EventType.REQUEST_STATE


class ChatEvent(BaseEvent):
    """Chat message event."""
    type: EventType = EventType.CHAT
    text: str = Field(..., min_length=1, max_length=200)


# Union type for all inbound events
InboundEvent = Union[
    JoinEvent,
    StartEvent,
    PlayEvent,
    PassEvent,
    GiftSelectEvent,
    DiscardSelectEvent,
    ExchangeReturnEvent,
    ExchangeReturnViceEvent,
    RequestStateEvent,
    ChatEvent
]


# Outbound event models
class JoinSuccessEvent(BaseModel):
    """Join success confirmation event."""
    type: OutboundEventType = OutboundEventType.JOIN_SUCCESS
    player_id: str
    timestamp: float


class StateFullEvent(BaseModel):
    """Full state event."""
    type: OutboundEventType = OutboundEventType.STATE_FULL
    state: Dict[str, Any]
    timestamp: float


class PatchOperation(BaseModel):
    """JSON Patch operation."""
    op: str = Field(..., pattern="^(replace|add|remove)$")
    path: str
    value: Optional[Any] = None


class StatePatchEvent(BaseModel):
    """State patch event."""
    type: OutboundEventType = OutboundEventType.STATE_PATCH
    version: int
    ops: List[PatchOperation]
    timestamp: float


class EffectEvent(BaseModel):
    """Effect notification event."""
    type: OutboundEventType = OutboundEventType.EFFECT
    effect_type: str
    data: Dict[str, Any]
    timestamp: float


class ErrorEvent(BaseModel):
    """Error event."""
    type: OutboundEventType = OutboundEventType.ERROR
    code: ErrorCode
    message: str
    timestamp: float


class ChatMessageEvent(BaseModel):
    """Chat message event."""
    type: OutboundEventType = OutboundEventType.CHAT
    player_id: str
    player_name: str
    text: str
    timestamp: float


# Union type for all outbound events
OutboundEvent = Union[
    JoinSuccessEvent,
    StateFullEvent,
    StatePatchEvent,
    EffectEvent,
    ErrorEvent,
    ChatMessageEvent
]


def parse_inbound_event(data: Dict[str, Any]) -> InboundEvent:
    """
    Parse raw event data into appropriate event model.
    
    Args:
        data: Raw event data from WebSocket
    
    Returns:
        Parsed event model
    
    Raises:
        ValueError: If event type is invalid or data is malformed
    """
    event_type = data.get("type")
    
    if not event_type:
        raise ValueError("Missing event type")
    
    try:
        event_type = EventType(event_type)
    except ValueError:
        raise ValueError(f"Invalid event type: {event_type}")
    
    event_map = {
        EventType.JOIN: JoinEvent,
        EventType.START: StartEvent,
        EventType.PLAY: PlayEvent,
        EventType.PASS: PassEvent,
        EventType.GIFT_SELECT: GiftSelectEvent,
        EventType.DISCARD_SELECT: DiscardSelectEvent,
        EventType.EXCHANGE_RETURN: ExchangeReturnEvent,
        EventType.EXCHANGE_RETURN_VICE: ExchangeReturnViceEvent,
        EventType.REQUEST_STATE: RequestStateEvent,
        EventType.CHAT: ChatEvent,
    }
    
    event_class = event_map.get(event_type)
    if not event_class:
        raise ValueError(f"No handler for event type: {event_type}")
    
    try:
        return event_class(**data)
    except Exception as e:
        raise ValueError(f"Invalid event data: {str(e)}")


def create_error_event(code: ErrorCode, message: str) -> ErrorEvent:
    """Create an error event."""
    import time
    return ErrorEvent(
        code=code,
        message=message,
        timestamp=time.time()
    )


def create_join_success_event(player_id: str) -> JoinSuccessEvent:
    """Create a join success event."""
    import time
    return JoinSuccessEvent(
        player_id=player_id,
        timestamp=time.time()
    )


def create_state_full_event(state: Dict[str, Any]) -> StateFullEvent:
    """Create a full state event."""
    import time
    return StateFullEvent(
        state=state,
        timestamp=time.time()
    )


def create_state_patch_event(version: int, ops: List[Dict]) -> StatePatchEvent:
    """Create a state patch event."""
    import time
    patch_ops = [PatchOperation(**op) for op in ops]
    return StatePatchEvent(
        version=version,
        ops=patch_ops,
        timestamp=time.time()
    )


def create_effect_event(effect_type: str, data: Dict[str, Any]) -> EffectEvent:
    """Create an effect event."""
    import time
    return EffectEvent(
        effect_type=effect_type,
        data=data,
        timestamp=time.time()
    )


def create_chat_event(player_id: str, player_name: str, text: str) -> ChatMessageEvent:
    """Create a chat message event."""
    import time
    return ChatMessageEvent(
        player_id=player_id,
        player_name=player_name,
        text=text,
        timestamp=time.time()
    ) 