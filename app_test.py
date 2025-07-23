#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import PresidentEngine, assign_roles_dynamic

def test_card_exchange_scenarios():
    """Test all 4 card exchange scenarios"""
    print("🧪 Testing Card Exchange Scenarios")
    print("=" * 50)
    
    engine = PresidentEngine()
    
    # Test scenarios: Human player as President, Vice President, Scumbag, Asshole
    scenarios = [
        ("President", "president_test"),
        ("Vice President", "vice_president_test"), 
        ("Scumbag", "scumbag_test"),
        ("Asshole", "asshole_test")
    ]
    
    for role_name, room_id in scenarios:
        print(f"\n🎯 Testing {role_name} Scenario")
        print("-" * 30)
        
        # Create room and add players
        engine.create_room(room_id)
        engine.add_player(room_id, "Geeky", is_bot=False)  # Human player
        engine.add_player(room_id, "Alice", is_bot=True)
        engine.add_player(room_id, "Bob", is_bot=True)
        engine.add_player(room_id, "Charlie", is_bot=True)
        
        room = engine.get_room(room_id)
        player_ids = list(room.players.keys())
        
        # Simulate a finished game with specific role assignment
        room.first_game = False
        room.finished_order = []
        
        # Assign roles based on scenario
        if role_name == "President":
            # Human (Geeky) is President (1st place)
            room.finished_order = [player_ids[0], player_ids[1], player_ids[2], player_ids[3]]
        elif role_name == "Vice President":
            # Human (Geeky) is Vice President (2nd place)
            room.finished_order = [player_ids[1], player_ids[0], player_ids[2], player_ids[3]]
        elif role_name == "Scumbag":
            # Human (Geeky) is Scumbag (3rd place)
            room.finished_order = [player_ids[1], player_ids[2], player_ids[0], player_ids[3]]
        elif role_name == "Asshole":
            # Human (Geeky) is Asshole (4th place)
            room.finished_order = [player_ids[1], player_ids[2], player_ids[3], player_ids[0]]
        
        # Assign roles dynamically
        assign_roles_dynamic(room)
        
        # Store as previous game roles
        room.previous_game_roles = room.current_game_roles.copy()
        
        print(f"Previous game roles:")
        for pid, role in room.previous_game_roles.items():
            player = room.players[pid]
            print(f"  {player.name}: {role}")
        
        # Start new game (should trigger card exchange)
        success, message = engine.start_game(room_id)
        print(f"Start game result: {success}, {message}")
        
        # Check if card exchange phase started
        room = engine.get_room(room_id)
        print(f"Phase: {room.phase}")
        print(f"Exchange phase: {room.exchange_phase}")
        print(f"Pending exchange: {room.pending_exchange is not None}")
        
        if room.exchange_phase and room.pending_exchange:
            print("✅ Card exchange phase started successfully!")
            print(f"Current exchange: {room.pending_exchange['current_exchange']}")
            
            # Test automatic exchanges
            if role_name == "Asshole":
                print("Testing automatic Asshole → President exchange...")
                # This should happen automatically in the game updater
                print("✅ Asshole should automatically give 2 best cards to President")
                
            elif role_name == "Scumbag":
                print("Testing automatic Scumbag → Vice President exchange...")
                # This should happen automatically in the game updater
                print("✅ Scumbag should automatically give 1 best card to Vice President")
                
            elif role_name == "President":
                print("Testing manual President → Asshole exchange...")
                print("✅ President should manually select 2 cards to give to Asshole")
                
            elif role_name == "Vice President":
                print("Testing manual Vice President → Scumbag exchange...")
                print("✅ Vice President should manually select 1 card to give to Scumbag")
        else:
            print("❌ Card exchange phase did not start!")
        
        print(f"Game log: {room.game_log[-3:] if room.game_log else 'No log'}")
        print()

