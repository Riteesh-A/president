"""
Exchange phase logic for role-based card exchanges.
"""

import copy
from typing import Dict, List, Optional, Tuple

from .comparator import get_best_cards_for_exchange
from .constants import PHASE_EXCHANGE, PHASE_PLAY, ROLE_PRESIDENT, ROLE_VICE_PRESIDENT, ROLE_SCUMBAG, ROLE_ASSHOLE
from .models import RoomState
from .ranking import get_exchange_pairs


class ExchangeState:
    """Tracks the state of exchange phase."""
    
    def __init__(self, pairs: List[Tuple[str, str, int]]):
        self.pairs = pairs
        self.completed_gives = set()  # Track which gives are completed
        self.completed_returns = set()  # Track which returns are completed
        self.pending_returns = {}  # receiver_id -> count
    
    def is_complete(self) -> bool:
        """Check if all exchanges are complete."""
        return (
            len(self.completed_gives) == len(self.pairs) and
            len(self.completed_returns) == len(self.pairs)
        )
    
    def get_pending_give(self, player_id: str) -> Optional[Tuple[str, int]]:
        """Get pending give for a player."""
        for giver, receiver, count in self.pairs:
            if giver == player_id and (giver, receiver) not in self.completed_gives:
                return receiver, count
        return None
    
    def get_pending_return(self, player_id: str) -> Optional[int]:
        """Get pending return count for a player."""
        return self.pending_returns.get(player_id)
    
    def mark_give_complete(self, giver_id: str, receiver_id: str, count: int):
        """Mark a give as complete and set up return."""
        self.completed_gives.add((giver_id, receiver_id))
        self.pending_returns[receiver_id] = count
    
    def mark_return_complete(self, receiver_id: str):
        """Mark a return as complete."""
        if receiver_id in self.pending_returns:
            del self.pending_returns[receiver_id]
        
        # Find the pair and mark return complete
        for giver, receiver, count in self.pairs:
            if receiver == receiver_id:
                self.completed_returns.add((giver, receiver))
                break


def start_exchange_phase(state: RoomState) -> RoomState:
    """
    Start the exchange phase by identifying pairs and performing automatic gives.
    
    Args:
        state: Current room state after role assignment
    
    Returns:
        Updated state in exchange phase
    """
    new_state = copy.deepcopy(state)
    
    # Set phase
    new_state.phase = PHASE_EXCHANGE
    
    # Get exchange pairs
    pairs = get_exchange_pairs(new_state)
    
    if not pairs:
        # No exchanges needed, go straight to play
        new_state.phase = PHASE_PLAY
        from .ranking import should_player_start_next_round
        new_state.turn = should_player_start_next_round(new_state)
        new_state.increment_version()
        return new_state
    
    # Perform automatic gives (best cards from lower roles)
    exchange_state = ExchangeState(pairs)
    
    for giver_id, receiver_id, count in pairs:
        giver = new_state.players[giver_id]
        receiver = new_state.players[receiver_id]
        
        # Get best cards from giver
        best_cards = get_best_cards_for_exchange(giver.hand, count)
        
        # Transfer cards
        for card in best_cards:
            if card in giver.hand:
                giver.hand.remove(card)
                receiver.hand.append(card)
        
        # Mark give complete
        exchange_state.mark_give_complete(giver_id, receiver_id, count)
        
        # Log the exchange
        new_state.add_effect_log(
            effect="exchange_give",
            data={
                'giver': giver_id,
                'receiver': receiver_id,
                'count': len(best_cards)
            },
            player_id=giver_id
        )
    
    # Store exchange state in effects log for tracking
    new_state.add_effect_log(
        effect="exchange_started",
        data={
            'pairs': [(g, r, c) for g, r, c in pairs],
            'pending_returns': exchange_state.pending_returns.copy()
        }
    )
    
    new_state.increment_version()
    return new_state


def process_exchange_return(
    state: RoomState,
    player_id: str,
    card_ids: List[str]
) -> RoomState:
    """
    Process a return of cards during exchange phase.
    
    Args:
        state: Current room state
        player_id: Player returning cards (President or Vice President)
        card_ids: Cards being returned
    
    Returns:
        Updated state with cards returned
    """
    new_state = copy.deepcopy(state)
    
    # Find the exchange pair for this player
    pairs = get_exchange_pairs(new_state)
    return_pair = None
    
    for giver_id, receiver_id, count in pairs:
        if receiver_id == player_id:
            return_pair = (giver_id, receiver_id, count)
            break
    
    if not return_pair:
        raise ValueError(f"No exchange pair found for player {player_id}")
    
    giver_id, receiver_id, expected_count = return_pair
    
    if len(card_ids) != expected_count:
        raise ValueError(f"Expected {expected_count} cards, got {len(card_ids)}")
    
    # Transfer cards back
    returner = new_state.players[receiver_id]
    receiver = new_state.players[giver_id]
    
    for card_id in card_ids:
        if card_id in returner.hand:
            returner.hand.remove(card_id)
            receiver.hand.append(card_id)
    
    # Log the return
    new_state.add_effect_log(
        effect="exchange_return",
        data={
            'returner': receiver_id,
            'receiver': giver_id,
            'count': len(card_ids)
        },
        player_id=receiver_id
    )
    
    new_state.increment_version()
    return new_state


