import dash
from dash import dcc, html, Input, Output, State, callback_context, ALL, MATCH, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Tuple, Union
import random
import json
import time
import threading
from collections import defaultdict
import uuid
import pandas as pd  # Add this import at the top

# ===================== GAME MODELS =====================

Rank = Union[int, Literal['J','Q','K','A',2,'JOKER']]

@dataclass
class Player:
    id: str
    name: str
    seat: int
    role: Optional[str] = None  # President, VicePresident, Citizen, Scumbag, Asshole
    hand: List[str] = field(default_factory=list)  # card ids
    passed: bool = False
    connected: bool = True
    is_bot: bool = False
    hand_count: int = 0

@dataclass
class RoomState:
    id: str
    version: int = 0
    phase: str = 'lobby'  # lobby|dealing|exchange|play|finished
    players: Dict[str, Player] = field(default_factory=dict)
    turn: Optional[str] = None
    current_rank: Optional[Rank] = None
    current_count: Optional[int] = None
    inversion_active: bool = False
    deck: List[str] = field(default_factory=list)
    discard: List[str] = field(default_factory=list)
    current_pile: List[str] = field(default_factory=list)  # Cards currently in play
    finished_order: List[str] = field(default_factory=list)
    pending_gift: Optional[dict] = None
    pending_discard: Optional[dict] = None
    last_play: Optional[dict] = None
    game_log: List[str] = field(default_factory=list)

# ===================== GAME CONSTANTS & UTILS =====================

NORMAL_ORDER = [3,4,5,6,7,8,9,10,'J','Q','K','A',2,'JOKER']
SUITS = ['S', 'H', 'D', 'C']

def create_deck(use_jokers=True):
    deck = []
    for suit in SUITS:
        for rank in [3,4,5,6,7,8,9,10,'J','Q','K','A',2]:
            deck.append(f"{rank}{suit}")
    if use_jokers:
        deck.extend(['JOKERa', 'JOKERb'])
    return deck

def parse_card(card_id):
    if card_id.startswith('JOKER'):
        return 'JOKER', None
    if card_id[:-1] in ['J', 'Q', 'K', 'A']:
        return card_id[:-1], card_id[-1]
    if card_id[:-1] == '10':
        return 10, card_id[-1]
    return int(card_id[:-1]), card_id[-1]

def compare_ranks(rank_a, rank_b, inversion=False):
    order = list(reversed(NORMAL_ORDER)) if inversion else NORMAL_ORDER
    try:
        return order.index(rank_a) - order.index(rank_b)
    except ValueError:
        return 0

def is_higher_rank(rank_a, rank_b, inversion=False):
    return compare_ranks(rank_a, rank_b, inversion) > 0

