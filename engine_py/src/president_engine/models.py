"""Game models and data structures"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Union

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
    round_history: List[dict] = field(default_factory=list)  # History of plays in current round
    completed_rounds: List[dict] = field(default_factory=list)  # Complete history of all finished rounds
    finished_order: List[str] = field(default_factory=list)
    pending_gift: Optional[dict] = None
    pending_discard: Optional[dict] = None
    last_play: Optional[dict] = None
    game_log: List[str] = field(default_factory=list)
    first_game: bool = True # Add this field
    last_round_winner: Optional[str] = None # Add this field
    first_game_first_play_done: bool = False # Add this field
    global_asshole_id: Optional[str] = None # Add this field
    # Card exchange phase
    pending_exchange: Optional[dict] = None  # Exchange phase data
    exchange_phase: bool = False  # Whether we're in exchange phase
    # Role tracking for current and previous game
    current_game_roles: Dict[str, str] = field(default_factory=dict)
    previous_game_roles: Dict[str, str] = field(default_factory=dict) 