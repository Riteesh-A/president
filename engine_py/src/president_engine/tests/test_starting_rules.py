"""
Test starting game rules for first game vs subsequent games.
"""

import pytest
from president_engine.engine import create_room, join_room, start_game, play_cards
from president_engine.models import Player
from president_engine.constants import STARTING_CARD, ROLE_ASSHOLE, ROLE_PRESIDENT


def test_first_game_starts_with_3_diamonds():
    """Test that first game starts with player holding 3♦."""
    room = create_room("test-room")
    
    # Add players
    result1 = join_room(room, "player1", "Alice")
    result2 = join_room(result1.state, "player2", "Bob")
    result3 = join_room(result2.state, "player3", "Charlie")
    
    # Start game
    result = start_game(result3.state, seed=42)  # Use seed for deterministic test
    assert result.success
    
    state = result.state
    assert state.phase == "play"
    
    # Find who has 3♦
    player_with_3d = None
    for player_id, player in state.players.items():
        if STARTING_CARD in player.hand:
            player_with_3d = player_id
            break
    
    # Verify that player starts
    assert state.turn == player_with_3d
    assert player_with_3d is not None


def test_first_game_must_play_threes():
    """Test that first play in first game must be 3s."""
    room = create_room("test-room")
    
    # Add players
    result1 = join_room(room, "player1", "Alice")
    result2 = join_room(result1.state, "player2", "Bob") 
    result3 = join_room(result2.state, "player3", "Charlie")
    
    # Start game
    result = start_game(result3.state, seed=42)
    state = result.state
    
    # Find starting player
    starting_player = state.turn
    player = state.players[starting_player]
    
    # Try to play non-3s (should fail)
    non_three_cards = [card for card in player.hand if not card.startswith('3')]
    if non_three_cards:
        result = play_cards(state, starting_player, [non_three_cards[0]])
        assert not result.success
        assert "First game opening play must be threes" in result.error_message
    
    # Find 3s in hand
    threes = [card for card in player.hand if card.startswith('3')]
    if threes:
        # Playing 3s should work
        result = play_cards(state, starting_player, [threes[0]])
        assert result.success


def test_subsequent_game_starts_with_asshole():
    """Test that subsequent games start with the Asshole."""
    room = create_room("test-room")
    
    # Add players with roles (simulating previous game)
    result1 = join_room(room, "player1", "Alice")
    result2 = join_room(result1.state, "player2", "Bob")
    result3 = join_room(result2.state, "player3", "Charlie")
    
    state = result3.state
    
    # Assign roles as if from previous game
    state.players["player1"].role = ROLE_PRESIDENT
    state.players["player2"].role = None  # Citizen
    state.players["player3"].role = ROLE_ASSHOLE
    
    # Start new game (should be subsequent game)
    result = start_game(state, seed=42)
    assert result.success
    
    # Asshole should start
    assert result.state.turn == "player3"


def test_subsequent_game_asshole_can_play_any_cards():
    """Test that Asshole can play any cards in subsequent games."""
    room = create_room("test-room")
    
    # Add players with roles
    result1 = join_room(room, "player1", "Alice")
    result2 = join_room(result1.state, "player2", "Bob")
    result3 = join_room(result2.state, "player3", "Charlie")
    
    state = result3.state
    
    # Assign roles
    state.players["player1"].role = ROLE_PRESIDENT
    state.players["player2"].role = None  # Citizen  
    state.players["player3"].role = ROLE_ASSHOLE
    
    # Start game (will go to exchange phase)
    result = start_game(state, seed=42)
    state = result.state
    
    # Skip exchange phase for this test by manually setting to play phase
    state.phase = "play"
    state.pending_gift = None
    state.pending_discard = None
    
    # Asshole should be starting
    assert state.turn == "player3"
    asshole_player = state.players["player3"]
    
    # Should be able to play any card (not restricted to 3s)
    if asshole_player.hand:
        any_card = asshole_player.hand[0]
        result = play_cards(state, "player3", [any_card])
        assert result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 