import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from dash.testing.application_runners import import_app
from dash.testing.composite import DashComposite
import json

# Import the app and components
from app import (
    PresidentEngine, GreedyBot, create_deck, parse_card, 
    compare_ranks, is_higher_rank, RoomState, Player
)

class TestGameLogic:
    """Test the core game logic components"""
    
    def setup_method(self):
        """Setup for each test"""
        self.engine = PresidentEngine()
        self.bot = GreedyBot(self.engine)
    
    def test_deck_creation(self):
        """Test deck creation with and without jokers"""
        deck_with_jokers = create_deck(True)
        deck_without_jokers = create_deck(False)
        
        assert len(deck_with_jokers) == 54  # 52 cards + 2 jokers
        assert len(deck_without_jokers) == 52
        assert 'JOKERa' in deck_with_jokers
        assert 'JOKERb' in deck_with_jokers
        assert 'JOKERa' not in deck_without_jokers
    
    def test_card_parsing(self):
        """Test card parsing functionality"""
        # Test regular cards
        assert parse_card('3S') == (3, 'S')
        assert parse_card('AS') == ('A', 'S')
        assert parse_card('10H') == (10, 'H')
        assert parse_card('JD') == ('J', 'D')
        
        # Test jokers
        assert parse_card('JOKERa') == ('JOKER', None)
        assert parse_card('JOKERb') == ('JOKER', None)
    
    def test_rank_comparison(self):
        """Test rank comparison logic"""
        # Normal order
        assert compare_ranks(4, 3, False) > 0  # 4 beats 3
        assert compare_ranks('A', 'K', False) > 0  # Ace beats King
        assert compare_ranks(2, 'A', False) > 0  # 2 beats Ace
        assert compare_ranks('JOKER', 2, False) > 0  # Joker beats 2
        
        # Inverted order
        assert compare_ranks(3, 4, True) > 0  # 3 beats 4 when inverted
        assert compare_ranks('K', 'A', True) > 0  # King beats Ace when inverted
    
    def test_room_creation(self):
        """Test room creation and management"""
        room_id = "test_room"
        room = self.engine.create_room(room_id)
        
        assert room.id == room_id
        assert room.phase == 'lobby'
        assert len(room.players) == 0
        assert room.version == 0
    
    def test_player_addition(self):
        """Test adding players to rooms"""
        room_id = "test_room"
        self.engine.create_room(room_id)
        
        # Add human player
        success, player_id = self.engine.add_player(room_id, "TestPlayer", False)
        assert success
        assert player_id is not None
        
        room = self.engine.get_room(room_id)
        assert len(room.players) == 1
        assert room.players[player_id].name == "TestPlayer"
        assert not room.players[player_id].is_bot
        
        # Add bot player
        success, bot_id = self.engine.add_player(room_id, "TestBot", True)
        assert success
        assert len(room.players) == 2
        assert room.players[bot_id].is_bot
    
    def test_room_full_limit(self):
        """Test room capacity limit"""
        room_id = "test_room"
        self.engine.create_room(room_id)
        
        # Add 5 players (max capacity)
        for i in range(5):
            success, _ = self.engine.add_player(room_id, f"Player{i}", False)
            assert success
        
        # Try to add 6th player
        success, _ = self.engine.add_player(room_id, "Player6", False)
        assert not success
    
    def test_game_start(self):
        """Test game starting logic"""
        room_id = "test_room"
        self.engine.create_room(room_id)
        
        # Can't start with less than 3 players
        success, msg = self.engine.start_game(room_id)
        assert not success
        
        # Add 3 players
        for i in range(3):
            self.engine.add_player(room_id, f"Player{i}", False)
        
        # Mock deck to ensure 3D goes to first player
        with patch('app.create_deck') as mock_deck:
            mock_deck.return_value = ['3D'] + [f'{r}S' for r in [4,5,6,7,8,9,10,'J','Q','K','A',2]] * 4
            success, msg = self.engine.start_game(room_id)
        
        assert success
        room = self.engine.get_room(room_id)
        assert room.phase == 'play'
        assert room.turn is not None
    
    def test_card_validation(self):
        """Test card play validation"""
        room_id = "test_room"
        self.engine.create_room(room_id)
        
        # Add players and start game
        player_ids = []
        for i in range(3):
            _, pid = self.engine.add_player(room_id, f"Player{i}", False)
            player_ids.append(pid)
        
        room = self.engine.get_room(room_id)
        room.phase = 'play'
        room.turn = player_ids[0]
        
        # Give player some cards
        player = room.players[player_ids[0]]
        player.hand = ['3S', '3H', '4D', '5C']
        
        # Valid play - first play
        valid, msg, pattern = self.engine.validate_play(room, player_ids[0], ['3S'])
        assert valid
        assert pattern['rank'] == 3
        assert pattern['count'] == 1
        
        # Invalid play - player doesn't own card
        valid, msg, pattern = self.engine.validate_play(room, player_ids[0], ['AS'])
        assert not valid
        
        # Invalid play - mixed ranks
        valid, msg, pattern = self.engine.validate_play(room, player_ids[0], ['3S', '4D'])
        assert not valid
    
    def test_special_card_effects(self):
        """Test special card effects detection"""
        room = RoomState(id="test")
        
        # Test effect detection
        assert self.engine._get_effect_type(7) == 'seven_gift'
        assert self.engine._get_effect_type(8) == 'eight_reset'
        assert self.engine._get_effect_type(10) == 'ten_discard'
        assert self.engine._get_effect_type('J') == 'jack_inversion'
        assert self.engine._get_effect_type(5) is None
    
    def test_bot_logic(self):
        """Test bot decision making"""
        room_id = "test_room"
        self.engine.create_room(room_id)
        
        # Add bot player
        _, bot_id = self.engine.add_player(room_id, "TestBot", True)
        
        room = self.engine.get_room(room_id)
        room.phase = 'play'
        room.turn = bot_id
        
        # Give bot some cards
        bot_player = room.players[bot_id]
        bot_player.hand = ['3S', '3H', '4D', '5C']
        
        # Test bot can find valid plays
        plays = self.bot._get_possible_plays(room, bot_player)
        assert len(plays) > 0
        
        # All returned plays should be valid
        for play in plays:
            valid, _, _ = self.engine.validate_play(room, bot_id, play)
            assert valid

