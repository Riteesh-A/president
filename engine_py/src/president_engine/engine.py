# engine_py/src/president_engine/engine.py

from typing import List, Optional, Dict
from .models import RoomState
from .errors import raise_error, NOT_YOUR_TURN, ALREADY_PASSED, EFFECT_PENDING, INVALID_GIFT_DISTRIBUTION, INVALID_DISCARD_SELECTION, OWNERSHIP_MISMATCH
from .validate import validate_play
from .constants import (
    EFFECT_SEVEN_GIFT,
    EFFECT_EIGHT_RESET,
    EFFECT_TEN_DISCARD,
    EFFECT_JACK_INVERSION,
    PHASE_FINISHED, # NEW IMPORT
)
from .effects import apply_seven_gift, apply_ten_discard
# NEW IMPORT:
from .ranking import assign_roles


def _get_next_player_id(state: RoomState, start_player_id: str) -> Optional[str]:
    """Finds the next active player in the turn order."""
    start_index = state.player_order.index(start_player_id)
    num_players = len(state.player_order)

    for i in range(1, num_players):
        next_index = (start_index + i) % num_players
        next_player_id = state.player_order[next_index]
        
        # An active player has cards and is not in the finished list
        if state.players[next_player_id].hand and next_player_id not in state.finished_order:
            # We also skip players who have passed in the current round of plays
            if not state.players[next_player_id].passed:
                return next_player_id
            
    return None

def _reset_round(state: RoomState):
    """Resets the state for a new round of plays."""
    state.current_play_pattern = None
    state.inversion_active = False
    for player in state.players.values():
        player.passed = False

# --- NEW HELPER FUNCTION ---
def _check_for_game_end(state: RoomState):
    """Checks if the game round has concluded and assigns roles if so."""
    # The game ends when all but one player have finished
    if len(state.finished_order) == len(state.players) - 1:
        # Find the last player (the Asshole) and add them to the finish order
        last_player_id = None
        for pid in state.player_order:
            if pid not in state.finished_order:
                last_player_id = pid
                break
        
        if last_player_id:
            state.finished_order.append(last_player_id)

        # The game is over, assign roles and change phase
        state.phase = PHASE_FINISHED
        assign_roles(state)
        state.turn = None # No one's turn when the game is finished


def play_cards(state: RoomState, player_id: str, card_ids: List[str]):
    """Processes a player's attempt to play cards."""
    if state.pending_gift or state.pending_discard:
        raise_error(EFFECT_PENDING, "You must resolve the pending gift/discard before playing.")
        
    if state.turn != player_id:
        raise_error(NOT_YOUR_TURN, "It is not your turn to play.")

    player = state.players[player_id]
    if player.passed:
        raise_error(ALREADY_PASSED, "You have already passed for this round.")

    validation_result = validate_play(state, player_id, card_ids)
    state.version += 1
    
    for card in card_ids:
        player.hand.remove(card)
    state.discard_pile.extend(card_ids)

    # --- NEW LOGIC: CHECK IF PLAYER HAS FINISHED ---
    if not player.hand:
        state.finished_order.append(player_id)
        # Check if this finish ends the entire game
        _check_for_game_end(state)
        # If the game is now over, stop processing the turn
        if state.phase == PHASE_FINISHED:
            return
    # --- END NEW LOGIC ---

    for p in state.players.values():
        p.passed = False

    state.last_player_to_play = player_id
    state.current_play_pattern = validation_result['pattern']
    
    effect = validation_result['effect']
    play_count = validation_result['pattern']['count']

    if effect == EFFECT_SEVEN_GIFT:
        apply_seven_gift(state, player_id, play_count)
    elif effect == EFFECT_EIGHT_RESET:
        _reset_round(state)
        state.turn = player_id
    elif effect == EFFECT_TEN_DISCARD:
        _reset_round(state)
        state.turn = _get_next_player_id(state, player_id)
        apply_ten_discard(state, player_id, play_count)
    elif effect == EFFECT_JACK_INVERSION:
        state.inversion_active = True
        state.turn = _get_next_player_id(state, player_id)
    else:
        state.turn = _get_next_player_id(state, player_id)

    if state.turn is None and not (state.pending_gift or state.pending_discard):
        _reset_round(state)
        state.turn = state.last_player_to_play

# ... (pass_turn and submit_* functions remain the same) ...
def pass_turn(state: RoomState, player_id: str):
    """Processes a player's decision to pass their turn."""
    if state.pending_gift or state.pending_discard:
        raise_error(EFFECT_PENDING, "You must resolve the pending gift/discard before passing.")
        
    if state.turn != player_id:
        raise_error(NOT_YOUR_TURN, "It's not your turn to pass.")

    state.version += 1
    state.players[player_id].passed = True

    next_player_id = _get_next_player_id(state, player_id)

    if next_player_id is None:
        _reset_round(state)
        state.turn = state.last_player_to_play
    else:
        state.turn = next_player_id

def submit_gift_distribution(state: RoomState, player_id: str, assignments: List[Dict[str, List[str]]]):
    """Processes a player's selection of cards to gift for a Seven Gift effect."""
    if not state.pending_gift or state.pending_gift['player_id'] != player_id:
        raise_error(EFFECT_PENDING, "You do not have a pending gift to resolve.")

    giver = state.players[player_id]
    required_count = state.pending_gift['count']
    
    total_gifted_cards = sum(len(item['cards']) for item in assignments)
    if total_gifted_cards != required_count:
        raise_error(INVALID_GIFT_DISTRIBUTION, f"You must gift exactly {required_count} cards, but you provided {total_gifted_cards}.")

    all_cards_to_gift = [card for item in assignments for card in item['cards']]
    for card in all_cards_to_gift:
        if card not in giver.hand:
            raise_error(OWNERSHIP_MISMATCH, f"You do not own the card '{card}' to gift it.")

    state.version += 1
    for item in assignments:
        recipient_id = item['to']
        cards = item['cards']
        recipient = state.players[recipient_id]
        for card in cards:
            giver.hand.remove(card)
            recipient.hand.append(card)

    state.pending_gift = None
    state.turn = _get_next_player_id(state, player_id)
    
    if state.turn is None:
        _reset_round(state)
        state.turn = state.last_player_to_play


def submit_discard_selection(state: RoomState, player_id: str, card_ids: List[str]):
    """Processes a player's selection of cards to discard for a Ten Discard effect."""
    if not state.pending_discard or state.pending_discard['player_id'] != player_id:
        raise_error(EFFECT_PENDING, "You do not have a pending discard to resolve.")

    discarder = state.players[player_id]
    required_count = state.pending_discard['count']

    if len(card_ids) > required_count:
        raise_error(INVALID_DISCARD_SELECTION, f"You can discard a maximum of {required_count} cards.")
    if len(card_ids) > len(discarder.hand):
        raise_error(INVALID_DISCARD_SELECTION, "You cannot discard more cards than you have.")

    for card in card_ids:
        if card not in discarder.hand:
            raise_error(OWNERSHIP_MISMATCH, f"You do not own the card '{card}' to discard it.")

    state.version += 1
    for card in card_ids:
        discarder.hand.remove(card)
        state.discard_pile.append(card)

    state.pending_discard = None