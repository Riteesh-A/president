import dash
from dash import dcc, html, Input, Output, State, callback_context, ALL, MATCH, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Tuple, Union
import random
import json
import time
import threading
from collections import defaultdict
import uuid
import num2words
import pandas as pd  # Add this import at the top

# ===================== GAME MODELS =====================

Rank = Union[int, Literal['J','Q','K','A',2,'JOKER']]

@dataclass
class Player:
    id: str
    name: str
    seat: int
    role: Optional[str] = None  # President, VicePresident, Citizen, Scumbag, Asshole
    hand: List[str] = field(default_factory=list)  # card ids
    passed: bool = False
    connected: bool = True
    is_bot: bool = False
    hand_count: int = 0

@dataclass
class RoomState:
    id: str
    version: int = 0
    phase: str = 'lobby'  # lobby|dealing|exchange|play|finished
    players: Dict[str, Player] = field(default_factory=dict)
    turn: Optional[str] = None
    current_rank: Optional[Rank] = None
    current_count: Optional[int] = None
    inversion_active: bool = False
    deck: List[str] = field(default_factory=list)
    discard: List[str] = field(default_factory=list)
    current_pile: List[str] = field(default_factory=list)  # Cards currently in play
    round_history: List[dict] = field(default_factory=list)  # History of plays in current round
    completed_rounds: List[dict] = field(default_factory=list)  # Complete history of all finished rounds
    finished_order: List[str] = field(default_factory=list)
    pending_gift: Optional[dict] = None
    pending_discard: Optional[dict] = None
    last_play: Optional[dict] = None
    game_log: List[str] = field(default_factory=list)
    first_game: bool = True # Add this field
    last_round_winner: Optional[str] = None # Add this field
    first_game_first_play_done: bool = False # Add this field
    global_asshole_id: Optional[str] = None # Add this field
    # Card exchange phase
    pending_exchange: Optional[dict] = None  # Exchange phase data
    exchange_phase: bool = False  # Whether we're in exchange phase
    # Role tracking for current and previous game
    current_game_roles: Dict[str, str] = field(default_factory=dict)
    previous_game_roles: Dict[str, str] = field(default_factory=dict)

# ===================== GAME CONSTANTS & UTILS =====================

NORMAL_ORDER = [3,4,5,6,7,8,9,10,'J','Q','K','A',2,'JOKER']
SUITS = ['S', 'H', 'D', 'C']

def create_deck(use_jokers=True):
    deck = []
    for suit in SUITS:
        for rank in [3,4,5,6,7,8,9,10,'J','Q','K','A',2]:
            deck.append(f"{rank}{suit}")
    if use_jokers:
        deck.extend(['JOKERa', 'JOKERb'])
    return deck

def parse_card(card_id):
    if card_id.startswith('JOKER'):
        return 'JOKER', None
    if card_id[:-1] in ['J', 'Q', 'K', 'A']:
        return card_id[:-1], card_id[-1]
    if card_id[:-1] == '10':
        return 10, card_id[-1]
    return int(card_id[:-1]), card_id[-1]

def compare_ranks(rank_a, rank_b, inversion=False):
    order = list(reversed(NORMAL_ORDER)) if inversion else NORMAL_ORDER
    try:
        return order.index(rank_a) - order.index(rank_b)
    except ValueError:
        return 0

def is_higher_rank(rank_a, rank_b, inversion=False):
    return compare_ranks(rank_a, rank_b, inversion) > 0

def can_joker_beat_rank(target_rank, inversion=False):
    """
    Check if a joker can beat the target rank by acting as any valid rank.
    Args:
        target_rank: The rank to beat
        inversion: Whether inversion is active
    Returns:
        bool: True if joker can beat the target rank
    """
    if inversion:
        # During inversion, joker can act as any rank that beats the target
        # Inverted order, lower ranks beat higher ranks
        order = list(reversed(NORMAL_ORDER))
        try:
            target_index = order.index(target_rank)
            # Joker can act as any rank with lower index (higher in normal order)
            # But must be a valid rank for the current game state
            return True  # Joker can always choose an appropriate rank
        except ValueError:
            return False
    else:
        # Normal order, joker can act as any rank that beats the target
        order = NORMAL_ORDER
        try:
            target_index = order.index(target_rank)
            # Joker can act as any rank with higher index
            return True  # Joker can always choose an appropriate rank
        except ValueError:
            return False

def determine_joker_effective_rank(target_rank, inversion=False):
    """
    Determine what rank a joker should act as to beat the target rank.
    Args:
        target_rank: The rank to beat
        inversion: Whether inversion is active
    Returns:
        The effective rank the joker should act as
    """
    if inversion:
        # During inversion, lower ranks beat higher ranks
        # Choose the lowest rank that still beats the target
        order = list(reversed(NORMAL_ORDER))
        try:
            target_index = order.index(target_rank)
            # Find the next rank in the inverted order (lower index = higher rank in normal order)
            for i in range(target_index + 1, len(order)):
                rank = order[i]
                # Skip JOKER itself and invalid ranks
                if rank != 'JOKER' and rank in NORMAL_ORDER:
                    return rank
            # If no better rank found, use the highest possible rank
            return 2
        except ValueError:
            return 2
    else:
        # Normal order, higher ranks beat lower ranks
        # Choose the lowest rank that still beats the target
        order = NORMAL_ORDER
        try:
            target_index = order.index(target_rank)
            # Find the next rank in normal order
            for i in range(target_index + 1, len(order)):
                rank = order[i]
                # Skip JOKER itself
                if rank != 'JOKER':
                    return rank
            # If no better rank found, use JOKER as the highest
            return 'JOKER'
        except ValueError:
            return 'JOKER'