class TestDashApp:
    """Test the Dash application interface"""
    
    @pytest.fixture
    def dash_duo(self):
        """Pytest fixture for Dash testing"""
        from dash.testing.application_runners import import_app
        from dash.testing.composite import DashComposite
        
        app = import_app("app")
        dash_duo = DashComposite()
        dash_duo.start_server(app)
        return dash_duo
    
    def test_app_loads(self, dash_duo):
        """Test that the app loads successfully"""
        dash_duo.wait_for_element("#game-content", timeout=10)
        
        # Check that the lobby layout is displayed
        assert dash_duo.find_element("#room-input")
        assert dash_duo.find_element("#name-input")
    
    def test_room_creation(self, dash_duo):
        """Test creating and joining a room"""
        # Enter player name
        name_input = dash_duo.find_element("#name-input")
        name_input.send_keys("TestPlayer")
        
        # Click join button
        join_btn = dash_duo.find_element("button[data-dash-args='join']")
        join_btn.click()
        
        # Wait for lobby to update
        dash_duo.wait_for_text_to_equal("#game-content h3", "Lobby", timeout=5)
    
    def test_bot_addition(self, dash_duo):
        """Test adding bots to a room"""
        # First join a room
        name_input = dash_duo.find_element("#name-input")
        name_input.send_keys("TestPlayer")
        
        join_btn = dash_duo.find_element("button[data-dash-args='join']")
        join_btn.click()
        
        # Wait for lobby
        dash_duo.wait_for_text_to_equal("#game-content h3", "Lobby", timeout=5)
        
        # Add a bot
        add_bot_btn = dash_duo.find_element("button[data-dash-args='add-bot']")
        add_bot_btn.click()
        
        # Check that player count increased
        dash_duo.wait_for_text_to_equal("p", "Players: 2/5", timeout=5)

