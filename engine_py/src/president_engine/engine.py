"""
Main game engine with public mutation functions.
"""

import copy
import time
from typing import List, Optional

from .constants import (
    PHASE_LOBBY, PHASE_DEALING, PHASE_EXCHANGE, PHASE_PLAY, PHASE_FINISHED,
    ERROR_ROOM_FULL, ERROR_ACTION_NOT_ALLOWED, ERROR_INTERNAL
)
from .effects import (
    process_effect, complete_gift_distribution, complete_discard_selection,
    has_pending_effects, should_clear_inversion
)
from .exchange import (
    start_exchange_phase, process_exchange_return, check_exchange_complete,
    complete_exchange_phase, validate_exchange_return, auto_complete_bot_exchanges
)
from .models import Player, RoomState, GameResult
from .ranking import (
    check_round_end, add_finished_player, complete_round, assign_roles,
    reset_for_new_round
)
from .rules import RuleConfig, default_rules
from .shuffle import setup_round
from .validate import (
    validate_play, validate_pass, validate_gift_distribution,
    validate_discard_selection
)


def create_room(room_id: str, rule_config: Optional[RuleConfig] = None) -> RoomState:
    """
    Create a new game room.
    
    Args:
        room_id: Unique identifier for the room
        rule_config: Game rules configuration
    
    Returns:
        New room state
    """
    state = RoomState(
        id=room_id,
        phase=PHASE_LOBBY,
        rule_config=rule_config or default_rules,
        last_activity=time.time()
    )
    
    state.add_effect_log("room_created", {"room_id": room_id})
    return state


def join_room(
    state: RoomState,
    player_id: str,
    player_name: str,
    is_bot: bool = False
) -> GameResult:
    """
    Add a player to the room.
    
    Args:
        state: Current room state
        player_id: Unique player identifier
        player_name: Display name for player
        is_bot: Whether this is a bot player
    
    Returns:
        GameResult with updated state or error
    """
    if state.phase != PHASE_LOBBY:
        return GameResult.error_result(
            ERROR_ACTION_NOT_ALLOWED,
            "Cannot join room after game has started"
        )
    
    if len(state.players) >= state.rule_config.max_players:
        return GameResult.error_result(
            ERROR_ROOM_FULL,
            f"Room is full (max {state.rule_config.max_players} players)"
        )
    
    if player_id in state.players:
        return GameResult.error_result(
            ERROR_ACTION_NOT_ALLOWED,
            "Player is already in the room"
        )
    
    # Create new state
    new_state = copy.deepcopy(state)
    
    # Find available seat
    taken_seats = {player.seat for player in new_state.players.values()}
    seat = 0
    while seat in taken_seats:
        seat += 1
    
    # Add player
    player = Player(
        id=player_id,
        name=player_name,
        seat=seat,
        is_bot=is_bot
    )
    new_state.players[player_id] = player
    new_state.last_activity = time.time()
    
    # Log join
    new_state.add_effect_log(
        "player_joined",
        {
            "player_id": player_id,
            "name": player_name,
            "seat": seat,
            "is_bot": is_bot
        },
        player_id
    )
    
    new_state.increment_version()
    return GameResult.success_result(new_state, ["player_joined"])


def start_game(state: RoomState, seed: Optional[int] = None) -> GameResult:
    """
    Start the game by dealing cards and beginning first round.
    
    Args:
        state: Current room state
        seed: Optional seed for deterministic shuffling
    
    Returns:
        GameResult with updated state or error
    """
    if state.phase != PHASE_LOBBY:
        return GameResult.error_result(
            ERROR_ACTION_NOT_ALLOWED,
            "Game has already started"
        )
    
    player_count = len(state.players)
    if not state.rule_config.validate_player_count(player_count):
        return GameResult.error_result(
            ERROR_ACTION_NOT_ALLOWED,
            f"Need {state.rule_config.min_players}-{state.rule_config.max_players} players to start"
        )
    
    try:
        # Create new state
        new_state = copy.deepcopy(state)
        new_state.phase = PHASE_DEALING
        
        # Setup round (shuffle and deal)
        new_state = setup_round(new_state, seed)
        
        # Check if we need exchange phase
        has_roles = any(player.role for player in new_state.players.values())
        
        if has_roles:
            # Start exchange phase
            new_state = start_exchange_phase(new_state)
            # Auto-complete bot exchanges
            new_state = auto_complete_bot_exchanges(new_state)
            # Check if exchange is complete
            if check_exchange_complete(new_state):
                new_state = complete_exchange_phase(new_state)
        else:
            # First game, go directly to play
            new_state.phase = PHASE_PLAY
        
        new_state.last_activity = time.time()
        new_state.add_effect_log("game_started", {"seed": seed})
        new_state.increment_version()
        
        return GameResult.success_result(new_state, ["game_started"])
        
    except Exception as e:
        return GameResult.error_result(
            ERROR_INTERNAL,
            f"Failed to start game: {str(e)}"
        )


