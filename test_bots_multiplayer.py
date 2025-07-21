#!/usr/bin/env python3
"""
Specialized tests for bot functionality and multiplayer scenarios
Run with: python test_bots_multiplayer.py
"""

import sys
import time
import threading
import traceback
from app import (
    PresidentEngine, GreedyBot, bot_manager, RoomState, Player
)

class BotMultiplayerTester:
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
        print(f"\n{'='*60}")
        print(f"Bot & Multiplayer Tests Summary:")
        print(f"Tests run: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        print(f"Success rate: {self.tests_passed/self.tests_run*100:.1f}%")
        print(f"{'='*60}")
        return self.tests_failed == 0

def test_bot_can_make_moves():
    """Test that bots can make valid moves"""
    engine = PresidentEngine()
    bot = GreedyBot(engine)
    room_id = "bot_test"
    engine.create_room(room_id)
    
    # Add human and bot players
    _, human_id = engine.add_player(room_id, "Human", False)
    _, bot_id = engine.add_player(room_id, "Bot", True)
    _, bot2_id = engine.add_player(room_id, "Bot2", True)
    
    room = engine.get_room(room_id)
    room.phase = 'play'
    room.turn = bot_id
    
    # Give bot some cards
    room.players[bot_id].hand = ['3S', '4H', '5D', 'AS']
    room.players[bot_id].hand_count = 4
    
    # Bot should be able to make a move
    initial_hand_size = len(room.players[bot_id].hand)
    bot.make_move(room_id, bot_id)
    
    # Check that bot made a move (hand size decreased or passed)
    final_hand_size = len(room.players[bot_id].hand)
    turn_changed = room.turn != bot_id
    
    assert final_hand_size < initial_hand_size or turn_changed, "Bot should make a move or pass"

def test_bot_handles_special_effects():
    """Test that bots can handle special card effects"""
    engine = PresidentEngine()
    bot = GreedyBot(engine)
    room_id = "bot_effects_test"
    engine.create_room(room_id)
    
    # Add bot players
    _, bot_id = engine.add_player(room_id, "Bot", True)
    _, bot2_id = engine.add_player(room_id, "Bot2", True)
    
    room = engine.get_room(room_id)
    room.phase = 'play'
    room.turn = bot_id
    
    # Test 7s effect (gift cards)
    room.players[bot_id].hand = ['7S', '7H', '8D', '9C']
    room.players[bot_id].hand_count = 4
    room.pending_gift = {'player_id': bot_id, 'remaining': 2}
    
    initial_hand_size = len(room.players[bot_id].hand)
    bot.make_move(room_id, bot_id)
    
    # Bot should handle gift effect
    assert room.pending_gift is None, "Bot should handle gift effect"
    assert len(room.players[bot_id].hand) < initial_hand_size, "Bot should have gifted cards"

def test_bot_handles_discard_effect():
    """Test that bots can handle discard effects from 10s"""
    engine = PresidentEngine()
    bot = GreedyBot(engine)
    room_id = "bot_discard_test"
    engine.create_room(room_id)
    
    # Add bot
    _, bot_id = engine.add_player(room_id, "Bot", True)
    _, bot2_id = engine.add_player(room_id, "Bot2", True)
    
    room = engine.get_room(room_id)
    room.phase = 'play'
    room.turn = bot_id
    
    # Test 10s effect (discard cards)
    room.players[bot_id].hand = ['10S', '10H', '8D', '9C']
    room.players[bot_id].hand_count = 4
    room.pending_discard = {'player_id': bot_id, 'remaining': 2}
    
    initial_hand_size = len(room.players[bot_id].hand)
    initial_discard_size = len(room.discard)
    
    bot.make_move(room_id, bot_id)
    
    # Bot should handle discard effect
    assert room.pending_discard is None, "Bot should handle discard effect"
    assert len(room.players[bot_id].hand) < initial_hand_size, "Bot should have discarded cards"
    assert len(room.discard) > initial_discard_size, "Cards should be in discard pile"

def test_multiplayer_room_creation():
    """Test that multiple players can join rooms"""
    engine = PresidentEngine()
    room_id = "multiplayer_test"
    engine.create_room(room_id)
    
    # Add multiple players
    players = []
    for i in range(5):  # Max capacity
        is_bot = i >= 2  # First 2 are human, rest are bots
        success, pid = engine.add_player(room_id, f"Player{i}", is_bot)
        assert success, f"Should be able to add player {i}"
        players.append(pid)
    
    room = engine.get_room(room_id)
    assert len(room.players) == 5, f"Should have 5 players, got {len(room.players)}"
    
    # Verify mix of humans and bots
    human_count = sum(1 for p in room.players.values() if not p.is_bot)
    bot_count = sum(1 for p in room.players.values() if p.is_bot)
    
    assert human_count == 2, f"Should have 2 humans, got {human_count}"
    assert bot_count == 3, f"Should have 3 bots, got {bot_count}"

def test_multiplayer_game_flow():
    """Test complete multiplayer game flow with bots"""
    engine = PresidentEngine()
    room_id = "multiplayer_flow_test"
    engine.create_room(room_id)
    
    # Add mixed players
    player_ids = []
    for i in range(4):
        is_bot = i > 0  # First is human, rest are bots
        _, pid = engine.add_player(room_id, f"Player{i}", is_bot)
        player_ids.append(pid)
    
    room = engine.get_room(room_id)
    
    # Start game
    success, msg = engine.start_game(room_id)
    assert success, f"Game should start: {msg}"
    assert room.phase == 'play', "Game should be in play phase"
    assert room.turn is not None, "Should have a starting player"
    
    # Verify all players have cards
    for pid in player_ids:
        player = room.players[pid]
        assert len(player.hand) > 0, f"Player {player.name} should have cards"
        assert player.hand_count == len(player.hand), "Hand count should match actual hand"

def test_bot_manager_functionality():
    """Test that the bot manager can handle multiple bots in a game"""
    engine = PresidentEngine()
    room_id = "bot_manager_test"
    engine.create_room(room_id)
    
    # Add mostly bots
    _, human_id = engine.add_player(room_id, "Human", False)
    bot_ids = []
    for i in range(3):
        _, bot_id = engine.add_player(room_id, f"Bot{i}", True)
        bot_ids.append(bot_id)
    
    # Start game
    engine.start_game(room_id)
    room = engine.get_room(room_id)
    
    # Manually set up a quick game scenario
    room.players[human_id].hand = ['3D', '4S']
    room.players[bot_ids[0]].hand = ['5H', '6C']
    room.players[bot_ids[1]].hand = ['7D', '8S']
    room.players[bot_ids[2]].hand = ['9H', '10C']
    
    for player in room.players.values():
        player.hand_count = len(player.hand)
    
    room.turn = human_id
    
    # Human plays first
    engine.play_cards(room_id, human_id, ['3D'])
    
    # Now turn should be on a bot
    assert room.players[room.turn].is_bot, "Turn should be on a bot after human play"
    
    # Test that bot manager would handle bot turns
    bot = GreedyBot(engine)
    current_turn = room.turn
    if room.players[current_turn].is_bot:
        bot.make_move(room_id, current_turn)
        # Turn should have advanced
        assert room.turn != current_turn or room.players[current_turn].passed, "Bot should have made a move"

def test_multiplayer_with_special_effects():
    """Test multiplayer game with special card effects"""
    engine = PresidentEngine()
    room_id = "multiplayer_effects_test"
    engine.create_room(room_id)
    
    # Add players
    _, human_id = engine.add_player(room_id, "Human", False)
    _, bot_id = engine.add_player(room_id, "Bot", True)
    _, bot2_id = engine.add_player(room_id, "Bot2", True)
    
    room = engine.get_room(room_id)
    room.phase = 'play'
    room.turn = human_id
    
    # Give human 7s to test gift effect
    room.players[human_id].hand = ['7S', '7H', '8D']
    room.players[bot_id].hand = ['9S', '10H']
    room.players[bot2_id].hand = ['JS', 'QH']
    
    for player in room.players.values():
        player.hand_count = len(player.hand)
    
    # Human plays 7s
    success, msg = engine.play_cards(room_id, human_id, ['7S', '7H'])
    assert success, f"Should be able to play 7s: {msg}"
    
    # Should trigger gift effect
    assert room.pending_gift is not None, "Should have pending gift effect"
    assert room.pending_gift['player_id'] == human_id, "Gift should be for human player"
    assert room.pending_gift['remaining'] == 2, "Should need to gift 2 cards"

def test_bot_vs_bot_gameplay():
    """Test pure bot vs bot gameplay"""
    engine = PresidentEngine()
    bot = GreedyBot(engine)
    room_id = "bot_vs_bot_test"
    engine.create_room(room_id)
    
    # Add only bots
    bot_ids = []
    for i in range(3):
        _, bot_id = engine.add_player(room_id, f"Bot{i}", True)
        bot_ids.append(bot_id)
    
    room = engine.get_room(room_id)
    room.phase = 'play'
    room.turn = bot_ids[0]
    
    # Give bots simple hands
    room.players[bot_ids[0]].hand = ['3S', '4H']
    room.players[bot_ids[1]].hand = ['5D', '6C']
    room.players[bot_ids[2]].hand = ['7S', '8H']
    
    for player in room.players.values():
        player.hand_count = len(player.hand)
    
    # Simulate a few bot moves
    moves_made = 0
    max_moves = 5
    
    while moves_made < max_moves and room.phase == 'play':
        current_player = room.players[room.turn]
        if current_player.is_bot and not current_player.passed:
            initial_hand_size = len(current_player.hand)
            bot.make_move(room_id, room.turn)
            
            # Check that something happened (move or pass)
            final_hand_size = len(current_player.hand)
            assert final_hand_size <= initial_hand_size, "Bot should play cards or keep same hand if passing"
            
            moves_made += 1
        else:
            break
    
    assert moves_made > 0, "Bots should be able to make moves"

def test_game_completion_with_bots():
    """Test that games complete properly with bots"""
    engine = PresidentEngine()
    room_id = "completion_test"
    engine.create_room(room_id)
    
    # Add players
    _, human_id = engine.add_player(room_id, "Human", False)
    _, bot_id = engine.add_player(room_id, "Bot", True)
    _, bot2_id = engine.add_player(room_id, "Bot2", True)
    
    room = engine.get_room(room_id)
    room.phase = 'play'
    
    # Set up near-completion scenario
    room.players[human_id].hand = []  # Human finishes first
    room.players[bot_id].hand = ['AS']  # Bot has 1 card
    room.players[bot2_id].hand = ['2S', '2H']  # Bot2 has 2 cards
    
    for player in room.players.values():
        player.hand_count = len(player.hand)
    
    # Manually finish the game
    room.finished_order = [human_id, bot_id, bot2_id]
    engine._end_game(room)
    
    # Check final state
    assert room.phase == 'finished', "Game should be finished"
    assert room.players[human_id].role == 'President', "First player should be President"
    assert room.players[bot_id].role == 'Vice President', "Second player should be Vice President"
    assert room.players[bot2_id].role == 'Asshole', "Last player should be Asshole"

def test_concurrent_bot_operations():
    """Test that bots can operate concurrently without conflicts"""
    engine = PresidentEngine()
    bot = GreedyBot(engine)
    
    # Create multiple rooms with bots
    rooms = []
    for i in range(3):
        room_id = f"concurrent_test_{i}"
        engine.create_room(room_id)
        
        # Add bots to each room
        for j in range(3):
            engine.add_player(room_id, f"Bot_{i}_{j}", True)
        
        rooms.append(room_id)
    
    # Set up concurrent bot operations
    results = []
    
    def bot_operation(room_id):
        try:
            room = engine.get_room(room_id)
            room.phase = 'play'
            
            # Give bots cards
            for player in room.players.values():
                player.hand = ['3S', '4H', '5D']
                player.hand_count = 3
            
            # Set first player as current turn
            first_player = list(room.players.keys())[0]
            room.turn = first_player
            
            # Bot makes a move
            bot.make_move(room_id, first_player)
            results.append(True)
        except Exception as e:
            print(f"Concurrent bot operation failed: {e}")
            results.append(False)
    
    # Run concurrent operations
    threads = []
    for room_id in rooms:
        thread = threading.Thread(target=bot_operation, args=(room_id,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    # All operations should succeed
    assert len(results) == 3, "Should have 3 results"
    assert all(results), "All concurrent bot operations should succeed"

def run_all_bot_multiplayer_tests():
    """Run all bot and multiplayer tests"""
    tester = BotMultiplayerTester()
    
    print("🤖 Testing Bot & Multiplayer Functionality")
    print("=" * 60)
    
    # Bot functionality tests
    tester.run_test(test_bot_can_make_moves)
    tester.run_test(test_bot_handles_special_effects)
    tester.run_test(test_bot_handles_discard_effect)
    tester.run_test(test_bot_manager_functionality)
    tester.run_test(test_bot_vs_bot_gameplay)
    
    # Multiplayer tests
    tester.run_test(test_multiplayer_room_creation)
    tester.run_test(test_multiplayer_game_flow)
    tester.run_test(test_multiplayer_with_special_effects)
    tester.run_test(test_game_completion_with_bots)
    tester.run_test(test_concurrent_bot_operations)
    
    return tester.summary()

if __name__ == "__main__":
    success = run_all_bot_multiplayer_tests()
    sys.exit(0 if success else 1) 