# ===================== GAME ENGINE =====================
class PresidentEngine:
    def __init__(self):
        self.rooms: Dict[str, RoomState] = {}
        self.room_locks = defaultdict(threading.Lock)
    
    def create_room(self, room_id: str) -> RoomState:
        with self.room_locks[room_id]:
            if room_id not in self.rooms:
                self.rooms[room_id] = RoomState(id=room_id)
            return self.rooms[room_id]
    
    def get_room(self, room_id: str) -> Optional[RoomState]:
        return self.rooms.get(room_id)
    
    def add_player(self, room_id: str, player_name: str, is_bot: bool = False) -> Tuple[bool, str]:
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room:
                return False, "Room not found"
            if len(room.players) >= 5:
                return False, "Room is full"
            player_id = str(uuid.uuid4())[:8]
            seat = len(room.players)
            room.players[player_id] = Player(
                id=player_id,
                name=player_name,
                seat=seat,
                is_bot=is_bot
            )
            room.version += 1
            return True, player_id
    
    def start_game(self, room_id: str) -> Tuple[bool, str]:
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room:
                return False, "Room not found"
            if len(room.players) < 3:
                return False, "Need at least 3 players"
            room.phase = 'dealing'
            room.finished_order = []
            room.game_log = []
            deck = create_deck(True)
            random.shuffle(deck)
            players = list(room.players.values())
            cards_per_player = len(deck) // len(players)
            for i, player in enumerate(players):
                start_idx = i * cards_per_player
                end_idx = start_idx + cards_per_player
                if i == len(players) - 1:
                    end_idx = len(deck)
                player.hand = deck[start_idx:end_idx]
                player.hand_count = len(player.hand)
                player.passed = False
            starter = None
            for player in players:
                if '3D' in player.hand:
                    starter = player.id
                    break
            room.turn = starter
            room.phase = 'play'
            room.current_rank = None
            room.current_count = None
            room.inversion_active = False
            room.version += 1
            room.game_log.append(f"Game started! {room.players[starter].name} goes first (has 3♦)")
            return True, "Game started!"
    
    def validate_play(self, room: RoomState, player_id: str, card_ids: List[str]) -> Tuple[bool, str, Optional[dict]]:
        player = room.players.get(player_id)
        if not player:
            return False, "Player not found", None
        if room.turn != player_id:
            return False, "Not your turn", None
        for card_id in card_ids:
            if card_id not in player.hand:
                return False, f"You don't own {card_id}", None
        ranks = [parse_card(c)[0] for c in card_ids]
        if len(set(ranks)) > 1:
            return False, "All cards must be same rank", None
        play_rank = ranks[0]
        play_count = len(card_ids)
        if room.current_rank is None:
            effect = self._get_effect_type(play_rank)
            return True, "Valid play", {'rank': play_rank, 'count': play_count, 'effect': effect}
        if play_count != room.current_count:
            return False, f"Must play exactly {room.current_count} cards", None
        if not is_higher_rank(play_rank, room.current_rank, room.inversion_active):
            return False, f"Must play higher than {room.current_rank}", None
        if room.inversion_active and room.current_rank == 'J':
            pre_jack_ranks = [3,4,5,6,7,8,9,10]
            if play_rank not in pre_jack_ranks:
                return False, "After Jack inversion, only lower ranks (3-10) allowed", None
        effect = self._get_effect_type(play_rank)
        return True, "Valid play", {'rank': play_rank, 'count': play_count, 'effect': effect}

    def _get_effect_type(self, rank) -> Optional[str]:
        if rank == 7: return 'seven_gift'
        if rank == 8: return 'eight_reset'
        if rank == 10: return 'ten_discard'
        if rank == 'J': return 'jack_inversion'
        return None

    def play_cards(self, room_id: str, player_id: str, card_ids: List[str]) -> Tuple[bool, str]:
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            valid, message, pattern = self.validate_play(room, player_id, card_ids)
            if not valid:
                return False, message
            player = room.players[player_id]
            for card_id in card_ids:
                player.hand.remove(card_id)
            player.hand_count = len(player.hand)
            
            # Add cards to current pile
            room.current_pile = card_ids.copy()
            room.current_rank = pattern['rank']
            room.current_count = pattern['count']
            room.last_play = {'player_id': player_id, 'player_name': player.name, 'cards': card_ids, 'rank': pattern['rank'], 'count': pattern['count']}
            for p in room.players.values(): p.passed = False
            
            # Check for automatic round win (2, JOKER, or 3 during inversion)
            auto_win = False
            # Auto-win only if playing the absolute highest rank
            if not room.inversion_active and (pattern['rank'] == 2 or pattern['rank'] == 'JOKER'):
                auto_win = True
                room.game_log.append(f"{player.name} played {pattern['rank']} - automatic round win!")
            elif room.inversion_active and pattern['rank'] == 3:
                auto_win = True
                room.game_log.append(f"{player.name} played 3 during inversion - automatic round win!")
            
            if auto_win:
                # Move current pile to discard
                room.discard.extend(room.current_pile)
                room.current_pile = []
                room.current_rank = None
                room.current_count = None
                room.inversion_active = False
                # Same player starts next round
                for p in room.players.values(): p.passed = False
                room.version += 1
                room.game_log.append(f"{player.name} starts new round after auto-win")
                return True, "Auto-win! New round started"
            
            effect_applied = False
            if pattern['effect']:
                effect_applied = self._apply_effect(room, player_id, pattern['effect'], pattern['count'])
            if len(player.hand) == 0:
                if player_id not in room.finished_order:
                    room.finished_order.append(player_id)
                    room.game_log.append(f"{player.name} finished in position {len(room.finished_order)}!")
                if len(room.finished_order) == len(room.players) - 1:
                    self._end_game(room)
            if not effect_applied or pattern['effect'] == 'eight_reset':
                if pattern['effect'] == 'eight_reset':
                    # Move current pile to discard before reset
                    room.discard.extend(room.current_pile)
                    room.current_pile = []
                    room.current_rank = None
                    room.current_count = None
                    room.inversion_active = False
                    room.game_log.append(f"{player.name} played {pattern['count']} 8s - pile cleared!")
                else:
                    self._advance_turn(room)
            room.version += 1
            room.game_log.append(f"{player.name} played: {', '.join([self._format_card(c) for c in card_ids])}")
            return True, "Cards played successfully"

    def _apply_effect(self, room: RoomState, player_id: str, effect: str, count: int) -> bool:
        if effect == 'seven_gift':
            room.pending_gift = {'player_id': player_id, 'remaining': count}
            room.game_log.append(f"{room.players[player_id].name} must gift {count} cards!")
            return True
        if effect == 'eight_reset': return False
        if effect == 'ten_discard':
            room.pending_discard = {'player_id': player_id, 'remaining': count}
            room.game_log.append(f"{room.players[player_id].name} must discard {count} cards!")
            return True
        if effect == 'jack_inversion':
            room.inversion_active = True
            room.game_log.append("Rank order inverted! Lower ranks now beat higher ranks!")
            return False
        return False

    def _advance_turn_if_no_pending(self, room: RoomState):
        """Only advance turn if no pending effects"""
        if not room.pending_gift and not room.pending_discard:
            self._advance_turn(room)

    def _advance_turn(self, room: RoomState):
        players = sorted(room.players.values(), key=lambda p: p.seat)
        idx = next(i for i,p in enumerate(players) if p.id == room.turn)
        for i in range(1, len(players)):
            nxt = players[(idx + i) % len(players)]
            if nxt.hand and not nxt.passed:
                room.turn = nxt.id
                return

    def pass_turn(self, room_id: str, player_id: str) -> Tuple[bool, str]:
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room: return False, "Room not found"
            if room.turn != player_id: return False, "Not your turn"
            player = room.players[player_id]
            player.passed = True
            room.game_log.append(f"{player.name} passed")
            active = [p for p in room.players.values() if p.hand and not p.passed]
            if len(active) <= 1:
                # Move current pile to discard when round ends
                room.discard.extend(room.current_pile)
                room.current_pile = []
                room.current_rank = None
                room.current_count = None
                room.inversion_active = False
                if room.last_play:
                    room.turn = room.last_play['player_id']
                    room.game_log.append(f"{room.players[room.turn].name} starts new round")
                for p in room.players.values(): p.passed = False
            else:
                self._advance_turn(room)
            room.version += 1
            return True, "Passed"

    def _end_game(self, room: RoomState):
        for p in room.players.values():
            if p.id not in room.finished_order and p.hand:
                room.finished_order.append(p.id)
        roles = ['President','Vice President','Citizen','Scumbag','Asshole']
        n = len(room.players)
        if n == 3: 
            roles = ['President','Vice President','Asshole']
        elif n == 4: 
            roles = ['President','Vice President','Scumbag','Asshole']
        else:  # 5 players
            roles = ['President','Vice President','Citizen','Scumbag','Asshole']
        for i, pid in enumerate(room.finished_order):
            if i < len(roles): room.players[pid].role = roles[i]
        room.phase = 'finished'
        room.game_log.append("Game finished!")
        for i, pid in enumerate(room.finished_order):
            p = room.players[pid]
            room.game_log.append(f"{i+1}. {p.name} - {p.role}")

    def _format_card(self, card_id: str) -> str:
        rank, suit = parse_card(card_id)
        suit_symbols = {'S':'♠','H':'♥','D':'♦','C':'♣'}
        if rank == 'JOKER': return '🃏'
        return f"{rank}{suit_symbols.get(suit,'')}"

    def _get_card_color(self, card_id: str) -> str:
        rank, suit = parse_card(card_id)
        if suit in ['H', 'D']: return 'red'
        elif suit in ['S', 'C']: return 'black'
        return 'purple'  # JOKER