# ===================== GAME ENGINE =====================
class PresidentEngine:
    def __init__(self):
        self.rooms: Dict[str, RoomState] = {}
        self.room_locks = defaultdict(threading.Lock)
    
    def create_room(self, room_id: str) -> RoomState:
        with self.room_locks[room_id]:
            if room_id not in self.rooms:
                self.rooms[room_id] = RoomState(id=room_id)
            return self.rooms[room_id]
    
    def get_room(self, room_id: str) -> Optional[RoomState]:
        return self.rooms.get(room_id)
    
    def add_player(self, room_id: str, player_name: str, is_bot: bool = False) -> Tuple[bool, str]:
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room:
                return False, "Room not found"
            if len(room.players) >= 5:
                return False, "Room is full"
            player_id = str(uuid.uuid4())[:8]
            seat = len(room.players)
            room.players[player_id] = Player(
                id=player_id,
                name=player_name,
                seat=seat,
                is_bot=is_bot
            )
            room.version += 1
            return True, player_id
    
    def start_game(self, room_id: str) -> Tuple[bool, str]:
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room:
                return False, "Room not found"
            if len(room.players) < 3:
                return False, "Need at least 3 players"
            room.phase = 'dealing'
            # Clear game state for new game
            room.finished_order = []  # Always clear for new game
            room.current_game_roles.clear()  # Clear current game roles
            room.game_log = []

            # Clear player roles for new game (but preserve previous_game_roles for card exchange)
            for player in room.players.values():
                player.role = None

            # Create deck and deal cards
            deck = create_deck(True)
            random.shuffle(deck)
            players = list(room.players.values())
            cards_per_player = len(deck) // len(players)
            for i, player in enumerate(players):
                start_idx = i * cards_per_player
                end_idx = start_idx + cards_per_player
                if i == len(players) - 1:
                    end_idx = len(deck)
                player.hand = deck[start_idx:end_idx]
                player.hand_count = len(player.hand)
                player.passed = False

            # Set first_game flag
            if not hasattr(room, 'first_game'):
                room.first_game = True

            # Check if this is a subsequent game and start card exchange
            if not room.first_game and room.previous_game_roles:
                # Start card exchange phase
                self._start_card_exchange(room)
                room.phase = 'exchange'  # Set phase to exchange instead of play
                room.version += 1
                return True, "Card exchange phase started"
            else:
                # First game or no previous roles - start normal play
                # Set starter
                if room.first_game:
                    starter = None
                    for player in players:
                        if '3D' in player.hand:
                            starter = player.id
                            break
                    if not starter:
                        starter = players[0].id
                    room.turn = starter
                else:
                    # Asshole from previous game starts (last in finished_order)
                    asshole_id = None
                    if hasattr(room, 'global_asshole_id') and room.global_asshole_id in room.players:
                        asshole_id = room.global_asshole_id
                    elif room.finished_order:
                        asshole_id = room.finished_order[-1]
                    if asshole_id and asshole_id in room.players:
                        room.turn = asshole_id
                    else:
                        room.turn = players[0].id
                room.phase = 'play'
                room.current_rank = None
                room.current_count = None
                room.inversion_active = False
                room.version += 1
                starter_name = room.players[room.turn].name
                if room.first_game:
                    room.game_log.append(f"Game started! {starter_name} goes first (has 3♦)")
                else:
                    room.game_log.append(f"New round! {starter_name} (Asshole) goes first")
                return True, "Game started!"
    
    def validate_play(self, room: RoomState, player_id: str, card_ids: List[str]) -> Tuple[bool, str, Optional[dict]]:
        """
        Validate a play of cards by a player.
        Args:
            room: The current room state
            player_id: The ID of the player making the play
            card_ids: The IDs of the cards being played
        Returns:
            Tuple[bool, str, Optional[dict]]: A tuple containing:
                - bool: True if the play is valid, False otherwise
                - str: An error message if the play is invalid, or "Valid play" if it is valid
                - Optional[dict]: A dictionary containing the rank, count, and effect of the play if it is valid, None otherwise
        """
        if room.exchange_phase:
            return True, "Card exchange phase- Validation skipped", None
        player = room.players.get(player_id)
        if not player:
            return False, "Player not found", None
        if room.turn != player_id:
            return False, "Not your turn", None
        for card_id in card_ids:
            if card_id not in player.hand:
                return False, f"You don't own {card_id}", None
        
        # Parse all cards and handle Jokers
        ranks = [parse_card(c)[0] for c in card_ids]
        
        # Separate jokers from regular cards
        regular_ranks = [r for r in ranks if r != 'JOKER']
        joker_count = ranks.count('JOKER')
        
        # Validate card combination
        if len(set(regular_ranks)) > 1:
            return False, "All non-Joker cards must be same rank", None
        
        # Determine effective play rank
        if regular_ranks:
            # If we have regular cards, Jokers act as that rank
            play_rank = regular_ranks[0]
        elif joker_count > 0:
            # If only Jokers, they can act as any rank
            # For validation purposes, we'll treat them as the highest possible rank
            # The actual rank will be determined when the play is made
            play_rank = 'JOKER'
        else:
            return False, "No cards to play", None
            
        play_count = len(card_ids)
        
        # Only enforce 3s rule if first_game and opening play
        if room.current_rank is None:
            if getattr(room, 'first_game', True) and not getattr(room, 'first_game_first_play_done', False):
                # Check if the play contains any 3s or Jokers
                has_valid_first_play = False
                for card_id in card_ids:
                    rank = parse_card(card_id)[0]
                    if rank == 3 or rank == 'JOKER':
                        has_valid_first_play = True
                        break
                if not has_valid_first_play:
                    return False, "First play of the game must contain 3s or Jokers", None
            effect = self._get_effect_type(play_rank)
            return True, "Valid play", {'rank': play_rank, 'count': play_count, 'effect': effect}
        
        # Check if play count matches current count
        if play_count != room.current_count:
            return False, f"Must play exactly {room.current_count} cards", None
        
        # Check if play can beat current rank
        can_beat = False
        if play_rank == 'JOKER':
            # Joker can act as any rank that beats the current rank
            can_beat = can_joker_beat_rank(room.current_rank, room.inversion_active)
        else:
            # Regular rank comparison (including when jokers act as the same rank)
            can_beat = is_higher_rank(play_rank, room.current_rank, room.inversion_active)
        
        if not can_beat:
            return False, f"Must play higher than {room.current_rank}", None
        
        # Check if play rank is valid after Jack inversion
        if room.inversion_active and room.current_rank == 'J':
            pre_jack_ranks = [3,4,5,6,7,8,9,10]
            if play_rank not in pre_jack_ranks and play_rank != 'JOKER':
                return False, "After Jack inversion, only lower ranks (3-10) allowed", None
        
        # Get effect type for the play
        effect = self._get_effect_type(play_rank)
        return True, "Valid play", {'rank': play_rank, 'count': play_count, 'effect': effect}

    def _get_effect_type(self, rank) -> Optional[str]:
        """
        Get the effect type for a given rank.
        Args:
            rank: The rank of the card
        Returns:
            Optional[str]: The effect type if the rank has an effect, None otherwise
        """
        if rank == 7: return 'seven_gift'
        if rank == 8: return 'eight_reset'
        if rank == 10: return 'ten_discard'
        if rank == 'J': return 'jack_inversion'
        return None

    def _save_completed_round(self, room: RoomState, reason: str):
        """
        Save the current round to completed rounds history
        Args:
            room: The current room state
            reason: The reason for saving the round
        """
        if room.round_history:
            round_data = {
                'round_number': len(room.completed_rounds) + 1,
                'plays': room.round_history.copy(),
                'ended_by': reason,
                'winner': room.last_play['player_name'] if room.last_play else 'Unknown'
            }
            room.completed_rounds.append(round_data)

    def play_cards(self, room_id: str, player_id: str, card_ids: List[str]) -> Tuple[bool, str]:
        """
        Play cards by a player.
        Args:
            room_id: The ID of the room
            player_id: The ID of the player making the play
            card_ids: The IDs of the cards being played
        Returns:
            Tuple[bool, str]: A tuple containing:
                - bool: True if the play is successful, False otherwise
                - str: A message indicating the result of the play
        """
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            valid, message, pattern = self.validate_play(room, player_id, card_ids)
            if not valid:
                return False, message
            
            # Determine effective rank for jokers
            effective_rank = pattern['rank']
            jokers_played = any(parse_card(c)[0] == 'JOKER' for c in card_ids)
            regular_cards = [c for c in card_ids if parse_card(c)[0] != 'JOKER']
            
            if jokers_played:
                if len(regular_cards) == 0:
                    # Only jokers played - they act as 2 (or 3 during inversion)
                    if room.inversion_active:
                        effective_rank = 3
                    else:
                        effective_rank = 2
                else:
                    # Mixed play - jokers assume the rank of the regular cards
                    regular_rank = parse_card(regular_cards[0])[0]
                    effective_rank = regular_rank
            
            # Mark first play of first game as done
            if getattr(room, 'first_game', True) and not getattr(room, 'first_game_first_play_done', False) and room.current_rank is None:
                room.first_game_first_play_done = True
            player = room.players[player_id]
            for card_id in card_ids:
                player.hand.remove(card_id)
            player.hand_count = len(player.hand)
            
            # Add cards to current pile
            room.current_pile = card_ids.copy()
            # Add to round history with effective rank
            room.round_history.append({
                'player_name': player.name,
                'cards': card_ids.copy(),
                'rank': effective_rank,
                'count': pattern['count']
            })
            room.current_rank = effective_rank
            room.current_count = pattern['count']
            room.last_play = {'player_id': player_id, 'player_name': player.name, 'cards': card_ids, 'rank': effective_rank, 'count': pattern['count']}
            for p in room.players.values(): p.passed = False
            
            #print(f"Current count: {room.current_count}, Hand count: {player.hand_count}")
            # Apply effects first (before auto-win check)
            effect_applied = False
            if pattern['effect']:
                effect_applied = self._apply_effect(room, player_id, pattern['effect'], pattern['count'])
            # Also check for effects based on effective rank (for jokers)
            if not effect_applied and effective_rank != pattern['rank']:
                effective_effect = self._get_effect_type(effective_rank)
                if effective_effect:
                    effect_applied = self._apply_effect(room, player_id, effective_effect, pattern['count'])
            
            # Check for automatic round win (2, JOKER, or 3 during inversion)
            auto_win = False
            
            # Auto-win if playing the absolute highest rank
            if not room.inversion_active and effective_rank == 2:
                auto_win = True
                room.game_log.append(f"{player.name} played {effective_rank} - automatic round win!")
            elif room.inversion_active and effective_rank == 3:
                auto_win = True
                room.game_log.append(f"{player.name} played {effective_rank} during inversion - automatic round win!")
            
            # Check if player finished this turn (before auto-win return)
            finished_this_turn = False
            if len(player.hand) == 0:
                if player_id not in room.finished_order:
                    room.finished_order.append(player_id)
                    room.game_log.append(f"{player.name} finished in position {len(room.finished_order)}!")
                    assign_roles_dynamic(room)
                finished_this_turn = True
            
            if auto_win:
                # Save round before clearing
                self._save_completed_round(room, f"Auto-win ({effective_rank})")
                # Move current pile to discard
                room.discard.extend(room.current_pile)
                room.current_pile = []
                room.round_history = []  # Clear round history
                room.current_rank = None
                room.current_count = None
                room.inversion_active = False
                
                # Check if player who auto-won has cards left in their hand
                if len(player.hand) == 0:
                    # Player who auto-won has no cards left in their hand
                    room.game_log.append(f"{player.name} completed their hand!")
                    # Advance turn to next player
                    self._advance_turn(room)
                    return True, "Auto-win + Completed hand! New round started"
                else:
                    # Same player starts next round
                    for p in room.players.values(): p.passed = False
                    room.version += 1
                    room.game_log.append(f"{player.name} starts new round after auto-win")
                    room.last_round_winner = player_id  # Set last_round_winner
                    return True, "Auto-win! New round started"
            # Check if game ended due to player finishing
            game_ended = False
            if finished_this_turn:
                game_ended = self._check_game_end(room)
            
            # Always advance turn if player finished and game didn't end
            if finished_this_turn and not game_ended:
                self._advance_turn(room)
            elif not effect_applied or pattern['effect'] == 'eight_reset':
                if pattern['effect'] == 'eight_reset':
                    # Save round before clearing
                    self._save_completed_round(room, "Eight reset")
                    # Move current pile to discard before reset
                    room.discard.extend(room.current_pile)
                    room.current_pile = []
                    room.round_history = []  # Clear round history on reset
                    room.current_rank = None
                    room.current_count = None
                    room.inversion_active = False
                    room.game_log.append(f"{player.name} played {pattern['count']} 8s - pile cleared!")
                    room.last_round_winner = player_id  # Set last_round_winner
                elif not game_ended:
                    # Only advance turn if game didn't end
                    self._advance_turn(room)
            room.version += 1
            # Show effective rank in log if joker was played
            if pattern['rank'] == 'JOKER' and effective_rank != 'JOKER':
                room.game_log.append(f"{player.name} played: {', '.join([self._format_card(c) for c in card_ids])} (as {effective_rank})")
            else:
                room.game_log.append(f"{player.name} played: {', '.join([self._format_card(c) for c in card_ids])}")
            return True, "Cards played successfully"

    def _apply_effect(self, room: RoomState, player_id: str, effect: str, count: int) -> bool:
        """
        Apply an effect to the room.
        Args:
            room: The current room state
            player_id: The ID of the player making the play
            effect: The effect to apply
            count: The number of cards to apply the effect to
        Returns:
            bool: True if the effect was applied, False otherwise
        """
        player = room.players[player_id]
        if effect == 'seven_gift':
            # If player has no cards left, skip the gift effect
            if len(player.hand) == 0:
                room.game_log.append(f"{room.players[player_id].name} played 7 as last card - no gift needed!")
                return False
            remaining = min(count, len(player.hand))
            room.pending_gift = {'player_id': player_id, 'remaining': remaining}
            room.game_log.append(f"{room.players[player_id].name} must gift {remaining} cards!")
            return True
        if effect == 'eight_reset': return False
        if effect == 'ten_discard':
            # If player has no cards left, skip the discard effect
            if len(player.hand) == 0:
                room.game_log.append(f"{room.players[player_id].name} played 10 as last card - no discard needed!")
                return False
            remaining = min(count, len(player.hand))
            room.pending_discard = {'player_id': player_id, 'remaining': remaining}
            room.game_log.append(f"{room.players[player_id].name} must discard {remaining} cards!")
            return True
        if effect == 'jack_inversion':
            room.inversion_active = True
            room.game_log.append("Rank order inverted! Lower ranks now beat higher ranks!")
            return False
        return False

    def _check_game_end(self, room: RoomState):
        """
        Check if the game should end (only one player left with cards)
        Args:
            room: The current room state
        Returns:
            bool: True if the game should end, False otherwise
        """
        players_with_cards = [p for p in room.players.values() if len(p.hand) > 0]
        if len(players_with_cards) <= 1:
            # Add the last player(s) to finished order if not already there
            for p in players_with_cards:
                if p.id not in room.finished_order:
                    room.finished_order.append(p.id)
                    room.game_log.append(f"{p.name} finished LAST - Asshole!")
            self._end_game(room)
            return True
        return False

    def _advance_turn_if_no_pending(self, room: RoomState):
        """
        Only advance turn if no pending effects
        Args:
            room: The current room state
        """
        if not room.pending_gift and not room.pending_discard:
            # Check if game should end before advancing turn
            if not self._check_game_end(room):
                self._advance_turn(room)

    def submit_gift_distribution(self, room_id: str, player_id: str, assignments: List[dict]) -> Tuple[bool, str]:
        """
        Submit a gift distribution to the room.
        Args:
            room_id: The ID of the room
            player_id: The ID of the player making the gift
            assignments: A list of dictionaries, each containing a 'to' key with the ID of the recipient and a 'cards' key with the IDs of the cards to be gifted
        Returns:
            Tuple[bool, str]: A tuple containing:
                - bool: True if the gift distribution was successful, False otherwise
                - str: A message indicating the result of the gift distribution
        """
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room: return False, "Room not found"
            if not room.pending_gift: return False, "No gift pending"
            if room.pending_gift['player_id'] != player_id: return False, "Not your gift"
            
            player = room.players[player_id]
            total_cards = sum(len(a['cards']) for a in assignments)
            
            if total_cards != room.pending_gift['remaining']:
                return False, f"Must gift exactly {room.pending_gift['remaining']} cards"
            
            # Validate ownership
            all_cards = []
            for assignment in assignments:
                all_cards.extend(assignment['cards'])
            
            for card in all_cards:
                if card not in player.hand:
                    return False, f"You don't own {card}"
            
            # Transfer cards
            for assignment in assignments:
                recipient = room.players[assignment['to']]
                for card in assignment['cards']:
                    player.hand.remove(card)
                    recipient.hand.append(card)
                    recipient.hand_count = len(recipient.hand)
            
            player.hand_count = len(player.hand)
            room.pending_gift = None
            
            # Log the gift
            gift_details = []
            for assignment in assignments:
                recipient_name = room.players[assignment['to']].name
                gifted_cards = [self._format_card(c) for c in assignment['cards']][0].replace(' of ', ' ')
                gift_details.append(f"{len(assignment['cards'])} {gifted_cards} to {recipient_name}")
            room.game_log.append(f"{player.name} gifted: {', '.join(gift_details)}")
            
            # Check if player finished after gifting
            finished_this_turn = False
            if len(player.hand) == 0:
                if player_id not in room.finished_order:
                    room.finished_order.append(player_id)
                    room.game_log.append(f"{player.name} finished in position {len(room.finished_order)}!")
                    assign_roles_dynamic(room)
                finished_this_turn = True
                self._check_game_end(room)
            
            # Check if game ends after gift, otherwise advance turn
            if not self._check_game_end(room):
                if finished_this_turn:
                    self._advance_turn_if_no_pending(room)
                else:
                    self._advance_turn_if_no_pending(room)
            room.version += 1
            return True, "Gift distributed successfully"

    def submit_discard_selection(self, room_id: str, player_id: str, card_ids: List[str]) -> Tuple[bool, str]:
        """
        Submit a discard selection to the room.
        Args:
            room_id: The ID of the room
            player_id: The ID of the player making the discard
            card_ids: The IDs of the cards being discarded
        Returns:
            Tuple[bool, str]: A tuple containing:
                - bool: True if the discard selection was successful, False otherwise
                - str: A message indicating the result of the discard selection
        """
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room: return False, "Room not found"
            if not room.pending_discard: return False, "No discard pending"
            if room.pending_discard['player_id'] != player_id: return False, "Not your discard"
            
            player = room.players[player_id]
            required = room.pending_discard['remaining']
            
            if len(card_ids) > required:
                return False, f"Can only discard {required} cards"
            
            # Validate ownership
            for card in card_ids:
                if card not in player.hand:
                    return False, f"You don't own {card}"
            
            # Remove cards from hand and add to discard
            for card in card_ids:
                player.hand.remove(card)
                room.discard.append(card)
            
            player.hand_count = len(player.hand)
            discarded_count = len(card_ids)
            remaining = required - discarded_count
            
            # Check if player finished after discarding
            finished_this_turn = False
            if len(player.hand) == 0:
                if player_id not in room.finished_order:
                    room.finished_order.append(player_id)
                    room.game_log.append(f"{player.name} finished in position {len(room.finished_order)}!")
                    assign_roles_dynamic(room)
                finished_this_turn = True
                self._check_game_end(room)
            
            if remaining <= 0:
                room.pending_discard = None
                room.game_log.append(f"{player.name} discarded {discarded_count} cards")
                # Check if game ends after discard, otherwise advance turn
                if not self._check_game_end(room):
                    if finished_this_turn:
                        self._advance_turn_if_no_pending(room)
                    else:
                        self._advance_turn_if_no_pending(room)
            else:
                room.pending_discard['remaining'] = remaining
                room.game_log.append(f"{player.name} discarded {discarded_count} cards ({remaining} more needed)")
            
            room.version += 1
            return True, f"Discarded {discarded_count} cards" + (f" ({remaining} more needed)" if remaining > 0 else "")

    def _advance_turn(self, room: RoomState):
        players = sorted(room.players.values(), key=lambda p: p.seat)
        idx = next((i for i,p in enumerate(players) if p.id == room.turn), 0)
        n = len(players)
        for i in range(1, n+1):
            nxt = players[(idx + i) % n]
            if len(nxt.hand) > 0:  # Only advance to players with cards
                room.turn = nxt.id
                return
        # If no one has cards, set turn to None
        room.turn = None

    def pass_turn(self, room_id: str, player_id: str) -> Tuple[bool, str]:
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room: return False, "Room not found"
            if room.turn != player_id: return False, "Not your turn"
            player = room.players[player_id]
            player.passed = True
            room.game_log.append(f"{player.name} passed")
            active = [p for p in room.players.values() if p.hand and not p.passed]
            if len(active) <= 1:
                # Save round before clearing
                self._save_completed_round(room, "All players passed")
                # Move current pile to discard when round ends
                room.discard.extend(room.current_pile)
                room.current_pile = []
                room.round_history = []  # Clear round history when round ends
                room.current_rank = None
                room.current_count = None
                room.inversion_active = False
                if room.last_play:
                    room.turn = room.last_play['player_id']
                    room.game_log.append(f"{room.players[room.turn].name} starts new round")
                    room.last_round_winner = room.last_play['player_id'] # Set last_round_winner
                for p in room.players.values(): p.passed = False
                # Assign roles in case the last player finished by passing
                assign_roles_dynamic(room)
            else:
                self._advance_turn(room)
            room.version += 1
            return True, "Passed"

    def _end_game(self, room: RoomState):
        # Add any remaining players to finished_order if they haven't been added yet
        for p in room.players.values():
            if p.id not in room.finished_order and len(p.hand) == 0:
                room.finished_order.append(p.id)
                room.game_log.append(f"{p.name} finished in position {len(room.finished_order)}!")
        
        # Only add players who actually finished (have no cards) to finished_order
        # Don't add players who still have cards - they should be added when they actually finish
        # The finished_order should only contain players who actually emptied their hands
        
        # Use assign_roles_dynamic to ensure consistent role assignment
        assign_roles_dynamic(room)
        
        # Store current game roles as previous game roles for card exchange
        room.previous_game_roles = room.current_game_roles.copy()
        
        room.phase = 'finished'
        room.game_log.append("Game finished!")
        for i, pid in enumerate(room.finished_order):
            p = room.players[pid]
            room.game_log.append(f"{i+1}. {p.name} - {p.role}")
        room.first_game = False
        # Set global_asshole_id to the last player in finished_order
        if room.finished_order:
            room.global_asshole_id = room.finished_order[-1]

    def _start_card_exchange(self, room: RoomState):
        """Start the card exchange phase between roles"""
        # Find players by role
        president_id = None
        vice_president_id = None
        scumbag_id = None
        asshole_id = None
        
        for pid, role in room.previous_game_roles.items():
            if role == 'President':
                president_id = pid
            elif role == 'Vice President':
                vice_president_id = pid
            elif role == 'Scumbag':
                scumbag_id = pid
            elif role == 'Asshole':
                asshole_id = pid
        
        # Set up exchange phase
        room.exchange_phase = True
        room.pending_exchange = {
            'president_id': president_id,
            'vice_president_id': vice_president_id,
            'scumbag_id': scumbag_id,
            'asshole_id': asshole_id,
            'current_exchange': 'asshole_to_president',  # Start with asshole giving to president
            'asshole_given_cards': [],
            'president_given_cards': [],
            'scumbag_given_cards': [],
            'vice_president_given_cards': []
        }
        
        room.game_log.append("🎁 Card exchange phase started!")
        room.game_log.append(f"Asshole ({room.players[asshole_id].name}) must give 2 best cards to President ({room.players[president_id].name})")

    def submit_asshole_cards(self, room_id: str, asshole_id: str, card_ids: List[str]) -> Tuple[bool, str]:
        """Submit the 2 best cards from asshole to president"""
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room or not room.exchange_phase:
                return False, "Not in exchange phase"
            
            if room.pending_exchange['current_exchange'] != 'asshole_to_president':
                return False, "Not asshole's turn to give cards"
            
            if room.pending_exchange['asshole_id'] != asshole_id:
                return False, "Not your turn"
            
            if len(card_ids) != 2:
                return False, "Must give exactly 2 cards"
            
            # Validate ownership
            asshole = room.players[asshole_id]
            for card in card_ids:
                if card not in asshole.hand:
                    return False, f"You don't own {card}"
            
            # Transfer cards from asshole to president
            president_id = room.pending_exchange['president_id']
            president = room.players[president_id]
            
            for card in card_ids:
                asshole.hand.remove(card)
                president.hand.append(card)
            
            asshole.hand_count = len(asshole.hand)
            president.hand_count = len(president.hand)
            
            room.pending_exchange['asshole_given_cards'] = card_ids
            room.pending_exchange['current_exchange'] = 'president_to_asshole'
            
            room.game_log.append(f"{asshole.name} gave {', '.join([self._format_card(c) for c in card_ids])} to {president.name}")
            room.game_log.append(f"President ({president.name}) must now give 2 cards to Asshole ({asshole.name})")
            
            room.version += 1
            return True, "Cards given to president"

    def submit_president_cards(self, room_id: str, president_id: str, card_ids: List[str]) -> Tuple[bool, str]:
        """Submit the 2 cards from president to asshole"""
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room or not room.exchange_phase:
                return False, "Not in exchange phase"
            
            if room.pending_exchange['current_exchange'] != 'president_to_asshole':
                return False, "Not president's turn to give cards"
            
            if room.pending_exchange['president_id'] != president_id:
                return False, "Not your turn"
            
            if len(card_ids) != 2:
                return False, "Must give exactly 2 cards"
            
            # Validate ownership
            president = room.players[president_id]
            for card in card_ids:
                if card not in president.hand:
                    return False, f"You don't own {card}"
            
            # Transfer cards from president to asshole
            asshole_id = room.pending_exchange['asshole_id']
            asshole = room.players[asshole_id]
            
            for card in card_ids:
                president.hand.remove(card)
                asshole.hand.append(card)
            
            president.hand_count = len(president.hand)
            asshole.hand_count = len(asshole.hand)
            
            room.pending_exchange['president_given_cards'] = card_ids
            
            # Check if we need to do Scumbag → Vice President exchange
            scumbag_id = room.pending_exchange['scumbag_id']
            vice_president_id = room.pending_exchange['vice_president_id']
            
            if scumbag_id and vice_president_id:
                # Move to Scumbag → Vice President exchange
                room.pending_exchange['current_exchange'] = 'scumbag_to_vice'
                room.game_log.append(f"{president.name} gave {', '.join([self._format_card(c) for c in card_ids])} to {asshole.name}")
                room.game_log.append(f"Scumbag ({room.players[scumbag_id].name}) must now give 1 best card to Vice President ({room.players[vice_president_id].name})")
            else:
                # No more exchanges, finish
                room.game_log.append(f"{president.name} gave {', '.join([self._format_card(c) for c in card_ids])} to {asshole.name}")
                self._finish_card_exchange(room)
            
            room.version += 1
            return True, "Cards given to asshole"

    def submit_scumbag_card(self, room_id: str, scumbag_id: str, card_id: str) -> Tuple[bool, str]:
        """Submit the best card from scumbag to vice president"""
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room or not room.exchange_phase:
                return False, "Not in exchange phase"
            
            if room.pending_exchange['current_exchange'] != 'scumbag_to_vice':
                return False, "Not scumbag's turn to give card"
            
            if room.pending_exchange['scumbag_id'] != scumbag_id:
                return False, "Not your turn"
            
            # Validate ownership
            scumbag = room.players[scumbag_id]
            if card_id not in scumbag.hand:
                return False, f"You don't own {card_id}"
            
            # Transfer card from scumbag to vice president
            vice_president_id = room.pending_exchange['vice_president_id']
            vice_president = room.players[vice_president_id]
            
            scumbag.hand.remove(card_id)
            vice_president.hand.append(card_id)
            
            scumbag.hand_count = len(scumbag.hand)
            vice_president.hand_count = len(vice_president.hand)
            
            room.pending_exchange['scumbag_given_cards'] = [card_id]
            room.pending_exchange['current_exchange'] = 'vice_to_scumbag'
            
            room.game_log.append(f"{scumbag.name} gave {self._format_card(card_id)} to {vice_president.name}")
            room.game_log.append(f"Vice President ({vice_president.name}) must now give 1 card to Scumbag ({scumbag.name})")
            
            room.version += 1
            return True, "Card given to vice president"

    def submit_vice_president_card(self, room_id: str, vice_president_id: str, card_id: str) -> Tuple[bool, str]:
        """Submit 1 card from vice president to scumbag"""
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room or not room.exchange_phase:
                return False, "Not in exchange phase"
            
            if room.pending_exchange['current_exchange'] != 'vice_to_scumbag':
                return False, "Not vice president's turn to give card"
            
            if room.pending_exchange['vice_president_id'] != vice_president_id:
                return False, "Not your turn"
            
            # Validate ownership
            vice_president = room.players[vice_president_id]
            if card_id not in vice_president.hand:
                return False, f"You don't own {card_id}"
            
            # Transfer card from vice president to scumbag
            scumbag_id = room.pending_exchange['scumbag_id']
            scumbag = room.players[scumbag_id]
            
            vice_president.hand.remove(card_id)
            scumbag.hand.append(card_id)
            
            vice_president.hand_count = len(vice_president.hand)
            scumbag.hand_count = len(scumbag.hand)
            
            room.pending_exchange['vice_president_given_cards'] = [card_id]
            
            # Finish exchange
            self._finish_card_exchange(room)
            
            room.game_log.append(f"{vice_president.name} gave {self._format_card(card_id)} to {scumbag.name}")
            room.version += 1
            return True, "Card given to scumbag"

    def _finish_card_exchange(self, room: RoomState):
        """Finish the card exchange phase"""
        room.exchange_phase = False
        room.pending_exchange = None
        room.phase = 'play'  # Transition to play phase
        room.game_log.append("🎉 Card exchange completed! Game ready to start.")
        
        # Set turn to the asshole from the previous game
        if room.global_asshole_id and room.global_asshole_id in room.players:
            room.turn = room.global_asshole_id
            room.game_log.append(f"🎯 {room.players[room.global_asshole_id].name} (Asshole from last game) starts the new game!")
        else:
            # Fallback: set turn to first player
            room.turn = list(room.players.keys())[0]
            room.game_log.append(f"🎯 {room.players[room.turn].name} starts the new game!")
        
        # Clear previous game roles for card exchange
        room.previous_game_roles.clear()

    def _format_card(self, card_id: str) -> str:
        rank, suit = parse_card(card_id)
        suit_symbols = {'S':'♠','H':'♥','D':'♦','C':'♣'}
        if rank == 'JOKER': return '🃏'
        return f"{rank}{suit_symbols.get(suit,'')}"

    def _get_card_color(self, card_id: str) -> str:
        rank, suit = parse_card(card_id)
        if suit in ['H', 'D']: return 'red'
        elif suit in ['S', 'C']: return 'black'
        return 'purple'  # JOKER

