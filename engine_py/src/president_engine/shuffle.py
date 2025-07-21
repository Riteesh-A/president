"""
Card shuffling and dealing utilities.
"""

import random
from typing import Dict, List, Optional

from .constants import JOKER_CARDS, SUITS
from .models import Player, RoomState
from .rules import RuleConfig


def create_deck(use_jokers: bool = True) -> List[str]:
    """Create a standard deck of cards."""
    deck = []
    
    # Standard 52 cards
    for suit in SUITS:
        for rank in [3, 4, 5, 6, 7, 8, 9, 10, 'J', 'Q', 'K', 'A', 2]:
            deck.append(f"{rank}{suit}")
    
    # Add jokers if enabled
    if use_jokers:
        deck.extend(JOKER_CARDS)
    
    return deck


def shuffle_deck(deck: List[str], seed: Optional[int] = None) -> List[str]:
    """
    Shuffle a deck deterministically if seed is provided.
    
    Args:
        deck: List of card IDs to shuffle
        seed: Optional seed for deterministic shuffling
    
    Returns:
        Shuffled copy of the deck
    """
    deck_copy = deck.copy()
    
    if seed is not None:
        # Use deterministic shuffling with seed
        rng = random.Random(seed)
        rng.shuffle(deck_copy)
    else:
        # Use system random
        random.shuffle(deck_copy)
    
    return deck_copy


def deal_cards(deck: List[str], players: Dict[str, Player]) -> Dict[str, List[str]]:
    """
    Deal cards evenly to all players.
    
    Args:
        deck: Shuffled deck of cards
        players: Dictionary of players to deal to
    
    Returns:
        Dictionary mapping player_id to their dealt cards
    """
    if not players:
        return {}
    
    player_ids = list(players.keys())
    player_count = len(player_ids)
    cards_per_player = len(deck) // player_count
    
    hands = {player_id: [] for player_id in player_ids}
    
    # Deal cards round-robin style
    for i, card in enumerate(deck):
        if i < cards_per_player * player_count:
            player_index = i % player_count
            player_id = player_ids[player_index]
            hands[player_id].append(card)
    
    return hands


def find_starting_player(players: Dict[str, Player]) -> Optional[str]:
    """
    Find the player who should start the round (holds 3♦).
    
    Args:
        players: Dictionary of players with their hands
    
    Returns:
        Player ID who should start, or None if 3♦ not found
    """
    from .constants import STARTING_CARD
    
    for player_id, player in players.items():
        if STARTING_CARD in player.hand:
            return player_id
    
    return None


def find_asshole_player(players: Dict[str, Player]) -> Optional[str]:
    """
    Find the player with Asshole role (starts subsequent games).
    
    Args:
        players: Dictionary of players with their roles
    
    Returns:
        Player ID who has Asshole role, or None if not found
    """
    from .constants import ROLE_ASSHOLE
    
    for player_id, player in players.items():
        if player.role == ROLE_ASSHOLE:
            return player_id
    
    return None