def create_card_element(card_id: str, size='normal', selectable=False, selected=False):
    rank, suit = parse_card(card_id)
    suit_symbols = {'S':'♠','H':'♥','D':'♦','C':'♣'}
    
    if rank == 'JOKER':
        display_text = '🃏'
        color_class = 'joker'
    else:
        display_text = f"{rank}"
        suit_symbol = suit_symbols.get(suit, '')
        color_class = 'red' if suit in ['H', 'D'] else 'black'
    
    card_style = {
        'border': '2px solid #333',
        'borderRadius': '12px',
        'backgroundColor': 'white',
        'padding': '8px',
        'margin': '4px',
        'display': 'inline-block',
        'textAlign': 'center',
        'minWidth': '50px' if size == 'small' else '70px' if size == 'normal' else '90px',
        'minHeight': '70px' if size == 'small' else '100px' if size == 'normal' else '130px',
        'fontSize': '12px' if size == 'small' else '16px' if size == 'normal' else '24px',
        'fontWeight': 'bold',
        'cursor': 'pointer' if selectable else 'default',
        'boxShadow': '0 4px 8px rgba(0,0,0,0.1)',
        'position': 'relative',
        'transition': 'all 0.2s ease',
        'transform': 'scale(1)'
    }
    
    if selected:
        card_style['backgroundColor'] = '#e8f5e8'
        card_style['border'] = '3px solid #4caf50'
        card_style['boxShadow'] = '0 0 20px rgba(76, 175, 80, 0.6)'
        card_style['transform'] = 'scale(1.05) translateY(-5px)'
        
    # Hover effect for selectable cards
    hover_class = 'card-hover' if selectable else ''
    
    if color_class == 'red':
        card_style['color'] = '#d32f2f'
    elif color_class == 'black':
        card_style['color'] = '#000'
    else:  # joker
        card_style['color'] = '#9c27b0'
    
    content = []
    if rank != 'JOKER':
        # Top left corner
        content.append(html.Div([
            html.Div(str(rank), style={'fontSize': '0.8em', 'lineHeight': '1'}),
            html.Div(suit_symbols.get(suit, ''), style={'fontSize': '0.8em', 'lineHeight': '1'})
        ], style={'position': 'absolute', 'top': '6px', 'left': '6px'}))
        
        # Center
        content.append(html.Div([
            html.Div(str(rank), style={'fontSize': '1.2em' if size != 'large' else '1.8em'}),
            html.Div(suit_symbols.get(suit, ''), style={'fontSize': '1.5em' if size != 'large' else '2.2em'})
        ], style={'position': 'absolute', 'top': '50%', 'left': '50%', 'transform': 'translate(-50%, -50%)'}))
        
        # Bottom right corner (upside down)
        content.append(html.Div([
            html.Div(str(rank), style={'fontSize': '0.8em', 'lineHeight': '1'}),
            html.Div(suit_symbols.get(suit, ''), style={'fontSize': '0.8em', 'lineHeight': '1'})
        ], style={'position': 'absolute', 'bottom': '6px', 'right': '6px', 'transform': 'rotate(180deg)'}))
    else:
        # Joker center
        content.append(html.Div('🃏', style={
            'position': 'absolute', 
            'top': '50%', 
            'left': '50%', 
            'transform': 'translate(-50%, -50%)',
            'fontSize': '2em' if size != 'large' else '3em'
        }))
    
    if selectable:
        return dbc.Button(
            content,
            id={'type':'card-btn','card':card_id},
            style=card_style,
            className=f'p-0 {hover_class}',
            color='light' if not selected else 'success'
        )
    else:
        return html.Div(content, style=card_style)