class TestGameFlow:
    """Test complete game flow scenarios"""
    
    def setup_method(self):
        """Setup for each test"""
        self.engine = PresidentEngine()
        self.bot = GreedyBot(self.engine)
    
    def test_complete_game_flow(self):
        """Test a complete game from start to finish"""
        room_id = "test_game"
        self.engine.create_room(room_id)
        
        # Add 3 players
        player_ids = []
        for i in range(3):
            _, pid = self.engine.add_player(room_id, f"Player{i}", i > 0)  # Make 2 bots
            player_ids.append(pid)
        
        # Start game with controlled deck
        room = self.engine.get_room(room_id)
        room.phase = 'dealing'
        room.finished_order = []
        room.game_log = []
        
        # Manually set up a simple game state
        room.players[player_ids[0]].hand = ['3D', '4S']  # Human starts
        room.players[player_ids[1]].hand = ['5H', '6C']  # Bot 1
        room.players[player_ids[2]].hand = ['7D', '8S']  # Bot 2
        
        for player in room.players.values():
            player.hand_count = len(player.hand)
            player.passed = False
        
        room.turn = player_ids[0]  # Human starts with 3D
        room.phase = 'play'
        room.current_rank = None
        room.current_count = None
        room.version += 1
        
        # Test first play
        success, msg = self.engine.play_cards(room_id, player_ids[0], ['3D'])
        assert success
        
        room = self.engine.get_room(room_id)
        assert room.current_rank == 3
        assert room.current_count == 1
        assert room.turn != player_ids[0]  # Turn should advance
    
    def test_special_effects_flow(self):
        """Test game flow with special card effects"""
        room_id = "test_effects"
        self.engine.create_room(room_id)
        
        # Add 2 players
        _, p1 = self.engine.add_player(room_id, "Player1", False)
        _, p2 = self.engine.add_player(room_id, "Player2", False)
        
        room = self.engine.get_room(room_id)
        room.phase = 'play'
        room.turn = p1
        
        # Give players cards with special effects
        room.players[p1].hand = ['7S', '7H', '8D']  # 7s for gift, 8 for reset
        room.players[p2].hand = ['9S', '10H']
        
        for player in room.players.values():
            player.hand_count = len(player.hand)
        
        # Test playing 7s (gift effect)
        success, msg = self.engine.play_cards(room_id, p1, ['7S', '7H'])
        assert success
        
        room = self.engine.get_room(room_id)
        assert room.pending_gift is not None
        assert room.pending_gift['player_id'] == p1
        assert room.pending_gift['remaining'] == 2
    
    def test_game_completion(self):
        """Test game completion and role assignment"""
        room_id = "test_completion"
        self.engine.create_room(room_id)
        
        # Add 3 players
        player_ids = []
        for i in range(3):
            _, pid = self.engine.add_player(room_id, f"Player{i}", False)
            player_ids.append(pid)
        
        room = self.engine.get_room(room_id)
        room.phase = 'play'
        
        # Set up game near completion
        room.players[player_ids[0]].hand = []  # Empty hand - should finish first
        room.players[player_ids[1]].hand = ['AS']
        room.players[player_ids[2]].hand = ['2S', '2H']
        
        for player in room.players.values():
            player.hand_count = len(player.hand)
        
        # Manually trigger game end logic
        room.finished_order = [player_ids[0]]  # First player finished
        
        # Add remaining players to finish order
        for pid in player_ids[1:]:
            if pid not in room.finished_order:
                room.finished_order.append(pid)
        
        # Call end game logic
        self.engine._end_game(room)
        
        assert room.phase == 'finished'
        assert room.players[player_ids[0]].role == 'President'
        assert room.players[player_ids[1]].role == 'Vice President'
        assert room.players[player_ids[2]].role == 'Asshole'

class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def setup_method(self):
        """Setup for each test"""
        self.engine = PresidentEngine()
    
    def test_nonexistent_room(self):
        """Test operations on nonexistent rooms"""
        # Try to get nonexistent room
        room = self.engine.get_room("nonexistent")
        assert room is None
        
        # Try to add player to nonexistent room
        success, msg = self.engine.add_player("nonexistent", "Player", False)
        assert not success
        assert "not found" in msg
    
    def test_invalid_player_operations(self):
        """Test operations with invalid players"""
        room_id = "test_room"
        self.engine.create_room(room_id)
        
        room = self.engine.get_room(room_id)
        room.phase = 'play'
        
        # Try to validate play for nonexistent player
        valid, msg, _ = self.engine.validate_play(room, "nonexistent", ['3S'])
        assert not valid
        assert "not found" in msg
    
    def test_concurrent_access(self):
        """Test thread safety with concurrent access"""
        room_id = "concurrent_test"
        self.engine.create_room(room_id)
        
        results = []
        
        def add_player(i):
            success, pid = self.engine.add_player(room_id, f"Player{i}", False)
            results.append((success, pid))
        
        # Create multiple threads trying to add players
        threads = []
        for i in range(10):
            thread = threading.Thread(target=add_player, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Only first 5 should succeed (room capacity)
        successful = [r for r in results if r[0]]
        assert len(successful) == 5
    
    def test_empty_card_selection(self):
        """Test handling of empty card selections"""
        room_id = "test_room"
        self.engine.create_room(room_id)
        
        _, player_id = self.engine.add_player(room_id, "TestPlayer", False)
        
        room = self.engine.get_room(room_id)
        room.phase = 'play'
        room.turn = player_id
        
        # Try to play with empty card list
        valid, msg, _ = self.engine.validate_play(room, player_id, [])
        # Should be handled gracefully (exact behavior depends on implementation)

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 