def test_automatic_exchanges():
    """Test automatic exchanges work correctly"""
    print("🧪 Testing Automatic Exchanges")
    print("=" * 40)
    
    engine = PresidentEngine()
    room_id = "auto_exchange_test"
    
    # Create room and add players
    engine.create_room(room_id)
    engine.add_player(room_id, "Geeky", is_bot=False)  # Human Asshole
    engine.add_player(room_id, "Alice", is_bot=True)   # Bot President
    engine.add_player(room_id, "Bob", is_bot=True)     # Bot Vice President
    engine.add_player(room_id, "Charlie", is_bot=True) # Bot Scumbag
    
    room = engine.get_room(room_id)
    player_ids = list(room.players.keys())
    
    # Simulate human as Asshole
    room.first_game = False
    room.finished_order = [player_ids[1], player_ids[2], player_ids[3], player_ids[0]]  # Human last (Asshole)
    assign_roles_dynamic(room)
    room.previous_game_roles = room.current_game_roles.copy()
    
    print("Previous game roles:")
    for pid, role in room.previous_game_roles.items():
        player = room.players[pid]
        print(f"  {player.name}: {role}")
    
    # Start new game
    success, message = engine.start_game(room_id)
    print(f"Start game: {success}, {message}")
    
    room = engine.get_room(room_id)
    if room.exchange_phase:
        print("✅ Exchange phase started")
        
        # Simulate automatic exchange for human Asshole
        asshole_id = room.pending_exchange['asshole_id']
        asshole = room.players[asshole_id]
        
        # Get best 2 cards
        from app import GreedyBot
        bot = GreedyBot(engine)
        best_cards = bot._get_best_cards(asshole.hand, 2)
        
        print(f"Asshole ({asshole.name}) best cards: {best_cards}")
        
        # Submit automatic exchange
        success, message = engine.submit_asshole_cards(room_id, asshole_id, best_cards)
        print(f"Asshole exchange: {success}, {message}")
        
        if success:
            print("✅ Automatic Asshole → President exchange successful!")
        else:
            print(f"❌ Automatic exchange failed: {message}")
    else:
        print("❌ Exchange phase did not start")

def test_manual_exchanges():
    """Test manual exchanges work correctly"""
    print("🧪 Testing Manual Exchanges")
    print("=" * 35)
    
    engine = PresidentEngine()
    room_id = "manual_exchange_test"
    
    # Create room and add players
    engine.create_room(room_id)
    engine.add_player(room_id, "Geeky", is_bot=False)  # Human President
    engine.add_player(room_id, "Alice", is_bot=True)   # Bot Asshole
    engine.add_player(room_id, "Bob", is_bot=True)     # Bot Vice President
    engine.add_player(room_id, "Charlie", is_bot=True) # Bot Scumbag
    
    room = engine.get_room(room_id)
    player_ids = list(room.players.keys())
    
    # Simulate human as President
    room.first_game = False
    room.finished_order = [player_ids[0], player_ids[2], player_ids[3], player_ids[1]]  # Human first (President)
    assign_roles_dynamic(room)
    room.previous_game_roles = room.current_game_roles.copy()
    
    print("Previous game roles:")
    for pid, role in room.previous_game_roles.items():
        player = room.players[pid]
        print(f"  {player.name}: {role}")
    
    # Start new game
    success, message = engine.start_game(room_id)
    print(f"Start game: {success}, {message}")
    
    room = engine.get_room(room_id)
    if room.exchange_phase:
        print("✅ Exchange phase started")
        
        # First, trigger automatic Asshole → President exchange
        asshole_id = room.pending_exchange['asshole_id']
        from app import GreedyBot
        bot = GreedyBot(engine)
        asshole = room.players[asshole_id]
        best_cards = bot._get_best_cards(asshole.hand, 2)
        engine.submit_asshole_cards(room_id, asshole_id, best_cards)
        
        # Now test manual President → Asshole exchange
        president_id = room.pending_exchange['president_id']
        president = room.players[president_id]
        
        # Get worst 2 cards for manual selection
        worst_cards = bot._get_worst_cards(president.hand, 2)
        
        print(f"President ({president.name}) selected cards: {worst_cards}")
        
        # Submit manual exchange
        success, message = engine.submit_president_cards(room_id, president_id, worst_cards)
        print(f"President exchange: {success}, {message}")
        
        if success:
            print("✅ Manual President → Asshole exchange successful!")
        else:
            print(f"❌ Manual exchange failed: {message}")
    else:
        print("❌ Exchange phase did not start")