def create_card_element(card_id: str, size='normal', selectable=False, selected=False):
    rank, suit = parse_card(card_id)
    suit_symbols = {'S':'♠','H':'♥','D':'♦','C':'♣'}
    
    if rank == 'JOKER':
        display_text = '🃏'
        color_class = 'joker'
    else:
        display_text = f"{rank}"
        suit_symbol = suit_symbols.get(suit, '')
        color_class = 'red' if suit in ['H', 'D'] else 'black'
    
    card_style = {
        'border': '2px solid #333',
        'borderRadius': '12px',
        'backgroundColor': 'white',
        'padding': '8px',
        'margin': '4px',
        'display': 'inline-block',
        'textAlign': 'center',
        'minWidth': '50px' if size == 'small' else '70px' if size == 'normal' else '90px',
        'minHeight': '70px' if size == 'small' else '100px' if size == 'normal' else '130px',
        'fontSize': '12px' if size == 'small' else '16px' if size == 'normal' else '24px',
        'fontWeight': 'bold',
        'cursor': 'pointer' if selectable else 'default',
        'boxShadow': '0 4px 8px rgba(0,0,0,0.1)',
        'position': 'relative',
        'transition': 'all 0.2s ease',
        'transform': 'scale(1)'
    }
    
    if selected:
        card_style['backgroundColor'] = '#fff3e0'
        card_style['border'] = '3px solid #ff9800'
        card_style['boxShadow'] = '0 0 25px rgba(255, 152, 0, 0.8), inset 0 0 10px rgba(255, 152, 0, 0.3)'
        card_style['transform'] = 'scale(1.1) translateY(-8px)'
        card_style['zIndex'] = '100'
    else:
        # Add hover effect via CSS class
        card_style['transition'] = 'all 0.15s ease'
    
    if color_class == 'red':
        card_style['color'] = '#d32f2f'
    elif color_class == 'black':
        card_style['color'] = '#000'
    else:  # joker
        card_style['color'] = '#9c27b0'
    
    content = []
    if rank != 'JOKER':
        # Top left corner
        content.append(html.Div([
            html.Div(str(rank), style={'fontSize': '0.8em', 'lineHeight': '1'}),
            html.Div(suit_symbols.get(suit, ''), style={'fontSize': '0.8em', 'lineHeight': '1'})
        ], style={'position': 'absolute', 'top': '6px', 'left': '6px'}))
        
        # Center
        content.append(html.Div([
            html.Div(str(rank), style={'fontSize': '1.2em' if size != 'large' else '1.8em'}),
            html.Div(suit_symbols.get(suit, ''), style={'fontSize': '1.5em' if size != 'large' else '2.2em'})
        ], style={'position': 'absolute', 'top': '50%', 'left': '50%', 'transform': 'translate(-50%, -50%)'}))
        
        # Bottom right corner (upside down)
        content.append(html.Div([
            html.Div(str(rank), style={'fontSize': '0.8em', 'lineHeight': '1'}),
            html.Div(suit_symbols.get(suit, ''), style={'fontSize': '0.8em', 'lineHeight': '1'})
        ], style={'position': 'absolute', 'bottom': '6px', 'right': '6px', 'transform': 'rotate(180deg)'}))
    else:
        # Joker center
        content.append(html.Div('🃏', style={
            'position': 'absolute', 
            'top': '50%', 
            'left': '50%', 
            'transform': 'translate(-50%, -50%)',
            'fontSize': '2em' if size != 'large' else '3em'
        }))
    
    if selectable:
        return dbc.Button(
            content,
            id={'type':'card-btn','card':card_id},
            style=card_style,
            className='p-0',
            color='light' if not selected else 'warning',
            outline=not selected
        )
    else:
        return html.Div(content, style=card_style)

