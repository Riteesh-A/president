"""
Core data models for the President game engine.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .constants import Rank


@dataclass
class Player:
    """Represents a player in the game."""
    id: str
    name: str
    seat: int
    role: Optional[str] = None  # President, VicePresident, Citizen, Scumbag, Asshole
    hand: List[str] = field(default_factory=list)  # card ids
    passed: bool = False
    connected: bool = True
    is_bot: bool = False
    
    def __post_init__(self):
        """Validate player data after initialization."""
        if self.seat < 0:
            raise ValueError("Seat number must be non-negative")
        if not self.id.strip():
            raise ValueError("Player ID cannot be empty")
        if not self.name.strip():
            raise ValueError("Player name cannot be empty")


@dataclass
class EffectLogEntry:
    """Represents an effect that occurred during the game."""
    effect: str
    data: dict
    version: int
    player_id: str = ""
    timestamp: float = 0.0


@dataclass
class PendingGift:
    """Represents a pending gift distribution."""
    player_id: str
    remaining: int
    original_count: int


@dataclass
class PendingDiscard:
    """Represents a pending discard selection."""
    player_id: str
    remaining: int
    original_count: int


@dataclass
class CurrentPattern:
    """Represents the current play pattern on the table."""
    rank: Optional[Rank] = None
    count: Optional[int] = None
    last_player: Optional[str] = None


@dataclass
class RoomState:
    """Main game state container."""
    id: str
    version: int = 0
    phase: str = 'lobby'  # lobby|dealing|exchange|play|finished
    players: Dict[str, Player] = field(default_factory=dict)
    turn: Optional[str] = None
    current_pattern: CurrentPattern = field(default_factory=CurrentPattern)
    inversion_active: bool = False
    deck: List[str] = field(default_factory=list)  # remaining undealt
    discard: List[str] = field(default_factory=list)
    finished_order: List[str] = field(default_factory=list)
    effects_log: List[EffectLogEntry] = field(default_factory=list)
    pending_gift: Optional[PendingGift] = None
    pending_discard: Optional[PendingDiscard] = None
    rule_config: Optional['RuleConfig'] = None  # Forward reference
    last_activity: float = 0.0
    
    @property
    def current_rank(self) -> Optional[Rank]:
        """Get current rank for backward compatibility."""
        return self.current_pattern.rank
    
    @property
    def current_count(self) -> Optional[int]:
        """Get current count for backward compatibility."""
        return self.current_pattern.count
    
    def get_active_players(self) -> List[Player]:
        """Get list of players who still have cards."""
        return [p for p in self.players.values() if len(p.hand) > 0]
    
    def get_connected_players(self) -> List[Player]:
        """Get list of connected players."""
        return [p for p in self.players.values() if p.connected]
    
    def get_player_by_seat(self, seat: int) -> Optional[Player]:
        """Get player by seat number."""
        for player in self.players.values():
            if player.seat == seat:
                return player
        return None
    
    def increment_version(self):
        """Increment version counter for state changes."""
        self.version += 1
    
    def add_effect_log(self, effect: str, data: dict, player_id: str = ""):
        """Add an effect to the log."""
        import time
        entry = EffectLogEntry(
            effect=effect,
            data=data,
            version=self.version,
            player_id=player_id,
            timestamp=time.time()
        )
        self.effects_log.append(entry)
        
        # Keep only last 10 effects to prevent memory growth
        if len(self.effects_log) > 10:
            self.effects_log = self.effects_log[-10:]
    
    def clear_passes(self):
        """Reset all player pass states."""
        for player in self.players.values():
            player.passed = False
    
    def get_next_player(self, current_player_id: str) -> Optional[str]:
        """Get the next player in turn order."""
        if not self.players:
            return None
            
        # Get sorted list of active players by seat
        active_players = [
            p for p in self.players.values() 
            if len(p.hand) > 0 and p.connected
        ]
        active_players.sort(key=lambda p: p.seat)
        
        if not active_players:
            return None
        
        # Find current player index
        current_index = None
        for i, player in enumerate(active_players):
            if player.id == current_player_id:
                current_index = i
                break
        
        if current_index is None:
            # Current player not found, return first active player
            return active_players[0].id
        
        # Return next player (wrap around)
        next_index = (current_index + 1) % len(active_players)
        return active_players[next_index].id


@dataclass
class GameResult:
    """Result of a game action."""
    success: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    state: Optional[RoomState] = None
    effects: List[str] = field(default_factory=list)
    
    @classmethod
    def success_result(cls, state: RoomState, effects: List[str] = None) -> 'GameResult':
        """Create a successful result."""
        return cls(
            success=True,
            state=state,
            effects=effects or []
        )
    
    @classmethod
    def error_result(cls, error_code: str, error_message: str) -> 'GameResult':
        """Create an error result."""
        return cls(
            success=False,
            error_code=error_code,
            error_message=error_message
        ) 