"""
Basic tests for the President game engine.
"""

import pytest
from president_engine.engine import create_room, join_room, start_game, play_cards
from president_engine.constants import STARTING_CARD
from president_engine.rules import default_rules
from president_engine.shuffle import create_deck


def test_create_room():
    """Test room creation."""
    room = create_room("test-room")
    assert room.id == "test-room"
    assert room.phase == "lobby"
    assert len(room.players) == 0
    assert room.rule_config is not None


def test_join_room():
    """Test player joining room."""
    room = create_room("test-room")
    result = join_room(room, "player1", "Alice")
    
    assert result.success
    assert len(result.state.players) == 1
    
    player = result.state.players["player1"]
    assert player.name == "Alice"
    assert player.seat == 0
    assert not player.is_bot


def test_join_room_multiple_players():
    """Test multiple players joining room."""
    room = create_room("test-room")
    
    # Add first player
    result1 = join_room(room, "player1", "Alice")
    assert result1.success
    
    # Add second player
    result2 = join_room(result1.state, "player2", "Bob")
    assert result2.success
    assert len(result2.state.players) == 2
    
    # Check seats are different
    alice = result2.state.players["player1"]
    bob = result2.state.players["player2"]
    assert alice.seat != bob.seat


def test_room_full():
    """Test room capacity limit."""
    room = create_room("test-room")
    state = room
    
    # Fill room to capacity
    for i in range(default_rules.max_players):
        result = join_room(state, f"player{i}", f"Player {i}")
        assert result.success
        state = result.state
    
    # Try to add one more player
    result = join_room(state, "extra", "Extra Player")
    assert not result.success
    assert "full" in result.error_message.lower()


def test_start_game():
    """Test game start with minimum players."""
    room = create_room("test-room")
    state = room
    
    # Add minimum required players
    for i in range(default_rules.min_players):
        result = join_room(state, f"player{i}", f"Player {i}")
        state = result.state
    
    # Start game
    result = start_game(state, seed=42)  # Use deterministic seed
    assert result.success
    assert result.state.phase in ["exchange", "play"]  # Could be either depending on roles
    
    # Check that cards were dealt
    for player in result.state.players.values():
        assert len(player.hand) > 0


def test_start_game_insufficient_players():
    """Test game start fails with too few players."""
    room = create_room("test-room")
    
    # Add only one player
    result = join_room(room, "player1", "Alice")
    
    # Try to start game
    start_result = start_game(result.state)
    assert not start_result.success


def test_deck_creation():
    """Test deck creation and properties."""
    # Test without jokers
    deck_no_jokers = create_deck(use_jokers=False)
    assert len(deck_no_jokers) == 52
    assert STARTING_CARD in deck_no_jokers
    
    # Test with jokers
    deck_with_jokers = create_deck(use_jokers=True)
    assert len(deck_with_jokers) == 54
    assert "JOKERa" in deck_with_jokers
    assert "JOKERb" in deck_with_jokers


def test_card_validation():
    """Test basic card validation and patterns."""
    from president_engine.validate import detect_pattern
    
    # Test single card
    rank, count = detect_pattern(["3D"])
    assert rank == 3
    assert count == 1
    
    # Test pair
    rank, count = detect_pattern(["3D", "3H"])
    assert rank == 3
    assert count == 2
    
    # Test invalid mixed pattern
    rank, count = detect_pattern(["3D", "4H"])
    assert rank is None
    assert count == 0


def test_rank_comparison():
    """Test rank comparison logic."""
    from president_engine.comparator import is_higher_rank, is_lower_rank
    
    # Normal order tests
    assert is_higher_rank(4, 3, inversion=False)
    assert is_higher_rank('A', 'K', inversion=False)
    assert is_higher_rank(2, 'A', inversion=False)
    assert is_higher_rank('JOKER', 2, inversion=False)
    
    # Inversion tests
    assert is_lower_rank(4, 3, inversion=True)  # Inverted: lower is higher
    assert is_higher_rank('K', 'A', inversion=True)  # In inverted order K > A


def test_bot_creation():
    """Test bot player creation and basic functionality."""
    from president_engine.bots.greedy import GreedyBot
    from president_engine.models import RoomState, Player
    
    bot = GreedyBot("bot1")
    assert bot.player_id == "bot1"
    
    # Create a simple state for testing with multiple players
    state = RoomState(id="test")
    state.players["bot1"] = Player(id="bot1", name="Bot", seat=0, is_bot=True, hand=["3D", "4H"])
    state.players["player2"] = Player(id="player2", name="Human", seat=1, is_bot=False, hand=["5S", "6H", "7C"])
    state.phase = "play"
    state.turn = "bot1"
    
    # Bot should be able to choose an action
    action = bot.choose_action(state)
    assert action is not None


@pytest.mark.asyncio
async def test_websocket_events():
    """Test WebSocket event parsing."""
    from president_engine.ws.events import parse_inbound_event, JoinEvent
    
    # Test valid join event
    event_data = {
        "type": "join",
        "room_id": "test-room",
        "name": "Alice"
    }
    
    event = parse_inbound_event(event_data)
    assert isinstance(event, JoinEvent)
    assert event.room_id == "test-room"
    assert event.name == "Alice"
    
    # Test invalid event
    with pytest.raises(ValueError):
        parse_inbound_event({"type": "invalid"})


def test_state_serialization():
    """Test state sanitization for clients."""
    from president_engine.serialization import sanitize_state
    
    room = create_room("test-room")
    result = join_room(room, "player1", "Alice")
    state = result.state
    
    # Add some cards to player
    state.players["player1"].hand = ["3D", "4H", "5S"]
    
    # Sanitize for the player themselves
    sanitized = sanitize_state(state, "player1")
    assert "hand" in sanitized["players"]["player1"]
    assert len(sanitized["players"]["player1"]["hand"]) == 3
    
    # Sanitize for another player
    sanitized_other = sanitize_state(state, "other_player")
    assert "hand" not in sanitized_other["players"]["player1"]
    assert sanitized_other["players"]["player1"]["hand_count"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 