# ===================== BOT LOGIC =====================
class GreedyBot:
    def __init__(self, engine: PresidentEngine): self.engine = engine
    def make_move(self, room_id: str, player_id: str):
        """
        Make a move for the bot.
        Args:
            room_id: The ID of the room
            player_id: The ID of the player making the move
        """
        room = self.engine.get_room(room_id)
        if not room or room.turn != player_id: return
        if room.pending_gift and room.pending_gift['player_id'] == player_id:
            self._handle_gift(room_id, player_id, room.pending_gift['remaining']); return
        if room.pending_discard and room.pending_discard['player_id'] == player_id:
            self._handle_discard(room_id, player_id, room.pending_discard['remaining']); return
        if room.exchange_phase and room.pending_exchange:
            # Handle card exchange based on the exchange type
            exchange = room.pending_exchange
            player = room.players[player_id]
            
            # Automatic exchanges (for both bots and humans):
            # - Asshole to President (asshole gives 2 best cards)
            # - Scumbag to Vice President (scumbag gives 1 best card)
            if (exchange['current_exchange'] == 'asshole_to_president' and player_id == exchange['asshole_id']) or \
               (exchange['current_exchange'] == 'scumbag_to_vice' and player_id == exchange['scumbag_id']):
                self._handle_card_exchange(room_id, player_id)
                return
            
            # Manual exchanges (only for bots, humans handle via UI):
            # - President to Asshole (president gives 2 cards)
            # - Vice President to Scumbag (vice president gives 1 card)
            if (exchange['current_exchange'] == 'president_to_asshole' and player_id == exchange['president_id']) or \
               (exchange['current_exchange'] == 'vice_to_scumbag' and player_id == exchange['vice_president_id']):
                if player.is_bot:
                    self._handle_card_exchange(room_id, player_id)
                return
        player = room.players[player_id]
        # --- PATCH: allow any valid play on empty pile except for very first play of first game ---
        hand = player.hand
        valid_plays = []
        if room.current_rank is None:
            # Case 1: Empty pile - special rules may apply
            # Traditional President rules require the player with 3♦ to start
            if getattr(room, 'first_game', True) and not getattr(room, 'first_game_first_play_done', False):
                # Check if this bot has the 3 of diamonds and any 3s
                if '3D' in hand and 3 in [parse_card(c)[0] for c in hand]:
                    # Collect all 3s from hand
                    threes = [c for c in hand if parse_card(c)[0] == 3]
                    # Add all possible combinations of 3s (singles, pairs, etc.)
                    for cnt in range(1, len(threes)+1):
                        valid_plays.append(threes[:cnt])
            else:
                # Normal empty pile - any valid set of same-ranked cards is allowed
                # Group cards by rank
                rank_groups = {}
                for card in hand:
                    rank = parse_card(card)[0]
                    if rank not in rank_groups:
                        rank_groups[rank] = []
                    rank_groups[rank].append(card)
                
                # For each rank group, try all possible play sizes (1 card, 2 cards, etc.)
                for rank, cards in rank_groups.items():
                    for cnt in range(1, len(cards)+1):
                        play = cards[:cnt]
                        # Validate the play against game rules
                        ok,_,_ = self.engine.validate_play(room, player_id, play)
                        if ok:
                            valid_plays.append(play)
        else:
            # Normal play: must match count and be higher rank
            groups = defaultdict(list)
            for c in hand:
                r,_ = parse_card(c)
                groups[r].append(c)
            for rank, cards in groups.items():
                # Check if the number of cards in the hand is greater than or equal to the current count
                if len(cards) >= room.current_count:
                    # Try all possible plays of the current count
                    play = cards[:room.current_count]
                    ok,_,_ = self.engine.validate_play(room, player_id, play)
                    if ok:
                        valid_plays.append(play)
        if valid_plays:
            # Use the same scoring as before
            best = max(valid_plays, key=len)
            self.engine.play_cards(room_id, player_id, best)
        else:
            self.engine.pass_turn(room_id, player_id)

    def _get_possible_plays(self, room: RoomState, player: Player) -> List[List[str]]:
        groups = defaultdict(list)
        for c in player.hand:
            r,_ = parse_card(c); groups[r].append(c)
        res=[]
        
        # Special case: if it's the opening play, ONLY allow 3s
        if room.current_rank is None and not hasattr(room, 'first_play_made'):
            if 3 in groups:
                # Only return plays with 3s for opening
                for cnt in range(1, len(groups[3])+1):
                    play = groups[3][:cnt]
                    valid,_,_ = self.engine.validate_play(room, player.id, play)
                    if valid: res.append(play)
            return res
        
        # Normal play - all valid combinations
        for rank, cards in groups.items():
            for cnt in range(1, len(cards)+1):
                play = cards[:cnt]
                valid,_,_ = self.engine.validate_play(room, player.id, play)
                if valid: res.append(play)
        return res
    def _handle_gift(self, room_id: str, player_id: str, rem: int):
        room = self.engine.get_room(room_id)
        if not room:
            return
        player = room.players[player_id]
        
        # Get cards to gift (worst cards first)
        to_gift = self._get_worst_cards(player.hand, rem)
        
        # Find other players to give cards to (random distribution)
        other_players = [p for p in room.players.values() if p.id != player_id and len(p.hand) > 0]
        
        # Randomly shuffle the players for fair distribution
        import random
        random.shuffle(other_players)
        
        if not other_players:
            # If no other players have cards, just discard them
            for card in to_gift:
                player.hand.remove(card)
                room.discard.append(card)
            player.hand_count = len(player.hand)
            room.pending_gift = None
            room.version += 1
            room.game_log.append(f"{player.name} discarded {len(to_gift)} cards (no players to gift to)")
            self.engine._advance_turn_if_no_pending(room)
            return
        
        # Distribute cards among other players
        assignments = []
        cards_per_player = rem // len(other_players)
        remaining_cards = rem % len(other_players)
        
        card_index = 0
        for i, recipient in enumerate(other_players):
            cards_for_this_player = cards_per_player + (1 if i < remaining_cards else 0)
            if cards_for_this_player > 0 and card_index < len(to_gift):
                player_cards = to_gift[card_index:card_index + cards_for_this_player]
                assignments.append({
                    'to': recipient.id,
                    'cards': player_cards
                })
                card_index += cards_for_this_player
        
        # Use the proper gift distribution method
        success, msg = self.engine.submit_gift_distribution(room_id, player_id, assignments)
        if not success:
            # Fallback: just discard the cards
            for card in to_gift:
                player.hand.remove(card)
                room.discard.append(card)
            player.hand_count = len(player.hand)
            room.pending_gift = None
            room.version += 1
            room.game_log.append(f"{player.name} discarded {len(to_gift)} cards (gift failed)")
            self.engine._advance_turn_if_no_pending(room)
        
    def _handle_discard(self, room_id: str, player_id: str, rem: int):
        room = self.engine.get_room(room_id)
        if not room:
            return
        player = room.players[player_id]
        to_discard = player.hand[:rem] if len(player.hand) >= rem else player.hand.copy()
        
        for card in to_discard:
            player.hand.remove(card)
            room.discard.append(card)
        player.hand_count = len(player.hand)
        
        room.pending_discard = None
        room.version += 1
        room.game_log.append(f"{player.name} discarded {len(to_discard)} cards")
        self.engine._advance_turn_if_no_pending(room)

    def _handle_card_exchange(self, room_id: str, player_id: str):
        """Handle card exchange for bots"""
        room = self.engine.get_room(room_id)
        if not room or not room.exchange_phase or not room.pending_exchange:
            return
        
        exchange = room.pending_exchange
        player = room.players[player_id]
        
        if exchange['current_exchange'] == 'asshole_to_president' and player_id == exchange['asshole_id']:
            # Asshole gives 2 best cards
            best_cards = self._get_best_cards(player.hand, 2)
            self.engine.submit_asshole_cards(room_id, player_id, best_cards)
            
        elif exchange['current_exchange'] == 'president_to_asshole' and player_id == exchange['president_id']:
            # President gives 2 worst cards to Asshole
            worst_cards = self._get_worst_cards(player.hand, 2)
            self.engine.submit_president_cards(room_id, player_id, worst_cards)
            
        elif exchange['current_exchange'] == 'scumbag_to_vice' and player_id == exchange['scumbag_id']:
            # Scumbag gives best card
            best_cards = self._get_best_cards(player.hand, 1)
            if best_cards:
                self.engine.submit_scumbag_card(room_id, player_id, best_cards[0])
                
        elif exchange['current_exchange'] == 'vice_to_scumbag' and player_id == exchange['vice_president_id']:
            # Vice president gives 1 worst card to Scumbag
            worst_cards = self._get_worst_cards(player.hand, 1)
            if worst_cards:
                self.engine.submit_vice_president_card(room_id, player_id, worst_cards[0])

    def _get_best_cards(self, hand: List[str], count: int) -> List[str]:
        """Get the best cards from hand based on game rank order"""
        if not hand or count <= 0:
            return []
        
        # Sort cards by rank (highest first) using NORMAL_ORDER
        def card_rank(card):
            rank, _ = parse_card(card)
            try:
                return NORMAL_ORDER.index(rank)
            except ValueError:
                return 999  # Unknown ranks go to the end
        
        sorted_cards = sorted(hand, key=card_rank, reverse=True)
        return sorted_cards[:count]
    
    def _get_worst_cards(self, hand: List[str], count: int) -> List[str]:
        """Get the worst cards from hand based on game rank order"""
        if not hand or count <= 0:
            return []
        
        # Sort cards by rank (lowest first) using NORMAL_ORDER
        def card_rank(card):
            rank, _ = parse_card(card)
            try:
                return NORMAL_ORDER.index(rank)
            except ValueError:
                return 999  # Unknown ranks go to the end
        
        sorted_cards = sorted(hand, key=card_rank, reverse=False) # Lowest first  
        return sorted_cards[:count]

