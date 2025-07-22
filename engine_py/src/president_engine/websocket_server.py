"""WebSocket server for real-time multiplayer communication"""

import asyncio
import json
import logging
from typing import Dict, Set
import uuid
from fastapi import WebSocket, WebSocketDisconnect

from .engine import PresidentEngine
from .bots import GreedyBot

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.room_connections: Dict[str, Set[str]] = {}
        self.player_to_room: Dict[str, str] = {}
        self.ws_to_game_player: Dict[str, str] = {}  # Map WebSocket player to game player
        
    async def connect(self, websocket: WebSocket, player_id: str):
        await websocket.accept()
        self.active_connections[player_id] = websocket
        logger.info(f"Player {player_id} connected")
        
    def disconnect(self, player_id: str):
        if player_id in self.active_connections:
            del self.active_connections[player_id]
        if player_id in self.player_to_room:
            room_id = self.player_to_room[player_id]
            if room_id in self.room_connections:
                self.room_connections[room_id].discard(player_id)
            del self.player_to_room[player_id]
        if player_id in self.ws_to_game_player:
            del self.ws_to_game_player[player_id]
        logger.info(f"Player {player_id} disconnected")
        
    def add_to_room(self, ws_player_id: str, room_id: str, game_player_id: str):
        if room_id not in self.room_connections:
            self.room_connections[room_id] = set()
        self.room_connections[room_id].add(ws_player_id)
        self.player_to_room[ws_player_id] = room_id
        self.ws_to_game_player[ws_player_id] = game_player_id
        
    async def send_personal_message(self, message: dict, player_id: str):
        if player_id in self.active_connections:
            try:
                await self.active_connections[player_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {player_id}: {e}")
                
    async def broadcast_to_room(self, message: dict, room_id: str):
        if room_id in self.room_connections:
            disconnected = []
            for player_id in self.room_connections[room_id]:
                if player_id in self.active_connections:
                    try:
                        await self.active_connections[player_id].send_text(json.dumps(message))
                    except Exception as e:
                        logger.error(f"Error broadcasting to {player_id}: {e}")
                        disconnected.append(player_id)
                        
            # Clean up disconnected players
            for player_id in disconnected:
                self.disconnect(player_id)

class GameWebSocketManager:
    def __init__(self):
        self.engine = PresidentEngine()
        self.bot = GreedyBot(self.engine)
        self.connection_manager = ConnectionManager()
        self.bot_tasks: Dict[str, asyncio.Task] = {}
        
    async def handle_websocket(self, websocket: WebSocket, player_id: str = None):
        if not player_id:
            player_id = str(uuid.uuid4())[:8]
            
        await self.connection_manager.connect(websocket, player_id)
        
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                await self.handle_message(message, player_id)
                
        except WebSocketDisconnect:
            self.connection_manager.disconnect(player_id)
            logger.info(f"WebSocket disconnected for player {player_id}")
        except Exception as e:
            logger.error(f"WebSocket error for player {player_id}: {e}")
            self.connection_manager.disconnect(player_id)
            
    async def handle_message(self, message: dict, ws_player_id: str):
        msg_type = message.get('type')
        
        try:
            if msg_type == 'join':
                await self.join_room(message.get('room_id'), ws_player_id, 
                                   message.get('name', 'Player'), message.get('is_bot', False))
            elif msg_type == 'start':
                room_id = self.connection_manager.player_to_room.get(ws_player_id)
                if room_id:
                    await self.start_game(room_id)
            elif msg_type == 'play':
                await self.play_cards(ws_player_id, message.get('cards', []))
            elif msg_type == 'pass':
                await self.pass_turn(ws_player_id)
            elif msg_type == 'gift_select':
                await self.gift_cards(ws_player_id, message.get('assignments', []))
            elif msg_type == 'discard_select':
                await self.discard_cards(ws_player_id, message.get('cards', []))
            elif msg_type == 'request_state':
                await self.send_game_state(ws_player_id)
        except Exception as e:
            logger.error(f"Error handling message {msg_type}: {e}")
            await self.connection_manager.send_personal_message({
                'type': 'error',
                'code': 'INTERNAL_ERROR',
                'message': str(e),
                'timestamp': int(asyncio.get_event_loop().time() * 1000)
            }, ws_player_id)
            
    async def join_room(self, room_id: str, ws_player_id: str, player_name: str, is_bot: bool = False):
        if not room_id:
            # Create new room
            room_id = str(uuid.uuid4())[:8].upper()
            self.engine.create_room(room_id)
            
        room = self.engine.get_room(room_id)
        if not room:
            await self.connection_manager.send_personal_message({
                'type': 'error',
                'code': 'ROOM_NOT_FOUND',
                'message': 'Room not found',
                'timestamp': int(asyncio.get_event_loop().time() * 1000)
            }, ws_player_id)
            return
            
        success, game_player_id = self.engine.add_player(room_id, player_name, is_bot)
        if success:
            self.connection_manager.add_to_room(ws_player_id, room_id, game_player_id)
            await self.connection_manager.send_personal_message({
                'type': 'join_success',
                'player_id': game_player_id,
                'timestamp': int(asyncio.get_event_loop().time() * 1000)
            }, ws_player_id)
            await self.broadcast_game_state(room_id)
        else:
            await self.connection_manager.send_personal_message({
                'type': 'error',
                'code': 'JOIN_FAILED',
                'message': 'Failed to join room (room may be full)',
                'timestamp': int(asyncio.get_event_loop().time() * 1000)
            }, ws_player_id)
        
    async def start_game(self, room_id: str):
        success, message = self.engine.start_game(room_id)
        if success:
            await self.broadcast_game_state(room_id)
            # Start bot automation
            await self.start_bot_automation(room_id)
        else:
            await self.connection_manager.broadcast_to_room({
                'type': 'error',
                'code': 'START_FAILED',
                'message': message,
                'timestamp': int(asyncio.get_event_loop().time() * 1000)
            }, room_id)
            
    async def play_cards(self, ws_player_id: str, card_ids: list):
        game_player_id = self.connection_manager.ws_to_game_player.get(ws_player_id)
        room_id = self.connection_manager.player_to_room.get(ws_player_id)
        
        print(f"🎮 BACKEND PLAY DEBUG:")
        print(f"  ws_player_id: {ws_player_id}")
        print(f"  game_player_id: {game_player_id}")
        print(f"  room_id: {room_id}")
        print(f"  card_ids: {card_ids}")
        
        if not game_player_id or not room_id:
            print(f"❌ Missing game_player_id or room_id")
            return
            
        room = self.engine.get_room(room_id)
        if room:
            print(f"  current_turn: {room.turn}")
            print(f"  phase: {room.phase}")
            print(f"  turn_matches: {room.turn == game_player_id}")
            print(f"  current_player_hand: {room.players[game_player_id].hand if game_player_id in room.players else 'N/A'}")
            print(f"  current_rank: {room.current_rank}")
            print(f"  current_count: {room.current_count}")
            print(f"  first_game: {getattr(room, 'first_game', 'N/A')}")
            print(f"  first_game_first_play_done: {getattr(room, 'first_game_first_play_done', 'N/A')}")
        
        success, message = self.engine.play_cards(room_id, game_player_id, card_ids)
        print(f"  play_result: success={success}, message='{message}'")
        
        if success:
            await self.broadcast_game_state(room_id)
        else:
            await self.connection_manager.send_personal_message({
                'type': 'error',
                'code': 'INVALID_PLAY',
                'message': message,
                'timestamp': int(asyncio.get_event_loop().time() * 1000)
            }, ws_player_id)
            
    async def pass_turn(self, ws_player_id: str):
        game_player_id = self.connection_manager.ws_to_game_player.get(ws_player_id)
        room_id = self.connection_manager.player_to_room.get(ws_player_id)
        
        if not game_player_id or not room_id:
            return
            
        success, message = self.engine.pass_turn(room_id, game_player_id)
        if success:
            await self.broadcast_game_state(room_id)
        else:
            await self.connection_manager.send_personal_message({
                'type': 'error',
                'code': 'PASS_FAILED',
                'message': message,
                'timestamp': int(asyncio.get_event_loop().time() * 1000)
            }, ws_player_id)
            
    async def gift_cards(self, ws_player_id: str, assignments: list):
        game_player_id = self.connection_manager.ws_to_game_player.get(ws_player_id)
        room_id = self.connection_manager.player_to_room.get(ws_player_id)
        
        if not game_player_id or not room_id:
            return
            
        success, message = self.engine.submit_gift_distribution(room_id, game_player_id, assignments)
        if success:
            await self.broadcast_game_state(room_id)
        else:
            await self.connection_manager.send_personal_message({
                'type': 'error',
                'code': 'GIFT_FAILED',
                'message': message,
                'timestamp': int(asyncio.get_event_loop().time() * 1000)
            }, ws_player_id)
            
    async def discard_cards(self, ws_player_id: str, card_ids: list):
        game_player_id = self.connection_manager.ws_to_game_player.get(ws_player_id)
        room_id = self.connection_manager.player_to_room.get(ws_player_id)
        
        if not game_player_id or not room_id:
            return
            
        success, message = self.engine.submit_discard_selection(room_id, game_player_id, card_ids)
        if success:
            await self.broadcast_game_state(room_id)
        else:
            await self.connection_manager.send_personal_message({
                'type': 'error',
                'code': 'DISCARD_FAILED',
                'message': message,
                'timestamp': int(asyncio.get_event_loop().time() * 1000)
            }, ws_player_id)
            
    async def send_game_state(self, ws_player_id: str):
        game_player_id = self.connection_manager.ws_to_game_player.get(ws_player_id)
        room_id = self.connection_manager.player_to_room.get(ws_player_id)
        
        if not room_id:
            return
            
        room = self.engine.get_room(room_id)
        if room:
            await self.connection_manager.send_personal_message({
                'type': 'state_full',
                'state': self.serialize_room_for_player(room, game_player_id),
                'timestamp': int(asyncio.get_event_loop().time() * 1000)
            }, ws_player_id)
            
    async def broadcast_game_state(self, room_id: str):
        room = self.engine.get_room(room_id)
        if not room or room_id not in self.connection_manager.room_connections:
            return
            
        # Send personalized game state to each connected player
        for ws_player_id in self.connection_manager.room_connections[room_id]:
            game_player_id = self.connection_manager.ws_to_game_player.get(ws_player_id)
            await self.connection_manager.send_personal_message({
                'type': 'state_full',
                'state': self.serialize_room_for_player(room, game_player_id),
                'timestamp': int(asyncio.get_event_loop().time() * 1000)
            }, ws_player_id)
                        
    def serialize_room_for_player(self, room, player_id):
        """Serialize room state for a specific player (hiding other players' hands)"""
        players_data = {}
        for pid, player in room.players.items():
            players_data[pid] = {
                'id': player.id,
                'name': player.name,
                'seat': player.seat,
                'role': player.role,
                'hand_count': player.hand_count,
                'passed': player.passed,
                'connected': player.connected,
                'is_bot': player.is_bot
            }
            # Only include hand for the current player
            if pid == player_id:
                players_data[pid]['hand'] = player.hand
        
        # Create current pattern from room state
        current_pattern = {
            'rank': room.current_rank,
            'count': room.current_count,
            'cards': room.current_pile.copy() if room.current_pile else []
        }
        if room.last_play:
            current_pattern['last_player'] = room.last_play['player_id']
        
        # Create pending effects from room state
        pending_effects = {}
        if room.pending_gift:
            pending_effects['gift'] = {
                'player_id': room.pending_gift['player_id'],
                'remaining': room.pending_gift['remaining'],
                'original_count': room.pending_gift['remaining']  # Simplified
            }
        if room.pending_discard:
            pending_effects['discard'] = {
                'player_id': room.pending_discard['player_id'],
                'remaining': room.pending_discard['remaining'],
                'original_count': room.pending_discard['remaining']  # Simplified
            }
            
        return {
            'id': room.id,
            'version': room.version,
            'phase': room.phase,
            'players': players_data,
            'turn': room.turn,
            'inversion_active': room.inversion_active,
            'current_pattern': current_pattern,
            'finished_order': room.finished_order.copy(),
            'pending_effects': pending_effects,
            'recent_effects': [],  # We could populate this with recent game log entries
            'discard': room.discard.copy()
        }
        
    async def start_bot_automation(self, room_id: str):
        """Start background task for bot automation"""
        if room_id in self.bot_tasks:
            self.bot_tasks[room_id].cancel()
            
        self.bot_tasks[room_id] = asyncio.create_task(self.bot_automation_loop(room_id))
        
    async def bot_automation_loop(self, room_id: str):
        """Background loop to handle bot moves"""
        try:
            while True:
                room = self.engine.get_room(room_id)
                if not room or room.phase != 'play':
                    break
                print(f"[BOT LOOP] Current turn: {room.turn} ({room.players[room.turn].name if room.turn in room.players else 'Unknown'})")
                if room.turn and room.turn in room.players:
                    current_player = room.players[room.turn]
                    if current_player.is_bot:
                        print(f"[BOT LOOP] Bot {current_player.name} ({current_player.id}) is making a move.")
                        # Add small delay for realism
                        await asyncio.sleep(0.8)
                        
                        # Handle pending effects first
                        if room.pending_gift and room.pending_gift['player_id'] == room.turn:
                            self.bot._handle_gift(room_id, room.turn, room.pending_gift['remaining'])
                        elif room.pending_discard and room.pending_discard['player_id'] == room.turn:
                            self.bot._handle_discard(room_id, room.turn, room.pending_discard['remaining'])
                        else:
                            self.bot.make_move(room_id, room.turn)
                            
                        # Broadcast updated state
                        await self.broadcast_game_state(room_id)
                        
                await asyncio.sleep(0.2)  # Small delay to prevent busy waiting
                
        except asyncio.CancelledError:
            logger.info(f"Bot automation cancelled for room {room_id}")
        except Exception as e:
            logger.error(f"Bot automation error for room {room_id}: {e}")

# Global instance
game_manager = GameWebSocketManager() 