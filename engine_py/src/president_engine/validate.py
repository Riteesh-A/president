"""
Pattern validation for card plays.
"""

from typing import Dict, List, Optional, Tuple, Union

from .comparator import extract_rank_from_card, is_valid_next_rank
from .constants import EFFECT_SEVEN_GIFT, EFFECT_EIGHT_RESET, EFFECT_TEN_DISCARD, EFFECT_JACK_INVERSION, Rank
from .models import Player, RoomState


class ValidationResult:
    """Result of pattern validation."""
    
    def __init__(
        self,
        valid: bool,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        pattern: Optional[Dict] = None,
        effect: Optional[str] = None
    ):
        self.valid = valid
        self.error_code = error_code
        self.error_message = error_message
        self.pattern = pattern
        self.effect = effect
    
    @classmethod
    def success(cls, pattern: Dict, effect: Optional[str] = None) -> 'ValidationResult':
        """Create a successful validation result."""
        return cls(valid=True, pattern=pattern, effect=effect)
    
    @classmethod
    def error(cls, error_code: str, error_message: str) -> 'ValidationResult':
        """Create an error validation result."""
        return cls(valid=False, error_code=error_code, error_message=error_message)


def validate_ownership(player: Player, card_ids: List[str]) -> bool:
    """Check if player owns all the specified cards."""
    return all(card_id in player.hand for card_id in card_ids)


def detect_pattern(card_ids: List[str]) -> Tuple[Optional[Rank], int]:
    """
    Detect the pattern of cards being played.
    
    Args:
        card_ids: List of card IDs being played
    
    Returns:
        Tuple of (rank, count) or (None, 0) if invalid
    """
    if not card_ids:
        return None, 0
    
    # Extract ranks from all cards
    ranks = [extract_rank_from_card(card_id) for card_id in card_ids]
    
    # Handle jokers - they can be played as any rank
    # For simplicity, treat all jokers as the same rank
    if all(rank == "JOKER" for rank in ranks):
        return "JOKER", len(ranks)
    
    # Check if all non-joker cards have the same rank
    non_joker_ranks = [rank for rank in ranks if rank != "JOKER"]
    
    if not non_joker_ranks:
        # All jokers case (handled above)
        return "JOKER", len(ranks)
    
    # All non-joker cards must have the same rank
    primary_rank = non_joker_ranks[0]
    if not all(rank == primary_rank for rank in non_joker_ranks):
        return None, 0  # Mixed ranks not allowed
    
    # Valid pattern: all cards are same rank (possibly with jokers)
    return primary_rank, len(card_ids)


def get_effect_for_rank(rank: Rank) -> Optional[str]:
    """Get the special effect for a given rank."""
    effect_map = {
        7: EFFECT_SEVEN_GIFT,
        8: EFFECT_EIGHT_RESET,
        10: EFFECT_TEN_DISCARD,
        'J': EFFECT_JACK_INVERSION
    }
    return effect_map.get(rank)