# ===================== BOT LOGIC =====================
class GreedyBot:
    def __init__(self, engine: PresidentEngine): self.engine = engine
    def make_move(self, room_id: str, player_id: str):
        room = self.engine.get_room(room_id)
        if not room or room.turn != player_id: return
        if room.pending_gift and room.pending_gift['player_id'] == player_id:
            self._handle_gift(room_id, player_id, room.pending_gift['remaining']); return
        if room.pending_discard and room.pending_discard['player_id'] == player_id:
            self._handle_discard(room_id, player_id, room.pending_discard['remaining']); return
        player = room.players[player_id]
        plays = self._get_possible_plays(room, player)
        if plays:
            best = max(plays, key=len)
            self.engine.play_cards(room_id, player_id, best)
        else:
            self.engine.pass_turn(room_id, player_id)
    def _get_possible_plays(self, room: RoomState, player: Player) -> List[List[str]]:
        groups = defaultdict(list)
        for c in player.hand:
            r,_ = parse_card(c); groups[r].append(c)
        res=[]
        for rank, cards in groups.items():
            for cnt in range(1, len(cards)+1):
                play = cards[:cnt]
                valid,_,_ = self.engine.validate_play(room, player.id, play)
                if valid: res.append(play)
        return res
    def _handle_gift(self, room_id: str, player_id: str, rem: int):
        room = self.engine.get_room(room_id)
        if not room:
            return
        player = room.players[player_id]
        to_gift = player.hand[:rem] if len(player.hand) >= rem else player.hand.copy()
        
        for card in to_gift:
            player.hand.remove(card)
        player.hand_count = len(player.hand)
        
        room.pending_gift = None
        room.version += 1
        room.game_log.append(f"{player.name} gifted {len(to_gift)} cards")
        self.engine._advance_turn_if_no_pending(room)
        
    def _handle_discard(self, room_id: str, player_id: str, rem: int):
        room = self.engine.get_room(room_id)
        if not room:
            return
        player = room.players[player_id]
        to_discard = player.hand[:rem] if len(player.hand) >= rem else player.hand.copy()
        
        for card in to_discard:
            player.hand.remove(card)
            room.discard.append(card)
        player.hand_count = len(player.hand)
        
        room.pending_discard = None
        room.version += 1
        room.game_log.append(f"{player.name} discarded {len(to_discard)} cards")
        self.engine._advance_turn_if_no_pending(room)