# ===================== DASH APP =====================
engine = PresidentEngine()
bot = GreedyBot(engine)

# Add bot names at the top
BOT_NAMES = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Henry']

def bot_manager(room_id):
    while True:
        room = engine.get_room(room_id)
        if not room or room.phase != 'play': break
        for p in list(room.players.values()):
            if p.is_bot and room.turn == p.id:
                time.sleep(random.uniform(0.3,0.7))
                bot.make_move(room_id, p.id)
        time.sleep(0.5)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "President Card Game"

# ===================== LAYOUTS =====================

def create_mode_select_layout():
    return dbc.Container([
        html.H2("President Card Game"),
        html.Hr(),
        dbc.Row([
            dbc.Col([
                dbc.Input(id='player-name-input', placeholder='Enter your name', type='text', value='', className='mb-2', maxLength=16, style={'width': '220px'}),
                dbc.Button("Singleplayer (vs Bots)", id="singleplayer-btn", color="primary", size="lg", className="me-3"),
                dbc.Button("Multiplayer (coming soon)", id="multiplayer-btn", color="secondary", size="lg", disabled=True),
            ], width="auto")
        ], justify="center", className="mb-4"),
        html.Div(id="mode-info")
    ], fluid=True)

def create_main_layout():
    return dbc.Container([
        dcc.Store(id='player-name', data=''),
        dcc.Store(id='current-room', data=None),
        dcc.Store(id='current-player', data=None),
        dcc.Store(id='selected-cards', data=[]),
        dcc.Store(id='game-version', data=0),
        dcc.Store(id='play-error', data=''),
        dcc.Interval(id='game-updater', interval=1000, n_intervals=0),
        html.Div(id='game-content')
    ], fluid=True)


