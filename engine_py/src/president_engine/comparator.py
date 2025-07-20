"""
Rank comparison logic with support for Jack inversion.
"""

from typing import List

from .constants import NORMAL_ORDER, Rank


def get_rank_order(inversion: bool) -> List[Rank]:
    """Get the current rank order based on inversion state."""
    if inversion:
        return list(reversed(NORMAL_ORDER))
    return NORMAL_ORDER


def get_rank_index(rank: Rank, inversion: bool = False) -> int:
    """Get the index of a rank in the current ordering."""
    order = get_rank_order(inversion)
    try:
        return order.index(rank)
    except ValueError:
        raise ValueError(f"Invalid rank: {rank}")


def compare_ranks(rank_a: Rank, rank_b: Rank, inversion: bool = False) -> int:
    """
    Compare two ranks.
    
    Returns:
        < 0 if rank_a is lower than rank_b
        0 if ranks are equal
        > 0 if rank_a is higher than rank_b
    """
    index_a = get_rank_index(rank_a, inversion)
    index_b = get_rank_index(rank_b, inversion)
    return index_a - index_b


def is_higher_rank(rank_a: Rank, rank_b: Rank, inversion: bool = False) -> bool:
    """Check if rank_a is higher than rank_b."""
    return compare_ranks(rank_a, rank_b, inversion) > 0


def is_lower_rank(rank_a: Rank, rank_b: Rank, inversion: bool = False) -> bool:
    """Check if rank_a is lower than rank_b."""
    return compare_ranks(rank_a, rank_b, inversion) < 0


def is_equal_rank(rank_a: Rank, rank_b: Rank) -> bool:
    """Check if two ranks are equal (inversion doesn't affect equality)."""
    return rank_a == rank_b


def get_highest_rank(ranks: List[Rank], inversion: bool = False) -> Rank:
    """Get the highest rank from a list of ranks."""
    if not ranks:
        raise ValueError("Cannot get highest rank from empty list")
    
    return max(ranks, key=lambda r: get_rank_index(r, inversion))


def get_lowest_rank(ranks: List[Rank], inversion: bool = False) -> Rank:
    """Get the lowest rank from a list of ranks."""
    if not ranks:
        raise ValueError("Cannot get lowest rank from empty list")
    
    return min(ranks, key=lambda r: get_rank_index(r, inversion))


def sort_ranks(ranks: List[Rank], inversion: bool = False, reverse: bool = False) -> List[Rank]:
    """Sort ranks according to current ordering."""
    sorted_ranks = sorted(ranks, key=lambda r: get_rank_index(r, inversion))
    if reverse:
        sorted_ranks.reverse()
    return sorted_ranks


def is_valid_next_rank(current_rank: Rank, next_rank: Rank, inversion: bool = False, 
                      jack_restriction: bool = False) -> bool:
    """
    Check if next_rank is a valid play after current_rank.
    
    Args:
        current_rank: The rank currently on the table
        next_rank: The rank being played
        inversion: Whether inversion is active
        jack_restriction: Whether Jack inversion restriction applies
                         (only ranks lower than Jack in normal order allowed)
    """
    # If no current rank, any rank is valid
    if current_rank is None:
        return True
    
    # Jack inversion restriction
    if jack_restriction and inversion:
        # During Jack inversion, only ranks that were lower than Jack
        # in normal order are allowed
        jack_index = NORMAL_ORDER.index('J')
        next_rank_normal_index = NORMAL_ORDER.index(next_rank)
        
        # Must be lower than Jack in normal ordering
        if next_rank_normal_index >= jack_index:
            return False
    
    # Normal higher rank check
    return is_higher_rank(next_rank, current_rank, inversion)


def extract_rank_from_card(card_id: str) -> Rank:
    """Extract rank from a card ID string."""
    if card_id.startswith("JOKER"):
        return "JOKER"
    
    # Handle card format like "3D", "10H", "JS", "AS", "2C"
    if card_id.startswith("10"):
        return 10
    elif card_id[0] in "JQKA":
        return card_id[0]  # type: ignore
    elif card_id[0] == "2":
        return 2
    else:
        # Regular number cards 3-9
        try:
            return int(card_id[0])
        except ValueError:
            raise ValueError(f"Invalid card ID format: {card_id}")


def get_best_cards_for_exchange(hand: List[str], count: int) -> List[str]:
    """
    Get the best (highest) cards from a hand for exchange.
    Always uses normal ordering regardless of current inversion state.
    """
    if len(hand) < count:
        return hand.copy()
    
    # Extract ranks and sort by normal order (highest first)
    cards_with_ranks = [(card, extract_rank_from_card(card)) for card in hand]
    cards_with_ranks.sort(
        key=lambda x: get_rank_index(x[1], inversion=False),
        reverse=True
    )
    
    return [card for card, _ in cards_with_ranks[:count] ]