"""
Greedy bot implementation with basic heuristics.
"""

import random
from typing import Dict, List, Optional

from .base import BaseBot, BotAction
from ..comparator import extract_rank_from_card, get_rank_index, sort_ranks
from ..constants import PHASE_EXCHANGE, EFFECT_TEN_DISCARD
from ..models import RoomState


class GreedyBot(BaseBot):
    """
    Greedy bot that tries to play optimally with simple heuristics.
    
    Strategy:
    - Play lowest possible cards to win tricks
    - Avoid triggering ten discard unless forced
    - Try to shed many cards when possible
    - Gift low cards to opponents
    - Return low cards during exchange
    """
    
    def choose_action(self, state: RoomState) -> Optional[BotAction]:
        """Choose the best action for the current state."""
        
        # Handle pending effects first
        if self.has_pending_gift(state):
            return self._choose_gift_distribution(state)
        
        if self.has_pending_discard(state):
            return self._choose_discard_selection(state)
        
        if self.has_pending_exchange(state):
            return self._choose_exchange_return(state)
        
        # Handle regular play
        if state.phase == "play" and self.is_my_turn(state):
            return self._choose_play_action(state)
        
        return None
    
    def _choose_play_action(self, state: RoomState) -> BotAction:
        """Choose whether to play cards or pass."""
        valid_plays = self.get_valid_plays(state)
        
        if not valid_plays:
            return BotAction.pass_turn()
        
        # Score each valid play
        best_play = None
        best_score = float('-inf')
        
        for play in valid_plays:
            score = self._score_play(state, play)
            if score > best_score:
                best_score = score
                best_play = play
        
        if best_play and best_score > self._get_pass_threshold(state):
            return BotAction.play(best_play)
        else:
            return BotAction.pass_turn()
    
    def _score_play(self, state: RoomState, cards: List[str]) -> float:
        """Score a potential play."""
        if not cards:
            return 0.0
        
        score = 0.0
        hand = self.get_player_hand(state)
        
        # Base score: number of cards played (more is better)
        score += len(cards) * 10
        
        # Penalty for playing high-value cards
        for card in cards:
            rank = extract_rank_from_card(card)
            rank_index = get_rank_index(rank, state.inversion_active)
            # Higher ranks get negative score (want to save them)
            score -= rank_index * 2
        
        # Bonus for going out
        if len(cards) == len(hand):
            score += 100
        
        # Bonus for getting close to going out
        remaining_cards = len(hand) - len(cards)
        if remaining_cards <= 3:
            score += (4 - remaining_cards) * 20
        
        # Check for special effects
        rank = extract_rank_from_card(cards[0])
        
        # Avoid ten discard unless hand is large
        if rank == 10:
            if len(hand) > 8:
                score += 5  # Good to discard when we have many cards
            else:
                score -= 15  # Avoid when we have few cards
        
        # Eight reset is generally good
        if rank == 8:
            score += 15
        
        # Seven gift can be strategic
        if rank == 7:
            # Good if we have many low cards to gift
            low_cards = self._count_low_cards(hand)
            if low_cards >= len(cards):
                score += 10
            else:
                score -= 5
        
        # Jack inversion can be strategic
        if rank == 'J':
            if state.inversion_active:
                score -= 10  # Avoid playing jacks during inversion
            else:
                # Consider if inversion would help us
                if self._would_inversion_help(state, hand):
                    score += 20
                else:
                    score -= 5
        
        return score
    
    def _get_pass_threshold(self, state: RoomState) -> float:
        """Get the threshold for passing vs playing."""
        hand = self.get_player_hand(state)
        
        # Lower threshold (more likely to play) when:
        # - We have many cards
        # - Other players have few cards
        base_threshold = 0.0
        
        if len(hand) > 10:
            base_threshold -= 10
        elif len(hand) < 5:
            base_threshold += 5
        
        # Check other players' card counts
        min_opponent_cards = min(
            self.count_cards_in_hand(state, pid)
            for pid in self.get_other_players(state)
        )
        
        if min_opponent_cards <= 3:
            base_threshold -= 15  # Play aggressively if someone is close to winning
        
        return base_threshold
    
    def _choose_gift_distribution(self, state: RoomState) -> BotAction:
        """Choose how to distribute gift cards."""
        if not state.pending_gift:
            return None
        
        hand = self.get_player_hand(state)
        gift_count = state.pending_gift.remaining
        other_players = self.get_other_players(state)
        
        if not other_players or not hand:
            return None
        
        # Sort hand to give away lowest cards
        from ..shuffle import sort_hand
        sorted_hand = sort_hand(hand, state.inversion_active)
        cards_to_gift = sorted_hand[:gift_count]
        
        # Distribute cards somewhat evenly, favoring players with fewer cards
        assignments = []
        cards_given = 0
        
        # Sort players by card count (ascending)
        players_by_count = sorted(
            other_players,
            key=lambda pid: self.count_cards_in_hand(state, pid)
        )
        
        for i, card in enumerate(cards_to_gift):
            # Distribute round-robin among players, starting with those with fewer cards
            player_index = i % len(players_by_count)
            recipient = players_by_count[player_index]
            
            # Find existing assignment or create new one
            existing = next(
                (a for a in assignments if a['to'] == recipient),
                None
            )
            
            if existing:
                existing['cards'].append(card)
            else:
                assignments.append({
                    'to': recipient,
                    'cards': [card]
                })
        
        return BotAction.gift_distribution(assignments)
    
    def _choose_discard_selection(self, state: RoomState) -> BotAction:
        """Choose which cards to discard for ten effect."""
        if not state.pending_discard:
            return None
        
        hand = self.get_player_hand(state)
        discard_count = state.pending_discard.remaining
        
        if not hand:
            return BotAction.discard_selection([])
        
        # Discard lowest cards up to the required count
        from ..shuffle import sort_hand
        sorted_hand = sort_hand(hand, state.inversion_active)
        cards_to_discard = sorted_hand[:min(discard_count, len(hand))]
        
        return BotAction.discard_selection(cards_to_discard)
    
    def _choose_exchange_return(self, state: RoomState) -> BotAction:
        """Choose which cards to return during exchange."""
        from ..exchange import get_pending_exchange_actions
        
        pending_actions = get_pending_exchange_actions(state)
        action = pending_actions.get(self.player_id)
        
        if not action or action['action'] != 'return':
            return None
        
        hand = self.get_player_hand(state)
        return_count = action['count']
        
        # Return lowest cards
        from ..shuffle import sort_hand
        sorted_hand = sort_hand(hand, inversion=False)  # Always use normal order for exchange
        cards_to_return = sorted_hand[:return_count]
        
        return BotAction.exchange_return(cards_to_return)
    
    def _count_low_cards(self, hand: List[str]) -> int:
        """Count cards that are considered 'low' value."""
        low_count = 0
        for card in hand:
            rank = extract_rank_from_card(card)
            if isinstance(rank, int) and rank <= 6:  # 3,4,5,6 are considered low
                low_count += 1
        return low_count
    
    def _would_inversion_help(self, state: RoomState, hand: List[str]) -> bool:
        """Check if jack inversion would be beneficial."""
        if not hand:
            return False
        
        # Count low ranks in hand
        low_ranks = 0
        high_ranks = 0
        
        for card in hand:
            rank = extract_rank_from_card(card)
            rank_index = get_rank_index(rank, inversion=False)
            
            if rank_index < 7:  # Lower half of ranks
                low_ranks += 1
            else:
                high_ranks += 1
        
        # Inversion helps if we have more low ranks than high ranks
        return low_ranks > high_ranks
    
    def _get_strategic_wait_value(self, state: RoomState) -> float:
        """Calculate value of waiting/passing strategically."""
        hand = self.get_player_hand(state)
        
        # Check if we have powerful effect cards
        has_eight = any(extract_rank_from_card(c) == 8 for c in hand)
        has_jack = any(extract_rank_from_card(c) == 'J' for c in hand)
        
        strategic_value = 0.0
        
        if has_eight:
            strategic_value += 10  # Eight reset is always useful
        
        if has_jack and not state.inversion_active:
            if self._would_inversion_help(state, hand):
                strategic_value += 15  # Jack inversion could be very helpful
        
        return strategic_value 