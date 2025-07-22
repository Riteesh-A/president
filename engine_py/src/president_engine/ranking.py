# engine_py/src/president_engine/ranking.py

from .models import RoomState
from .constants import (
    ROLE_PRESIDENT,
    ROLE_VICE_PRESIDENT,
    ROLE_CITIZEN,
    ROLE_SCUMBAG,
    ROLE_ASSHOLE,
)

def assign_roles(state: RoomState):
    """
    Assigns roles to players based on their finish order from the previous round.

    This function mutates the state by setting the 'role' attribute on each player
    object according to the rules for 3, 4, and 5 player games.
    
    Args:
        state: The current RoomState, which must have a populated 'finished_order'.
    """
    if not state.finished_order:
        return # Cannot assign roles without a finish order

    num_players = len(state.players)
    finish_order = state.finished_order

    # Role distribution depends on the number of players
    if num_players == 3:
        # P, VP, Asshole
        roles_to_assign = [ROLE_PRESIDENT, ROLE_VICE_PRESIDENT, ROLE_ASSHOLE]
    elif num_players == 4:
        # P, VP, Scumbag, Asshole
        roles_to_assign = [ROLE_PRESIDENT, ROLE_VICE_PRESIDENT, ROLE_SCUMBAG, ROLE_ASSHOLE]
    elif num_players == 5:
        # P, VP, Citizen, Scumbag, Asshole
        roles_to_assign = [ROLE_PRESIDENT, ROLE_VICE_PRESIDENT, ROLE_CITIZEN, ROLE_SCUMBAG, ROLE_ASSHOLE]
    else:
        # For other counts (if rules are expanded later), default to Citizen
        for player_id in finish_order:
            state.players[player_id].role = ROLE_CITIZEN
        return

    for i, player_id in enumerate(finish_order):
        if i < len(roles_to_assign):
            state.players[player_id].role = roles_to_assign[i]