def play_cards(state: RoomState, player_id: str, card_ids: List[str]) -> GameResult:
    """
    Play cards from a player's hand.
    
    Args:
        state: Current room state
        player_id: Player making the play
        card_ids: Cards being played
    
    Returns:
        GameResult with updated state or error
    """
    # Validate the play
    validation = validate_play(state, player_id, card_ids)
    if not validation.valid:
        return GameResult.error_result(validation.error_code, validation.error_message)
    
    try:
        # Create new state
        new_state = copy.deepcopy(state)
        
        # Remove cards from player's hand
        player = new_state.players[player_id]
        for card_id in card_ids:
            if card_id in player.hand:
                player.hand.remove(card_id)
        
        # Update current pattern
        pattern = validation.pattern
        new_state.current_pattern.rank = pattern['rank']
        new_state.current_pattern.count = pattern['count']
        new_state.current_pattern.last_player = player_id
        new_state.current_pattern.cards = card_ids.copy()
        
        # Clear passes for new round
        new_state.clear_passes()
        
        # Check for special effects
        effect = validation.effect
        if effect:
            new_state = process_effect(new_state, effect, player_id, pattern['count'])
        
        # Check if player finished
        if len(player.hand) == 0:
            new_state = add_finished_player(new_state, player_id)
        
        # Check round end
        round_ended, newly_finished = check_round_end(new_state)
        if newly_finished and newly_finished != player_id:
            new_state = add_finished_player(new_state, newly_finished)
        
        if round_ended:
            new_state = complete_round(new_state)
            new_state = assign_roles(new_state)
            new_state.phase = PHASE_FINISHED
        elif not has_pending_effects(new_state):
            # Move to next player if no pending effects
            new_state.turn = new_state.get_next_player(player_id)
        
        # Check inversion clearing
        if should_clear_inversion(new_state):
            new_state.inversion_active = False
        
        new_state.last_activity = time.time()
        new_state.add_effect_log(
            "cards_played",
            {
                "player_id": player_id,
                "cards": len(card_ids),
                "rank": pattern['rank'],
                "effect": effect
            },
            player_id
        )
        new_state.increment_version()
        
        effects = ["cards_played"]
        if effect:
            effects.append(effect)
        if round_ended:
            effects.append("round_ended")
        
        return GameResult.success_result(new_state, effects)
        
    except Exception as e:
        return GameResult.error_result(
            ERROR_INTERNAL,
            f"Failed to play cards: {str(e)}"
        )


def pass_turn(state: RoomState, player_id: str) -> GameResult:
    """
    Pass the current turn.
    
    Args:
        state: Current room state
        player_id: Player passing
    
    Returns:
        GameResult with updated state or error
    """
    # Validate the pass
    validation = validate_pass(state, player_id)
    if not validation.valid:
        return GameResult.error_result(validation.error_code, validation.error_message)
    
    try:
        # Create new state
        new_state = copy.deepcopy(state)
        
        # Mark player as passed
        player = new_state.players[player_id]
        player.passed = True
        
        # Check if round should end (all but one player passed)
        active_players = [
            p for p in new_state.players.values()
            if len(p.hand) > 0 and p.connected
        ]
        passed_players = [p for p in active_players if p.passed]
        
        if len(passed_players) >= len(active_players) - 1:
            # Round ends, clear pile and start new round
            new_state.current_pattern.rank = None
            new_state.current_pattern.count = None
            new_state.current_pattern.last_player = None
            new_state.current_pattern.cards = []
            new_state.inversion_active = False
            new_state.clear_passes()
            
            # Find the player who didn't pass (last successful player)
            last_player = None
            for p in active_players:
                if not p.passed:
                    last_player = p.id
                    break
            
            # If no non-passed player found, use the last one to play
            if not last_player:
                last_player = new_state.current_pattern.last_player
            
            new_state.turn = last_player
            
            new_state.add_effect_log(
                "round_cleared",
                {"next_player": last_player},
                player_id
            )
        else:
            # Move to next player
            new_state.turn = new_state.get_next_player(player_id)
        
        new_state.last_activity = time.time()
        new_state.add_effect_log("player_passed", {"player_id": player_id}, player_id)
        new_state.increment_version()
        
        return GameResult.success_result(new_state, ["player_passed"])
        
    except Exception as e:
        return GameResult.error_result(
            ERROR_INTERNAL,
            f"Failed to pass turn: {str(e)}"
        )


def submit_gift_distribution(
    state: RoomState,
    player_id: str,
    assignments: List[dict]
) -> GameResult:
    """
    Submit gift distribution for Seven effect.
    
    Args:
        state: Current room state
        player_id: Player distributing gifts
        assignments: List of {to: player_id, cards: [card_ids]}
    
    Returns:
        GameResult with updated state or error
    """
    # Validate the distribution
    validation = validate_gift_distribution(state, player_id, assignments)
    if not validation.valid:
        return GameResult.error_result(validation.error_code, validation.error_message)
    
    try:
        # Complete the gift distribution
        new_state = complete_gift_distribution(state, player_id, assignments)
        new_state.last_activity = time.time()
        
        return GameResult.success_result(new_state, ["gift_distributed"])
        
    except Exception as e:
        return GameResult.error_result(
            ERROR_INTERNAL,
            f"Failed to distribute gifts: {str(e)}"
        )


