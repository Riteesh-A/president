# engine_py/src/president_engine/models.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Union
from .rules import RuleConfig # Will be defined next

# Type alias for Rank, including int for numeric ranks and Literal for face cards/Joker
Rank = Union[int, Literal['J','Q','K','A',2,'JOKER']]

@dataclass
class Player:
    id: str
    name: str
    seat: int # Player's position at the table (0 to N-1)
    role: Optional[str] = None  # e.g., 'President', 'Asshole'
    hand: List[str] = field(default_factory=list)  # list of card IDs (e.g., '3D', 'AS')
    passed: bool = False # Has this player passed in the current turn cycle?
    connected: bool = True # Is the client currently connected?
    is_bot: bool = False

@dataclass
class EffectLogEntry:
    effect: str # Name of the effect, e.g., 'seven_gift'
    data: dict  # Arbitrary data specific to the effect (e.g., player_id, count)
    version: int # The game state version when the effect occurred

@dataclass
class RoomState:
    id: str # Unique ID for the game room
    version: int = 0 # Increments on every state mutation
    phase: str = 'lobby'  # 'lobby'|'dealing'|'exchange'|'play'|'finished'
    players: Dict[str, Player] = field(default_factory=dict) # Keyed by player_id
    player_order: List[str] = field(default_factory=list) # Ordered list of player IDs for turn rotation
    turn: Optional[str] = None # player_id of the current player
    last_player_to_play: Optional[str] = None # player_id of the last person to play cards in a round
    current_play_pattern: Optional[Dict[str, Union[Rank, int]]] = None # {'rank': Rank, 'count': int}
    inversion_active: bool = False # Is rank ordering currently inverted?
    deck: List[str] = field(default_factory=list)  # Cards remaining in the deck
    discard_pile: List[str] = field(default_factory=list) # Cards discarded during play
    finished_order: List[str] = field(default_factory=list) # Player IDs in order of finishing the round
    effects_log: List[EffectLogEntry] = field(default_factory=list) # History of triggered effects
    pending_gift: Optional[Dict[str, Union[int, str]]] = None # {'count': x, 'player_id': 'id'}
    pending_discard: Optional[Dict[str, Union[int, str]]] = None # {'count': x, 'player_id': 'id'}
    rule_config: RuleConfig = field(default_factory=RuleConfig) # Injected post-creation, set to default here