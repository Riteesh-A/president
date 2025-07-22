"""Game constants and utilities"""

from typing import List, Tuple, Optional
from .models import Rank

NORMAL_ORDER = [3,4,5,6,7,8,9,10,'J','Q','K','A',2,'JOKER']
SUITS = ['S', 'H', 'D', 'C']

def create_deck(use_jokers=True) -> List[str]:
    deck = []
    for suit in SUITS:
        for rank in [3,4,5,6,7,8,9,10,'J','Q','K','A',2]:
            deck.append(f"{rank}{suit}")
    if use_jokers:
        deck.extend(['JOKERa', 'JOKERb'])
    return deck

def parse_card(card_id: str) -> Tuple[Rank, Optional[str]]:
    if card_id.startswith('JOKER'):
        return 'JOKER', None
    if card_id[:-1] in ['J', 'Q', 'K', 'A']:
        return card_id[:-1], card_id[-1]
    if card_id[:-1] == '10':
        return 10, card_id[-1]
    return int(card_id[:-1]), card_id[-1]

def compare_ranks(rank_a: Rank, rank_b: Rank, inversion=False) -> int:
    order = list(reversed(NORMAL_ORDER)) if inversion else NORMAL_ORDER
    try:
        return order.index(rank_a) - order.index(rank_b)
    except ValueError:
        return 0

def is_higher_rank(rank_a: Rank, rank_b: Rank, inversion=False) -> bool:
    return compare_ranks(rank_a, rank_b, inversion) > 0 