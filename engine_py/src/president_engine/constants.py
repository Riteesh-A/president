# engine_py/src/president_engine/constants.py

# Define standard card ranks and suits
RANKS_NORMAL = [3, 4, 5, 6, 7, 8, 9, 10, 'J', 'Q', 'K', 'A', 2]
SUITS = ['S', 'H', 'D', 'C'] # Spades, Hearts, Diamonds, Clubs

# Special card ranks (Joker is highest by default)
JOKER_RANK = 'JOKER'

# All possible ranks including Joker
ALL_RANKS_WITH_JOKER = RANKS_NORMAL + [JOKER_RANK]

# Card encoding scheme: <RANK><SUIT> or JOKER<INDEX>
# Example: '3D', 'AS', 'JOKERa'

# Player Roles
ROLE_PRESIDENT = 'President'
ROLE_VICE_PRESIDENT = 'Vice President'
ROLE_CITIZEN = 'Citizen'
ROLE_SCUMBAG = 'Scumbag'
ROLE_ASSHOLE = 'Asshole'

PLAYER_ROLES = [
    ROLE_PRESIDENT,
    ROLE_VICE_PRESIDENT,
    ROLE_CITIZEN,
    ROLE_SCUMBAG,
    ROLE_ASSHOLE
]

# Game Phases
PHASE_LOBBY = 'lobby'
PHASE_DEALING = 'dealing'
PHASE_EXCHANGE = 'exchange'
PHASE_PLAY = 'play'
PHASE_FINISHED = 'finished'

GAME_PHASES = [
    PHASE_LOBBY,
    PHASE_DEALING,
    PHASE_EXCHANGE,
    PHASE_PLAY,
    PHASE_FINISHED
]

# Special Effect Names
EFFECT_SEVEN_GIFT = 'seven_gift'
EFFECT_EIGHT_RESET = 'eight_reset'
EFFECT_TEN_DISCARD = 'ten_discard'
EFFECT_JACK_INVERSION = 'jack_inversion'

# Card counts for special effects
SEVEN_GIFT_RANK = 7
EIGHT_RESET_RANK = 8
TEN_DISCARD_RANK = 10
JACK_INVERSION_RANK = 'J'