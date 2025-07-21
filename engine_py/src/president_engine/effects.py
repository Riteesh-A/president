"""
Special card effects implementation.
"""

import copy
from typing import Dict, List

from .constants import (
    EFFECT_SEVEN_GIFT, EFFECT_EIGHT_RESET, EFFECT_TEN_DISCARD, 
    EFFECT_JACK_INVERSION, PHASE_PLAY
)
from .models import PendingGift, PendingDiscard, RoomState


def apply_seven_gift(state: RoomState, player_id: str, count: int) -> RoomState:
    """
    Apply Seven Gift effect - player must gift cards to other players.
    
    Args:
        state: Current room state
        player_id: Player who played the sevens
        count: Number of sevens played (number of cards to gift)
    
    Returns:
        Updated state with pending gift set
    """
    new_state = copy.deepcopy(state)
    
    # Set up pending gift
    new_state.pending_gift = PendingGift(
        player_id=player_id,
        remaining=count,
        original_count=count
    )
    
    # Log the effect
    new_state.add_effect_log(
        effect=EFFECT_SEVEN_GIFT,
        data={'count': count, 'player_id': player_id},
        player_id=player_id
    )
    
    new_state.increment_version()
    return new_state


def apply_eight_reset(state: RoomState, player_id: str) -> RoomState:
    """
    Apply Eight Reset effect - clear the pile and same player continues.
    
    Args:
        state: Current room state
        player_id: Player who played the eights
    
    Returns:
        Updated state with pile cleared and same player's turn
    """
    new_state = copy.deepcopy(state)
    
    # Clear the current pattern (pile)
    new_state.current_pattern.rank = None
    new_state.current_pattern.count = None
    new_state.current_pattern.last_player = None
    new_state.current_pattern.cards = []
    
    # Clear inversion if active (round ended)
    new_state.inversion_active = False
    
    # Same player continues (turn stays the same)
    new_state.turn = player_id
    
    # Clear all passes since it's a new round
    new_state.clear_passes()
    
    # Log the effect
    new_state.add_effect_log(
        effect=EFFECT_EIGHT_RESET,
        data={'player_id': player_id},
        player_id=player_id
    )
    
    new_state.increment_version()
    return new_state


def apply_ten_discard(state: RoomState, player_id: str, count: int) -> RoomState:
    """
    Apply Ten Discard effect - player must discard additional cards.
    
    Args:
        state: Current room state
        player_id: Player who played the tens
        count: Number of tens played (number of cards to discard)
    
    Returns:
        Updated state with pending discard set
    """
    new_state = copy.deepcopy(state)
    
    # Set up pending discard
    new_state.pending_discard = PendingDiscard(
        player_id=player_id,
        remaining=count,
        original_count=count
    )
    
    # Log the effect
    new_state.add_effect_log(
        effect=EFFECT_TEN_DISCARD,
        data={'count': count, 'player_id': player_id},
        player_id=player_id
    )
    
    new_state.increment_version()
    return new_state


def apply_jack_inversion(state: RoomState, player_id: str) -> RoomState:
    """
    Apply Jack Inversion effect - invert rank ordering for the remainder of the round.
    
    Args:
        state: Current room state
        player_id: Player who played the jacks
    
    Returns:
        Updated state with inversion active
    """
    new_state = copy.deepcopy(state)
    
    # Activate inversion
    new_state.inversion_active = True
    
    # Log the effect
    new_state.add_effect_log(
        effect=EFFECT_JACK_INVERSION,
        data={'player_id': player_id},
        player_id=player_id
    )
    
    new_state.increment_version()
    return new_state