def validate_play(
    state: RoomState,
    player_id: str,
    card_ids: List[str]
) -> ValidationResult:
    """
    Validate a card play attempt.
    
    Args:
        state: Current room state
        player_id: ID of player attempting the play
        card_ids: List of card IDs being played
    
    Returns:
        ValidationResult with validation outcome
    """
    from .constants import (
        ERROR_NOT_YOUR_TURN, ERROR_OWNERSHIP, ERROR_PATTERN_MISMATCH,
        ERROR_RANK_TOO_LOW, ERROR_EFFECT_PENDING, ERROR_ALREADY_PASSED,
        PHASE_PLAY
    )
    
    # Check if it's the play phase
    if state.phase != PHASE_PLAY:
        return ValidationResult.error(
            ERROR_NOT_YOUR_TURN,
            f"Game is not in play phase (current: {state.phase})"
        )
    
    # Check if it's player's turn
    if state.turn != player_id:
        return ValidationResult.error(
            ERROR_NOT_YOUR_TURN,
            f"It's not your turn (current turn: {state.turn})"
        )
    
    # Check for pending effects
    if state.pending_gift or state.pending_discard:
        return ValidationResult.error(
            ERROR_EFFECT_PENDING,
            "Must complete pending effect before playing"
        )
    
    # Get player
    player = state.players.get(player_id)
    if not player:
        return ValidationResult.error(
            ERROR_NOT_YOUR_TURN,
            "Player not found"
        )
    
    # Check if player has already passed
    if player.passed:
        return ValidationResult.error(
            ERROR_ALREADY_PASSED,
            "Player has already passed this round"
        )
    
    # Validate card ownership
    if not validate_ownership(player, card_ids):
        return ValidationResult.error(
            ERROR_OWNERSHIP,
            "Player does not own all specified cards"
        )
    
    # Detect pattern
    rank, count = detect_pattern(card_ids)
    if rank is None:
        return ValidationResult.error(
            ERROR_PATTERN_MISMATCH,
            "Cards do not form a valid pattern"
        )
    
    # Check if this is opening play 
    current_rank = state.current_pattern.rank
    current_count = state.current_pattern.count
    
    if current_rank is None:
        # Opening play - Section 4.3 compliance: first game starts with 3♦ holder playing 3s
        has_roles = any(p.role for p in state.players.values())
        
        if not has_roles:
            # First game: must play 3s and player must have 3♦ (Section 4.3)
            from .constants import STARTING_CARD
            
            # Verify this player has the 3♦ (additional safety check)
            if STARTING_CARD not in player.hand:
                return ValidationResult.error(
                    ERROR_NOT_YOUR_TURN,
                    "Only the player with 3♦ (Three of Diamonds) can start the first game"
                )
            
            # Must play 3s on opening (Section 4.3: "may play any number of 3s they possess")
            if rank != 3:
                return ValidationResult.error(
                    ERROR_PATTERN_MISMATCH,
                    "First game opening play must be threes (per Section 4.3)"
                )
        # For subsequent games: Asshole can play any cards (no restriction)
    else:
        # Must match count
        if count != current_count:
            return ValidationResult.error(
                ERROR_PATTERN_MISMATCH,
                f"Must play {current_count} cards (played {count})"
            )
        
        # Check if rank is valid
        jack_restriction = (
            state.inversion_active and 
            state.current_pattern.last_player and
            extract_rank_from_card(
                state.players[state.current_pattern.last_player].hand[0] if 
                state.players[state.current_pattern.last_player].hand else ""
            ) == 'J'
        )
        
        if not is_valid_next_rank(
            current_rank, 
            rank, 
            state.inversion_active,
            jack_restriction
        ):
            return ValidationResult.error(
                ERROR_RANK_TOO_LOW,
                f"Rank {rank} is not higher than current rank {current_rank}"
            )
    
    # Check for special effects
    effect = get_effect_for_rank(rank)
    
    # Create pattern info
    pattern = {
        'rank': rank,
        'count': count,
        'cards': card_ids.copy()
    }
    
    return ValidationResult.success(pattern, effect)


def validate_pass(state: RoomState, player_id: str) -> ValidationResult:
    """
    Validate a pass attempt.
    
    Args:
        state: Current room state
        player_id: ID of player attempting to pass
    
    Returns:
        ValidationResult with validation outcome
    """
    from .constants import (
        ERROR_NOT_YOUR_TURN, ERROR_ALREADY_PASSED, ERROR_EFFECT_PENDING,
        PHASE_PLAY
    )
    
    # Check if it's the play phase
    if state.phase != PHASE_PLAY:
        return ValidationResult.error(
            ERROR_NOT_YOUR_TURN,
            f"Game is not in play phase (current: {state.phase})"
        )
    
    # Check if it's player's turn
    if state.turn != player_id:
        return ValidationResult.error(
            ERROR_NOT_YOUR_TURN,
            f"It's not your turn (current turn: {state.turn})"
        )
    
    # Check for pending effects
    if state.pending_gift or state.pending_discard:
        return ValidationResult.error(
            ERROR_EFFECT_PENDING,
            "Must complete pending effect before passing"
        )
    
    # Get player
    player = state.players.get(player_id)
    if not player:
        return ValidationResult.error(
            ERROR_NOT_YOUR_TURN,
            "Player not found"
        )
    
    # Check if player has already passed
    if player.passed:
        return ValidationResult.error(
            ERROR_ALREADY_PASSED,
            "Player has already passed this round"
        )
    
    # Cannot pass on opening play
    if state.current_pattern.rank is None:
        return ValidationResult.error(
            ERROR_NOT_YOUR_TURN,
            "Cannot pass on opening play"
        )
    
    return ValidationResult.success({'action': 'pass'})