# ===================== DASH APP =====================
engine = PresidentEngine()
bot = GreedyBot(engine)

def bot_manager(room_id):
    while True:
        room = engine.get_room(room_id)
        if not room or room.phase != 'play': break
        for p in list(room.players.values()):
            if p.is_bot and room.turn == p.id:
                time.sleep(random.uniform(0.3,0.7))
                bot.make_move(room_id, p.id)
        time.sleep(0.5)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "President Card Game"

# ===================== LAYOUTS =====================

def create_mode_select_layout():
    return dbc.Container([
        html.H2("President Card Game"),
        html.Hr(),
        dbc.Row([
            dbc.Col([
                dbc.Button("Singleplayer (vs Bots)", id="singleplayer-btn", color="primary", size="lg", className="me-3"),
                dbc.Button("Multiplayer (coming soon)", id="multiplayer-btn", color="secondary", size="lg", disabled=True),
            ], width="auto")
        ], justify="center", className="mb-4"),
        html.Div(id="mode-info")
    ], fluid=True)

def create_main_layout():
    return dbc.Container([
        dcc.Store(id='current-room', data=None),
        dcc.Store(id='current-player', data=None),
        dcc.Store(id='selected-cards', data=[]),
        dcc.Interval(id='game-updater', interval=1000, n_intervals=0),
        html.Div(id='game-content')
    ], fluid=True)