def complete_gift_distribution(
    state: RoomState, 
    player_id: str, 
    assignments: List[Dict]
) -> RoomState:
    """
    Complete gift distribution by transferring cards.
    
    Args:
        state: Current room state
        player_id: Player giving the gifts
        assignments: List of {to: player_id, cards: [card_ids]}
    
    Returns:
        Updated state with cards transferred and pending gift cleared
    """
    new_state = copy.deepcopy(state)
    
    # Get the gifting player
    gifter = new_state.players[player_id]
    
    # Transfer cards
    for assignment in assignments:
        recipient_id = assignment['to']
        cards = assignment['cards']
        
        # Remove cards from gifter
        for card in cards:
            if card in gifter.hand:
                gifter.hand.remove(card)
        
        # Add cards to recipient
        recipient = new_state.players[recipient_id]
        recipient.hand.extend(cards)
    
    # Clear pending gift
    new_state.pending_gift = None
    
    # Move to next player's turn
    new_state.turn = new_state.get_next_player(player_id)
    
    # Log completion
    new_state.add_effect_log(
        effect="gift_completed",
        data={
            'gifter': player_id,
            'assignments': [
                {'to': a['to'], 'count': len(a['cards'])}
                for a in assignments
            ]
        },
        player_id=player_id
    )
    
    new_state.increment_version()
    return new_state


def complete_discard_selection(
    state: RoomState,
    player_id: str,
    card_ids: List[str]
) -> RoomState:
    """
    Complete discard selection by removing cards from game.
    
    Args:
        state: Current room state
        player_id: Player discarding cards
        card_ids: Cards to discard
    
    Returns:
        Updated state with cards discarded and pending discard cleared
    """
    new_state = copy.deepcopy(state)
    
    # Get the discarding player
    player = new_state.players[player_id]
    
    # Remove cards from player's hand
    for card_id in card_ids:
        if card_id in player.hand:
            player.hand.remove(card_id)
    
    # Add cards to discard pile (removed from game)
    new_state.discard.extend(card_ids)
    
    # Clear the current pattern if pile should be cleared after ten discard
    new_state.current_pattern.rank = None
    new_state.current_pattern.count = None
    new_state.current_pattern.last_player = None
    new_state.current_pattern.cards = []
    
    # Clear all passes for new round
    new_state.clear_passes()
    
    # Clear pending discard
    new_state.pending_discard = None
    
    # Next player starts new round
    new_state.turn = new_state.get_next_player(player_id)
    
    # Log completion
    new_state.add_effect_log(
        effect="discard_completed",
        data={
            'player_id': player_id,
            'count': len(card_ids)
        },
        player_id=player_id
    )
    
    new_state.increment_version()
    return new_state


def check_inversion_termination(state: RoomState, played_rank) -> bool:
    """
    Check if playing a 3 during inversion should terminate the round early.
    
    Args:
        state: Current room state
        played_rank: The rank that was just played
    
    Returns:
        True if the round should terminate early
    """
    # Early termination only happens if:
    # 1. Inversion is active
    # 2. A 3 was played
    # 3. All other players pass
    return (
        state.inversion_active and 
        played_rank == 3
    )


def should_clear_inversion(state: RoomState) -> bool:
    """
    Check if inversion should be cleared (round ended).
    
    Args:
        state: Current room state
    
    Returns:
        True if inversion should be cleared
    """
    # Inversion clears when:
    # 1. Round ends normally (all players pass except one)
    # 2. Eight reset occurs
    # 3. Early termination with 3 during inversion
    
    # Count active players who haven't passed
    active_players = [
        p for p in state.players.values() 
        if len(p.hand) > 0 and p.connected and not p.passed
    ]
    
    # If only one active player hasn't passed, round should end
    return len(active_players) <= 1


def process_effect(state: RoomState, effect: str, player_id: str, count: int = 1) -> RoomState:
    """
    Process a special effect based on the effect type.
    
    Args:
        state: Current room state
        effect: Effect type to process
        player_id: Player who triggered the effect
        count: Number of cards played (for counting effects)
    
    Returns:
        Updated state with effect applied
    """
    if effect == EFFECT_SEVEN_GIFT:
        return apply_seven_gift(state, player_id, count)
    elif effect == EFFECT_EIGHT_RESET:
        return apply_eight_reset(state, player_id)
    elif effect == EFFECT_TEN_DISCARD:
        return apply_ten_discard(state, player_id, count)
    elif effect == EFFECT_JACK_INVERSION:
        return apply_jack_inversion(state, player_id)
    else:
        # No effect to process
        return state


def has_pending_effects(state: RoomState) -> bool:
    """
    Check if there are any pending effects that need to be resolved.
    
    Args:
        state: Current room state
    
    Returns:
        True if there are pending effects
    """
    return state.pending_gift is not None or state.pending_discard is not None 