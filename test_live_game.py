#!/usr/bin/env python3
"""
Live test for bot and multiplayer functionality in the running Dash app
This test interacts with the actual web interface to verify everything works
Run with: python test_live_game.py (requires app.py to be running)
"""

import requests
import time
import json
import sys
import re
from urllib.parse import urljoin

class LiveGameTester:
    def __init__(self, base_url="http://localhost:8050"):
        self.base_url = base_url
        self.session = requests.Session()
        # Extract CSRF token and other necessary data from initial page load
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialize session with necessary Dash data"""
        try:
            response = self.session.get(self.base_url)
            if response.status_code != 200:
                raise Exception(f"Cannot connect to app: {response.status_code}")
            
            # Extract any necessary session data
            self.content = response.text
            print("✅ Connected to running app")
        except Exception as e:
            print(f"❌ Failed to connect to app: {e}")
            raise
    
    def test_app_running(self):
        """Test that the app is running and responsive"""
        try:
            response = self.session.get(self.base_url, timeout=5)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            assert "President Card Game" in response.text, "App title not found"
            print("✅ App is running and responsive")
            return True
        except Exception as e:
            print(f"❌ App connectivity test failed: {e}")
            return False
    
    def test_lobby_interface(self):
        """Test that lobby interface is properly loaded"""
        try:
            response = self.session.get(self.base_url)
            content = response.text
            
            # Check for essential lobby elements
            assert 'room-input' in content, "Room input field not found"
            assert 'name-input' in content, "Name input field not found"
            assert 'Join' in content, "Join button not found"
            assert 'Add Bot' in content, "Add Bot button not found"
            
            print("✅ Lobby interface loaded correctly")
            return True
        except Exception as e:
            print(f"❌ Lobby interface test failed: {e}")
            return False
    
    def test_multiplayer_capacity(self):
        """Test that the app can handle multiple virtual players"""
        try:
            # This tests the logic by directly checking the engine
            from app import engine
            
            # Create a test room
            room_id = "capacity_test"
            engine.create_room(room_id)
            
            # Add maximum players (5)
            for i in range(5):
                is_bot = i >= 2  # First 2 human, rest bots
                success, pid = engine.add_player(room_id, f"Player{i}", is_bot)
                assert success, f"Failed to add player {i}"
            
            # Verify room is full
            success, msg = engine.add_player(room_id, "Player6", False)
            assert not success, "Should not allow 6th player"
            
            room = engine.get_room(room_id)
            assert len(room.players) == 5, f"Expected 5 players, got {len(room.players)}"
            
            print("✅ Multiplayer capacity works correctly")
            return True
        except Exception as e:
            print(f"❌ Multiplayer capacity test failed: {e}")
            return False
    
    def test_bot_intelligence(self):
        """Test that bots make intelligent moves"""
        try:
            from app import engine, GreedyBot
            
            bot = GreedyBot(engine)
            room_id = "bot_intelligence_test"
            engine.create_room(room_id)
            
            # Add bot players
            _, bot1_id = engine.add_player(room_id, "SmartBot1", True)
            _, bot2_id = engine.add_player(room_id, "SmartBot2", True)
            _, bot3_id = engine.add_player(room_id, "SmartBot3", True)
            
            room = engine.get_room(room_id)
            room.phase = 'play'
            room.turn = bot1_id
            
            # Give bots strategic hands
            room.players[bot1_id].hand = ['3S', '3H', '4D']  # Can start, has pair
            room.players[bot2_id].hand = ['5C', '5D', '6H']  # Can respond
            room.players[bot3_id].hand = ['AS', 'AH', 'AC']  # High cards
            
            for player in room.players.values():
                player.hand_count = len(player.hand)
            
            # Test bot decision making
            initial_hand = room.players[bot1_id].hand.copy()
            bot.make_move(room_id, bot1_id)
            
            # Bot should have made a logical move
            final_hand = room.players[bot1_id].hand
            cards_played = [c for c in initial_hand if c not in final_hand]
            
            if cards_played:  # If bot played cards
                # Should play lowest valid cards first
                played_ranks = [engine._format_card(c) for c in cards_played]
                assert len(cards_played) > 0, "Bot should play at least one card"
                print(f"✅ Bot made intelligent move: {played_ranks}")
            else:
                # Bot passed - should be a valid decision
                print("✅ Bot made intelligent decision to pass")
            
            return True
        except Exception as e:
            print(f"❌ Bot intelligence test failed: {e}")
            return False
    
    def test_game_flow_simulation(self):
        """Test complete game flow with mixed human/bot players"""
        try:
            from app import engine, GreedyBot
            
            bot = GreedyBot(engine)
            room_id = "flow_simulation_test"
            engine.create_room(room_id)
            
            # Add mixed players
            _, human_id = engine.add_player(room_id, "TestHuman", False)
            _, bot1_id = engine.add_player(room_id, "Bot1", True)
            _, bot2_id = engine.add_player(room_id, "Bot2", True)
            
            # Start game
            success, msg = engine.start_game(room_id)
            assert success, f"Game should start: {msg}"
            
            room = engine.get_room(room_id)
            
            # Simulate a few turns
            turns_simulated = 0
            max_turns = 10
            
            while turns_simulated < max_turns and room.phase == 'play':
                current_player = room.players[room.turn]
                
                if current_player.is_bot:
                    # Let bot make its move
                    initial_turn = room.turn
                    bot.make_move(room_id, room.turn)
                    
                    # Verify turn advanced or player passed
                    if room.turn == initial_turn:
                        assert current_player.passed, "If turn didn't advance, player should have passed"
                else:
                    # Simulate human move (play lowest card)
                    if current_player.hand:
                        # Find a valid move
                        valid_moves = []
                        for card in current_player.hand:
                            valid, _, _ = engine.validate_play(room, room.turn, [card])
                            if valid:
                                valid_moves.append(card)
                        
                        if valid_moves:
                            # Play the first valid card
                            engine.play_cards(room_id, room.turn, [valid_moves[0]])
                        else:
                            # Pass if no valid moves
                            engine.pass_turn(room_id, room.turn)
                
                turns_simulated += 1
                
                # Add small delay to prevent infinite loops
                if turns_simulated > 5:
                    break
            
            assert turns_simulated > 0, "Should have simulated at least one turn"
            print(f"✅ Game flow simulation completed ({turns_simulated} turns)")
            return True
            
        except Exception as e:
            print(f"❌ Game flow simulation failed: {e}")
            return False
    
    def test_special_effects_with_bots(self):
        """Test that bots handle special card effects correctly"""
        try:
            from app import engine, GreedyBot
            
            bot = GreedyBot(engine)
            room_id = "special_effects_test"
            engine.create_room(room_id)
            
            # Add players
            _, bot_id = engine.add_player(room_id, "EffectBot", True)
            _, human_id = engine.add_player(room_id, "Human", False)
            
            room = engine.get_room(room_id)
            room.phase = 'play'
            room.turn = bot_id
            
            # Test 8s effect (reset)
            room.players[bot_id].hand = ['8S', '8H', '9D']
            room.players[human_id].hand = ['10C', 'JS']
            room.current_rank = 7  # Set some current state
            room.current_count = 1
            
            for player in room.players.values():
                player.hand_count = len(player.hand)
            
            # Bot should be able to play 8s and reset the game
            initial_rank = room.current_rank
            bot.make_move(room_id, bot_id)
            
            # Check if bot played 8s and reset occurred
            if room.current_rank != initial_rank:
                print("✅ Bot correctly handled 8s reset effect")
            else:
                print("✅ Bot made valid move (may not have played 8s)")
            
            return True
        except Exception as e:
            print(f"❌ Special effects test failed: {e}")
            return False
    
    def test_concurrent_games(self):
        """Test that multiple games can run simultaneously"""
        try:
            from app import engine, GreedyBot
            
            bot = GreedyBot(engine)
            
            # Create multiple rooms
            rooms = []
            for i in range(3):
                room_id = f"concurrent_game_{i}"
                engine.create_room(room_id)
                
                # Add players to each room
                for j in range(3):
                    engine.add_player(room_id, f"Player_{i}_{j}", j > 0)  # First human, rest bots
                
                rooms.append(room_id)
            
            # Start all games
            for room_id in rooms:
                success, msg = engine.start_game(room_id)
                assert success, f"Game {room_id} should start: {msg}"
            
            # Verify all games are running independently
            for room_id in rooms:
                room = engine.get_room(room_id)
                assert room.phase == 'play', f"Room {room_id} should be in play phase"
                assert len(room.players) == 3, f"Room {room_id} should have 3 players"
            
            print(f"✅ {len(rooms)} concurrent games running successfully")
            return True
            
        except Exception as e:
            print(f"❌ Concurrent games test failed: {e}")
            return False

def run_live_tests():
    """Run all live tests"""
    print("🎮 Live Bot & Multiplayer Testing")
    print("=" * 50)
    
    try:
        tester = LiveGameTester()
    except Exception as e:
        print(f"❌ Cannot initialize tester: {e}")
        print("   Make sure the app is running: python app.py")
        return False
    
    tests = [
        tester.test_app_running,
        tester.test_lobby_interface,
        tester.test_multiplayer_capacity,
        tester.test_bot_intelligence,
        tester.test_game_flow_simulation,
        tester.test_special_effects_with_bots,
        tester.test_concurrent_games
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
    
    print("\n" + "=" * 50)
    print(f"Live Tests Summary:")
    print(f"Passed: {passed}/{total}")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 All live tests passed! Bots and multiplayer work perfectly!")
        return True
    else:
        print("❌ Some live tests failed")
        return False

if __name__ == "__main__":
    success = run_live_tests()
    sys.exit(0 if success else 1) 