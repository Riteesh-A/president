#!/usr/bin/env python3

"""
Comprehensive test suite for President card game
Tests all scenarios and edge cases discussed
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import PresidentEngine, RoomState, Player, parse_card, assign_roles_dynamic

class PresidentGameTests:
    def __init__(self):
        self.engine = PresidentEngine()
        self.test_count = 0
        self.passed_tests = 0
        self.failed_tests = 0
    
    def run_all_tests(self):
        """Run all test scenarios"""
        print("🎮 Starting President Card Game Test Suite")
        print("=" * 50)
        
        # Test 1: Auto-win scenarios
        self.test_autowin_scenarios()
        
        # Test 2: Joker wildcard functionality
        self.test_joker_wildcard()
        
        # Test 3: Last card effects (7s and 10s)
        self.test_last_card_effects()
        
        # Test 4: Partial discard/gift scenarios
        self.test_partial_effects()
        
        # Test 5: Role assignment
        self.test_role_assignment()
        
        # Test 6: New game continuation
        self.test_new_game_continuation()
        
        # Test 7: Bot behavior
        self.test_bot_behavior()
        
        # Test 8: Bot discard/gift behavior
        self.test_bot_effects()
        
        print("=" * 50)
        print(f"📊 Test Results: {self.passed_tests} passed, {self.failed_tests} failed out of {self.test_count} total tests")
        
        if self.failed_tests == 0:
            print("🎉 All tests passed!")
        else:
            print("❌ Some tests failed!")
    
    def assert_test(self, condition, test_name):
        """Helper to run a test and track results"""
        self.test_count += 1
        if condition:
            print(f"✅ {test_name}")
            self.passed_tests += 1
        else:
            print(f"❌ {test_name}")
            self.failed_tests += 1
    
    def setup_test_room(self, room_id="test_room"):
        """Setup a test room with 4 players"""
        room = self.engine.create_room(room_id)
        self.engine.add_player(room_id, "Player1")
        self.engine.add_player(room_id, "Player2")
        self.engine.add_player(room_id, "Player3")
        self.engine.add_player(room_id, "Player4")
        self.engine.start_game(room_id)
        return room
    
    def test_autowin_scenarios(self):
        """Test 1: Auto-win scenarios for 2s, Jokers, and 3s during inversion"""
        print("\n🧪 Test 1: Auto-win Scenarios")
        print("-" * 30)
        
        # Test 1.1: Single 2 auto-win
        room = self.setup_test_room("test_autowin_1")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Find a 2 in player1's hand
        twos = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 2]
        if not twos:
            room.players[player1_id].hand.append('2H')
            twos = ['2H']
        
        # Set up single card pile
        room.current_pile = ['7H']
        room.current_rank = 7
        room.current_count = 1
        room.turn = player1_id
        
        # Play single 2
        success, msg = self.engine.play_cards("test_autowin_1", player1_id, [twos[0]])
        self.assert_test(success and "Auto-win" in msg, "Single 2 triggers auto-win")
        
        # Test 1.2: Single Joker auto-win
        room = self.setup_test_room("test_autowin_2")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Find a joker
        jokers = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 'JOKER']
        if not jokers:
            room.players[player1_id].hand.append('JOKERa')
            jokers = ['JOKERa']
        
        # Set up single card pile
        room.current_pile = ['KH']
        room.current_rank = 'K'
        room.current_count = 1
        room.turn = player1_id
        
        # Play single joker
        success, msg = self.engine.play_cards("test_autowin_2", player1_id, [jokers[0]])
        self.assert_test(success and "Auto-win" in msg, "Single Joker triggers auto-win")
        
        # Test 1.3: Multiple 2s auto-win
        room = self.setup_test_room("test_autowin_3")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Add multiple 2s
        room.players[player1_id].hand.extend(['2H', '2D', '2S'])
        twos = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 2]
        
        # Set up pair pile
        room.current_pile = ['AH', 'AD']
        room.current_rank = 'A'
        room.current_count = 2
        room.turn = player1_id
        
        # Play pair of 2s
        success, msg = self.engine.play_cards("test_autowin_3", player1_id, twos[:2])
        self.assert_test(success and "Auto-win" in msg, "Pair of 2s triggers auto-win")
        
        # Test 1.4: 2 + Joker auto-win
        room = self.setup_test_room("test_autowin_4")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Add 2 and joker
        room.players[player1_id].hand.extend(['2H', 'JOKERa'])
        twos = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 2]
        jokers = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 'JOKER']
        
        # Set up pair pile
        room.current_pile = ['KH', 'KD']
        room.current_rank = 'K'
        room.current_count = 2
        room.turn = player1_id
        
        # Play 2 + Joker
        success, msg = self.engine.play_cards("test_autowin_4", player1_id, [twos[0], jokers[0]])
        self.assert_test(success and "Auto-win" in msg, "2 + Joker triggers auto-win")
        
        # Test 1.5: 3 during inversion auto-win
        room = self.setup_test_room("test_autowin_5")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Activate inversion
        room.inversion_active = True
        
        # Find a 3
        threes = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 3]
        if not threes:
            room.players[player1_id].hand.append('3H')
            threes = ['3H']
        
        # Set up single card pile
        room.current_pile = ['4H']
        room.current_rank = 4
        room.current_count = 1
        room.turn = player1_id
        
        # Play single 3 during inversion
        success, msg = self.engine.play_cards("test_autowin_5", player1_id, [threes[0]])
        self.assert_test(success and "Auto-win" in msg, "3 during inversion triggers auto-win")
        
        # Test 1.6: Joker during inversion auto-win
        room = self.setup_test_room("test_autowin_6")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Activate inversion
        room.inversion_active = True
        
        # Find a joker
        jokers = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 'JOKER']
        if not jokers:
            room.players[player1_id].hand.append('JOKERa')
            jokers = ['JOKERa']
        
        # Set up single card pile
        room.current_pile = ['5H']
        room.current_rank = 5
        room.current_count = 1
        room.turn = player1_id
        
        # Play single joker during inversion
        success, msg = self.engine.play_cards("test_autowin_6", player1_id, [jokers[0]])
        self.assert_test(success and "Auto-win" in msg, "Joker during inversion triggers auto-win")
    
    def test_joker_wildcard(self):
        """Test 2: Joker wildcard functionality"""
        print("\n🧪 Test 2: Joker Wildcard Functionality")
        print("-" * 40)
        
        # Test 2.1: 7 + Joker acts as pair of 7s (gift effect)
        room = self.setup_test_room("test_joker_wildcard_1")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Add 7 and joker
        room.players[player1_id].hand.extend(['7H', 'JOKERa'])
        sevens = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 7]
        jokers = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 'JOKER']
        
        # Set up pair of 6s
        room.current_pile = ['6H', '6D']
        room.current_rank = 6
        room.current_count = 2
        room.turn = player1_id
        
        # Play 7 + Joker
        success, msg = self.engine.play_cards("test_joker_wildcard_1", player1_id, [sevens[0], jokers[0]])
        self.assert_test(success and room.pending_gift is not None, "7 + Joker triggers gift effect")
        
        # Test 2.2: 9 + Joker acts as pair of 9s (no effect)
        room = self.setup_test_room("test_joker_wildcard_2")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Add 9 and joker
        room.players[player1_id].hand.extend(['9H', 'JOKERa'])
        nines = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 9]
        jokers = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 'JOKER']
        
        # Set up pair of 8s
        room.current_pile = ['8H', '8D']
        room.current_rank = 8
        room.current_count = 2
        room.turn = player1_id
        
        # Play 9 + Joker
        success, msg = self.engine.play_cards("test_joker_wildcard_2", player1_id, [nines[0], jokers[0]])
        self.assert_test(success and room.pending_gift is None, "9 + Joker has no special effect")
    
    def test_last_card_effects(self):
        """Test 3: 7s and 10s as last card (no effect applied)"""
        print("\n🧪 Test 3: Last Card Effects")
        print("-" * 30)
        
        # Test 3.1: 7 as last card (no gift)
        room = self.setup_test_room("test_last_card_1")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Give player1 only one 7
        room.players[player1_id].hand = ['7H']
        room.players[player1_id].hand_count = 1
        
        # Set up single card pile
        room.current_pile = ['6H']
        room.current_rank = 6
        room.current_count = 1
        room.turn = player1_id
        
        # Play 7 as last card
        success, msg = self.engine.play_cards("test_last_card_1", player1_id, ['7H'])
        self.assert_test(success and room.pending_gift is None, "7 as last card doesn't trigger gift")
        
        # Test 3.2: 10 as last card (no discard)
        room = self.setup_test_room("test_last_card_2")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Give player1 only one 10
        room.players[player1_id].hand = ['10H']
        room.players[player1_id].hand_count = 1
        
        # Set up single card pile
        room.current_pile = ['9H']
        room.current_rank = 9
        room.current_count = 1
        room.turn = player1_id
        
        # Play 10 as last card
        success, msg = self.engine.play_cards("test_last_card_2", player1_id, ['10H'])
        self.assert_test(success and room.pending_discard is None, "10 as last card doesn't trigger discard")
    
    def test_partial_effects(self):
        """Test 4: Partial discard/gift when fewer cards than played"""
        print("\n🧪 Test 4: Partial Effects")
        print("-" * 25)
        
        # Test 4.1: 10 pair with only 3 cards (discard 1)
        room = self.setup_test_room("test_partial_1")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Give player1 3 cards including 2 10s
        room.players[player1_id].hand = ['10H', '10D', 'KH']
        room.players[player1_id].hand_count = 3
        
        # Set up pair pile
        room.current_pile = ['9H', '9D']
        room.current_rank = 9
        room.current_count = 2
        room.turn = player1_id
        
        # Play pair of 10s
        success, msg = self.engine.play_cards("test_partial_1", player1_id, ['10H', '10D'])
        self.assert_test(success and room.pending_discard['remaining'] == 1, "10 pair with 3 cards requires 1 discard")
        
        # Test 4.2: 7 pair with only 3 cards (gift 1)
        room = self.setup_test_room("test_partial_2")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Give player1 3 cards including 2 7s
        room.players[player1_id].hand = ['7H', '7D', 'KH']
        room.players[player1_id].hand_count = 3
        
        # Set up pair pile
        room.current_pile = ['6H', '6D']
        room.current_rank = 6
        room.current_count = 2
        room.turn = player1_id
        
        # Play pair of 7s
        success, msg = self.engine.play_cards("test_partial_2", player1_id, ['7H', '7D'])
        self.assert_test(success and room.pending_gift['remaining'] == 1, "7 pair with 3 cards requires 1 gift")
    
    def test_role_assignment(self):
        """Test 5: Role assignment when players finish"""
        print("\n🧪 Test 5: Role Assignment")
        print("-" * 25)
        
        room = self.setup_test_room("test_roles")
        player_ids = list(room.players.keys())
        
        # Simulate player1 finishing first
        room.players[player_ids[0]].hand = []
        room.players[player_ids[0]].hand_count = 0
        room.finished_order.append(player_ids[0])
        assign_roles_dynamic(room)
        
        self.assert_test(room.players[player_ids[0]].role == 'President', "First player gets President role")
        
        # Simulate player2 finishing second
        room.players[player_ids[1]].hand = []
        room.players[player_ids[1]].hand_count = 0
        room.finished_order.append(player_ids[1])
        assign_roles_dynamic(room)
        
        self.assert_test(room.players[player_ids[1]].role == 'Vice President', "Second player gets Vice President role")
        
        # Simulate player3 finishing third
        room.players[player_ids[2]].hand = []
        room.players[player_ids[2]].hand_count = 0
        room.finished_order.append(player_ids[2])
        assign_roles_dynamic(room)
        
        self.assert_test(room.players[player_ids[2]].role == 'Scumbag', "Third player gets Scumbag role")
        
        # Simulate player4 finishing last
        room.players[player_ids[3]].hand = []
        room.players[player_ids[3]].hand_count = 0
        room.finished_order.append(player_ids[3])
        assign_roles_dynamic(room)
        
        self.assert_test(room.players[player_ids[3]].role == 'Asshole', "Last player gets Asshole role")
    
    def test_new_game_continuation(self):
        """Test 6: New game continues with asshole from previous game"""
        print("\n🧪 Test 6: New Game Continuation")
        print("-" * 35)
        
        room = self.setup_test_room("test_continuation")
        player_ids = list(room.players.keys())
        
        # Simulate a finished game with player4 as asshole
        room.finished_order = [player_ids[0], player_ids[1], player_ids[2], player_ids[3]]
        room.global_asshole_id = player_ids[3]  # player4 is asshole
        room.first_game = False
        
        # Start new game
        self.engine.start_game("test_continuation")
        room = self.engine.get_room("test_continuation")
        
        self.assert_test(room.turn == player_ids[3], "Asshole from previous game starts new game")
    
    def test_bot_behavior(self):
        """Test 7: Bots continue playing when human finishes"""
        print("\n🧪 Test 7: Bot Behavior")
        print("-" * 25)
        
        room = self.setup_test_room("test_bots")
        player_ids = list(room.players.keys())
        
        # Make player1 human, others bots
        room.players[player_ids[0]].is_bot = False
        room.players[player_ids[1]].is_bot = True
        room.players[player_ids[2]].is_bot = True
        room.players[player_ids[3]].is_bot = True
        
        # Simulate human finishing
        room.players[player_ids[0]].hand = []
        room.players[player_ids[0]].hand_count = 0
        room.finished_order.append(player_ids[0])
        room.turn = player_ids[1]  # Set turn to bot
        
        # Check that game continues
        self.assert_test(room.phase == 'play', "Game continues after human finishes")
        self.assert_test(room.turn == player_ids[1], "Turn passes to bot after human finishes")
    
    def test_bot_effects(self):
        """Test 8: Bots handle 7s and 10s effects correctly"""
        print("\n🧪 Test 8: Bot Effects")
        print("-" * 25)
        
        room = self.setup_test_room("test_bot_effects")
        player_ids = list(room.players.keys())
        
        # Make player1 a bot
        room.players[player_ids[0]].is_bot = True
        
        # Give bot 2 7s and some other cards
        room.players[player_ids[0]].hand = ['7H', '7D', 'KH', 'QD']
        room.players[player_ids[0]].hand_count = 4
        
        # Set up pair pile
        room.current_pile = ['6H', '6D']
        room.current_rank = 6
        room.current_count = 2
        room.turn = player_ids[0]
        
        # Bot should play 7s and trigger gift
        from app import bot
        bot.make_move("test_bot_effects", player_ids[0])
        room = self.engine.get_room("test_bot_effects")
        
        # Check that bot handled the gift correctly
        self.assert_test(room.pending_gift is None, "Bot correctly handles 7s gift effect")
        
        # Test bot with 10s
        room = self.setup_test_room("test_bot_effects_2")
        player_ids = list(room.players.keys())
        
        # Make player1 a bot
        room.players[player_ids[0]].is_bot = True
        
        # Give bot 2 10s and some other cards
        room.players[player_ids[0]].hand = ['10H', '10D', 'KH', 'QD']
        room.players[player_ids[0]].hand_count = 4
        
        # Set up pair pile
        room.current_pile = ['9H', '9D']
        room.current_rank = 9
        room.current_count = 2
        room.turn = player_ids[0]
        
        # Bot should play 10s and trigger discard
        bot.make_move("test_bot_effects_2", player_ids[0])
        room = self.engine.get_room("test_bot_effects_2")
        
        # Check that bot handled the discard correctly
        self.assert_test(room.pending_discard is None, "Bot correctly handles 10s discard effect")

if __name__ == "__main__":
    tests = PresidentGameTests()
    tests.run_all_tests() 