def create_game_layout(room: RoomState, pid: str):
    p = room.players.get(pid)
    if not p: return html.Div("Error: Player not found")
    
    # Game info card
    info = dbc.Card([
        dbc.CardHeader(html.H4("Game Info", className='text-center mb-0')),
        dbc.CardBody([
            html.P([html.Strong("Turn: "), (room.players[room.turn].name) if room.turn and room.turn in room.players else 'None'], className='mb-2'),
            html.P([html.Strong("Current: "), f"{room.current_count or 0} × {room.current_rank or 'None'}"], className='mb-2'),
            html.P([html.Strong("Inversion: "), html.Span('YES', className='text-danger') if room.inversion_active else html.Span('NO', className='text-success')], className='mb-0'),
        ])
    ], className='mb-3', style={'background': 'rgba(255,255,255,0.95)', 'border': 'none', 'borderRadius': '15px', 'boxShadow': '0 8px 32px rgba(0,0,0,0.1)'})
    
    # Current pile display - CENTER AND ENLARGED
    pile_cards = []
    if room.current_pile:
        for card in room.current_pile:
            pile_cards.append(create_card_element(card, size='large'))
    
    pile_display = dbc.Card([
        dbc.CardHeader(html.H3("🎯 Current Pile", className='text-center mb-0')),
        dbc.CardBody([
            html.Div(
                pile_cards if pile_cards else [html.H4("🃏 Empty", className='text-muted')], 
                className='text-center',
                style={'minHeight': '160px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'flexWrap': 'wrap', 'background': 'linear-gradient(45deg, #f8f9fa, #e9ecef)', 'borderRadius': '10px', 'border': '2px dashed #dee2e6'}
            ),
            html.P(f"🗑️ Discard pile: {len(room.discard)} cards", className='text-muted text-center mt-3 mb-0')
        ])
    ], className='mb-3', style={'background': 'rgba(255,255,255,0.95)', 'border': 'none', 'borderRadius': '15px', 'boxShadow': '0 8px 32px rgba(0,0,0,0.1)'})
    
    # Players table
    table_data = {
        'Player':[pl.name+(' (Bot)' if pl.is_bot else '') for pl in sorted(room.players.values(), key=lambda x:x.seat)],
        'Role':[pl.role or '-' for pl in sorted(room.players.values(), key=lambda x:x.seat)],
        'Cards':[pl.hand_count for pl in sorted(room.players.values(), key=lambda x:x.seat)],
        'Passed':['✓' if pl.passed else '' for pl in sorted(room.players.values(), key=lambda x:x.seat)],
        'Turn':['▶' if room.turn==pl.id else '' for pl in sorted(room.players.values(), key=lambda x:x.seat)]
    }
    table = dbc.Table.from_dataframe(pd.DataFrame(table_data), striped=True, bordered=True, size='sm')
    
    # Player's hand - BETTER CARD DISPLAY
    hand = []
    if room.phase != 'finished' and p.hand:
        groups=defaultdict(list)
        for c in p.hand: 
            groups[parse_card(c)[0]].append(c)
        for rank in sorted(groups.keys(), key=lambda r:NORMAL_ORDER.index(r) if r in NORMAL_ORDER else 999):
            for c in sorted(groups[rank]):
                hand.append(create_card_element(c, size='normal', selectable=True))
    
    # Action buttons and special prompts
    actions = []
    special_prompt = []
    
    if room.phase == 'finished':
        # Game finished - show results and restart option
        role_colors = {
            'President': 'success',
            'Vice President': 'info', 
            'Citizen': 'secondary',
            'Scumbag': 'warning',
            'Asshole': 'danger'
        }
        special_prompt = [
            html.Div([
                html.H3("🎉 Game Finished!", className="text-center text-success mb-3"),
                dbc.Alert([
                    html.H5(f"You are: {p.role}", className='mb-0')
                ], color=role_colors.get(p.role, 'secondary'), className='text-center'),
                html.Div([
                    html.H6("Final Rankings:", className='text-center mb-2'),
                    html.Ol([
                        html.Li([
                            f"{room.players[pid].name} - ",
                            html.Span(room.players[pid].role, 
                                className=f'badge bg-{role_colors.get(room.players[pid].role, "secondary")}')
                        ]) for pid in room.finished_order if pid in room.players
                    ])
                ], className='mb-3'),
                dbc.Button('New Game', id={'type': 'action-btn', 'action': 'restart'}, color='success', className='mt-2'),
            ], className='mb-3')
        ]
    elif room.pending_gift and room.pending_gift['player_id'] == pid:
        special_prompt = [
            dbc.Alert([
                html.H5(f"🎁 Gift {room.pending_gift['remaining']} cards!", className="mb-2"),
                html.P("Select cards from your hand and click Gift", className='mb-2'),
                dbc.Button('Gift Selected Cards', id={'type': 'game-btn', 'action': 'gift'}, color='warning', className='me-2'),
            ], color='warning', className='mb-3')
        ]
    elif room.pending_discard and room.pending_discard['player_id'] == pid:
        special_prompt = [
            dbc.Alert([
                html.H5(f"🗑️ Discard {room.pending_discard['remaining']} cards!", className="mb-2"),
                html.P("Select cards from your hand and click Discard", className='mb-2'),
                dbc.Button('Discard Selected Cards', id={'type': 'game-btn', 'action': 'discard'}, color='warning', className='me-2'),
            ], color='danger', className='mb-3')
        ]
    elif room.turn==pid and room.phase=='play':
        actions=[
            dbc.ButtonGroup([
                dbc.Button('🎯 Play Cards', id={'type': 'game-btn', 'action': 'play'}, color='primary', disabled=True),
                dbc.Button('⏭️ Pass', id={'type': 'game-btn', 'action': 'pass'}, color='secondary')
            ], className='d-grid')
        ]
    
    # Game log
    log = html.Div([
        html.P(e, className='mb-1 p-2 bg-light rounded') for e in room.game_log[-8:]
    ], style={'height':'200px','overflowY':'auto', 'border': '1px solid #dee2e6', 'borderRadius': '8px', 'padding': '8px'})
    
    return html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    info, 
                    dbc.Card([
                        dbc.CardHeader(html.H5('👥 Players', className='mb-0')), 
                        dbc.CardBody(table)
                    ], className='mb-3', style={'background': 'rgba(255,255,255,0.95)', 'border': 'none', 'borderRadius': '15px', 'boxShadow': '0 8px 32px rgba(0,0,0,0.1)'}), 
                    dbc.Card([
                        dbc.CardHeader(html.H5('📜 Game Log', className='mb-0')), 
                        dbc.CardBody(log)
                    ], style={'background': 'rgba(255,255,255,0.95)', 'border': 'none', 'borderRadius': '15px', 'boxShadow': '0 8px 32px rgba(0,0,0,0.1)'})
                ], width=3),
                dbc.Col([
                    pile_display,
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5(f'🃏 {p.name}\'s Hand', className='mb-0')), 
                        dbc.CardBody([
                            html.Div(special_prompt),
                            html.Div(hand, className='mb-3', style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'center', 'gap': '4px'}) if hand else html.Div("🚫 No cards", className='mb-3 text-center text-muted'), 
                            html.Div(actions, className='text-center')
                        ])
                    ], style={'background': 'rgba(255,255,255,0.95)', 'border': 'none', 'borderRadius': '15px', 'boxShadow': '0 8px 32px rgba(0,0,0,0.1)'})
                ], width=3)
            ])
        ], fluid=True)
    ], style={'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 'minHeight': '100vh', 'padding': '20px'})

app.layout = create_main_layout()

# ===================== CALLBACKS =====================

@app.callback(
    Output('game-content','children'),
    Input('game-updater','n_intervals'),
    State('current-room','data'),
    State('current-player','data')
)
def update_game_display(n_int, cur_room, cur_player):
    if cur_room and cur_player:
        room = engine.get_room(cur_room)
        if not room:
            return create_mode_select_layout()
        if cur_player not in room.players:
            return html.Div("Error: Player not found. Please restart the game.")
        if room.phase=='lobby':
            return create_mode_select_layout()
        else:
            return create_game_layout(room, cur_player)
    return create_mode_select_layout()

@app.callback(
    Output('current-room','data'),
    Output('current-player','data'),
    Output('mode-info','children'),
    Input('singleplayer-btn', 'n_clicks'),
    prevent_initial_call=True
)
def start_singleplayer(n_single):
    if n_single:
        # Use a unique room id for each session
        rid = f'singleplayer_{uuid.uuid4().hex[:8]}'
        engine.create_room(rid)
        ok, pid = engine.add_player(rid, "You")
        for i in range(3):
            engine.add_player(rid, f"Bot_{i+1}", True)
        engine.start_game(rid)
        threading.Thread(target=bot_manager, args=(rid,), daemon=True).start()
        return rid, pid, None
    return dash.no_update, dash.no_update, dash.no_update

@app.callback(
    Output('selected-cards','data'),
    Output({'type':'card-btn','card':ALL},'color'),
    Input({'type':'card-btn','card':ALL},'n_clicks'),
    Input({'type': 'game-btn', 'action': ALL},'n_clicks'),
    State('selected-cards','data'),
    State({'type':'card-btn','card':ALL},'id'),
    State('current-room','data'),
    State('current-player','data'),
    prevent_initial_call=True
)
def handle_all_card_actions(card_clicks, game_btn_clicks, selected, ids, rid, pid):
    ctx = callback_context
    if not ctx.triggered:
        return selected or [], [('success' if (ids and selected and id['card'] in selected) else 'light') for id in (ids or [])]
    
    trig = ctx.triggered[0]['prop_id']
    
    # Handle card selection
    if 'card-btn' in trig:
        tid = json.loads(trig.split('.')[0])
        card = tid['card']
        if not selected: selected = []
        if card in selected:
            selected = [c for c in selected if c != card]
        else:
            selected = selected + [card]
        colors = [('success' if id['card'] in selected else 'light') for id in ids]
        return selected, colors
    
    # Handle action buttons - all clear selection after action
    elif 'play' in trig and selected and rid and pid:
        engine.play_cards(rid, pid, selected)
        return [], ['light' for id in ids]
        
    elif 'pass' in trig and rid and pid:
        engine.pass_turn(rid, pid)
        return [], ['light' for id in ids]
        
    elif 'gift' in trig and selected and rid and pid:
        room = engine.get_room(rid)
        if room and room.pending_gift and room.pending_gift['player_id'] == pid:
            required = room.pending_gift['remaining']
            if len(selected) < required:
                return selected, [('success' if id['card'] in selected else 'light') for id in ids]  # Don't process if not enough cards
            to_gift = selected[:required]
            player = room.players[pid]
            for card in to_gift:
                if card in player.hand:
                    player.hand.remove(card)
            player.hand_count = len(player.hand)
            room.pending_gift = None
            room.version += 1
            room.game_log.append(f"{player.name} gifted {len(to_gift)} cards")
            engine._advance_turn_if_no_pending(room)
        return [], ['light' for id in ids]
        
    elif 'discard' in trig and selected and rid and pid:
        room = engine.get_room(rid)
        if room and room.pending_discard and room.pending_discard['player_id'] == pid:
            required = room.pending_discard['remaining']
            if len(selected) != required:
                return selected, [('success' if id['card'] in selected else 'light') for id in ids]  # Must select exactly the required number
            to_discard = selected
            player = room.players[pid]
            for card in to_discard:
                if card in player.hand:
                    player.hand.remove(card)
                    room.discard.append(card)
            player.hand_count = len(player.hand)
            room.pending_discard = None
            room.version += 1
            room.game_log.append(f"{player.name} discarded {len(to_discard)} cards")
            engine._advance_turn_if_no_pending(room)
        return [], ['light' for id in ids]
    
    return selected or [], [('success' if (ids and selected and id['card'] in selected) else 'light') for id in (ids or [])]

@app.callback(
    Output({'type': 'game-btn', 'action': 'play'},'disabled'),
    Input('selected-cards','data'),
    prevent_initial_call=False
)
def update_play_button(selected):
    try:
        if selected is None:
            return True
        return len(selected) == 0
    except:
        return no_update

# ===================== RUN SERVER =====================
if __name__=='__main__':
    app.run(debug=True)
