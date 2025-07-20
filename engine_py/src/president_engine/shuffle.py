# engine_py/src/president_engine/shuffle.py

import random
from typing import List, Dict
from .models import Player, RoomState
from .constants import SUITS, RANKS_NORMAL, JOKER_RANK

def create_deck(use_jokers: bool = True) -> List[str]:
    """
    Generates a standard 52-card deck plus optional jokers.

    Each card is represented as a string, e.g., "KH" for King of Hearts,
    or "JOKERa" for a joker.

    Args:
        use_jokers: If True, two jokers will be added to the deck.

    Returns:
        A list of strings representing a full card deck.
    """
    deck = [f'{rank}{suit}' for rank in RANKS_NORMAL for suit in SUITS]
    if use_jokers:
        deck.append(f'{JOKER_RANK}a')
        deck.append(f'{JOKER_RANK}b')
    return deck

def deal_cards(state: RoomState, seed: Optional[int] = None) -> None:
    """
    Shuffles the deck and deals the cards evenly to all players.

    This function mutates the state object by populating each player's hand.
    It uses a deterministic shuffle if a seed is provided, which is crucial for testing.

    Args:
        state: The current RoomState object, containing the players and deck.
        seed: An optional integer to seed the random number generator for
              reproducible shuffles.
    """
    if not state.players:
        return # Cannot deal without players

    # Create a new deck based on the room's rules
    deck = create_deck(state.rule_config.use_jokers)

    # Use a seeded random generator for deterministic testing
    rng = random.Random(seed)
    rng.shuffle(deck)

    # Clear all player hands before dealing
    for player in state.players.values():
        player.hand.clear()

    # Deal cards one by one to each player in order
    player_ids = list(state.players.keys())
    i = 0
    while deck:
        card = deck.pop()
        player_id = player_ids[i % len(player_ids)]
        state.players[player_id].hand.append(card)
        i += 1