def create_game_layout(room: RoomState, pid: str, selected_cards=None):
    p = room.players.get(pid)
    if not p: return html.Div("Error: Player not found")
    selected_cards = selected_cards or []
    
    # Determine if it's player's turn
    is_my_turn = (room.turn == pid and room.phase == 'play' and len(p.hand) > 0)
    
    # Game info card
    info = dbc.Card([
        dbc.CardHeader(html.H4("Game Info", className='text-center mb-0')),
        dbc.CardBody([
            html.P([
                html.Strong("Turn: "), 
                html.Span(
                    "YOUR TURN!" if is_my_turn else (room.players[room.turn].name if room.turn and room.turn in room.players else 'None'),
                    className='text-success fw-bold' if is_my_turn else ''
                )
            ], className='mb-2'),
            html.P([html.Strong("Current: "), f"{room.current_count or 0} × {room.current_rank or 'None'}"], className='mb-2'),
            html.P([html.Strong("Inversion: "), html.Span('YES', className='text-danger') if room.inversion_active else html.Span('NO', className='text-success')], className='mb-0'),
        ])
    ], className='mb-3', style={'background': 'rgba(255,255,255,0.95)', 'border': 'none', 'borderRadius': '15px', 'boxShadow': '0 8px 32px rgba(0,0,0,0.1)'})
    
    # Current pile display - CENTER AND ENLARGED
    pile_cards = []
    if room.current_pile:
        for card in room.current_pile:
            pile_cards.append(create_card_element(card, size='large'))
    
    # Round history display - show previous plays in current round
    history_display = []
    if room.round_history:
        for i, play in enumerate(room.round_history[-4:]):  # Show last 4 plays
            player_name = play['player_name']
            cards = play['cards']
            
            # Create mini cards for history
            mini_cards = []
            for card in cards:
                mini_cards.append(create_card_element(card, size='small'))
            
            history_item = html.Div([
                html.Div(f"{player_name}:", className='text-muted small fw-bold mb-1'),
                html.Div(mini_cards, style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '2px'})
            ], style={
                'padding': '8px',
                'margin': '4px',
                'background': 'rgba(0,0,0,0.05)',
                'borderRadius': '8px',
                'border': '1px solid #dee2e6'
            })
            history_display.append(history_item)
    
    # Complete round history dropdown
    completed_rounds_dropdown = []
    if room.completed_rounds:
        dropdown_items = []
        for round_data in room.completed_rounds:
            round_num = round_data['round_number']
            ended_by = round_data['ended_by']
            winner = round_data['winner']
            plays = round_data['plays']
            
            # Create content for this round
            round_plays = []
            for play in plays:
                mini_cards = []
                for card in play['cards']:
                    mini_cards.append(create_card_element(card, size='small'))
                round_plays.append(html.Div([
                    html.Div(f"{play['player_name']}:", className='text-muted small fw-bold mb-1'),
                    html.Div(mini_cards, style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '2px'})
                ], style={
                    'padding': '6px',
                    'margin': '2px',
                    'background': 'rgba(0,0,0,0.03)',
                    'borderRadius': '6px'
                }))
            
            dropdown_items.append(
                dbc.AccordionItem([
                    html.Div([
                        html.Div(round_plays, style={'marginBottom': '8px'}),
                        html.Small(f"Won by: {winner} • Ended by: {ended_by}", className='text-muted')
                    ])
                ], title=f"Round {round_num}")
            )
        
        completed_rounds_dropdown = [
            html.Hr(className='my-3'),
            html.H6("📚 Complete Round History", className='text-center mb-2 text-muted'),
            dbc.Accordion(dropdown_items, flush=True, style={'fontSize': '0.9rem'})
        ]
    
    pile_display = dbc.Card([
        dbc.CardHeader(html.H3("🎯 Current Pile", className='text-center mb-0')),
        dbc.CardBody([
            html.Div(
                pile_cards if pile_cards else [html.H4("🃏 Empty", className='text-muted')], 
                className='text-center',
                style={'minHeight': '160px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'flexWrap': 'wrap', 'background': 'linear-gradient(45deg, #f8f9fa, #e9ecef)', 'borderRadius': '10px', 'border': '2px dashed #dee2e6'}
            ),
            html.Hr(className='my-3') if history_display else None,
            html.Div([
                html.H6("📜 Round History", className='text-center mb-2 text-muted') if history_display else None,
                html.Div(
                    history_display,
                    style={'display': 'flex', 'flexDirection': 'column', 'gap': '4px', 'maxHeight': '200px', 'overflowY': 'auto'}
                ) if history_display else None,
                html.Div(completed_rounds_dropdown) if completed_rounds_dropdown else None,
                html.P(f"🗑️ Total discarded: {len(room.discard)} cards", className='text-muted text-center mt-2 mb-0 small')
            ])
        ])
    ], className='mb-3', style={'background': 'rgba(255,255,255,0.95)', 'border': 'none', 'borderRadius': '15px', 'boxShadow': '0 8px 32px rgba(0,0,0,0.1)'})
    
    # Players table - show roles only during exchange phase or finished phase
    def get_role_display(player):
        if room.exchange_phase or room.phase == 'finished':
            return player.role or '-'
        else:
            # Keep track of roles: first person to finish gets president, second gets vice, etc.
            if player.id in room.finished_order:
                return f"{player.role}"
            else:
                return '-'
    
    table_data = {
        'Player':[pl.name+(' (Bot)' if pl.is_bot else '') for pl in sorted(room.players.values(), key=lambda x:x.seat)],
        'Role':[get_role_display(pl) for pl in sorted(room.players.values(), key=lambda x:x.seat)],
        'Cards':[pl.hand_count for pl in sorted(room.players.values(), key=lambda x:x.seat)],
        'Passed':['✓' if pl.passed else '' for pl in sorted(room.players.values(), key=lambda x:x.seat)],
        'Turn':['🎯 YOU!' if room.turn==pl.id and pl.id==pid and len(pl.hand) > 0 else '▶' if room.turn==pl.id and len(pl.hand) > 0 else '' for pl in sorted(room.players.values(), key=lambda x:x.seat)]
    }
    table = dbc.Table.from_dataframe(pd.DataFrame(table_data), striped=True, bordered=True, size='sm')
    
    # Player's hand - SORTED BY GAME ORDER
    hand = []
    if room.phase != 'finished' and p.hand:
        # Sort cards by game rank order: 3,4,5,6,7,8,9,10,J,Q,K,A,2,JOKER
        def sort_key(card_id):
            rank, suit = parse_card(card_id)
            try:
                return NORMAL_ORDER.index(rank)
            except ValueError:
                return 999  # Unknown ranks go to the end
        
        sorted_hand = sorted(p.hand, key=sort_key)
        
        for c in sorted_hand:
            # Create card buttons that are always selectable
            hand.append(create_card_element(c, size='normal', selectable=True, selected=(c in selected_cards)))
    
    # Action buttons and special prompts
    actions = []
    special_prompt = []
    
    if room.phase == 'finished' or room.exchange_phase:
        # Game finished or card exchange phase
        role_colors = {
            'President': 'success',
            'Vice President': 'info', 
            'Citizen': 'secondary',
            'Scumbag': 'warning',
            'Asshole': 'danger'
        }
        
        if room.exchange_phase and room.pending_exchange:
            # Card exchange phase
            exchange = room.pending_exchange
            exchange_ui = []
            
            if exchange['current_exchange'] == 'asshole_to_president' and pid == exchange['asshole_id']:
                # Automatic exchange - no manual selection needed
                exchange_ui = [
                    dbc.Alert([
                        html.H5("🎁 Automatic Exchange", className="mb-3"),
                        html.P("Your 2 best cards will be automatically given to the President", className='mb-2'),
                    ], color='danger', className='mb-3')
                ]
            elif exchange['current_exchange'] == 'president_to_asshole' and pid == exchange['president_id']:
                exchange_ui = [
                    dbc.Alert([
                        html.H5("🎁 Give 2 Cards to Asshole", className="mb-3"),
                        html.P("Select 2 cards to give to the Asshole", className='mb-2'),
                        dbc.Button('Give Selected Cards', id={'type': 'exchange-btn', 'action': 'president_to_asshole'}, color='success', className='me-2', disabled=len(selected_cards) != 2),
                    ], color='success', className='mb-3')
                ]
            elif exchange['current_exchange'] == 'scumbag_to_vice' and pid == exchange['scumbag_id']:
                # Automatic exchange - no manual selection needed
                exchange_ui = [
                    dbc.Alert([
                        html.H5("🎁 Automatic Exchange", className="mb-3"),
                        html.P("Your best card will be automatically given to the Vice President", className='mb-2'),
                    ], color='warning', className='mb-3')
                ]
            elif exchange['current_exchange'] == 'vice_to_scumbag' and pid == exchange['vice_president_id']:
                exchange_ui = [
                    dbc.Alert([
                        html.H5("🎁 Give 1 Card to Scumbag", className="mb-3"),
                        html.P("Select 1 card to give to the Scumbag", className='mb-2'),
                        dbc.Button('Give Selected Card', id={'type': 'exchange-btn', 'action': 'vice_to_scumbag'}, color='info', className='mb-3', disabled=len(selected_cards) != 1),
                    ], color='info', className='mb-3')
                ]
            else:
                # Waiting for other player's exchange
                current_player_name = ""
                if exchange['current_exchange'] == 'asshole_to_president':
                    current_player_name = room.players[exchange['asshole_id']].name
                elif exchange['current_exchange'] == 'president_to_asshole':
                    current_player_name = room.players[exchange['president_id']].name
                elif exchange['current_exchange'] == 'scumbag_to_vice':
                    current_player_name = room.players[exchange['scumbag_id']].name
                elif exchange['current_exchange'] == 'vice_to_scumbag':
                    current_player_name = room.players[exchange['vice_president_id']].name
                
                exchange_ui = [
                    dbc.Alert([
                        html.H5("⏳ Waiting for Card Exchange", className="mb-3"),
                        html.P(f"Waiting for {current_player_name} to complete their exchange...", className='mb-0'),
                    ], color='secondary', className='mb-3')
                ]
            
            special_prompt = [
                html.Div([
                    html.H3("🎁 Card Exchange Phase", className="text-center text-primary mb-3"),
                    dbc.Alert([
                        html.H5(f"You are: {p.role}", className='mb-0')
                    ], color=role_colors.get(p.role, 'secondary'), className='text-center mb-3'),
                    html.Div(exchange_ui),
                ], className='mb-3')
            ]
        else:
            # Game finished - show results and restart option
            special_prompt = [
                html.Div([
                    html.H3("🎉 Game Finished!", className="text-center text-success mb-3"),
                    dbc.Alert([
                        html.H5(f"You are: {p.role}", className='mb-0')
                    ], color=role_colors.get(p.role, 'secondary'), className='text-center'),
                    html.Div([
                        html.H6("Final Rankings:", className='text-center mb-2'),
                        html.Ol([
                            html.Li([
                                f"{room.players[pid].name} - ",
                                html.Span(room.players[pid].role, 
                                    className=f'badge bg-{role_colors.get(room.players[pid].role, "secondary")}')
                            ]) for pid in room.finished_order if pid in room.players
                        ])
                    ], className='mb-3'),
                    dbc.Button('🎮 New Game', id='restart-btn', color='success', size='lg', className='mt-2'),
                ], className='mb-3')
            ]
    elif room.pending_gift and room.pending_gift['player_id'] == pid:
        # Enhanced 7-gift UI - choose recipients and distribute cards unevenly (e.g. 2 to bot1, 1 to bot2)
        # Only show as recipients those who are not in finished_order and have cards
        other_players = [pl for pl in room.players.values() if pl.id != pid and pl.id not in room.finished_order and pl.hand_count > 0]
        gift_ui = []
        remaining = room.pending_gift['remaining']
        # Add recipient selection UI
        for other_player in other_players:
            gift_ui.append(html.Div([
                html.Label(f"Give to {other_player.name}:", className='form-label small'),
                dcc.Input(
                    id={'type': 'gift-input', 'player': other_player.id},
                    type='number',
                    value=0,
                    min=0,
                    max=remaining,
                    className='form-control form-control-sm mb-2',
                    style={'width': '80px'}
                )
            ], className='mb-2'))
        special_prompt = [
            dbc.Alert([
                html.H5(f"🎁 Gift {remaining} cards total!", className="mb-3"),
                html.P("1. Select cards from your hand to give away", className='mb-2'),
                html.P("2. Choose how many to give each player:", className='mb-2'),
                html.Div(gift_ui, className='mb-3'),
                html.Div(id='gift-total-display', className='mb-2'),
                dbc.Button('Confirm Gift Distribution', id={'type': 'game-btn', 'action': 'gift'}, color='warning', className='me-2', disabled=not p.hand),
            ], color='warning', className='mb-3')
        ]
    elif room.pending_discard and room.pending_discard['player_id'] == pid:
        special_prompt = [
            dbc.Alert([
                html.H5(f"🗑️ Discard {room.pending_discard['remaining']} cards!", className="mb-2"),
                html.P("Select cards from your hand and click Discard", className='mb-2'),
                dbc.Button('Discard Selected Cards', id={'type': 'game-btn', 'action': 'discard'}, color='danger', className='me-2', disabled=not p.hand),
            ], color='danger', className='mb-3')
        ]
    elif is_my_turn:
        actions=[
            dbc.Alert([
                html.H5("🎯 YOUR TURN!", className='text-center mb-2 text-success'),
                html.P("Select cards and click Play, or Pass your turn", className='text-center mb-0')
            ], color='success', className='mb-3'),
            dbc.ButtonGroup([
                dbc.Button('🎯 Play Cards', id={'type': 'game-btn', 'action': 'play'}, color='primary', disabled=not p.hand),
                dbc.Button('⏭️ Pass', id={'type': 'game-btn', 'action': 'pass'}, color='secondary', disabled=not p.hand)
            ], className='d-grid')
        ]
    
    # Game log
    log = html.Div([
        html.P(e, className='mb-1 p-2 bg-light rounded') for e in room.game_log[-8:]
    ], style={'height':'400px','overflowY':'auto', 'border': '1px solid #dee2e6', 'borderRadius': '8px', 'padding': '8px'})
    
    # Selection info - always show when it's player's turn
    selection_info = html.Div([
        html.P("📋 Click cards to select them" if is_my_turn else "⏳ Wait for your turn", 
               className='text-center mb-0 text-muted small')
    ])
    
    # Add error modal
    error_modal = dbc.Modal([
        dbc.ModalHeader("Invalid Play"),
        dbc.ModalBody(dcc.Store(id='play-error-modal-msg', data='')), # Placeholder, will be set by callback
        dbc.ModalFooter(
            dbc.Button("Close", id="close-play-error-modal", className="ms-auto", n_clicks=0)
        )
    ], id="play-error-modal", is_open=False)
    
    return html.Div([
        error_modal,
        dbc.Container([
            dbc.Row([
        dbc.Col([
            info, 
                    dbc.Card([
                        dbc.CardHeader(html.H5('👥 Players', className='mb-0')), 
                        dbc.CardBody(table)
                    ], className='mb-3', style={'background': 'rgba(255,255,255,0.95)', 'border': 'none', 'borderRadius': '15px', 'boxShadow': '0 8px 32px rgba(0,0,0,0.1)'}), 
                    dbc.Card([
                        dbc.CardHeader(html.H5('📜 Game Log', className='mb-0')), 
                        dbc.CardBody(log)
                    ], style={'background': 'rgba(255,255,255,0.95)', 'border': 'none', 'borderRadius': '15px', 'boxShadow': '0 8px 32px rgba(0,0,0,0.1)'})
                ], width=3),
                dbc.Col([
                    pile_display,
                ], width=6),
        dbc.Col([
            dbc.Card([
                        dbc.CardHeader(html.H5(f'🃏 {p.name}\'s Hand', className='mb-0')), 
                dbc.CardBody([
                    html.Div(special_prompt),
                            selection_info,
                            html.Div(hand, className='mb-3', style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'center', 'gap': '4px'}) if hand else html.Div("🚫 No cards", className='mb-3 text-center text-muted'), 
                            html.Div(actions, className='text-center')
                ])
                    ], style={'background': 'rgba(255,255,255,0.95)', 'border': 'none', 'borderRadius': '15px', 'boxShadow': '0 8px 32px rgba(0,0,0,0.1)'})
                ], width=3)
            ])
        ], fluid=True)
    ], style={'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 'minHeight': '100vh', 'padding': '20px'})

app.layout = create_main_layout()

# ===================== CALLBACKS =====================

# Add restart callback
@app.callback(
    [Output('current-room','data', allow_duplicate=True),
     Output('current-player','data', allow_duplicate=True),
     Output('game-version', 'data', allow_duplicate=True)],
    Input('restart-btn', 'n_clicks'),
    [State('player-name', 'data'),
     State('current-room', 'data')],
    prevent_initial_call=True
)
def restart_game(n_clicks, player_name, current_room_id):
    if n_clicks and current_room_id:
        # Reuse the same room to preserve game state
        room = engine.get_room(current_room_id)
        if room:
            # Reset the room for a new game while preserving the global_asshole_id and roles
            room.phase = 'lobby'
            # Don't clear finished_order - it's needed for role assignment
            room.game_log = []
            room.current_rank = None
            room.current_count = None
            room.inversion_active = False
            room.current_pile = []
            room.round_history = []
            room.completed_rounds = []
            room.pending_gift = None
            room.pending_discard = None
            room.last_play = None
            room.exchange_phase = False
            room.pending_exchange = None
            room.first_game = False  # This is now a continuation game
            room.first_game_first_play_done = False
            
            # Preserve roles for card exchange, but reset other player states
            for player in room.players.values():
                player.hand = []
                player.hand_count = 0
                player.passed = False
                # Don't clear roles yet - they're needed for card exchange
            
            # Start the new game
            engine.start_game(current_room_id)
            room = engine.get_room(current_room_id)
            
            # Start card exchange phase for subsequent games (only if roles are assigned)
            if room and not room.first_game and any(p.role for p in room.players.values()):
                engine._start_card_exchange(room)
            else:
                # Clear roles for new game if no card exchange needed
                for player in room.players.values():
                    player.role = None
            
            return current_room_id, list(room.players.keys())[0], room.version if room else 0
    
    # Fallback: create completely new game if no current room
    if n_clicks:
        rid = f'singleplayer_{uuid.uuid4().hex[:8]}'
        engine.create_room(rid)
        name = player_name.strip().title() if player_name and player_name.strip() else 'You'
        ok, pid = engine.add_player(rid, name)
        for i in range(3):
            engine.add_player(rid, BOT_NAMES[i], True)
        engine.start_game(rid)
        room = engine.get_room(rid)
        return rid, pid, room.version if room else 0
    
    return dash.no_update, dash.no_update, dash.no_update

@app.callback(
    Output('player-name', 'data'),
    Input('player-name-input', 'value'),
    prevent_initial_call=False
)
def update_player_name(name):
    return name or ''

@app.callback(
    [Output('current-room','data'),
    Output('current-player','data'),
     Output('mode-info','children'),
     Output('game-version', 'data', allow_duplicate=True)],
    Input('singleplayer-btn', 'n_clicks'),
    State('player-name', 'data'),
    prevent_initial_call=True
)
def start_singleplayer(n_single, player_name):
    if n_single:
        # Use a unique room id for each session
        rid = f'singleplayer_{uuid.uuid4().hex[:8]}'
        engine.create_room(rid)
        name = player_name.strip().title() if player_name and player_name.strip() else 'You'
        ok, pid = engine.add_player(rid, name)
        for i in range(3):
            engine.add_player(rid, BOT_NAMES[i], True)
        engine.start_game(rid)
        room = engine.get_room(rid)
        return rid, pid, None, room.version if room else 0
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update

# Event-driven game display - updates only when game state changes
@app.callback(
    Output('game-content', 'children'),
    [Input('current-room', 'data'),
     Input('current-player', 'data'),
     Input('selected-cards', 'data')],
    prevent_initial_call=False
)
def update_game_display(rid, pid, selected_cards):
    if not rid or not pid:
        return create_mode_select_layout()
    
    room = engine.get_room(rid)
    if not room:
        return create_mode_select_layout()
        
    cur_player = room.players.get(pid)
    if not cur_player:
        return html.Div("Error: Player not found")
    
    # Bot moves are now handled by the interval callback
    
    return create_game_layout(room, pid, selected_cards)

# Removed old bot checker - now using single interval for everything

# Main game progression with bot automation
@app.callback(
    Output('game-content', 'children', allow_duplicate=True),
    Output('game-version', 'data', allow_duplicate=True),
    Input('game-updater', 'n_intervals'),
    [State('current-room', 'data'),
     State('current-player', 'data'),
     State('selected-cards', 'data'),
     State('game-version', 'data')],
    prevent_initial_call=True
)
def update_game_and_trigger_bots(n_intervals, rid, pid, selected_cards, last_version):
    if not rid or not pid:
        raise dash.exceptions.PreventUpdate
        
    room = engine.get_room(rid)
    if not room:
        raise dash.exceptions.PreventUpdate
    

    print(f"\n🔍 DEBUG - Room: {rid}, Phase: {room.phase}, Exchange Phase: {room.exchange_phase}")
    print(f"Turn: {room.players[room.turn].name if room.turn else 'None'}")
    for player_id, player in room.players.items():
        # Sort cards by rank for better debugging visibility
        sorted_hand = sorted(player.hand, key=lambda card: NORMAL_ORDER.index(parse_card(card)[0]) if parse_card(card)[0] in NORMAL_ORDER else 999)
        print(f"  {player.name} ({player.role}): {len(player.hand)} cards - {sorted_hand}")
    if room.pending_exchange:
        print(f"Pending Exchange: {room.pending_exchange['current_exchange']}")
    # Always trigger bot moves if it's a bot's turn (but not during card exchange phase)
    if room.phase == 'play' and room.turn and room.turn in room.players:
        # Don't trigger normal bot moves during card exchange, only card exchange handling
        if not room.exchange_phase:
            current_player = room.players[room.turn]
            if current_player.is_bot:
                # Handle pending effects first
                if room.pending_gift and room.pending_gift['player_id'] == room.turn:
                    bot._handle_gift(rid, room.turn, room.pending_gift['remaining'])
                elif room.pending_discard and room.pending_discard['player_id'] == room.turn:
                    bot._handle_discard(rid, room.turn, room.pending_discard['remaining'])
                else:
                    bot.make_move(rid, room.turn)
    
    # Handle card exchange (automatic for all players in automatic exchanges, manual for humans in manual exchanges)
    if room.exchange_phase and room.pending_exchange:
        exchange = room.pending_exchange
        current_exchange = exchange['current_exchange']
        
        # Automatic exchanges (for both bots and humans):
        # - Asshole to President (asshole gives 2 best cards)
        # - Scumbag to Vice President (scumbag gives 1 best card)
        if current_exchange == 'asshole_to_president' and exchange['asshole_id'] in room.players:
            asshole_id = exchange['asshole_id']
            asshole = room.players[asshole_id]
            if asshole.is_bot:
                bot._handle_card_exchange(rid, asshole_id)
            else:
                # Human asshole - trigger automatic exchange
                best_cards = bot._get_best_cards(asshole.hand, 2)
                if best_cards:
                    engine.submit_asshole_cards(rid, asshole_id, best_cards)
                    
        elif current_exchange == 'scumbag_to_vice' and exchange['scumbag_id'] in room.players:
            scumbag_id = exchange['scumbag_id']
            scumbag = room.players[scumbag_id]
            if scumbag.is_bot:
                bot._handle_card_exchange(rid, scumbag_id)
            else:
                # Human scumbag - trigger automatic exchange
                best_cards = bot._get_best_cards(scumbag.hand, 1)
                if best_cards:
                    print(f"🔍 DEBUG: Human scumbag {scumbag.name} automatically giving {best_cards[0]} to Vice President")
                    engine.submit_scumbag_card(rid, scumbag_id, best_cards[0])
                    # Return early to prevent immediate triggering of next exchange
                    print(f"🔍 DEBUG: Returning early to prevent automatic Vice President exchange")
                    return create_game_layout(room, pid, selected_cards), room.version
        
        # Manual exchanges (only for bots, humans handle via UI):
        # - President to Asshole (president gives 2 cards)
        # - Vice President to Scumbag (vice president gives 1 card)
        elif current_exchange == 'president_to_asshole' and exchange['president_id'] in room.players:
            president_id = exchange['president_id']
            president = room.players[president_id]
            if president.is_bot:
                bot._handle_card_exchange(rid, president_id)
                
        elif current_exchange == 'vice_to_scumbag' and exchange['vice_president_id'] in room.players:
            vice_president_id = exchange['vice_president_id']
            vice_president = room.players[vice_president_id]
            print(f"🔍 DEBUG: Vice President exchange detected for {vice_president.name} (is_bot: {vice_president.is_bot})")
            if vice_president.is_bot:
                print(f"🔍 DEBUG: Triggering automatic exchange for bot Vice President")
                bot._handle_card_exchange(rid, vice_president_id)
            else:
                print(f"🔍 DEBUG: Human Vice President - should show manual UI, not triggering automatic exchange")
    
    # Only update layout if game version changed
    if room.version != last_version:
        return create_game_layout(room, pid, selected_cards), room.version
    raise dash.exceptions.PreventUpdate

@app.callback(
    [Output('selected-cards','data'),
     Output({'type':'card-btn','card':ALL},'color'),
     Output('game-version', 'data', allow_duplicate=True),
     Output('play-error', 'data')],
    [Input({'type':'card-btn','card':ALL},'n_clicks'),
     Input({'type': 'game-btn', 'action': ALL},'n_clicks'),
     Input({'type': 'exchange-btn', 'action': ALL},'n_clicks')],
    [State('selected-cards','data'),
     State({'type':'card-btn','card':ALL},'id'),
     State('current-room','data'),
     State('current-player','data'),
     State('game-version', 'data'),
     State({'type': 'gift-input', 'player': ALL}, 'value'),
     State({'type': 'gift-input', 'player': ALL}, 'id')],
    prevent_initial_call=True
)
def handle_all_card_actions(card_clicks, action_clicks, exchange_clicks, selected, ids, rid, pid, last_version, gift_values=None, gift_ids=None):
    ctx = dash.callback_context
    if not ctx.triggered:
        return selected or [], ['light'] * len(ids or []), last_version, ''
    
    trig = ctx.triggered[0]['prop_id']
    
    # Handle card selection
    if 'card-btn' in trig and rid and pid:
        tid = eval(trig.split('.')[0])
        card = tid['card']
        if not selected: selected = []
        if card in selected:
            selected = [c for c in selected if c != card]
        else:
            selected = selected + [card]
        colors = [('warning' if id['card'] in selected else 'light') for id in ids]
        return selected, colors, last_version, ''
    
    # Handle action buttons - all clear selection after action
    elif 'play' in trig and selected and rid and pid:
        ok, msg = engine.play_cards(rid, pid, selected)
        room = engine.get_room(rid)
        updated_version = room.version if room else last_version
        if not ok:
            return selected, ['light'] * len(ids or []), updated_version, msg
        return [], ['light'] * len(ids or []), updated_version, ''
        
    elif 'pass' in trig and rid and pid:
        engine.pass_turn(rid, pid)
        room = engine.get_room(rid)
        updated_version = room.version if room else last_version
        return [], ['light'] * len(ids or []), updated_version, ''
        
    # Handle exchange buttons
    elif 'asshole_to_president' in trig and selected and rid and pid:
        ok, msg = engine.submit_asshole_cards(rid, pid, selected)
        room = engine.get_room(rid)
        updated_version = room.version if room else last_version
        if not ok:
            return selected, ['light'] * len(ids or []), updated_version, msg
        return [], ['light'] * len(ids or []), updated_version, ''
        
    elif 'president_to_asshole' in trig and selected and rid and pid:
        ok, msg = engine.submit_president_cards(rid, pid, selected)
        room = engine.get_room(rid)
        updated_version = room.version if room else last_version
        if not ok:
            return selected, ['light'] * len(ids or []), updated_version, msg
        return [], ['light'] * len(ids or []), updated_version, ''
        
    elif 'scumbag_to_vice' in trig and selected and rid and pid:
        ok, msg = engine.submit_scumbag_card(rid, pid, selected[0])
        room = engine.get_room(rid)
        updated_version = room.version if room else last_version
        if not ok:
            return selected, ['light'] * len(ids or []), updated_version, msg
        return [], ['light'] * len(ids or []), updated_version, ''
        
    elif 'vice_to_scumbag' in trig and selected and rid and pid:
        ok, msg = engine.submit_vice_president_card(rid, pid, selected[0])
        room = engine.get_room(rid)
        updated_version = room.version if room else last_version
        if not ok:
            return selected, ['light'] * len(ids or []), updated_version, msg
        return [], ['light'] * len(ids or []), updated_version, ''
        
    elif 'gift' in trig and selected and rid and pid:
        room = engine.get_room(rid)
        updated_version = last_version
        if room and room.pending_gift and room.pending_gift['player_id'] == pid:
            required = room.pending_gift['remaining']
            # Build assignments from gift_values and gift_ids
            if gift_values is not None and gift_ids is not None:
                # Map player_id to number of cards
                assignments = []
                total = 0
                selected_cards_for_assignment = selected.copy() # Use a copy to avoid modifying selected directly
                for val, gid in zip(gift_values, gift_ids):
                    num = val or 0
                    if num > 0:
                        give_cards = selected_cards_for_assignment[:num]
                        selected_cards_for_assignment = selected_cards_for_assignment[num:]
                        assignments.append({'to': gid['player'], 'cards': give_cards})
                        total += num
                if total == required:
                    ok, msg = engine.submit_gift_distribution(rid, pid, assignments)
                    room = engine.get_room(rid)
                    updated_version = room.version if room else last_version
                    if not ok:
                        return selected, ['light'] * len(ids or []), updated_version, msg
                else:
                    return selected, ['light'] * len(ids or []), updated_version, f"Must distribute exactly {required} cards (currently {total})"
        return [], ['light'] * len(ids or []), updated_version, ''
        
    elif 'discard' in trig and selected and rid and pid:
        room = engine.get_room(rid)
        if room and room.pending_discard and room.pending_discard['player_id'] == pid:
            required = room.pending_discard['remaining']
            if len(selected) == required:
                to_discard = selected
                player = room.players[pid]
                for card in to_discard:
                    if card in player.hand:
                        player.hand.remove(card)
                        room.discard.append(card)
                player.hand_count = len(player.hand)
                room.pending_discard = None
                room.version += 1
                room.game_log.append(f"{player.name} discarded {len(to_discard)} cards")
                engine._advance_turn_if_no_pending(room)
                updated_version = room.version
        return [], ['light'] * len(ids or []), updated_version, ''
    
    return selected or [], [('warning' if (ids and selected and id['card'] in selected) else 'light') for id in (ids or [])], last_version, ''

# Separate callback for play button state (only when it exists)
@app.callback(
    Output({'type': 'game-btn', 'action': 'play'}, 'disabled'),
    [Input('selected-cards', 'data'),
     Input('game-version', 'data')],
    [State('current-room', 'data'),
     State('current-player', 'data')],
    prevent_initial_call=True
)
def update_play_button(selected, version, rid, pid):
    if not rid or not pid:
        return True
    room = engine.get_room(rid)
    if not room:
        return True
    player = room.players.get(pid)
    if not player or not player.hand:
        return True
    # If there are pending gifts/discards or exchange phase, keep disabled
    if room.pending_gift or room.pending_discard or room.exchange_phase:
        return True
    # Check if any valid play exists
    hand = player.hand
    valid_play_exists = False
    if room.current_rank is None:
        # Any set of same rank is valid (except first play of first game)
        if getattr(room, 'first_game', True) and not getattr(room, 'first_game_first_play_done', False):
            threes = [c for c in hand if parse_card(c)[0] == 3]
            jokers = [c for c in hand if parse_card(c)[0] == 'JOKER']
            if threes or jokers:
                valid_play_exists = True
        else:
            rank_groups = {}
            for card in hand:
                rank = parse_card(card)[0]
                if rank not in rank_groups:
                    rank_groups[rank] = []
                rank_groups[rank].append(card)
            for cards in rank_groups.values():
                if cards:
                    valid_play_exists = True
                    break
    else:
        # More sophisticated validation that handles jokers properly
        # First, try all combinations of cards that could form valid plays
        from itertools import combinations
        
        # Get all cards and their ranks
        card_ranks = [(c, parse_card(c)[0]) for c in hand]
        regular_cards = [(c, r) for c, r in card_ranks if r != 'JOKER']
        jokers = [c for c, r in card_ranks if r == 'JOKER']
        
        # Try different combinations
        for combo_size in range(1, min(room.current_count + 1, len(hand) + 1)):
            for combo in combinations(hand, combo_size):
                if len(combo) == room.current_count:
                    ok, _, _ = engine.validate_play(room, pid, list(combo))
                    if ok:
                        valid_play_exists = True
                        break
            if valid_play_exists:
                break
    if not valid_play_exists:
        return True
    # If cards are selected, still check if the selected play is valid
    if selected:
        ok,_,_ = engine.validate_play(room, pid, selected)
        if not ok:
            return True
    return False



def get_card_style(card_id, selected):
    """Generate dynamic card style based on selection state"""
    base_style = {
        'border': '2px solid #333',
        'borderRadius': '12px',
        'backgroundColor': 'white',
        'padding': '8px',
        'margin': '4px',
        'minWidth': '70px',
        'minHeight': '100px',
        'fontSize': '16px',
        'fontWeight': 'bold',
        'position': 'relative',
        'transition': 'all 0.2s ease',
        'transform': 'scale(1)',
        'display': 'inline-block',
        'textAlign': 'center',
        'cursor': 'pointer',
        'color': 'inherit'  # Ensure text is visible
    }
    
    if selected:
        base_style.update({
            'backgroundColor': '#fff3e0',
            'border': '3px solid #ff9800',
            'boxShadow': '0 0 25px rgba(255, 152, 0, 0.8), inset 0 0 10px rgba(255, 152, 0, 0.3)',
            'transform': 'scale(1.1) translateY(-8px)',
            'zIndex': '100'
        })
    else:
        base_style.update({
            'boxShadow': '0 4px 8px rgba(0,0,0,0.1)',
            'backgroundColor': 'white',
            'border': '2px solid #333'
        })
    
    return base_style

@app.callback(
    Output('gift-total-display', 'children'),
    [Input({'type': 'gift-input', 'player': dash.dependencies.ALL}, 'value')],
    State('current-room', 'data'),
    State('current-player', 'data'),
    prevent_initial_call=True
)
def update_gift_total(gift_values, rid, pid):
    if not rid or not pid:
        return ""
    
    room = engine.get_room(rid)
    if not room or not room.pending_gift:
        return ""
    
    total_gifting = sum(v or 0 for v in gift_values)
    required = room.pending_gift['remaining']
    
    if total_gifting == required:
        return html.Div(f"✅ Total: {total_gifting}/{required} cards", className='text-success small fw-bold')
    elif total_gifting > required:
        return html.Div(f"❌ Too many: {total_gifting}/{required} cards", className='text-danger small fw-bold')
    else:
        return html.Div(f"⏳ Need {required - total_gifting} more cards", className='text-warning small fw-bold')

def assign_roles_dynamic(room):
    """
    Assign roles based on finished order:
    - First to finish = President
    - Second to finish = Vice President  
    - Third to finish = Scumbag (in 4+ player games)
    - Last to finish = Asshole
    """
    n = len(room.players)
    
    # Define role order based on number of players
    if n == 3:
        roles = ['President', 'Vice President', 'Asshole']
    elif n == 4:
        roles = ['President', 'Vice President', 'Scumbag', 'Asshole']
    else:
        roles = ['President', 'Vice President', 'Citizen', 'Scumbag', 'Asshole']
    
    # Clear current game roles
    room.current_game_roles.clear()
    
    # Assign roles based on finished order
    for i, pid in enumerate(room.finished_order):
        if i < len(roles):
            role = roles[i]
            room.players[pid].role = role
            room.current_game_roles[pid] = role
        else:
            room.players[pid].role = None
            room.current_game_roles[pid] = None
    
    # DO NOT clear roles for players still in the game
    # They should keep their previous roles until they actually finish
    # Only assign roles to players who have finished




@app.callback(
    [Output('play-error-modal', 'is_open'), Output('play-error-modal-msg', 'data')],
    [Input('play-error', 'data'), Input('close-play-error-modal', 'n_clicks')],
    [State('play-error-modal', 'is_open')],
    prevent_initial_call=True
)
def toggle_play_error_modal(error_msg, close_clicks, is_open):
    if error_msg:
        return True, error_msg
    if close_clicks:
        return False, ''
    return is_open, ''

# ===================== RUN SERVER =====================
if __name__=='__main__':
    app.run(debug=True)
