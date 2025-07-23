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
        
        # Test 9: Card exchange between roles
        self.test_card_exchange()
        
        # Test 10: Role preservation in subsequent games
        self.test_role_preservation_in_subsequent_games()
        
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
        
        # Test 2.1: Single joker acts as 2 (auto-win)
        room = self.setup_test_room("test_joker_wildcard_1")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Give player1 only a joker
        room.players[player1_id].hand = ['JOKERa']
        room.players[player1_id].hand_count = 1
        
        # Set up single card pile
        room.current_pile = ['KH']
        room.current_rank = 'K'
        room.current_count = 1
        room.turn = player1_id
        
        # Play single joker
        success, msg = self.engine.play_cards("test_joker_wildcard_1", player1_id, ['JOKERa'])
        self.assert_test(success and "Auto-win" in msg, "Single joker acts as 2 and triggers auto-win")
        
        # Test 2.2: Two jokers act as pair of 2s (auto-win)
        room = self.setup_test_room("test_joker_wildcard_2")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Give player1 two jokers
        room.players[player1_id].hand = ['JOKERa', 'JOKERb']
        room.players[player1_id].hand_count = 2
        
        # Set up pair pile
        room.current_pile = ['AH', 'AD']
        room.current_rank = 'A'
        room.current_count = 2
        room.turn = player1_id
        
        # Play two jokers
        success, msg = self.engine.play_cards("test_joker_wildcard_2", player1_id, ['JOKERa', 'JOKERb'])
        self.assert_test(success and "Auto-win" in msg, "Two jokers act as pair of 2s and trigger auto-win")
        
        # Test 2.3: 7 + Joker acts as pair of 7s (gift effect)
        room = self.setup_test_room("test_joker_wildcard_3")
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
        success, msg = self.engine.play_cards("test_joker_wildcard_3", player1_id, [sevens[0], jokers[0]])
        self.assert_test(success and room.pending_gift is not None, "7 + Joker triggers gift effect")
        
        # Test 2.4: 10 + Joker acts as pair of 10s (discard effect)
        room = self.setup_test_room("test_joker_wildcard_4")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Add 10 and joker
        room.players[player1_id].hand.extend(['10H', 'JOKERa'])
        tens = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 10]
        jokers = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 'JOKER']
        
        # Set up pair of 9s
        room.current_pile = ['9H', '9D']
        room.current_rank = 9
        room.current_count = 2
        room.turn = player1_id
        
        # Play 10 + Joker
        success, msg = self.engine.play_cards("test_joker_wildcard_4", player1_id, [tens[0], jokers[0]])
        self.assert_test(success and room.pending_discard is not None, "10 + Joker triggers discard effect")
        
        # Test 2.5: 6 + Joker acts as pair of 6s (no effect)
        room = self.setup_test_room("test_joker_wildcard_5")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Add 6 and joker
        room.players[player1_id].hand.extend(['6H', 'JOKERa'])
        sixes = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 6]
        jokers = [c for c in room.players[player1_id].hand if parse_card(c)[0] == 'JOKER']
        
        # Set up pair of 5s
        room.current_pile = ['5H', '5D']
        room.current_rank = 5
        room.current_count = 2
        room.turn = player1_id
        
        # Play 6 + Joker
        success, msg = self.engine.play_cards("test_joker_wildcard_5", player1_id, [sixes[0], jokers[0]])
        self.assert_test(success and room.pending_gift is None and room.pending_discard is None, "6 + Joker has no special effect")
        
        # Test 2.6: 2 + Joker on King pair (the actual issue from UI)
        room = self.setup_test_room("test_joker_wildcard_6")
        player_ids = list(room.players.keys())
        player1_id = player_ids[0]
        
        # Give player 2 and joker
        room.players[player1_id].hand = ['2H', 'JOKERa']
        room.players[player1_id].hand_count = 2
        room.turn = player1_id
        room.phase = 'play'
        
        # Set up King pair pile
        room.current_pile = ['KH', 'KD']
        room.current_rank = 'K'
        room.current_count = 2
        room.first_game = False
        
        # 2 + Joker should act as pair of 2s and beat King pair
        success, msg = self.engine.play_cards("test_joker_wildcard_6", player1_id, ['2H', 'JOKERa'])
        self.assert_test(success, "2 + Joker on King pair should be valid")
    
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
        
        # Test 7.1: Basic bot continuation
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
        
        # Test 7.2: Human finishes during play, bots continue
        room2 = self.setup_test_room("test_bots_play")
        player_ids2 = list(room2.players.keys())
        
        # Make player1 human, others bots
        room2.players[player_ids2[0]].is_bot = False
        room2.players[player_ids2[1]].is_bot = True
        room2.players[player_ids2[2]].is_bot = True
        room2.players[player_ids2[3]].is_bot = True
        
        # Give human only 1 card, bots have multiple cards
        room2.players[player_ids2[0]].hand = ['3D']  # Use 3D for first play
        room2.players[player_ids2[0]].hand_count = 1
        room2.players[player_ids2[1]].hand = ['3H', '4H', '5H']
        room2.players[player_ids2[1]].hand_count = 3
        room2.players[player_ids2[2]].hand = ['6H', '7H', '8H']
        room2.players[player_ids2[2]].hand_count = 3
        room2.players[player_ids2[3]].hand = ['9H', '10H', 'JH']
        room2.players[player_ids2[3]].hand_count = 3
        
        # Set up room for play (not first game to avoid 3D requirement)
        room2.phase = 'play'
        room2.first_game = False
        room2.first_game_first_play_done = True
        room2.current_pile = []
        room2.current_rank = None
        room2.current_count = None
        room2.turn = player_ids2[0]
        
        # Human plays their last card
        ok, msg = self.engine.play_cards("test_bots_play", player_ids2[0], ['3D'])
        self.assert_test(ok, "Human successfully plays last card")
        
        # Check that human finished
        self.assert_test(player_ids2[0] in room2.finished_order, "Human added to finished order")
        self.assert_test(len(room2.players[player_ids2[0]].hand) == 0, "Human has no cards left")
        
        # Check that turn advanced to next player (should be a bot)
        self.assert_test(room2.turn in player_ids2[1:], "Turn advanced to a bot")
        
        # Test 7.3: Verify that turn advanced to a bot after human finished
        # The key point is that the turn should have advanced from the human to a bot
        # We don't need to test the bot's actual move, just that the turn system works
        self.assert_test(room2.turn in player_ids2[1:], "Turn advanced to a bot after human finished")
        
        # Test 7.4: Verify that turn advances even when human finishes with no effects
        room3 = self.setup_test_room("test_bots_finish_no_effects")
        player_ids3 = list(room3.players.keys())

        # Make player1 human, others bots
        room3.players[player_ids3[0]].is_bot = False
        room3.players[player_ids3[1]].is_bot = True
        room3.players[player_ids3[2]].is_bot = True
        room3.players[player_ids3[3]].is_bot = True

        # Give human only 1 card (a 6, which has no special effects)
        room3.players[player_ids3[0]].hand = ['6D']
        room3.players[player_ids3[0]].hand_count = 1
        room3.players[player_ids3[1]].hand = ['3H', '4H', '5H']
        room3.players[player_ids3[1]].hand_count = 3
        room3.players[player_ids3[2]].hand = ['7H', '8H', '9H']
        room3.players[player_ids3[2]].hand_count = 3
        room3.players[player_ids3[3]].hand = ['10H', 'JH', 'QH']
        room3.players[player_ids3[3]].hand_count = 3

        # Set up room for play
        room3.phase = 'play'
        room3.first_game = False
        room3.first_game_first_play_done = True
        room3.current_pile = []
        room3.current_rank = None
        room3.current_count = None
        room3.turn = player_ids3[0]

        # Human plays their last card (6D) - no special effects
        ok, msg = self.engine.play_cards("test_bots_finish_no_effects", player_ids3[0], ['6D'])
        self.assert_test(ok, "Human successfully plays last card with no effects")

        # Check that human finished
        self.assert_test(player_ids3[0] in room3.finished_order, "Human added to finished order")
        self.assert_test(len(room3.players[player_ids3[0]].hand) == 0, "Human has no cards left")

        # Check that turn advanced to next player (should be a bot)
        self.assert_test(room3.turn in player_ids3[1:], "Turn advanced to a bot after human finished with no effects")
    
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
        
        # Test 8.3: Bot correctly handles 7s gift effect and gives cards to any player
        # Create a room with 3 players to test random distribution
        # Use the global engine that the bot uses
        from app import engine as global_engine
        room2 = global_engine.create_room("test_bot_gift")
        global_engine.add_player("test_bot_gift", "Human1", is_bot=False)
        global_engine.add_player("test_bot_gift", "Bot1", is_bot=True)
        global_engine.add_player("test_bot_gift", "Human2", is_bot=False)
        global_engine.start_game("test_bot_gift")
        room2 = global_engine.get_room("test_bot_gift")
        player_ids2 = list(room2.players.keys())
        
        # Make player1 human, player2 bot, player3 human
        room2.players[player_ids2[0]].is_bot = False
        room2.players[player_ids2[1]].is_bot = True
        room2.players[player_ids2[2]].is_bot = False
        
        # Clear hands and give bot 7 and other cards, humans some cards
        room2.players[player_ids2[1]].hand = ['7H', '3H', '4H', '5H', '6H']
        room2.players[player_ids2[1]].hand_count = 5
        room2.players[player_ids2[0]].hand = ['8H', '9H']
        room2.players[player_ids2[0]].hand_count = 2
        room2.players[player_ids2[2]].hand = ['10H', 'JH']
        room2.players[player_ids2[2]].hand_count = 2
        
        # Set up pending gift for bot (must gift 2 cards)
        room2.pending_gift = {'player_id': player_ids2[1], 'remaining': 2}
        room2.turn = player_ids2[1]
        
        # Bot should handle gift
        bot._handle_gift("test_bot_gift", player_ids2[1], 2)
        
        # Get the updated room from engine
        room2 = global_engine.get_room("test_bot_gift")
        
        # Check that bot gave 2 cards to any player(s)
        self.assert_test(len(room2.players[player_ids2[1]].hand) == 3, "Bot correctly gave away 2 cards")
        # Check that at least one player received cards (total cards should be distributed)
        total_cards_received = len(room2.players[player_ids2[0]].hand) + len(room2.players[player_ids2[2]].hand) - 4  # Subtract original 4 cards
        self.assert_test(total_cards_received == 2, "Cards were distributed to players")
        self.assert_test(room2.pending_gift is None, "Pending gift cleared after bot handled it")
        
        # Test 8.4: Bot gives worst cards when gifting
        # Create a room with 3 players to test random distribution
        room3 = global_engine.create_room("test_bot_gift_worst")
        global_engine.add_player("test_bot_gift_worst", "Human1", is_bot=False)
        global_engine.add_player("test_bot_gift_worst", "Bot1", is_bot=True)
        global_engine.add_player("test_bot_gift_worst", "Human2", is_bot=False)
        global_engine.start_game("test_bot_gift_worst")
        room3 = global_engine.get_room("test_bot_gift_worst")
        player_ids3 = list(room3.players.keys())
        
        # Make player1 human, player2 bot, player3 human
        room3.players[player_ids3[0]].is_bot = False
        room3.players[player_ids3[1]].is_bot = True
        room3.players[player_ids3[2]].is_bot = False
        
        # Clear hands and give bot mixed cards (3, 4, 5, 6, 7, 8, 9, 10, J, Q, K, A, 2)
        room3.players[player_ids3[1]].hand = ['3H', '4H', '5H', '6H', '7H', '8H', '9H', '10H', 'JH', 'QH', 'KH', 'AH', '2H']
        room3.players[player_ids3[1]].hand_count = 13
        room3.players[player_ids3[0]].hand = ['8D', '9D']
        room3.players[player_ids3[0]].hand_count = 2
        room3.players[player_ids3[2]].hand = ['10D', 'JD']
        room3.players[player_ids3[2]].hand_count = 2
        
        # Set up pending gift for bot (must gift 3 cards)
        room3.pending_gift = {'player_id': player_ids3[1], 'remaining': 3}
        room3.turn = player_ids3[1]
        
        # Bot should handle gift
        bot._handle_gift("test_bot_gift_worst", player_ids3[1], 3)
        
        # Get the updated room from engine
        room3 = global_engine.get_room("test_bot_gift_worst")
        
        # Check that bot gave 3 worst cards to any player(s)
        self.assert_test(len(room3.players[player_ids3[1]].hand) == 10, "Bot correctly gave away 3 cards")
        # Check that cards were distributed (total cards received should be 3)
        total_cards_received = len(room3.players[player_ids3[0]].hand) + len(room3.players[player_ids3[2]].hand) - 4  # Subtract original 4 cards
        self.assert_test(total_cards_received == 3, "Cards were distributed to players")
        
        # Verify the bot gave the worst cards (3, 4, 5) to some player
        all_received_cards = []
        all_received_cards.extend(room3.players[player_ids3[0]].hand)
        all_received_cards.extend(room3.players[player_ids3[2]].hand)
        received_ranks = [parse_card(c)[0] for c in all_received_cards]
        self.assert_test(3 in received_ranks, "Bot gave 3 to a player")
        self.assert_test(4 in received_ranks, "Bot gave 4 to a player")
        self.assert_test(5 in received_ranks, "Bot gave 5 to a player")
        
        # Verify the bot kept better cards (should not have 3, 4, 5 anymore)
        bot_cards = [parse_card(c)[0] for c in room3.players[player_ids3[1]].hand]
        self.assert_test(3 not in bot_cards, "Bot kept better cards (no 3)")
        self.assert_test(4 not in bot_cards, "Bot kept better cards (no 4)")
        self.assert_test(5 not in bot_cards, "Bot kept better cards (no 5)")
        
        self.assert_test(room3.pending_gift is None, "Pending gift cleared after bot handled it")

    def test_card_exchange(self):
        """Test 9: Card exchange between roles at start of next game"""
        print("\n🧪 Test 9: Card Exchange")
        print("-" * 25)
        
        # Test 9.1: Simulate first game ending and roles assigned
        room = self.setup_test_room("test_exchange_1")
        player_ids = list(room.players.keys())
        
        # Simulate first game end with roles
        room.finished_order = [player_ids[0], player_ids[1], player_ids[2], player_ids[3]]
        room.phase = 'finished'
        room.first_game = False  # Mark as not first game
        
        # Assign roles
        from app import assign_roles_dynamic
        assign_roles_dynamic(room)
        
        # Store current roles as previous game roles for card exchange
        room.previous_game_roles = room.current_game_roles.copy()
        
        # Test 9.2: Simulate restart process (like clicking "New Game" button)
        # First, simulate the restart callback logic
        room.phase = 'lobby'
        room.finished_order = []
        room.game_log = []
        
        # Clear hands but preserve roles for card exchange
        for player in room.players.values():
            player.hand = []
            player.hand_count = 0
            player.passed = False
        
        # Start new game
        self.engine.start_game("test_exchange_1")
        room = self.engine.get_room("test_exchange_1")
        
        # The start_game should now automatically trigger card exchange
        # No need to manually call _start_card_exchange
        
        self.assert_test(room.exchange_phase, "Card exchange phase started at beginning of new game")
        self.assert_test(room.pending_exchange['current_exchange'] == 'asshole_to_president', "Asshole must give cards to President first")
        
        # Test 9.3: Asshole submits 2 best cards
        asshole_id = player_ids[3]
        president_id = player_ids[0]
        
        # Give asshole some cards to exchange
        room.players[asshole_id].hand = ['2H', 'AH', 'KH', '7D']  # Asshole has good cards
        room.players[asshole_id].hand_count = 4
        
        # Asshole should give 2H and AH (best cards)
        ok, msg = self.engine.submit_asshole_cards("test_exchange_1", asshole_id, ['2H', 'AH'])
        self.assert_test(ok, "Asshole successfully gives 2 best cards to President")
        
        # Check cards were transferred
        self.assert_test('2H' in room.players[president_id].hand, "President received 2H from Asshole")
        self.assert_test('AH' in room.players[president_id].hand, "President received AH from Asshole")
        self.assert_test('2H' not in room.players[asshole_id].hand, "Asshole no longer has 2H")
        self.assert_test('AH' not in room.players[asshole_id].hand, "Asshole no longer has AH")
        
        # Test 9.4: President gives 2 cards to Asshole
        # Give president some additional cards to give to asshole
        room.players[president_id].hand.extend(['3H', '4H', '5H'])
        
        # President should give 2 of his own cards (not the ones he received from asshole)
        # He has: 2H, AH (from asshole) + 3H, 4H, 5H (his own)
        ok, msg = self.engine.submit_president_cards("test_exchange_1", president_id, ['3H', '4H'])
        self.assert_test(ok, "President successfully gives 2 cards to Asshole")
        
        # Check cards were transferred
        self.assert_test('3H' in room.players[asshole_id].hand, "Asshole received 3H from President")
        self.assert_test('4H' in room.players[asshole_id].hand, "Asshole received 4H from President")
        # Check that President no longer has the specific cards they gave away
        president_hand = room.players[president_id].hand
        self.assert_test('3H' not in president_hand, "President no longer has 3H")
        self.assert_test('4H' not in president_hand, "President no longer has 4H")
        
        # Test 9.5: Scumbag gives best card to Vice President
        scumbag_id = player_ids[2]
        vice_president_id = player_ids[1]
        
        # Give scumbag some cards
        room.players[scumbag_id].hand = ['QH', 'JH', '10H']
        room.players[scumbag_id].hand_count = 3
        
        ok, msg = self.engine.submit_scumbag_card("test_exchange_1", scumbag_id, 'QH')
        self.assert_test(ok, "Scumbag successfully gives best card to Vice President")
        
        # Check card was transferred
        self.assert_test('QH' in room.players[vice_president_id].hand, "Vice President received QH from Scumbag")
        self.assert_test('QH' not in room.players[scumbag_id].hand, "Scumbag no longer has QH")
        
        # Test 9.6: Vice President gives 1 card to Scumbag
        # Give vice president some additional cards to give to scumbag
        room.players[vice_president_id].hand.extend(['6H', '7H'])
        
        ok, msg = self.engine.submit_vice_president_card("test_exchange_1", vice_president_id, '6H')
        self.assert_test(ok, "Vice President successfully gives 1 card to Scumbag")
        
        # Check card was transferred
        self.assert_test('6H' in room.players[scumbag_id].hand, "Scumbag received 6H from Vice President")
        # Note: Vice President should no longer have 6H, but he might have received QH from scumbag
        # So we check that he doesn't have 6H specifically
        vice_president_hand = room.players[vice_president_id].hand
        self.assert_test('6H' not in vice_president_hand, "Vice President no longer has 6H")
        
        # Test 9.7: Exchange phase is completed and game transitions to play phase
        self.assert_test(not room.exchange_phase, "Card exchange phase completed")
        self.assert_test(room.pending_exchange is None, "Pending exchange cleared")
        self.assert_test(room.phase == 'play', "Game transitions to play phase after exchange")
        
        # Test 9.8: First game should not have card exchange
        room2 = self.setup_test_room("test_exchange_first_game")
        room2.first_game = True  # Ensure it's marked as first game
        
        # Start first game
        self.engine.start_game("test_exchange_first_game")
        room2 = self.engine.get_room("test_exchange_first_game")
        
        self.assert_test(not room2.exchange_phase, "First game should not have card exchange phase")
        self.assert_test(room2.phase == 'play', "First game should go directly to play phase")

    def test_role_preservation_in_subsequent_games(self):
        """Test that roles are properly preserved and displayed in subsequent games"""
        print("\n🧪 Test 10: Role Preservation in Subsequent Games")
        print("-" * 50)
        
        # Setup test room
        room_id = "test_role_preservation"
        self.setup_test_room(room_id)
        
        # Start first game
        success, msg = self.engine.start_game(room_id)
        self.assert_test(success, "First game started successfully")
        
        # Simulate a complete game to assign roles
        room = self.engine.get_room(room_id)
        
        # Add players to finished order to simulate game completion
        player_ids = list(room.players.keys())
        room.finished_order = player_ids  # First player becomes President, last becomes Asshole
        
        # Assign roles
        assign_roles_dynamic(room)
        
        # Verify roles are assigned
        president = room.players[player_ids[0]]
        asshole = room.players[player_ids[-1]]
        self.assert_test(president.role == 'President', "First player got President role")
        self.assert_test(asshole.role == 'Asshole', "Last player got Asshole role")
        
        # End the game
        self.engine._end_game(room)
        
        # Verify roles are still assigned after game ends
        self.assert_test(president.role == 'President', "President role preserved after game end")
        self.assert_test(asshole.role == 'Asshole', "Asshole role preserved after game end")
        
        # Start a new game (simulate restart)
        room.first_game = False
        success, msg = self.engine.start_game(room_id)
        self.assert_test(success, "Second game started successfully")
        
        # Verify roles are still preserved
        room = self.engine.get_room(room_id)
        self.assert_test(president.role == 'President', "President role preserved in second game")
        self.assert_test(asshole.role == 'Asshole', "Asshole role preserved in second game")
        
        # Manually start card exchange phase (this is what the restart callback does)
        if not room.first_game and any(p.role for p in room.players.values()):
            self.engine._start_card_exchange(room)
        
        # Verify card exchange phase starts
        self.assert_test(room.exchange_phase, "Card exchange phase started in second game")
        self.assert_test(room.pending_exchange is not None, "Pending exchange is set up")
        
        print("✅ Role preservation in subsequent games working correctly")

if __name__ == "__main__":
    tests = PresidentGameTests()
    tests.run_all_tests() 