def setup_round(state: RoomState, seed: Optional[int] = None) -> RoomState:
    """
    Set up a new round by shuffling and dealing cards.
    
    Args:
        state: Current room state
        seed: Optional seed for deterministic shuffling
    
    Returns:
        Updated state with cards dealt and starting player set
    """
    if not state.rule_config:
        raise ValueError("RuleConfig must be set before dealing")
    
    # Create and shuffle deck
    deck = create_deck(state.rule_config.use_jokers)
    shuffled_deck = shuffle_deck(deck, seed)
    
    # Deal cards to players
    hands = deal_cards(shuffled_deck, state.players)
    
    # Update player hands
    for player_id, cards in hands.items():
        state.players[player_id].hand = cards
    
    # Find starting player based on game type (Section 4.3 spec compliance):
    # - First game: Player with 3♦ (Three of Diamonds) starts and must play 3s
    # - Subsequent games: Asshole starts with any cards they choose
    has_roles = any(player.role for player in state.players.values())
    
    print(f"DEBUG: has_roles = {has_roles}")
    print(f"DEBUG: players and their roles:")
    for pid, player in state.players.items():
        print(f"  {player.name}: role = {player.role}")
    
    if has_roles:
        # Subsequent game: Asshole starts
        starting_player = find_asshole_player(state.players)
        print(f"DEBUG: Subsequent game, Asshole starts: {starting_player}")
        
        # Fallback if no Asshole found (shouldn't happen)
        if starting_player is None:
            print("WARNING: No Asshole found for subsequent game, falling back to 3♦ holder")
            starting_player = find_starting_player(state.players)
    else:
        # First game: Player with 3♦ starts
        starting_player = find_starting_player(state.players)
        print(f"DEBUG: First game, looking for 3♦ holder: {starting_player}")
        
        # Debug: show all hands
        print(f"DEBUG: All player hands:")
        for pid, player in state.players.items():
            print(f"  {player.name}: {player.hand}")
            if "3D" in player.hand:
                print(f"    *** {player.name} has 3♦! ***")
        
        # Error handling: if no one has 3♦ (shouldn't happen with proper deck)
        if starting_player is None:
            print("ERROR: No player found with 3♦! This shouldn't happen.")
            # Fallback to first player as emergency measure
            starting_player = list(state.players.keys())[0] if state.players else None
    
    print(f"DEBUG: Final starting player: {starting_player}")
    if starting_player:
        print(f"DEBUG: Starting player name: {state.players[starting_player].name}")
        print(f"DEBUG: Starting player hand: {state.players[starting_player].hand}")
    else:
        raise ValueError("No valid starting player found - this should never happen with a proper deck")
    
    # Update state
    state.deck = []  # All cards dealt
    state.turn = starting_player
    state.finished_order = []
    state.discard = []
    
    # Clear any pending effects
    state.pending_gift = None
    state.pending_discard = None
    state.inversion_active = False
    
    # Reset current pattern
    state.current_pattern.rank = None
    state.current_pattern.count = None
    state.current_pattern.last_player = None
    state.current_pattern.cards = []
    
    # Clear all passes
    state.clear_passes()
    
    return state


def get_hand_summary(hand: List[str]) -> Dict[str, int]:
    """
    Get a summary of cards in a hand by rank.
    
    Args:
        hand: List of card IDs
    
    Returns:
        Dictionary mapping rank to count
    """
    from .comparator import extract_rank_from_card
    
    summary = {}
    for card in hand:
        rank = extract_rank_from_card(card)
        rank_str = str(rank)
        summary[rank_str] = summary.get(rank_str, 0) + 1
    
    return summary


def validate_deck_integrity(state: RoomState) -> bool:
    """
    Validate that all cards are accounted for and no duplicates exist.
    
    Args:
        state: Room state to validate
    
    Returns:
        True if deck integrity is valid
    """
    if not state.rule_config:
        return False
    
    expected_deck = create_deck(state.rule_config.use_jokers)
    expected_cards = set(expected_deck)
    
    # Collect all cards currently in play
    all_cards = []
    
    # Add cards in player hands
    for player in state.players.values():
        all_cards.extend(player.hand)
    
    # Add cards in discard pile
    all_cards.extend(state.discard)
    
    # Add any remaining deck cards
    all_cards.extend(state.deck)
    
    actual_cards = set(all_cards)
    
    # Check for correct total and no duplicates
    return (
        len(all_cards) == len(actual_cards) and  # No duplicates
        actual_cards == expected_cards  # Correct cards
    )


def sort_hand(hand: List[str], inversion: bool = False) -> List[str]:
    """
    Sort a hand of cards by rank.
    
    Args:
        hand: List of card IDs to sort
        inversion: Whether to use inverted ordering
    
    Returns:
        Sorted list of card IDs
    """
    from .comparator import extract_rank_from_card, get_rank_index
    
    def sort_key(card_id: str) -> int:
        rank = extract_rank_from_card(card_id)
        return get_rank_index(rank, inversion)
    
    return sorted(hand, key=sort_key) 