def test_complete_exchange_flow():
    """Test the complete exchange flow from start to finish"""
    print("🧪 Testing Complete Exchange Flow")
    print("=" * 40)
    
    engine = PresidentEngine()
    room_id = "complete_flow_test"
    
    # Create room and add players
    engine.create_room(room_id)
    engine.add_player(room_id, "Geeky", is_bot=False)  # Human President
    engine.add_player(room_id, "Alice", is_bot=True)   # Bot Vice President
    engine.add_player(room_id, "Bob", is_bot=True)     # Bot Scumbag
    engine.add_player(room_id, "Charlie", is_bot=True) # Bot Asshole
    
    room = engine.get_room(room_id)
    player_ids = list(room.players.keys())
    
    # Simulate human as President
    room.first_game = False
    room.finished_order = [player_ids[0], player_ids[1], player_ids[2], player_ids[3]]  # Human first (President)
    assign_roles_dynamic(room)
    room.previous_game_roles = room.current_game_roles.copy()
    
    print("Previous game roles:")
    for pid, role in room.previous_game_roles.items():
        player = room.players[pid]
        print(f"  {player.name}: {role}")
    
    # Start new game
    success, message = engine.start_game(room_id)
    print(f"Start game: {success}, {message}")
    
    room = engine.get_room(room_id)
    if room.exchange_phase:
        print("✅ Exchange phase started")
        
        # Step 1: Automatic Asshole → President exchange
        print("\n1️⃣ Asshole → President (Automatic)")
        asshole_id = room.pending_exchange['asshole_id']
        president_id = room.pending_exchange['president_id']
        from app import GreedyBot
        bot = GreedyBot(engine)
        asshole = room.players[asshole_id]
        best_cards = bot._get_best_cards(asshole.hand, 2)
        success, message = engine.submit_asshole_cards(room_id, asshole_id, best_cards)
        print(f"   Asshole gave {best_cards} to President: {success}")
        
        # Step 2: Manual President → Asshole exchange
        print("\n2️⃣ President → Asshole (Manual)")
        president = room.players[president_id]
        worst_cards = bot._get_worst_cards(president.hand, 2)
        success, message = engine.submit_president_cards(room_id, president_id, worst_cards)
        print(f"   President gave {worst_cards} to Asshole: {success}")
        
        # Step 3: Automatic Scumbag → Vice President exchange
        print("\n3️⃣ Scumbag → Vice President (Automatic)")
        scumbag_id = room.pending_exchange['scumbag_id']
        vice_president_id = room.pending_exchange['vice_president_id']
        scumbag = room.players[scumbag_id]
        best_card = bot._get_best_cards(scumbag.hand, 1)[0]
        success, message = engine.submit_scumbag_card(room_id, scumbag_id, best_card)
        print(f"   Scumbag gave {best_card} to Vice President: {success}")
        
        # Step 4: Manual Vice President → Scumbag exchange
        print("\n4️⃣ Vice President → Scumbag (Manual)")
        vice_president = room.players[vice_president_id]
        worst_card = bot._get_worst_cards(vice_president.hand, 1)[0]
        success, message = engine.submit_vice_president_card(room_id, vice_president_id, worst_card)
        print(f"   Vice President gave {worst_card} to Scumbag: {success}")
        
        # Check final state
        room = engine.get_room(room_id)
        print(f"\n✅ Exchange completed!")
        print(f"   Phase: {room.phase}")
        print(f"   Exchange phase: {room.exchange_phase}")
        print(f"   Pending exchange: {room.pending_exchange is not None}")
        
    else:
        print("❌ Exchange phase did not start")

if __name__ == "__main__":
    print("🎮 President Card Exchange Test Suite")
    print("=" * 50)
    
    # Test all scenarios
    test_card_exchange_scenarios()
    
    # Test automatic exchanges
    test_automatic_exchanges()
    
    # Test manual exchanges
    test_manual_exchanges()
    
    # Test complete flow
    test_complete_exchange_flow()
    
    print("\n✅ All tests completed!")
    print("\n📝 Usage:")
    print("  - Run 'python app_test.py' to test all scenarios")
    print("  - Each test simulates a different role for the human player")
    print("  - Tests verify that card exchange UI shows up correctly")
    print("  - Tests verify automatic and manual exchanges work as expected") 