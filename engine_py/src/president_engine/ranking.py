"""
Player ranking and role assignment logic.
"""

import copy
from typing import Dict, List, Optional, Tuple

from .constants import (
    ROLE_PRESIDENT, ROLE_VICE_PRESIDENT, ROLE_CITIZEN,
    ROLE_SCUMBAG, ROLE_ASSHOLE
)
from .models import Player, RoomState


def check_round_end(state: RoomState) -> Tuple[bool, Optional[str]]:
    """
    Check if the round has ended and identify any player who just finished.
    
    Args:
        state: Current room state
    
    Returns:
        Tuple of (round_ended, finished_player_id)
    """
    # Find players who have finished (no cards left)
    finished_players = []
    for player_id, player in state.players.items():
        if len(player.hand) == 0 and player_id not in state.finished_order:
            finished_players.append(player_id)
    
    # Check if any new player finished
    newly_finished = None
    if finished_players:
        # Add to finished order (should only be one at a time)
        newly_finished = finished_players[0]
    
    # Round ends when all but one player have finished
    active_players = [p for p in state.players.values() if len(p.hand) > 0]
    round_ended = len(active_players) <= 1
    
    return round_ended, newly_finished


def add_finished_player(state: RoomState, player_id: str) -> RoomState:
    """
    Add a player to the finished order.
    
    Args:
        state: Current room state
        player_id: Player who just finished
    
    Returns:
        Updated state with player added to finished order
    """
    new_state = copy.deepcopy(state)
    
    if player_id not in new_state.finished_order:
        new_state.finished_order.append(player_id)
        
        # Log the finish
        new_state.add_effect_log(
            effect="player_finished",
            data={
                'player_id': player_id,
                'position': len(new_state.finished_order)
            },
            player_id=player_id
        )
    
    new_state.increment_version()
    return new_state


def complete_round(state: RoomState) -> RoomState:
    """
    Complete the round by adding the last remaining player to finished order.
    
    Args:
        state: Current room state
    
    Returns:
        Updated state with all players ranked
    """
    new_state = copy.deepcopy(state)
    
    # Find the last remaining player (Asshole)
    remaining_players = [
        player_id for player_id, player in new_state.players.items()
        if len(player.hand) > 0 and player_id not in new_state.finished_order
    ]
    
    # Add remaining players to finished order
    for player_id in remaining_players:
        if player_id not in new_state.finished_order:
            new_state.finished_order.append(player_id)
    
    new_state.increment_version()
    return new_state


def assign_roles(state: RoomState) -> RoomState:
    """
    Assign roles to players based on their finish order.
    
    Args:
        state: Current room state with completed finished_order
    
    Returns:
        Updated state with roles assigned
    """
    new_state = copy.deepcopy(state)
    
    if not new_state.rule_config:
        raise ValueError("RuleConfig must be set before assigning roles")
    
    player_count = len(new_state.players)
    role_mapping = new_state.rule_config.get_role_mapping(player_count)
    
    # Assign roles based on finish position
    for position, player_id in enumerate(new_state.finished_order, 1):
        if player_id in new_state.players:
            role = role_mapping.get(position, ROLE_CITIZEN)
            new_state.players[player_id].role = role
    
    # Log role assignments
    new_state.add_effect_log(
        effect="roles_assigned",
        data={
            'assignments': {
                player_id: player.role 
                for player_id, player in new_state.players.items()
            }
        }
    )
    
    new_state.increment_version()
    return new_state


def get_exchange_pairs(state: RoomState) -> List[Tuple[str, str, int]]:
    """
    Get the exchange pairs for the next round.
    
    Args:
        state: Current room state with roles assigned
    
    Returns:
        List of (giver_id, receiver_id, card_count) tuples
    """
    exchange_pairs = []
    
    # Find players by role
    president = None
    vice_president = None
    scumbag = None
    asshole = None
    
    for player_id, player in state.players.items():
        if player.role == ROLE_PRESIDENT:
            president = player_id
        elif player.role == ROLE_VICE_PRESIDENT:
            vice_president = player_id
        elif player.role == ROLE_SCUMBAG:
            scumbag = player_id
        elif player.role == ROLE_ASSHOLE:
            asshole = player_id
    
    # Asshole -> President (2 cards)
    if asshole and president:
        exchange_pairs.append((asshole, president, 2))
    
    # Scumbag -> Vice President (1 card)
    if scumbag and vice_president:
        exchange_pairs.append((scumbag, vice_president, 1))
    
    return exchange_pairs


def get_role_priority(role: str) -> int:
    """
    Get numeric priority for role (lower is better).
    
    Args:
        role: Role name
    
    Returns:
        Priority value
    """
    priority_map = {
        ROLE_PRESIDENT: 1,
        ROLE_VICE_PRESIDENT: 2,
        ROLE_CITIZEN: 3,
        ROLE_SCUMBAG: 4,
        ROLE_ASSHOLE: 5
    }
    return priority_map.get(role, 99)


def get_players_by_role(state: RoomState) -> Dict[str, List[str]]:
    """
    Get players grouped by their roles.
    
    Args:
        state: Current room state
    
    Returns:
        Dictionary mapping role to list of player IDs
    """
    players_by_role = {}
    
    for player_id, player in state.players.items():
        role = player.role
        if role:
            if role not in players_by_role:
                players_by_role[role] = []
            players_by_role[role].append(player_id)
    
    return players_by_role


def should_player_start_next_round(state: RoomState) -> Optional[str]:
    """
    Determine who should start the next round.
    
    For the first game: player with 3♦
    For subsequent games: the Asshole
    
    Args:
        state: Current room state
    
    Returns:
        Player ID who should start, or None
    """
    # If this is the first game ever (no previous roles), use 3♦
    if not any(player.role for player in state.players.values()):
        from .shuffle import find_starting_player
        return find_starting_player(state.players)
    
    # Otherwise, Asshole starts
    for player_id, player in state.players.items():
        if player.role == ROLE_ASSHOLE:
            return player_id
    
    # Fallback to 3♦ holder
    from .shuffle import find_starting_player
    return find_starting_player(state.players)


def reset_for_new_round(state: RoomState) -> RoomState:
    """
    Reset state for a new round while preserving roles.
    
    Args:
        state: Current room state
    
    Returns:
        Updated state ready for new round
    """
    new_state = copy.deepcopy(state)
    
    # Clear round-specific state
    new_state.finished_order = []
    new_state.current_pattern.rank = None
    new_state.current_pattern.count = None
    new_state.current_pattern.last_player = None
    new_state.inversion_active = False
    new_state.pending_gift = None
    new_state.pending_discard = None
    
    # Clear player passes
    new_state.clear_passes()
    
    # Clear hands (will be dealt new cards)
    for player in new_state.players.values():
        player.hand = []
    
    new_state.increment_version()
    return new_state


def get_round_summary(state: RoomState) -> Dict:
    """
    Get a summary of the completed round.
    
    Args:
        state: Current room state with completed round
    
    Returns:
        Dictionary with round summary information
    """
    summary = {
        'finished_order': state.finished_order.copy(),
        'roles': {},
        'player_count': len(state.players)
    }
    
    # Add role information
    for player_id, player in state.players.items():
        summary['roles'][player_id] = {
            'name': player.name,
            'role': player.role,
            'is_bot': player.is_bot
        }
    
    return summary 