"""
FastAPI WebSocket server for the President game.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from collections import defaultdict
from typing import Dict, Optional, Set

import orjson
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ..bots.greedy import GreedyBot
from ..diff import compute_diff, should_send_full_state
from ..engine import (
    create_room, join_room, start_game, play_cards, pass_turn,
    submit_gift_distribution, submit_discard_selection,
    submit_exchange_return, start_new_round, disconnect_player, reconnect_player
)
from ..models import RoomState
from ..serialization import sanitize_state
from .events import (
    parse_inbound_event, create_error_event, create_join_success_event,
    create_state_full_event, create_state_patch_event, create_effect_event, 
    create_chat_event, ErrorCode, EventType, JoinEvent, StartEvent, PlayEvent, PassEvent,
    GiftSelectEvent, DiscardSelectEvent, ExchangeReturnEvent,
    ExchangeReturnViceEvent, RequestStateEvent, ChatEvent
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="President Game Engine", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
rooms: Dict[str, RoomState] = {}
room_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
connection_players: Dict[WebSocket, Optional[str]] = {}
connection_rooms: Dict[WebSocket, Optional[str]] = {}
player_states: Dict[str, Dict] = {}  # Store last known state for diffing
bots: Dict[str, GreedyBot] = {}  # Active bots


class ConnectionManager:
    """Manages WebSocket connections and broadcasting."""
    
    async def connect(self, websocket: WebSocket, room_id: str, player_id: str):
        """Connect a player to a room."""
        # WebSocket is already accepted in the main endpoint
        room_connections[room_id].add(websocket)
        connection_players[websocket] = player_id
        connection_rooms[websocket] = room_id
        logger.info(f"Player {player_id} connected to room {room_id}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a player from their room."""
        player_id = connection_players.get(websocket)
        room_id = connection_rooms.get(websocket)
        
        if room_id and websocket in room_connections[room_id]:
            room_connections[room_id].remove(websocket)
        
        if websocket in connection_players:
            del connection_players[websocket]
        
        if websocket in connection_rooms:
            del connection_rooms[websocket]
        
        # Clean up empty room connections
        if room_id and not room_connections[room_id]:
            if room_id in room_connections:
                del room_connections[room_id]
        
        if player_id:
            logger.info(f"Player {player_id} disconnected from room {room_id}")
        
        return player_id, room_id
    
    async def broadcast_to_room(self, room_id: str, event_data: Dict):
        """Broadcast an event to all connections in a room."""
        if room_id not in room_connections:
            return
        
        connections = list(room_connections[room_id])
        if not connections:
            return
        
        # Send personalized state to each connection
        for websocket in connections:
            try:
                player_id = connection_players.get(websocket)
                
                # Personalize the event for this player
                if event_data.get("type") in ["state_full", "state_patch"]:
                    personalized_event = await self._personalize_state_event(
                        event_data, player_id, room_id
                    )
                else:
                    personalized_event = event_data
                
                await websocket.send_text(json.dumps(personalized_event))
                
            except Exception as e:
                logger.error(f"Error broadcasting to {player_id}: {e}")
                # Remove dead connection
                self.disconnect(websocket)
    
    async def send_to_player(self, player_id: str, room_id: str, event_data: Dict):
        """Send an event to a specific player."""
        # Find the player's connection
        target_websocket = None
        for websocket, pid in connection_players.items():
            if pid == player_id:
                target_websocket = websocket
                break
        
        if target_websocket:
            try:
                # Personalize the event
                if event_data.get("type") in ["state_full", "state_patch"]:
                    personalized_event = await self._personalize_state_event(
                        event_data, player_id, room_id
                    )
                else:
                    personalized_event = event_data
                
                await target_websocket.send_text(json.dumps(personalized_event))
            except Exception as e:
                logger.error(f"Error sending to player {player_id}: {e}")
                self.disconnect(target_websocket)
    
    async def _personalize_state_event(self, event_data: Dict, player_id: Optional[str], room_id: str) -> Dict:
        """Personalize a state event for a specific player."""
        if room_id not in rooms:
            return event_data
        
        room_state = rooms[room_id]
        
        if event_data.get("type") == "state_full":
            # Re-sanitize state for this player
            sanitized_state = sanitize_state(room_state, player_id)
            return {
                **event_data,
                "state": sanitized_state
            }
        elif event_data.get("type") == "state_patch":
            # Recompute diff for this player
            old_state = player_states.get(f"{player_id}_{room_id}")
            if old_state:
                diff_ops = compute_diff(old_state, room_state, player_id)
                # Store new state for next diff
                player_states[f"{player_id}_{room_id}"] = room_state
                
                return {
                    **event_data,
                    "ops": diff_ops
                }
        
        return event_data


