#!/usr/bin/env python3
"""
Basic tests for the President card game app
Run with: python test_basic.py
"""

import sys
import traceback
from app import (
    PresidentEngine, GreedyBot, create_deck, parse_card, 
    compare_ranks, is_higher_rank, RoomState, Player
)

class TestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        
    def run_test(self, test_func):
        """Run a single test function"""
        self.tests_run += 1
        test_name = test_func.__name__
        try:
            print(f"Running {test_name}...", end=" ")
            test_func()
            print("✅ PASSED")
            self.tests_passed += 1
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            print(f"  {traceback.format_exc()}")
            self.tests_failed += 1
    
    def summary(self):
        """Print test summary"""
        print(f"\n{'='*50}")
        print(f"Tests run: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        print(f"Success rate: {self.tests_passed/self.tests_run*100:.1f}%")
        print(f"{'='*50}")
        return self.tests_failed == 0

def test_deck_creation():
    """Test deck creation with and without jokers"""
    deck_with_jokers = create_deck(True)
    deck_without_jokers = create_deck(False)
    
    assert len(deck_with_jokers) == 54, f"Expected 54 cards, got {len(deck_with_jokers)}"
    assert len(deck_without_jokers) == 52, f"Expected 52 cards, got {len(deck_without_jokers)}"
    assert 'JOKERa' in deck_with_jokers, "JOKERa missing from deck with jokers"
    assert 'JOKERb' in deck_with_jokers, "JOKERb missing from deck with jokers"
    assert 'JOKERa' not in deck_without_jokers, "JOKERa found in deck without jokers"

def test_card_parsing():
    """Test card parsing functionality"""
    test_cases = [
        ('3S', (3, 'S')),
        ('AS', ('A', 'S')),
        ('10H', (10, 'H')),
        ('JD', ('J', 'D')),
        ('QC', ('Q', 'C')),
        ('KS', ('K', 'S')),
        ('2H', (2, 'H')),
        ('JOKERa', ('JOKER', None)),
        ('JOKERb', ('JOKER', None))
    ]
    
    for card_id, expected in test_cases:
        result = parse_card(card_id)
        assert result == expected, f"parse_card('{card_id}') returned {result}, expected {expected}"

def test_rank_comparison():
    """Test rank comparison logic"""
    # Normal order tests
    assert compare_ranks(4, 3, False) > 0, "4 should beat 3"
    assert compare_ranks('A', 'K', False) > 0, "Ace should beat King"
    assert compare_ranks(2, 'A', False) > 0, "2 should beat Ace"
    assert compare_ranks('JOKER', 2, False) > 0, "Joker should beat 2"
    assert compare_ranks(3, 4, False) < 0, "3 should lose to 4"
    
    # Inverted order tests
    assert compare_ranks(3, 4, True) > 0, "3 should beat 4 when inverted"
    assert compare_ranks('K', 'A', True) > 0, "King should beat Ace when inverted"
    assert compare_ranks(4, 3, True) < 0, "4 should lose to 3 when inverted"

def test_engine_room_creation():
    """Test room creation and management"""
    engine = PresidentEngine()
    room_id = "test_room"
    
    # Create room
    room = engine.create_room(room_id)
    assert room.id == room_id, f"Room ID mismatch: {room.id} != {room_id}"
    assert room.phase == 'lobby', f"New room should be in lobby phase, got {room.phase}"
    assert len(room.players) == 0, f"New room should have 0 players, got {len(room.players)}"
    
    # Get existing room
    same_room = engine.get_room(room_id)
    assert same_room is room, "get_room should return same room object"
    
    # Get nonexistent room
    nonexistent = engine.get_room("nonexistent")
    assert nonexistent is None, "get_room should return None for nonexistent room"

def test_player_addition():
    """Test adding players to rooms"""
    engine = PresidentEngine()
    room_id = "test_room"
    engine.create_room(room_id)
    
    # Add human player
    success, player_id = engine.add_player(room_id, "TestPlayer", False)
    assert success, "Adding player should succeed"
    assert player_id is not None, "Player ID should not be None"
    
    room = engine.get_room(room_id)
    assert len(room.players) == 1, f"Room should have 1 player, got {len(room.players)}"
    assert room.players[player_id].name == "TestPlayer", "Player name mismatch"
    assert not room.players[player_id].is_bot, "Player should not be a bot"
    
    # Add bot player
    success, bot_id = engine.add_player(room_id, "TestBot", True)
    assert success, "Adding bot should succeed"
    assert len(room.players) == 2, f"Room should have 2 players, got {len(room.players)}"
    assert room.players[bot_id].is_bot, "Bot should be marked as bot"

def test_room_capacity():
    """Test room capacity limits"""
    engine = PresidentEngine()
    room_id = "test_room"
    engine.create_room(room_id)
    
    # Add 5 players (max capacity)
    for i in range(5):
        success, _ = engine.add_player(room_id, f"Player{i}", False)
        assert success, f"Adding player {i} should succeed"
    
    # Try to add 6th player
    success, _ = engine.add_player(room_id, "Player6", False)
    assert not success, "Adding 6th player should fail"

def test_game_start_validation():
    """Test game starting requirements"""
    engine = PresidentEngine()
    room_id = "test_room"
    engine.create_room(room_id)
    
    # Can't start with 0 players
    success, msg = engine.start_game(room_id)
    assert not success, "Game should not start with 0 players"
    
    # Can't start with 2 players
    engine.add_player(room_id, "Player1", False)
    engine.add_player(room_id, "Player2", False)
    success, msg = engine.start_game(room_id)
    assert not success, "Game should not start with 2 players"
    
    # Should start with 3 players
    engine.add_player(room_id, "Player3", False)
    success, msg = engine.start_game(room_id)
    assert success, f"Game should start with 3 players: {msg}"

def test_card_validation():
    """Test card play validation"""
    engine = PresidentEngine()
    room_id = "test_room"
    engine.create_room(room_id)
    
    # Add players
    _, p1 = engine.add_player(room_id, "Player1", False)
    _, p2 = engine.add_player(room_id, "Player2", False)
    _, p3 = engine.add_player(room_id, "Player3", False)
    
    room = engine.get_room(room_id)
    room.phase = 'play'
    room.turn = p1
    
    # Give player some cards
    room.players[p1].hand = ['3S', '3H', '4D', '5C']
    
    # Valid play - single card
    valid, msg, pattern = engine.validate_play(room, p1, ['3S'])
    assert valid, f"Valid single card play should work: {msg}"
    assert pattern['rank'] == 3, "Pattern rank should be 3"
    assert pattern['count'] == 1, "Pattern count should be 1"
    
    # Valid play - pair
    valid, msg, pattern = engine.validate_play(room, p1, ['3S', '3H'])
    assert valid, f"Valid pair play should work: {msg}"
    assert pattern['rank'] == 3, "Pattern rank should be 3"
    assert pattern['count'] == 2, "Pattern count should be 2"
    
    # Invalid play - mixed ranks
    valid, msg, pattern = engine.validate_play(room, p1, ['3S', '4D'])
    assert not valid, "Mixed rank play should be invalid"
    
    # Invalid play - card not owned
    valid, msg, pattern = engine.validate_play(room, p1, ['AS'])
    assert not valid, "Playing unowned card should be invalid"

def test_special_effects():
    """Test special card effect detection"""
    engine = PresidentEngine()
    
    # Test effect types
    assert engine._get_effect_type(7) == 'seven_gift', "7 should trigger gift effect"
    assert engine._get_effect_type(8) == 'eight_reset', "8 should trigger reset effect"
    assert engine._get_effect_type(10) == 'ten_discard', "10 should trigger discard effect"
    assert engine._get_effect_type('J') == 'jack_inversion', "Jack should trigger inversion effect"
    assert engine._get_effect_type(5) is None, "5 should have no special effect"
    assert engine._get_effect_type('Q') is None, "Queen should have no special effect"

def test_bot_decision_making():
    """Test bot decision making logic"""
    engine = PresidentEngine()
    bot = GreedyBot(engine)
    room_id = "test_room"
    engine.create_room(room_id)
    
    # Add bot
    _, bot_id = engine.add_player(room_id, "TestBot", True)
    
    room = engine.get_room(room_id)
    room.phase = 'play'
    room.turn = bot_id
    
    # Give bot some cards
    bot_player = room.players[bot_id]
    bot_player.hand = ['3S', '3H', '4D', '5C', 'AS', 'AH']
    
    # Test bot can find valid plays
    plays = bot._get_possible_plays(room, bot_player)
    assert len(plays) > 0, "Bot should find some valid plays"
    
    # All plays should be valid
    for play in plays:
        valid, _, _ = engine.validate_play(room, bot_id, play)
        assert valid, f"Bot suggested invalid play: {play}"

def test_turn_advancement():
    """Test turn advancement logic"""
    engine = PresidentEngine()
    room_id = "test_room"
    engine.create_room(room_id)
    
    # Add 3 players
    players = []
    for i in range(3):
        _, pid = engine.add_player(room_id, f"Player{i}", False)
        players.append(pid)
    
    room = engine.get_room(room_id)
    room.phase = 'play'
    room.turn = players[0]
    
    # Set up players with cards
    for i, pid in enumerate(players):
        room.players[pid].hand = [f'{3+i}S', f'{4+i}H']
        room.players[pid].hand_count = 2
        room.players[pid].passed = False
    
    # Test turn advancement
    original_turn = room.turn
    engine._advance_turn(room)
    
    # Turn should advance to next player
    expected_next = players[1]  # Next player in seat order
    assert room.turn == expected_next, f"Turn should advance to {expected_next}, got {room.turn}"

def test_game_completion():
    """Test game completion logic"""
    engine = PresidentEngine()
    room_id = "test_room"
    engine.create_room(room_id)
    
    # Add 3 players
    players = []
    for i in range(3):
        _, pid = engine.add_player(room_id, f"Player{i}", False)
        players.append(pid)
    
    room = engine.get_room(room_id)
    room.phase = 'play'
    
    # Set up completion scenario
    room.players[players[0]].hand = []  # First to finish
    room.players[players[1]].hand = ['AS']
    room.players[players[2]].hand = ['2S', '2H']
    
    for player in room.players.values():
        player.hand_count = len(player.hand)
    
    # Simulate game end
    room.finished_order = players  # All players finished
    engine._end_game(room)
    
    assert room.phase == 'finished', "Game should be in finished phase"
    assert room.players[players[0]].role == 'President', "First player should be President"
    assert room.players[players[1]].role == 'Vice President', "Second player should be Vice President"
    assert room.players[players[2]].role == 'Asshole', "Last player should be Asshole"

def run_all_tests():
    """Run all tests"""
    runner = TestRunner()
    
    print("🎮 Testing President Card Game App")
    print("=" * 50)
    
    # Core functionality tests
    runner.run_test(test_deck_creation)
    runner.run_test(test_card_parsing)
    runner.run_test(test_rank_comparison)
    
    # Engine tests
    runner.run_test(test_engine_room_creation)
    runner.run_test(test_player_addition)
    runner.run_test(test_room_capacity)
    runner.run_test(test_game_start_validation)
    runner.run_test(test_card_validation)
    runner.run_test(test_special_effects)
    
    # Game logic tests
    runner.run_test(test_bot_decision_making)
    runner.run_test(test_turn_advancement)
    runner.run_test(test_game_completion)
    
    return runner.summary()

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 