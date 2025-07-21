# engine_py/src/president_engine/effects.py

from .models import RoomState

def apply_seven_gift(state: RoomState, player_id: str, count: int):
    """
    Initiates the 'Seven Gift' effect.
    
    This sets a pending_gift state on the room, requiring the player
    to select 'count' cards to give to other players. The turn does not
    advance until the gift is resolved.
    
    Args:
        state: The current RoomState.
        player_id: The ID of the player who played the seven(s).
        count: The number of sevens played (and thus cards to gift).
    """
    state.pending_gift = {'player_id': player_id, 'count': count}

def apply_ten_discard(state: RoomState, player_id: str, count: int):
    """
    Initiates the 'Ten Discard' effect.

    This sets a pending_discard state on the room, requiring the player
    to select 'count' cards to discard from the game.
    
    Args:
        state: The current RoomState.
        player_id: The ID of the player who played the ten(s).
        count: The number of tens played (and thus cards to discard).
    """
    state.pending_discard = {'player_id': player_id, 'count': count}