manager = ConnectionManager()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "rooms": len(rooms),
        "connections": sum(len(conns) for conns in room_connections.values())
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint."""
    player_id = None
    room_id = None
    
    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        
        while True:
            # Receive message
            raw_data = await websocket.receive_text()
            
            try:
                data = json.loads(raw_data)
                event = parse_inbound_event(data)
                
                # Handle the event
                result = await handle_event(websocket, event)
                
                # Update connection tracking if this was a join event
                if isinstance(event, JoinEvent) and result.get("success"):
                    player_id = result["player_id"]
                    room_id = event.room_id
                    await manager.connect(websocket, room_id, player_id)
                
            except ValueError as e:
                # Invalid event
                error_event = create_error_event(ErrorCode.INVALID_EVENT, str(e))
                await websocket.send_text(error_event.model_dump_json())
            except Exception as e:
                logger.error(f"Error handling event: {e}")
                error_event = create_error_event(ErrorCode.INTERNAL, "Internal server error")
                await websocket.send_text(error_event.model_dump_json())
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Clean up connection
        disconnected_player_id, disconnected_room_id = manager.disconnect(websocket)
        
        # Mark player as disconnected in game state
        if disconnected_player_id and disconnected_room_id and disconnected_room_id in rooms:
            disconnect_result = disconnect_player(rooms[disconnected_room_id], disconnected_player_id)
            if disconnect_result.success:
                rooms[disconnected_room_id] = disconnect_result.state
                await broadcast_state_update(disconnected_room_id, disconnect_result.state)


async def handle_event(websocket: WebSocket, event) -> Dict:
    """Handle an inbound event."""
    
    if isinstance(event, JoinEvent):
        return await handle_join(websocket, event)
    elif isinstance(event, StartEvent):
        return await handle_start(websocket, event)
    elif isinstance(event, PlayEvent):
        return await handle_play(websocket, event)
    elif isinstance(event, PassEvent):
        return await handle_pass(websocket, event)
    elif isinstance(event, GiftSelectEvent):
        return await handle_gift_select(websocket, event)
    elif isinstance(event, DiscardSelectEvent):
        return await handle_discard_select(websocket, event)
    elif isinstance(event, ExchangeReturnEvent):
        return await handle_exchange_return(websocket, event)
    elif isinstance(event, ExchangeReturnViceEvent):
        return await handle_exchange_return_vice(websocket, event)
    elif isinstance(event, RequestStateEvent):
        return await handle_request_state(websocket, event)
    elif isinstance(event, ChatEvent):
        return await handle_chat(websocket, event)
    else:
        raise ValueError(f"Unhandled event type: {type(event)}")


async def handle_join(websocket: WebSocket, event: JoinEvent) -> Dict:
    """Handle join room event."""
    room_id = event.room_id
    player_name = event.name
    is_bot = event.is_bot
    
    # Generate player ID
    player_id = str(uuid.uuid4())
    
    # Create room if it doesn't exist
    if room_id not in rooms:
        rooms[room_id] = create_room(room_id)
    
    # Join the room
    result = join_room(rooms[room_id], player_id, player_name, is_bot)
    
    if result.success:
        rooms[room_id] = result.state
        
        # If this is a bot, create the bot instance
        if is_bot:
            bots[player_id] = GreedyBot(player_id)
        
        # Send join success confirmation first
        join_success_event = create_join_success_event(player_id)
        await websocket.send_text(join_success_event.model_dump_json())
        
        # Send full state to the new player
        sanitized_state = sanitize_state(result.state, player_id)
        state_event = create_state_full_event(sanitized_state)
        await websocket.send_text(state_event.model_dump_json())
        
        # Broadcast state update to other players
        await broadcast_state_update(room_id, result.state, exclude_player=player_id)
        
        return {"success": True, "player_id": player_id}
    else:
        # Send error
        error_event = create_error_event(
            ErrorCode(result.error_code), 
            result.error_message
        )
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False, "error": result.error_message}


async def handle_start(websocket: WebSocket, event: StartEvent) -> Dict:
    """Handle start game event."""
    player_id = connection_players.get(websocket)
    room_id = connection_rooms.get(websocket)
    
    if not player_id or not room_id or room_id not in rooms:
        error_event = create_error_event(ErrorCode.ACTION_NOT_ALLOWED, "Not in a room")
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}
    
    result = start_game(rooms[room_id], event.seed)
    
    if result.success:
        rooms[room_id] = result.state
        await broadcast_state_update(room_id, result.state)
        
        # Schedule bot actions immediately after game start
        logger.info(f"Game started for room {room_id}, scheduling bot actions immediately")
        logger.info(f"Starting player: {result.state.turn}")
        logger.info(f"Starting player name: {result.state.players[result.state.turn].name if result.state.turn else 'None'}")
        logger.info(f"Starting player is bot: {result.state.players[result.state.turn].is_bot if result.state.turn else 'None'}")
        
        # Debug: Show who has 3♦ and who should start
        logger.info(f"=== GAME START DEBUG ===")
        logger.info(f"Game phase: {result.state.phase}")
        logger.info(f"Current turn: {result.state.turn}")
        if result.state.turn:
            logger.info(f"Starting player: {result.state.players[result.state.turn].name}")
            logger.info(f"Starting player is bot: {result.state.players[result.state.turn].is_bot}")
        
        for pid, player in result.state.players.items():
            if "3D" in player.hand:
                logger.info(f"Player {player.name} (ID: {pid}) has 3♦")
                if pid != result.state.turn:
                    logger.warning(f"MISMATCH: {player.name} has 3♦ but {result.state.players[result.state.turn].name} is starting!")
                else:
                    logger.info(f"✓ CORRECT: {player.name} has 3♦ and is starting")
        
        logger.info(f"=== END GAME START DEBUG ===")
        
        # Force immediate bot scheduling
        await schedule_bot_actions(room_id)
        
        return {"success": True}
    else:
        error_event = create_error_event(
            ErrorCode(result.error_code),
            result.error_message
        )
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}


async def handle_play(websocket: WebSocket, event: PlayEvent) -> Dict:
    """Handle play cards event."""
    player_id = connection_players.get(websocket)
    room_id = connection_rooms.get(websocket)
    
    if not player_id or not room_id or room_id not in rooms:
        error_event = create_error_event(ErrorCode.ACTION_NOT_ALLOWED, "Not in a room")
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}
    
    logger.info(f"🎮 Play event from {player_id}: {event.cards}")
    
    result = play_cards(rooms[room_id], player_id, event.cards)
    
    if result.success:
        logger.info(f"✅ Play successful for {player_id}: {event.cards}")
        rooms[room_id] = result.state
        await broadcast_state_update(room_id, result.state)
        
        # Schedule bot actions
        asyncio.create_task(schedule_bot_actions(room_id))
        
        return {"success": True}
    else:
        logger.error(f"❌ Play failed for {player_id}: {result.error_message}")
        error_event = create_error_event(
            ErrorCode(result.error_code),
            result.error_message
        )
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}


async def handle_pass(websocket: WebSocket, event: PassEvent) -> Dict:
    """Handle pass turn event."""
    player_id = connection_players.get(websocket)
    room_id = connection_rooms.get(websocket)
    
    if not player_id or not room_id or room_id not in rooms:
        error_event = create_error_event(ErrorCode.ACTION_NOT_ALLOWED, "Not in a room")
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}
    
    result = pass_turn(rooms[room_id], player_id)
    
    if result.success:
        rooms[room_id] = result.state
        await broadcast_state_update(room_id, result.state)
        
        # Schedule bot actions
        asyncio.create_task(schedule_bot_actions(room_id))
        
        return {"success": True}
    else:
        error_event = create_error_event(
            ErrorCode(result.error_code),
            result.error_message
        )
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}


async def handle_gift_select(websocket: WebSocket, event: GiftSelectEvent) -> Dict:
    """Handle gift selection event."""
    player_id = connection_players.get(websocket)
    room_id = connection_rooms.get(websocket)
    
    if not player_id or not room_id or room_id not in rooms:
        error_event = create_error_event(ErrorCode.ACTION_NOT_ALLOWED, "Not in a room")
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}
    
    # Convert assignments to dict format
    assignments = [
        {"to": assignment.to, "cards": assignment.cards}
        for assignment in event.assignments
    ]
    
    result = submit_gift_distribution(rooms[room_id], player_id, assignments)
    
    if result.success:
        rooms[room_id] = result.state
        await broadcast_state_update(room_id, result.state)
        
        # Schedule bot actions
        asyncio.create_task(schedule_bot_actions(room_id))
        
        return {"success": True}
    else:
        error_event = create_error_event(
            ErrorCode(result.error_code),
            result.error_message
        )
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}


async def handle_discard_select(websocket: WebSocket, event: DiscardSelectEvent) -> Dict:
    """Handle discard selection event."""
    player_id = connection_players.get(websocket)
    room_id = connection_rooms.get(websocket)
    
    if not player_id or not room_id or room_id not in rooms:
        error_event = create_error_event(ErrorCode.ACTION_NOT_ALLOWED, "Not in a room")
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}
    
    result = submit_discard_selection(rooms[room_id], player_id, event.cards)
    
    if result.success:
        rooms[room_id] = result.state
        await broadcast_state_update(room_id, result.state)
        
        # Schedule bot actions
        asyncio.create_task(schedule_bot_actions(room_id))
        
        return {"success": True}
    else:
        error_event = create_error_event(
            ErrorCode(result.error_code),
            result.error_message
        )
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}


async def handle_exchange_return(websocket: WebSocket, event: ExchangeReturnEvent) -> Dict:
    """Handle exchange return event (President)."""
    player_id = connection_players.get(websocket)
    room_id = connection_rooms.get(websocket)
    
    if not player_id or not room_id or room_id not in rooms:
        error_event = create_error_event(ErrorCode.ACTION_NOT_ALLOWED, "Not in a room")
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}
    
    result = submit_exchange_return(rooms[room_id], player_id, event.cards)
    
    if result.success:
        rooms[room_id] = result.state
        await broadcast_state_update(room_id, result.state)
        
        # Schedule bot actions
        asyncio.create_task(schedule_bot_actions(room_id))
        
        return {"success": True}
    else:
        error_event = create_error_event(
            ErrorCode(result.error_code),
            result.error_message
        )
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}


async def handle_exchange_return_vice(websocket: WebSocket, event: ExchangeReturnViceEvent) -> Dict:
    """Handle exchange return event (Vice President)."""
    player_id = connection_players.get(websocket)
    room_id = connection_rooms.get(websocket)
    
    if not player_id or not room_id or room_id not in rooms:
        error_event = create_error_event(ErrorCode.ACTION_NOT_ALLOWED, "Not in a room")
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}
    
    result = submit_exchange_return(rooms[room_id], player_id, event.cards)
    
    if result.success:
        rooms[room_id] = result.state
        await broadcast_state_update(room_id, result.state)
        
        # Schedule bot actions
        asyncio.create_task(schedule_bot_actions(room_id))
        
        return {"success": True}
    else:
        error_event = create_error_event(
            ErrorCode(result.error_code),
            result.error_message
        )
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}


async def handle_request_state(websocket: WebSocket, event: RequestStateEvent) -> Dict:
    """Handle request state event."""
    player_id = connection_players.get(websocket)
    room_id = connection_rooms.get(websocket)
    
    if not player_id or not room_id or room_id not in rooms:
        error_event = create_error_event(ErrorCode.ACTION_NOT_ALLOWED, "Not in a room")
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}
    
    # Send full state
    sanitized_state = sanitize_state(rooms[room_id], player_id)
    state_event = create_state_full_event(sanitized_state)
    await websocket.send_text(state_event.model_dump_json())
    
    return {"success": True}


async def handle_chat(websocket: WebSocket, event: ChatEvent) -> Dict:
    """Handle chat message event."""
    player_id = connection_players.get(websocket)
    room_id = connection_rooms.get(websocket)
    
    if not player_id or not room_id or room_id not in rooms:
        error_event = create_error_event(ErrorCode.ACTION_NOT_ALLOWED, "Not in a room")
        await websocket.send_text(error_event.model_dump_json())
        return {"success": False}
    
    # Get player name
    player = rooms[room_id].players.get(player_id)
    if not player:
        return {"success": False}
    
    # Broadcast chat message
    chat_event = create_chat_event(player_id, player.name, event.text)
    await manager.broadcast_to_room(room_id, chat_event.dict())
    
    return {"success": True}


async def broadcast_state_update(room_id: str, new_state: RoomState, exclude_player: Optional[str] = None):
    """Broadcast state update to all players in a room."""
    if room_id not in room_connections:
        return
    
    # For each connected player, compute personalized diff and send
    for websocket in list(room_connections[room_id]):
        try:
            player_id = connection_players.get(websocket)
            
            # Skip excluded player
            if player_id == exclude_player:
                continue
            
            # Get previous state for this player
            state_key = f"{player_id}_{room_id}"
            old_state = player_states.get(state_key)
            
            if old_state is None:
                # Send full state for first time
                sanitized_state = sanitize_state(new_state, player_id)
                logger.info(f"🎮 SENDING FULL STATE to {player_id}: turn={sanitized_state.get('turn')}, phase={sanitized_state.get('phase')}")
                state_event = create_state_full_event(sanitized_state)
                await websocket.send_text(state_event.model_dump_json())
            else:
                # Compute diff
                diff_ops = compute_diff(old_state, new_state, player_id)
                
                if should_send_full_state(diff_ops):
                    # Send full state if diff is too large
                    sanitized_state = sanitize_state(new_state, player_id)
                    state_event = create_state_full_event(sanitized_state)
                    await websocket.send_text(state_event.model_dump_json())
                else:
                    # Send patch
                    patch_event = create_state_patch_event(new_state.version, diff_ops)
                    await websocket.send_text(patch_event.model_dump_json())
            
            # Store new state for next diff
            player_states[state_key] = new_state
            
        except Exception as e:
            logger.error(f"Error broadcasting to player {player_id}: {e}")
            manager.disconnect(websocket)


async def schedule_bot_actions(room_id: str):
    """Schedule bot actions for a room."""
    if room_id not in rooms:
        logger.warning(f"Room {room_id} not found in schedule_bot_actions")
        return

    state = rooms[room_id]
    logger.info(f"Scheduling bot actions for room {room_id}")
    logger.info(f"Current turn: {state.turn}")
    logger.info(f"Current phase: {state.phase}")
    logger.info(f"Available bots: {list(bots.keys())}")
    logger.info(f"Room players: {list(state.players.keys())}")
    
    # Defensive check: if current turn player is a bot but not in bots dict, log error
    if state.turn and state.turn in state.players:
        current_player = state.players[state.turn]
        if current_player.is_bot and state.turn not in bots:
            logger.error(f"CRITICAL: Current turn player {current_player.name} is a bot but not in bots dict!")
            # Try to create the missing bot
            bots[state.turn] = GreedyBot(state.turn)
            logger.info(f"Created missing bot for {current_player.name}")
    
    # Safety check: ensure all bot players have bot instances
    for player_id, player in state.players.items():
        if player.is_bot and player_id not in bots:
            logger.warning(f"Bot player {player.name} missing from bots dict, creating now")
            bots[player_id] = GreedyBot(player_id)
    
    # Simplified bot scheduling logic
    scheduled_any = False
    
    # First priority: current turn player if it's a bot
    if state.turn and state.turn in state.players and state.players[state.turn].is_bot and state.turn in bots:
        current_player = state.players[state.turn]
        if state.phase == "play":
            logger.info(f"🎯 SCHEDULING: Current turn bot {current_player.name}")
            asyncio.create_task(execute_bot_action(room_id, state.turn, bots[state.turn]))
            scheduled_any = True
    
    # Second priority: bots with pending effects
    for player_id, player in state.players.items():
        if not player.is_bot or player_id not in bots:
            continue
            
        has_pending_gift = (state.pending_gift and state.pending_gift.player_id == player_id)
        has_pending_discard = (state.pending_discard and state.pending_discard.player_id == player_id)
        has_exchange_pending = (state.phase == "exchange" and player.role in ["President", "VicePresident"])
        
        if has_pending_gift or has_pending_discard or has_exchange_pending:
            logger.info(f"🎯 SCHEDULING: Bot {player.name} for pending effect (gift={has_pending_gift}, discard={has_pending_discard}, exchange={has_exchange_pending})")
            asyncio.create_task(execute_bot_action(room_id, player_id, bots[player_id]))
            scheduled_any = True
    
    if not scheduled_any:
        logger.info(f"No bot actions needed for room {room_id}")
        if state.turn:
            current_player = state.players[state.turn]
            logger.info(f"Current turn: {current_player.name} (bot: {current_player.is_bot})")
        else:
            logger.info(f"No current turn player")


async def execute_bot_action(room_id: str, player_id: str, bot: GreedyBot):
    """Execute a bot action after a delay."""
    # Add small delay to simulate thinking
    await asyncio.sleep(0.8)
    
    # Double-check everything still exists and is valid
    if room_id not in rooms:
        logger.warning(f"Room {room_id} no longer exists")
        return
        
    if player_id not in bots:
        logger.warning(f"Bot {player_id} no longer exists")
        return
        
    state = rooms[room_id]
    
    if player_id not in state.players:
        logger.warning(f"Player {player_id} not in room state")
        return
    
    player = state.players[player_id]
    logger.info(f"🤖 Executing action for bot {player.name}")
    
    try:
        # Get bot action
        action = bot.choose_action(state)
        if not action:
            logger.warning(f"Bot {player.name} returned no action")
            return
        
        logger.info(f"🤖 Bot {player.name} chose: {action.type}")
        
        # Execute the action
        result = None
        
        if action.type == "play":
            cards = action.data.get("cards", [])
            logger.info(f"🤖 Bot {player.name} playing: {cards}")
            result = play_cards(state, player_id, cards)
        elif action.type == "pass":
            logger.info(f"🤖 Bot {player.name} passing")
            result = pass_turn(state, player_id)
        elif action.type == "gift":
            assignments = action.data.get("assignments", [])
            logger.info(f"🤖 Bot {player.name} gifting")
            result = submit_gift_distribution(state, player_id, assignments)
        elif action.type == "discard":
            cards = action.data.get("cards", [])
            logger.info(f"🤖 Bot {player.name} discarding: {cards}")
            result = submit_discard_selection(state, player_id, cards)
        elif action.type == "exchange_return":
            cards = action.data.get("cards", [])
            logger.info(f"🤖 Bot {player.name} returning exchange: {cards}")
            result = submit_exchange_return(state, player_id, cards)
        else:
            logger.error(f"🤖 Bot {player.name} unknown action: {action.type}")
            return
        
        # Handle result
        if result and result.success:
            logger.info(f"✅ Bot {player.name} action successful")
            rooms[room_id] = result.state
            await broadcast_state_update(room_id, result.state)
            
            # Schedule next bot actions immediately
            await schedule_bot_actions(room_id)
        else:
            error_msg = result.error_message if result else 'No result returned'
            logger.error(f"❌ Bot {player.name} action failed: {error_msg}")
        
    except Exception as e:
        logger.error(f"💥 Error executing bot action for {player.name}: {e}")
        import traceback
        traceback.print_exc()


# Main entry point for module execution
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info") 