def submit_discard_selection(
    state: RoomState,
    player_id: str,
    card_ids: List[str]
) -> GameResult:
    """
    Submit discard selection for Ten effect.
    
    Args:
        state: Current room state
        player_id: Player discarding cards
        card_ids: Cards to discard
    
    Returns:
        GameResult with updated state or error
    """
    # Validate the discard
    validation = validate_discard_selection(state, player_id, card_ids)
    if not validation.valid:
        return GameResult.error_result(validation.error_code, validation.error_message)
    
    try:
        # Complete the discard
        new_state = complete_discard_selection(state, player_id, card_ids)
        new_state.last_activity = time.time()
        
        return GameResult.success_result(new_state, ["cards_discarded"])
        
    except Exception as e:
        return GameResult.error_result(
            ERROR_INTERNAL,
            f"Failed to discard cards: {str(e)}"
        )


def submit_exchange_return(
    state: RoomState,
    player_id: str,
    card_ids: List[str]
) -> GameResult:
    """
    Submit cards to return during exchange phase.
    
    Args:
        state: Current room state
        player_id: Player returning cards
        card_ids: Cards to return
    
    Returns:
        GameResult with updated state or error
    """
    # Validate the return
    is_valid, error_message = validate_exchange_return(state, player_id, card_ids)
    if not is_valid:
        return GameResult.error_result(ERROR_ACTION_NOT_ALLOWED, error_message)
    
    try:
        # Process the return
        new_state = process_exchange_return(state, player_id, card_ids)
        
        # Check if exchange is complete
        if check_exchange_complete(new_state):
            new_state = complete_exchange_phase(new_state)
        
        new_state.last_activity = time.time()
        
        effects = ["exchange_return"]
        if new_state.phase == PHASE_PLAY:
            effects.append("exchange_completed")
        
        return GameResult.success_result(new_state, effects)
        
    except Exception as e:
        return GameResult.error_result(
            ERROR_INTERNAL,
            f"Failed to process exchange return: {str(e)}"
        )


def start_new_round(state: RoomState, seed: Optional[int] = None) -> GameResult:
    """
    Start a new round after the previous one ended.
    
    Args:
        state: Current room state (should be in finished phase)
        seed: Optional seed for deterministic shuffling
    
    Returns:
        GameResult with updated state or error
    """
    if state.phase != PHASE_FINISHED:
        return GameResult.error_result(
            ERROR_ACTION_NOT_ALLOWED,
            "Cannot start new round - current round not finished"
        )
    
    try:
        # Reset for new round while preserving roles
        new_state = reset_for_new_round(state)
        new_state.phase = PHASE_DEALING
        
        # Setup round (shuffle and deal)
        new_state = setup_round(new_state, seed)
        
        # Start exchange phase
        new_state = start_exchange_phase(new_state)
        
        # Auto-complete bot exchanges
        new_state = auto_complete_bot_exchanges(new_state)
        
        # Check if exchange is complete
        if check_exchange_complete(new_state):
            new_state = complete_exchange_phase(new_state)
        
        new_state.last_activity = time.time()
        new_state.add_effect_log("new_round_started", {"seed": seed})
        new_state.increment_version()
        
        return GameResult.success_result(new_state, ["new_round_started"])
        
    except Exception as e:
        return GameResult.error_result(
            ERROR_INTERNAL,
            f"Failed to start new round: {str(e)}"
        )


def disconnect_player(state: RoomState, player_id: str) -> GameResult:
    """
    Mark a player as disconnected.
    
    Args:
        state: Current room state
        player_id: Player to disconnect
    
    Returns:
        GameResult with updated state or error
    """
    if player_id not in state.players:
        return GameResult.error_result(
            ERROR_ACTION_NOT_ALLOWED,
            "Player not found"
        )
    
    new_state = copy.deepcopy(state)
    new_state.players[player_id].connected = False
    new_state.last_activity = time.time()
    new_state.add_effect_log("player_disconnected", {"player_id": player_id}, player_id)
    new_state.increment_version()
    
    return GameResult.success_result(new_state, ["player_disconnected"])


def reconnect_player(state: RoomState, player_id: str) -> GameResult:
    """
    Mark a player as reconnected.
    
    Args:
        state: Current room state
        player_id: Player to reconnect
    
    Returns:
        GameResult with updated state or error
    """
    if player_id not in state.players:
        return GameResult.error_result(
            ERROR_ACTION_NOT_ALLOWED,
            "Player not found"
        )
    
    new_state = copy.deepcopy(state)
    new_state.players[player_id].connected = True
    new_state.last_activity = time.time()
    new_state.add_effect_log("player_reconnected", {"player_id": player_id}, player_id)
    new_state.increment_version()
    
    return GameResult.success_result(new_state, ["player_reconnected"]) 