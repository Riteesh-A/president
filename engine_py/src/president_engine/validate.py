# engine_py/src/president_engine/validate.py

from typing import List, Dict, Union, Tuple
import re
from .models import RoomState, Player
from .errors import raise_error, OWNERSHIP_MISMATCH, PATTERN_MISMATCH, RANK_TOO_LOW, ACTION_NOT_ALLOWED
from .constants import (
    JOKER_RANK,
    SEVEN_GIFT_RANK,
    EIGHT_RESET_RANK,
    TEN_DISCARD_RANK,
    JACK_INVERSION_RANK,
    EFFECT_SEVEN_GIFT,
    EFFECT_EIGHT_RESET,
    EFFECT_TEN_DISCARD,
    EFFECT_JACK_INVERSION,
)
from .comparator import is_higher

def _get_rank_from_card(card: str) -> str:
    """Helper to extract the rank from a card string (e.g., 'KH' -> 'K', '10S' -> 10, 'JOKERa' -> 'JOKER')."""
    if card.startswith(JOKER_RANK):
        return JOKER_RANK
    # Use regex to find the rank part of the card string
    match = re.match(r'(\d+|[JQKA])', card)
    if not match:
        raise ValueError(f"Invalid card format: {card}")
    rank_str = match.group(1)
    return int(rank_str) if rank_str.isdigit() else rank_str


def validate_play(state: RoomState, player_id: str, card_ids: List[str]) -> Dict:
    """
    Validates if a player's move is legal based on the current game state.

    This checks for card ownership, pattern validity (all cards same rank),
    and whether the play is higher than the current pile.

    Args:
        state: The current RoomState of the game.
        player_id: The ID of the player attempting the play.
        card_ids: A list of card IDs the player wants to play.

    Returns:
        A dictionary with validation result, pattern, and any triggered effect.
        Example: {'ok': True, 'pattern': {'rank': 'K', 'count': 2}, 'effect': None}

    Raises:
        GameError: If the play is invalid for any reason.
    """
    player = state.players.get(player_id)
    if not card_ids:
        raise_error(PATTERN_MISMATCH, "You must play at least one card.")

    # 1. Check for Card Ownership
    for card in card_ids:
        if card not in player.hand:
            raise_error(OWNERSHIP_MISMATCH, f"You do not own the card: {card}")

    # 2. Check for Pattern Uniformity (all cards must have the same rank)
    # Note: For now, Jokers are treated as their own rank. Wildcard logic will be added later.
    first_rank = _get_rank_from_card(card_ids[0])
    for card in card_ids[1:]:
        if _get_rank_from_card(card) != first_rank:
            raise_error(PATTERN_MISMATCH, "All cards in a play must have the same rank.")
    
    play_count = len(card_ids)
    play_rank = first_rank

    # 3. Compare with the current pile
    current_pattern = state.current_play_pattern
    if current_pattern is None:
        # This is the opening play of a new pile, so it's automatically valid.
        pass
    else:
        # A pile is already active, so we must play on it.
        current_count = current_pattern['count']
        current_rank = current_pattern['rank']

        if play_count != current_count:
            raise_error(PATTERN_MISMATCH, f"You must play {current_count} cards, but you played {play_count}.")

        # Special Rule: After a Jack is played, the next play must be a rank that is
        # normally LOWER than a Jack.
        if current_rank == JACK_INVERSION_RANK and not state.inversion_active:
             if play_rank in ['J', 'Q', 'K', 'A', 2, 'JOKER']:
                 raise_error(RANK_TOO_LOW, "After a Jack, you must play a 10 or lower.")

        # Normal comparison
        if not is_higher(play_rank, current_rank, state.inversion_active):
            raise_error(RANK_TOO_LOW, "Your play must be of a higher rank than the current pile.")

    # 4. Identify any triggered special effects
    effect = None
    if play_rank == SEVEN_GIFT_RANK:
        effect = EFFECT_SEVEN_GIFT
    elif play_rank == EIGHT_RESET_RANK:
        effect = EFFECT_EIGHT_RESET
    elif play_rank == TEN_DISCARD_RANK:
        effect = EFFECT_TEN_DISCARD
    elif play_rank == JACK_INVERSION_RANK:
        effect = EFFECT_JACK_INVERSION

    return {
        'ok': True,
        'pattern': {'rank': play_rank, 'count': play_count},
        'effect': effect
    }