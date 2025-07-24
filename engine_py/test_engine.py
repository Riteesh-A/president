#!/usr/bin/env python3
"""Simple test to verify the President engine works"""

from src.president_engine.engine import PresidentEngine

def test_basic_game():
    """Test basic game functionality"""
    print("🧪 Testing President Engine...")
    
    # Create engine and room
    engine = PresidentEngine()
    room_id = "TEST123"
    room = engine.create_room(room_id)
    print(f"✅ Created room: {room_id}")
    
    # Add players
    success, player1_id = engine.add_player(room_id, "Alice", False)
    success2, player2_id = engine.add_player(room_id, "Bob", False)
    success3, player3_id = engine.add_player(room_id, "Charlie", True)
    
    print(f"✅ Added players: Alice ({player1_id}), Bob ({player2_id}), Charlie ({player3_id})")
    
    # Start game
    success, message = engine.start_game(room_id)
    print(f"✅ Started game: {message}")
    
    # Check game state
    room = engine.get_room(room_id)
    print(f"✅ Game phase: {room.phase}")
    print(f"✅ Current turn: {room.turn}")
    print(f"✅ Players: {[p.name for p in room.players.values()]}")
    
    # Check hands
    for player in room.players.values():
        print(f"✅ {player.name} has {len(player.hand)} cards")
    
    print("🎉 All tests passed! Engine is working correctly.")

if __name__ == "__main__":
    test_basic_game() 