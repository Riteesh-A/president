"""
Base bot interface and utilities.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union

from ..constants import PHASE_PLAY, PHASE_EXCHANGE
from ..models import RoomState


class BotAction:
    """Represents a bot action."""
    
    def __init__(self, action_type: str, **kwargs):
        self.type = action_type
        self.data = kwargs
    
    @classmethod
    def play(cls, cards: List[str]) -> 'BotAction':
        """Create a play action."""
        return cls('play', cards=cards)
    
    @classmethod
    def pass_turn(cls) -> 'BotAction':
        """Create a pass action."""
        return cls('pass')
    
    @classmethod
    def gift_distribution(cls, assignments: List[Dict]) -> 'BotAction':
        """Create a gift distribution action."""
        return cls('gift', assignments=assignments)
    
    @classmethod
    def discard_selection(cls, cards: List[str]) -> 'BotAction':
        """Create a discard selection action."""
        return cls('discard', cards=cards)
    
    @classmethod
    def exchange_return(cls, cards: List[str]) -> 'BotAction':
        """Create an exchange return action."""
        return cls('exchange_return', cards=cards)


class BaseBot(ABC):
    """Abstract base class for bot players."""
    
    def __init__(self, player_id: str):
        self.player_id = player_id
    
    @abstractmethod
    def choose_action(self, state: RoomState) -> Optional[BotAction]:
        """
        Choose an action based on the current game state.
        
        Args:
            state: Current game state (sanitized for this player)
        
        Returns:
            BotAction to take, or None if no action needed
        """
        pass
    
    def get_player_hand(self, state: RoomState) -> List[str]:
        """Get this bot's current hand."""
        player = state.players.get(self.player_id)
        return player.hand if player else []
    
    def get_current_pattern(self, state: RoomState) -> Dict:
        """Get the current pattern on the table."""
        return {
            'rank': state.current_pattern.rank,
            'count': state.current_pattern.count,
            'last_player': state.current_pattern.last_player
        }
    
    def is_my_turn(self, state: RoomState) -> bool:
        """Check if it's this bot's turn."""
        return state.turn == self.player_id
    
    def has_pending_gift(self, state: RoomState) -> bool:
        """Check if this bot has a pending gift to distribute."""
        return (
            state.pending_gift is not None and
            state.pending_gift.player_id == self.player_id
        )
    
    def has_pending_discard(self, state: RoomState) -> bool:
        """Check if this bot has a pending discard to make."""
        return (
            state.pending_discard is not None and
            state.pending_discard.player_id == self.player_id
        )
    
    def has_pending_exchange(self, state: RoomState) -> bool:
        """Check if this bot has a pending exchange return."""
        if state.phase != PHASE_EXCHANGE:
            return False
        
        from ..exchange import get_pending_exchange_actions
        pending_actions = get_pending_exchange_actions(state)
        return self.player_id in pending_actions
    
    def get_valid_plays(self, state: RoomState) -> List[List[str]]:
        """
        Get all valid plays this bot can make.
        
        Args:
            state: Current game state
        
        Returns:
            List of valid card combinations that can be played
        """
        hand = self.get_player_hand(state)
        if not hand:
            return []
        
        current_pattern = self.get_current_pattern(state)
        current_rank = current_pattern['rank']
        current_count = current_pattern['count']
        
        # Group cards by rank
        from ..comparator import extract_rank_from_card
        from ..validate import validate_play
        
        rank_groups = {}
        for card in hand:
            rank = extract_rank_from_card(card)
            if rank not in rank_groups:
                rank_groups[rank] = []
            rank_groups[rank].append(card)
        
        valid_plays = []
        
        # If no current pattern, any group can be played
        if current_rank is None:
            # Opening play - must include 3s
            if 3 in rank_groups:
                for count in range(1, len(rank_groups[3]) + 1):
                    cards = rank_groups[3][:count]
                    valid_plays.append(cards)
        else:
            # Must match count and be higher rank
            for rank, cards in rank_groups.items():
                if len(cards) >= current_count:
                    # Try playing exactly the required count
                    play_cards = cards[:current_count]
                    
                    # Validate the play
                    validation = validate_play(state, self.player_id, play_cards)
                    if validation.valid:
                        valid_plays.append(play_cards)
        
        return valid_plays
    
    def get_other_players(self, state: RoomState) -> List[str]:
        """Get list of other player IDs."""
        return [pid for pid in state.players.keys() if pid != self.player_id]
    
    def count_cards_in_hand(self, state: RoomState, player_id: str) -> int:
        """Get number of cards in another player's hand."""
        player = state.players.get(player_id)
        return len(player.hand) if player else 0 