def check_exchange_complete(state: RoomState) -> bool:
    """
    Check if all exchange returns have been completed.
    
    Args:
        state: Current room state
    
    Returns:
        True if exchange phase is complete
    """
    if state.phase != PHASE_EXCHANGE:
        return True
    
    # Get exchange pairs and check completion
    pairs = get_exchange_pairs(state)
    
    # Count completed returns by looking at effect log
    completed_returns = 0
    for effect in state.effects_log:
        if effect.effect == "exchange_return":
            completed_returns += 1
    
    return completed_returns >= len(pairs)


def complete_exchange_phase(state: RoomState) -> RoomState:
    """
    Complete the exchange phase and transition to play phase.
    
    Args:
        state: Current room state with completed exchanges
    
    Returns:
        Updated state in play phase
    """
    new_state = copy.deepcopy(state)
    
    # Set phase to play
    new_state.phase = PHASE_PLAY
    
    # Determine starting player
    from .ranking import should_player_start_next_round
    new_state.turn = should_player_start_next_round(new_state)
    
    # Log completion
    new_state.add_effect_log(
        effect="exchange_completed",
        data={'starting_player': new_state.turn}
    )
    
    new_state.increment_version()
    return new_state


def get_pending_exchange_actions(state: RoomState) -> Dict[str, Dict]:
    """
    Get pending exchange actions for each player.
    
    Args:
        state: Current room state in exchange phase
    
    Returns:
        Dictionary mapping player_id to pending action info
    """
    if state.phase != PHASE_EXCHANGE:
        return {}
    
    pending_actions = {}
    pairs = get_exchange_pairs(state)
    
    # Count completed returns
    completed_returns = set()
    for effect in state.effects_log:
        if effect.effect == "exchange_return":
            returner = effect.data.get('returner')
            if returner:
                completed_returns.add(returner)
    
    # Check what each player needs to do
    for giver_id, receiver_id, count in pairs:
        if receiver_id not in completed_returns:
            pending_actions[receiver_id] = {
                'action': 'return',
                'count': count,
                'to': giver_id
            }
    
    return pending_actions


def validate_exchange_return(
    state: RoomState,
    player_id: str,
    card_ids: List[str]
) -> Tuple[bool, str]:
    """
    Validate an exchange return attempt.
    
    Args:
        state: Current room state
        player_id: Player attempting the return
        card_ids: Cards being returned
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if state.phase != PHASE_EXCHANGE:
        return False, "Not in exchange phase"
    
    # Check if player has a pending return
    pending_actions = get_pending_exchange_actions(state)
    if player_id not in pending_actions:
        return False, "No pending exchange return for this player"
    
    action = pending_actions[player_id]
    expected_count = action['count']
    
    if len(card_ids) != expected_count:
        return False, f"Must return exactly {expected_count} cards"
    
    # Check ownership
    player = state.players.get(player_id)
    if not player:
        return False, "Player not found"
    
    for card_id in card_ids:
        if card_id not in player.hand:
            return False, f"Player does not own card {card_id}"
    
    # Check for duplicates
    if len(set(card_ids)) != len(card_ids):
        return False, "Cannot return duplicate cards"
    
    return True, "Valid"


def auto_complete_bot_exchanges(state: RoomState) -> RoomState:
    """
    Automatically complete exchange returns for bot players.
    
    Args:
        state: Current room state
    
    Returns:
        Updated state with bot exchanges completed
    """
    new_state = copy.deepcopy(state)
    
    if new_state.phase != PHASE_EXCHANGE:
        return new_state
    
    pending_actions = get_pending_exchange_actions(new_state)
    
    for player_id, action in pending_actions.items():
        player = new_state.players.get(player_id)
        if player and player.is_bot and action['action'] == 'return':
            # Bot automatically returns lowest cards
            count = action['count']
            
            # Sort hand and return lowest cards
            from .shuffle import sort_hand
            sorted_hand = sort_hand(player.hand, inversion=False)
            cards_to_return = sorted_hand[:count]
            
            # Process the return
            new_state = process_exchange_return(new_state, player_id, cards_to_return)
    
    return new_state 