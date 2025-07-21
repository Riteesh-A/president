# engine_py/src/president_engine/engine.py

from typing import List, Optional
from .models import RoomState
from .errors import raise_error, NOT_YOUR_TURN, ALREADY_PASSED
from .validate import validate_play
from .constants import (
    EFFECT_EIGHT_RESET,
    EFFECT_TEN_DISCARD,
    EFFECT_JACK_INVERSION,
)

def _get_next_player_id(state: RoomState, start_player_id: str) -> Optional[str]:
    """
    Finds the next active player in the turn order.

    Skips players who have passed or have no cards left.
    Returns None if no other active players are found.
    """
    start_index = state.player_order.index(start_player_id)
    num_players = len(state.player_order)

    for i in range(1, num_players):
        next_index = (start_index + i) % num_players
        next_player_id = state.player_order[next_index]
        next_player = state.players[next_player_id]
        
        # An active player is one who has not finished and has not passed
        if len(next_player.hand) > 0 and not next_player.passed:
            return next_player_id
            
    return None # No other active players found

def _reset_round(state: RoomState):
    """Resets the state for a new round of plays."""
    state.current_play_pattern = None
    state.inversion_active = False # Inversion ends when the round ends
    for player in state.players.values():
        player.passed = False

def play_cards(state: RoomState, player_id: str, card_ids: List[str]):
    """
    Processes a player's attempt to play cards.
    This function validates the play and mutates the game state.
    """
    if state.turn != player_id:
        raise_error(NOT_YOUR_TURN, "It is not your turn to play.")

    player = state.players[player_id]
    if player.passed:
        raise_error(ALREADY_PASSED, "You have already passed for this round.")

    # 1. Validate the play. This will raise GameError on failure.
    validation_result = validate_play(state, player_id, card_ids)

    # 2. If validation succeeds, mutate the state.
    state.version += 1
    
    # Remove cards from player's hand and add to discard pile
    for card in card_ids:
        player.hand.remove(card)
    state.discard_pile.extend(card_ids)

    # Reset pass status for all players since a valid play was made
    for p in state.players.values():
        p.passed = False

    state.last_player_to_play = player_id
    state.current_play_pattern = validation_result['pattern']
    
    # 3. Handle immediate effects of the play
    effect = validation_result['effect']
    if effect == EFFECT_EIGHT_RESET:
        # The same player starts a new round immediately
        _reset_round(state)
        state.turn = player_id
    elif effect == EFFECT_TEN_DISCARD:
        # The next player starts a new round over a cleared pile
        # Note: We will handle the pending discard selection later.
        _reset_round(state)
        state.turn = _get_next_player_id(state, player_id)
    elif effect == EFFECT_JACK_INVERSION:
        # Invert the rank ordering for the rest of the round
        state.inversion_active = True
        state.turn = _get_next_player_id(state, player_id)
    else:
        # Standard play, turn proceeds to the next active player
        state.turn = _get_next_player_id(state, player_id)

    # If no one else can play, the current player starts a new round
    if state.turn is None:
        _reset_round(state)
        state.turn = state.last_player_to_play


def pass_turn(state: RoomState, player_id: str):
    """Processes a player's decision to pass their turn."""
    if state.turn != player_id:
        raise_error(NOT_YOUR_TURN, "It's not your turn to pass.")

    state.version += 1
    state.players[player_id].passed = True

    next_player_id = _get_next_player_id(state, player_id)

    if next_player_id is None:
        # All other active players have passed. The round ends.
        # The last person to play cards starts the new round.
        _reset_round(state)
        state.turn = state.last_player_to_play
    else:
        # The turn simply moves to the next active player.
        state.turn = next_player_id