def validate_gift_distribution(
    state: RoomState,
    player_id: str,
    assignments: List[Dict]
) -> ValidationResult:
    """
    Validate gift distribution assignments.
    
    Args:
        state: Current room state
        player_id: Player giving the gifts
        assignments: List of {to: player_id, cards: [card_ids]}
    
    Returns:
        ValidationResult with validation outcome
    """
    from .constants import (
        ERROR_EFFECT_PENDING, ERROR_INVALID_GIFT_DISTRIBUTION,
        ERROR_OWNERSHIP, ERROR_NOT_YOUR_TURN
    )
    
    # Check if there's a pending gift
    if not state.pending_gift:
        return ValidationResult.error(
            ERROR_EFFECT_PENDING,
            "No pending gift distribution"
        )
    
    # Check if it's the right player
    if state.pending_gift.player_id != player_id:
        return ValidationResult.error(
            ERROR_NOT_YOUR_TURN,
            "Not your gift to distribute"
        )
    
    # Get player
    player = state.players.get(player_id)
    if not player:
        return ValidationResult.error(
            ERROR_NOT_YOUR_TURN,
            "Player not found"
        )
    
    # Count total cards being gifted
    total_cards = sum(len(assignment.get('cards', [])) for assignment in assignments)
    
    if total_cards != state.pending_gift.remaining:
        return ValidationResult.error(
            ERROR_INVALID_GIFT_DISTRIBUTION,
            f"Must gift exactly {state.pending_gift.remaining} cards (gifting {total_cards})"
        )
    
    # Collect all cards being gifted
    all_gifted_cards = []
    for assignment in assignments:
        cards = assignment.get('cards', [])
        all_gifted_cards.extend(cards)
        
        # Check recipient exists
        recipient_id = assignment.get('to')
        if recipient_id not in state.players:
            return ValidationResult.error(
                ERROR_INVALID_GIFT_DISTRIBUTION,
                f"Invalid recipient: {recipient_id}"
            )
        
        # Cannot gift to self
        if recipient_id == player_id:
            return ValidationResult.error(
                ERROR_INVALID_GIFT_DISTRIBUTION,
                "Cannot gift cards to yourself"
            )
    
    # Check ownership of all cards
    if not validate_ownership(player, all_gifted_cards):
        return ValidationResult.error(
            ERROR_OWNERSHIP,
            "Player does not own all cards being gifted"
        )
    
    # Check for duplicates
    if len(all_gifted_cards) != len(set(all_gifted_cards)):
        return ValidationResult.error(
            ERROR_INVALID_GIFT_DISTRIBUTION,
            "Cannot gift the same card multiple times"
        )
    
    return ValidationResult.success({'assignments': assignments})


def validate_discard_selection(
    state: RoomState,
    player_id: str,
    card_ids: List[str]
) -> ValidationResult:
    """
    Validate discard selection for Ten effect.
    
    Args:
        state: Current room state
        player_id: Player discarding cards
        card_ids: Cards to discard
    
    Returns:
        ValidationResult with validation outcome
    """
    from .constants import (
        ERROR_EFFECT_PENDING, ERROR_INVALID_DISCARD_SELECTION,
        ERROR_OWNERSHIP, ERROR_NOT_YOUR_TURN
    )
    
    # Check if there's a pending discard
    if not state.pending_discard:
        return ValidationResult.error(
            ERROR_EFFECT_PENDING,
            "No pending discard selection"
        )
    
    # Check if it's the right player
    if state.pending_discard.player_id != player_id:
        return ValidationResult.error(
            ERROR_NOT_YOUR_TURN,
            "Not your discard to make"
        )
    
    # Get player
    player = state.players.get(player_id)
    if not player:
        return ValidationResult.error(
            ERROR_NOT_YOUR_TURN,
            "Player not found"
        )
    
    # Check card count
    required_count = state.pending_discard.remaining
    provided_count = len(card_ids)
    max_possible = len(player.hand)
    
    if provided_count > required_count:
        return ValidationResult.error(
            ERROR_INVALID_DISCARD_SELECTION,
            f"Can discard at most {required_count} cards (trying to discard {provided_count})"
        )
    
    if provided_count > max_possible:
        return ValidationResult.error(
            ERROR_INVALID_DISCARD_SELECTION,
            f"Player only has {max_possible} cards"
        )
    
    # Check ownership
    if not validate_ownership(player, card_ids):
        return ValidationResult.error(
            ERROR_OWNERSHIP,
            "Player does not own all specified cards"
        )
    
    # Check for duplicates
    if len(card_ids) != len(set(card_ids)):
        return ValidationResult.error(
            ERROR_INVALID_DISCARD_SELECTION,
            "Cannot discard the same card multiple times"
        )
    
    return ValidationResult.success({'cards': card_ids}) 