from president_engine.models import RoomState, Player
from president_engine.ranking import assign_roles

def test_assign_roles_for_4_players():
    # 1. Setup
    state = RoomState(id="test_room")
    p1 = Player(id="p1", name="Alice", seat=0)
    p2 = Player(id="p2", name="Bob", seat=1)
    p3 = Player(id="p3", name="Charlie", seat=2)
    p4 = Player(id="p4", name="Dana", seat=3)
    
    state.players = {"p1": p1, "p2": p2, "p3": p3, "p4": p4}
    state.finished_order = ["p3", "p1", "p4", "p2"] # Charlie, Alice, Dana, Bob

    # 2. Action
    assign_roles(state)

    # 3. Assert (Check the result)
    assert state.players["p3"].role == "President"
    assert state.players["p1"].role == "Vice President"
    assert state.players["p4"].role == "Scumbag"
    assert state.players["p2"].role == "Asshole"