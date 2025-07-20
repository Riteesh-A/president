"""
Game constants and configurations.
"""

from typing import Literal

# Rank types
Rank = int | Literal['J', 'Q', 'K', 'A', 2, 'JOKER']

# Standard rank ordering (lowest to highest)
NORMAL_ORDER: list[Rank] = [3, 4, 5, 6, 7, 8, 9, 10, 'J', 'Q', 'K', 'A', 2, 'JOKER']

# Suit definitions
SUITS = ['S', 'H', 'D', 'C']  # Spades, Hearts, Diamonds, Clubs

# Special cards
STARTING_CARD = "3D"  # Three of Diamonds
JOKER_CARDS = ["JOKERa", "JOKERb"]

# Game phases
PHASE_LOBBY = "lobby"
PHASE_DEALING = "dealing"
PHASE_EXCHANGE = "exchange"
PHASE_PLAY = "play"
PHASE_FINISHED = "finished"

# Player roles
ROLE_PRESIDENT = "President"
ROLE_VICE_PRESIDENT = "VicePresident"
ROLE_CITIZEN = "Citizen"
ROLE_SCUMBAG = "Scumbag"
ROLE_ASSHOLE = "Asshole"

# Effect types
EFFECT_SEVEN_GIFT = "seven_gift"
EFFECT_EIGHT_RESET = "eight_reset"
EFFECT_TEN_DISCARD = "ten_discard"
EFFECT_JACK_INVERSION = "jack_inversion"

# Error codes
ERROR_ROOM_FULL = "ROOM_FULL"
ERROR_NOT_YOUR_TURN = "NOT_YOUR_TURN"
ERROR_OWNERSHIP = "OWNERSHIP"
ERROR_PATTERN_MISMATCH = "PATTERN_MISMATCH"
ERROR_RANK_TOO_LOW = "RANK_TOO_LOW"
ERROR_EFFECT_PENDING = "EFFECT_PENDING"
ERROR_INVALID_GIFT_DISTRIBUTION = "INVALID_GIFT_DISTRIBUTION"
ERROR_INVALID_DISCARD_SELECTION = "INVALID_DISCARD_SELECTION"
ERROR_ALREADY_PASSED = "ALREADY_PASSED"
ERROR_ACTION_NOT_ALLOWED = "ACTION_NOT_ALLOWED"
ERROR_INTERNAL = "INTERNAL" 