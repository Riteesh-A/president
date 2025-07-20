# engine_py/src/president_engine/comparator.py

from typing import Union, Literal
from .constants import RANKS_NORMAL, JOKER_RANK

Rank = Union[int, Literal['J','Q','K','A',2,'JOKER']]

# Define the normal and inverted orderings
NORMAL_ORDER = RANKS_NORMAL + [JOKER_RANK]
INVERTED_ORDER = list(reversed(NORMAL_ORDER))

def get_rank_order(inversion: bool) -> List[Rank]:
    """Returns the appropriate rank order list based on inversion status."""
    return INVERTED_ORDER if inversion else NORMAL_ORDER

def compare_ranks(rank_a: Rank, rank_b: Rank, inversion: bool) -> int:
    """
    Compares two ranks based on the current inversion status.
    Returns:
    - Negative if rank_a < rank_b
    - Positive if rank_a > rank_b
    - Zero if rank_a == rank_b
    """
    current_order = get_rank_order(inversion)
    try:
        index_a = current_order.index(rank_a)
        index_b = current_order.index(rank_b)
        return index_a - index_b
    except ValueError:
        # This should ideally not happen if ranks are valid
        raise ValueError(f"Invalid rank encountered: {rank_a} or {rank_b}")

def is_higher(rank_a: Rank, rank_b: Rank, inversion: bool) -> bool:
    """Checks if rank_a is strictly higher than rank_b given inversion status."""
    return compare_ranks(rank_a, rank_b, inversion) > 0

def is_lower(rank_a: Rank, rank_b: Rank, inversion: bool) -> bool:
    """Checks if rank_a is strictly lower than rank_b given inversion status."""
    return compare_ranks(rank_a, rank_b, inversion) < 0

def is_equal(rank_a: Rank, rank_b: Rank, inversion: bool) -> bool:
    """Checks if rank_a is equal to rank_b given inversion status."""
    return compare_ranks(rank_a, rank_b, inversion) == 0

# Test cases (for your reference, not part of the module)
if __name__ == "__main__":
    # Normal order tests
    print("--- Normal Order Tests ---")
    print(f"Is 3 higher than 2 (Normal)? {is_higher(3, 2, False)}") # False
    print(f"Is 2 higher than K (Normal)? {is_higher(2, 'K', False)}") # True
    print(f"Is 7 higher than J (Normal)? {is_higher(7, 'J', False)}") # False
    print(f"Is JOKER higher than 2 (Normal)? {is_higher('JOKER', 2, False)}") # True

    # Inverted order tests
    print("\n--- Inverted Order Tests ---")
    print(f"Is 3 higher than 2 (Inverted)? {is_higher(3, 2, True)}") # True (because 2 is lowest in inverted)
    print(f"Is 2 higher than K (Inverted)? {is_higher(2, 'K', True)}") # False (because K is higher in inverted)
    print(f"Is 7 higher than J (Inverted)? {is_higher(7, 'J', True)}") # True (because J is lower in inverted)
    print(f"Is JOKER higher than 2 (Inverted)? {is_higher('JOKER', 2, True)}") # False (because JOKER is lowest in inverted)

    print("\n--- Equality Tests ---")
    print(f"Is 7 equal to 7 (Normal)? {is_equal(7, 7, False)}") # True
    print(f"Is J equal to J (Inverted)? {is_equal('J', 'J', True)}") # True

    print("\n--- Comparison Values ---")
    print(f"Compare 3 vs 5 (Normal): {compare_ranks(3, 5, False)}") # Negative
    print(f"Compare 5 vs 3 (Normal): {compare_ranks(5, 3, False)}") # Positive
    print(f"Compare 3 vs 5 (Inverted): {compare_ranks(3, 5, True)}") # Positive
    print(f"Compare 5 vs 3 (Inverted): {compare_ranks(5, 3, True)}") # Negative