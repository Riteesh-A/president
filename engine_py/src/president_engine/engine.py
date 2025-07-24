"""Main game engine with all game logic from app.py"""

import random
import threading
import uuid
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .models import Player, RoomState, Rank
from .constants import create_deck, parse_card, is_higher_rank


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
            room.finished_order = []
            room.game_log = []

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

            # Set starter
            if room.first_game:
                starter = None
                for player in players:
                    if '3D' in player.hand:
                        starter = player.id
                        print(f"[DEBUG] Player {player.name} ({player.id}) has 3D and will start.")
                        break
                if not starter:
                    starter = players[0].id
                room.turn = starter
                print(f"[DEBUG] Starter is {room.players[room.turn].name} ({room.turn})")
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
        """
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
        
        # Allow a Joker to be played with a single non-Joker card as a valid pair/triplet/etc.
        if len(set(regular_ranks)) > 1:
            return False, "All non-Joker cards must be same rank", None
        if regular_ranks:
            # If we have regular cards, Jokers act as that rank
            play_rank = regular_ranks[0]
            # Special case: allow [X, JOKER] as a valid pair/triplet/etc.
            if len(regular_ranks) == 1 and joker_count > 0:
                # Valid: treat as a pair/triplet/etc. of play_rank
                pass
            elif len(set(regular_ranks)) > 1:
                return False, "All non-Joker cards must be same rank", None
        elif joker_count > 0:
            # If only Jokers, they are treated as JOKER rank
            play_rank = 'JOKER'
        else:
            return False, "No cards to play", None
            
        play_count = len(card_ids)
        
        # Only enforce 3s rule if first_game and opening play
        if room.current_rank is None:
            if getattr(room, 'first_game', True) and not getattr(room, 'first_game_first_play_done', False):
                if play_rank != 3:
                    return False, "First play of the game must be 3s", None
            effect = self._get_effect_type(play_rank)
            return True, "Valid play", {'rank': play_rank, 'count': play_count, 'effect': effect}
        if play_count != room.current_count:
            return False, f"Must play exactly {room.current_count} cards", None
        if not is_higher_rank(play_rank, room.current_rank, room.inversion_active):
            return False, f"Must play higher than {room.current_rank}", None
        if room.inversion_active and room.current_rank == 'J':
            pre_jack_ranks = [3,4,5,6,7,8,9,10]
            if play_rank not in pre_jack_ranks:
                return False, "After Jack inversion, only lower ranks (3-10) allowed", None
        effect = self._get_effect_type(play_rank)
        return True, "Valid play", {'rank': play_rank, 'count': play_count, 'effect': effect}

    def _get_effect_type(self, rank) -> Optional[str]:
        """Get the effect type for a given rank."""
        if rank == 7: return 'seven_gift'
        if rank == 8: return 'eight_reset'
        if rank == 10: return 'ten_discard'
        if rank == 'J': return 'jack_inversion'
        return None

    def _save_completed_round(self, room: RoomState, reason: str):
        """Save the current round to completed rounds history"""
        if room.round_history:
            round_data = {
                'round_number': len(room.completed_rounds) + 1,
                'plays': room.round_history.copy(),
                'ended_by': reason,
                'winner': room.last_play['player_name'] if room.last_play else 'Unknown'
            }
            room.completed_rounds.append(round_data)

    def play_cards(self, room_id: str, player_id: str, card_ids: List[str]) -> Tuple[bool, str]:
        """Play cards by a player."""
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            valid, message, pattern = self.validate_play(room, player_id, card_ids)
            if not valid:
                return False, message
            
            # Mark first play of first game as done
            if getattr(room, 'first_game', True) and not getattr(room, 'first_game_first_play_done', False) and room.current_rank is None:
                room.first_game_first_play_done = True
            
            player = room.players[player_id]
            for card_id in card_ids:
                player.hand.remove(card_id)
            player.hand_count = len(player.hand)
            
            # Add cards to current pile
            room.current_pile = card_ids.copy()
            # Add to round history
            room.round_history.append({
                'player_name': player.name,
                'cards': card_ids.copy(),
                'rank': pattern['rank'],
                'count': pattern['count']
            })
            room.current_rank = pattern['rank']
            room.current_count = pattern['count']
            room.last_play = {'player_id': player_id, 'player_name': player.name, 'cards': card_ids, 'rank': pattern['rank'], 'count': pattern['count']}
            for p in room.players.values(): 
                p.passed = False
            
            # Check for automatic round win (2, JOKER, or 3 during inversion)
            auto_win = False
            if not room.inversion_active and (pattern['rank'] == 2 or pattern['rank'] == 'JOKER'):
                auto_win = True
                room.game_log.append(f"{player.name} played {pattern['rank']} - automatic round win!")
            elif room.inversion_active and (pattern['rank'] == 3 or pattern['rank'] == 'JOKER'):
                auto_win = True
                room.game_log.append(f"{player.name} played 3 during inversion - automatic round win!")
            
            if auto_win:
                # Save round before clearing
                self._save_completed_round(room, f"Auto-win ({pattern['rank']})")
                # Move current pile to discard
                room.discard.extend(room.current_pile)
                room.current_pile = []
                room.round_history = []  # Clear round history
                room.current_rank = None
                room.current_count = None
                room.inversion_active = False
                # Same player starts next round
                for p in room.players.values(): 
                    p.passed = False
                room.version += 1
                room.game_log.append(f"{player.name} starts new round after auto-win")
                room.last_round_winner = player_id
                return True, "Auto-win! New round started"
            
            effect_applied = False
            if pattern['effect']:
                effect_applied = self._apply_effect(room, player_id, pattern['effect'], pattern['count'])
            
            finished_this_turn = False
            if len(player.hand) == 0:
                if player_id not in room.finished_order:
                    room.finished_order.append(player_id)
                    room.game_log.append(f"{player.name} finished in position {len(room.finished_order)}!")
                    self._assign_roles_dynamic(room)
                finished_this_turn = True
                self._check_game_end(room)
                
            if not effect_applied or pattern['effect'] == 'eight_reset':
                if pattern['effect'] == 'eight_reset':
                    # Save round before clearing
                    self._save_completed_round(room, "Eight reset")
                    # Move current pile to discard before reset
                    room.discard.extend(room.current_pile)
                    room.current_pile = []
                    room.round_history = []
                    room.current_rank = None
                    room.current_count = None
                    room.inversion_active = False
                    room.game_log.append(f"{player.name} played {pattern['count']} 8s - pile cleared!")
                    room.last_round_winner = player_id
                else:
                    # If player finished, skip to next player with cards
                    if finished_this_turn and not self._check_game_end(room):
                        self._advance_turn(room)
                    else:
                        self._advance_turn(room)
            
            room.version += 1
            room.game_log.append(f"{player.name} played: {', '.join([self._format_card(c) for c in card_ids])}")
            return True, "Cards played successfully"

    def _apply_effect(self, room: RoomState, player_id: str, effect: str, count: int) -> bool:
        """Apply an effect to the room."""
        player = room.players[player_id]
        if effect == 'seven_gift':
            remaining = min(count, len(player.hand))
            room.pending_gift = {'player_id': player_id, 'remaining': remaining}
            room.game_log.append(f"{room.players[player_id].name} must gift {remaining} cards!")
            return True
        if effect == 'eight_reset': 
            return False
        if effect == 'ten_discard':
            remaining = min(count, len(player.hand))
            room.pending_discard = {'player_id': player_id, 'remaining': remaining}
            room.game_log.append(f"{room.players[player_id].name} must discard {remaining} cards!")
            return True
        if effect == 'jack_inversion':
            room.inversion_active = True
            room.game_log.append("Rank order inverted! Lower ranks now beat higher ranks!")
            return False
        return False

    def _check_game_end(self, room: RoomState) -> bool:
        """Check if the game should end (only one player left with cards)"""
        players_with_cards = [p for p in room.players.values() if len(p.hand) > 0]
        if len(players_with_cards) <= 1:
            # Add the last player(s) to finished order if not already there
            for p in players_with_cards:
                if p.id not in room.finished_order:
                    room.finished_order.append(p.id)
                    room.game_log.append(f"{p.name} finished LAST - Asshole!")
                    self._assign_roles_dynamic(room)
            self._end_game(room)
            return True
        return False

    def _advance_turn_if_no_pending(self, room: RoomState):
        """Only advance turn if no pending effects"""
        if not room.pending_gift and not room.pending_discard:
            # Check if game should end before advancing turn
            if not self._check_game_end(room):
                self._advance_turn(room)

    def submit_gift_distribution(self, room_id: str, player_id: str, assignments: List[dict]) -> Tuple[bool, str]:
        """Submit a gift distribution to the room."""
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room: 
                return False, "Room not found"
            if not room.pending_gift: 
                return False, "No gift pending"
            if room.pending_gift['player_id'] != player_id: 
                return False, "Not your gift"
            
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
            
            # Validate recipients: must not be in finished_order and must have cards
            for assignment in assignments:
                recipient = room.players[assignment['to']]
                if assignment['to'] in room.finished_order or recipient.hand_count == 0:
                    return False, f"Cannot gift to finished player: {recipient.name}"
            
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
                gift_details.append(f"{len(assignment['cards'])} to {recipient_name}")
            room.game_log.append(f"{player.name} gifted: {', '.join(gift_details)}")
            
            finished_this_turn = False
            if len(player.hand) == 0:
                if player_id not in room.finished_order:
                    room.finished_order.append(player_id)
                    room.game_log.append(f"{player.name} finished in position {len(room.finished_order)}!")
                    self._assign_roles_dynamic(room)
                finished_this_turn = True
                self._check_game_end(room)
            
            if not self._check_game_end(room):
                if finished_this_turn:
                    self._advance_turn_if_no_pending(room)
                else:
                    self._advance_turn_if_no_pending(room)
            room.version += 1
            return True, "Gift distributed successfully"

    def submit_discard_selection(self, room_id: str, player_id: str, card_ids: List[str]) -> Tuple[bool, str]:
        """Submit a discard selection to the room."""
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room: 
                return False, "Room not found"
            if not room.pending_discard: 
                return False, "No discard pending"
            if room.pending_discard['player_id'] != player_id: 
                return False, "Not your discard"
            
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
            
            finished_this_turn = False
            if len(player.hand) == 0:
                if player_id not in room.finished_order:
                    room.finished_order.append(player_id)
                    room.game_log.append(f"{player.name} finished in position {len(room.finished_order)}!")
                    self._assign_roles_dynamic(room)
                finished_this_turn = True
                self._check_game_end(room)
            
            if remaining <= 0:
                room.pending_discard = None
                room.game_log.append(f"{player.name} discarded {discarded_count} cards")
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
            if nxt.hand and len(nxt.hand) > 0:
                room.turn = nxt.id
                return
        # If no one has cards, set turn to None
        room.turn = None

    def pass_turn(self, room_id: str, player_id: str) -> Tuple[bool, str]:
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room: 
                return False, "Room not found"
            if room.turn != player_id: 
                return False, "Not your turn"
            
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
                room.round_history = []
                room.current_rank = None
                room.current_count = None
                room.inversion_active = False
                if room.last_play:
                    room.turn = room.last_play['player_id']
                    room.game_log.append(f"{room.players[room.turn].name} starts new round")
                    room.last_round_winner = room.last_play['player_id']
                for p in room.players.values(): 
                    p.passed = False
                # Assign roles in case the last player finished by passing
                self._assign_roles_dynamic(room)
            else:
                self._advance_turn(room)
            room.version += 1
            return True, "Passed"

    def _end_game(self, room: RoomState):
        for p in room.players.values():
            if p.id not in room.finished_order and p.hand:
                room.finished_order.append(p.id)
        
        n = len(room.players)
        if n == 3:
            roles = ['President', 'Vice President', 'Asshole']
        elif n == 4:
            roles = ['President', 'Vice President', 'Scumbag', 'Asshole']
        else:  # 5 players
            roles = ['President', 'Vice President', 'Citizen', 'Scumbag', 'Asshole']
        
        for i, pid in enumerate(room.finished_order):
            if i < len(roles):
                room.players[pid].role = roles[i]
            else:
                room.players[pid].role = None
        
        room.phase = 'finished'
        room.game_log.append("Game finished!")
        for i, pid in enumerate(room.finished_order):
            p = room.players[pid]
            room.game_log.append(f"{i+1}. {p.name} - {p.role}")
        room.first_game = False
        
        # Set global_asshole_id to the last player in finished_order
        if room.finished_order:
            room.global_asshole_id = room.finished_order[-1]

    def _assign_roles_dynamic(self, room: RoomState):
        n = len(room.players)
        if n == 3:
            roles = ['President', 'Vice President', 'Asshole']
        elif n == 4:
            roles = ['President', 'Vice President', 'Scumbag', 'Asshole']
        else:
            roles = ['President', 'Vice President', 'Citizen', 'Scumbag', 'Asshole']
        
        for i, pid in enumerate(room.finished_order):
            if i < len(roles):
                room.players[pid].role = roles[i]
            else:
                room.players[pid].role = None
        
        # For players still in the game, clear their role until they finish
        for pid, p in room.players.items():
            if pid not in room.finished_order:
                p.role = None

    def _start_card_exchange(self, room: RoomState):
        """Start the card exchange phase between games"""
        room.phase = 'exchange'
        room.exchange_phase = True
        room.game_log.append("Card exchange phase started!")
        
        # Set up exchange data
        n = len(room.players)
        if n == 3:
            # President gives 2 best cards to Asshole
            # Asshole gives 2 worst cards to President
            president_id = room.finished_order[0] if len(room.finished_order) > 0 else None
            asshole_id = room.finished_order[-1] if len(room.finished_order) > 0 else None
            
            if president_id and asshole_id:
                room.pending_exchange = {
                    'president_id': president_id,
                    'asshole_id': asshole_id,
                    'president_cards': [],
                    'asshole_cards': []
                }
        elif n == 4:
            # President gives 2 best cards to Asshole
            # Vice President gives 1 best card to Scumbag
            # Asshole gives 2 worst cards to President
            # Scumbag gives 1 worst card to Vice President
            president_id = room.finished_order[0] if len(room.finished_order) > 0 else None
            vice_president_id = room.finished_order[1] if len(room.finished_order) > 1 else None
            scumbag_id = room.finished_order[-2] if len(room.finished_order) > 1 else None
            asshole_id = room.finished_order[-1] if len(room.finished_order) > 0 else None
            
            if president_id and asshole_id and vice_president_id and scumbag_id:
                room.pending_exchange = {
                    'president_id': president_id,
                    'vice_president_id': vice_president_id,
                    'scumbag_id': scumbag_id,
                    'asshole_id': asshole_id,
                    'president_cards': [],
                    'vice_president_cards': [],
                    'scumbag_cards': [],
                    'asshole_cards': []
                }
        else:  # 5 players
            # President gives 2 best cards to Asshole
            # Vice President gives 1 best card to Scumbag
            # Asshole gives 2 worst cards to President
            # Scumbag gives 1 worst card to Vice President
            president_id = room.finished_order[0] if len(room.finished_order) > 0 else None
            vice_president_id = room.finished_order[1] if len(room.finished_order) > 1 else None
            scumbag_id = room.finished_order[-2] if len(room.finished_order) > 1 else None
            asshole_id = room.finished_order[-1] if len(room.finished_order) > 0 else None
            
            if president_id and asshole_id and vice_president_id and scumbag_id:
                room.pending_exchange = {
                    'president_id': president_id,
                    'vice_president_id': vice_president_id,
                    'scumbag_id': scumbag_id,
                    'asshole_id': asshole_id,
                    'president_cards': [],
                    'vice_president_cards': [],
                    'scumbag_cards': [],
                    'asshole_cards': []
                }

    def submit_asshole_cards(self, room_id: str, asshole_id: str, card_ids: List[str]) -> Tuple[bool, str]:
        """Submit cards from Asshole to President"""
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room or not room.pending_exchange:
                return False, "No exchange pending"
            
            player = room.players[asshole_id]
            if not player:
                return False, "Player not found"
            
            # Validate cards
            for card_id in card_ids:
                if card_id not in player.hand:
                    return False, f"You don't own {card_id}"
            
            # Store the cards
            room.pending_exchange['asshole_cards'] = card_ids.copy()
            room.game_log.append(f"{player.name} (Asshole) selected {len(card_ids)} cards for President")
            
            # Check if exchange is complete
            if self._is_exchange_complete(room):
                self._finish_card_exchange(room)
            
            room.version += 1
            return True, "Cards submitted"

    def submit_president_cards(self, room_id: str, president_id: str, card_ids: List[str]) -> Tuple[bool, str]:
        """Submit cards from President to Asshole"""
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room or not room.pending_exchange:
                return False, "No exchange pending"
            
            player = room.players[president_id]
            if not player:
                return False, "Player not found"
            
            # Validate cards
            for card_id in card_ids:
                if card_id not in player.hand:
                    return False, f"You don't own {card_id}"
            
            # Store the cards
            room.pending_exchange['president_cards'] = card_ids.copy()
            room.game_log.append(f"{player.name} (President) selected {len(card_ids)} cards for Asshole")
            
            # Check if exchange is complete
            if self._is_exchange_complete(room):
                self._finish_card_exchange(room)
            
            room.version += 1
            return True, "Cards submitted"

    def submit_scumbag_card(self, room_id: str, scumbag_id: str, card_id: str) -> Tuple[bool, str]:
        """Submit card from Scumbag to Vice President"""
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room or not room.pending_exchange:
                return False, "No exchange pending"
            
            player = room.players[scumbag_id]
            if not player:
                return False, "Player not found"
            
            if card_id not in player.hand:
                return False, f"You don't own {card_id}"
            
            room.pending_exchange['scumbag_cards'] = [card_id]
            room.game_log.append(f"{player.name} (Scumbag) selected 1 card for Vice President")
            
            if self._is_exchange_complete(room):
                self._finish_card_exchange(room)
            
            room.version += 1
            return True, "Card submitted"

    def submit_vice_president_card(self, room_id: str, vice_president_id: str, card_id: str) -> Tuple[bool, str]:
        """Submit card from Vice President to Scumbag"""
        with self.room_locks[room_id]:
            room = self.get_room(room_id)
            if not room or not room.pending_exchange:
                return False, "No exchange pending"
            
            player = room.players[vice_president_id]
            if not player:
                return False, "Player not found"
            
            if card_id not in player.hand:
                return False, f"You don't own {card_id}"
            
            room.pending_exchange['vice_president_cards'] = [card_id]
            room.game_log.append(f"{player.name} (Vice President) selected 1 card for Scumbag")
            
            if self._is_exchange_complete(room):
                self._finish_card_exchange(room)
            
            room.version += 1
            return True, "Card submitted"

    def _is_exchange_complete(self, room: RoomState) -> bool:
        """Check if all required cards have been submitted for exchange"""
        if not room.pending_exchange:
            return False
        
        n = len(room.players)
        if n == 3:
            return (len(room.pending_exchange.get('president_cards', [])) == 2 and
                    len(room.pending_exchange.get('asshole_cards', [])) == 2)
        else:  # 4 or 5 players
            return (len(room.pending_exchange.get('president_cards', [])) == 2 and
                    len(room.pending_exchange.get('asshole_cards', [])) == 2 and
                    len(room.pending_exchange.get('vice_president_cards', [])) == 1 and
                    len(room.pending_exchange.get('scumbag_cards', [])) == 1)

    def _finish_card_exchange(self, room: RoomState):
        """Complete the card exchange and start new game"""
        exchange = room.pending_exchange
        
        # Transfer cards
        if exchange.get('president_cards'):
            president = room.players[exchange['president_id']]
            asshole = room.players[exchange['asshole_id']]
            for card in exchange['president_cards']:
                president.hand.remove(card)
                asshole.hand.append(card)
            president.hand_count = len(president.hand)
            asshole.hand_count = len(asshole.hand)
        
        if exchange.get('asshole_cards'):
            president = room.players[exchange['president_id']]
            asshole = room.players[exchange['asshole_id']]
            for card in exchange['asshole_cards']:
                asshole.hand.remove(card)
                president.hand.append(card)
            president.hand_count = len(president.hand)
            asshole.hand_count = len(asshole.hand)
        
        if exchange.get('vice_president_cards'):
            vice_president = room.players[exchange['vice_president_id']]
            scumbag = room.players[exchange['scumbag_id']]
            for card in exchange['vice_president_cards']:
                vice_president.hand.remove(card)
                scumbag.hand.append(card)
            vice_president.hand_count = len(vice_president.hand)
            scumbag.hand_count = len(scumbag.hand)
        
        if exchange.get('scumbag_cards'):
            vice_president = room.players[exchange['vice_president_id']]
            scumbag = room.players[exchange['scumbag_id']]
            for card in exchange['scumbag_cards']:
                scumbag.hand.remove(card)
                vice_president.hand.append(card)
            vice_president.hand_count = len(vice_president.hand)
            scumbag.hand_count = len(scumbag.hand)
        
        room.game_log.append("Card exchange completed!")
        room.pending_exchange = None
        room.exchange_phase = False
        
        # Start new game
        self.start_game(room.id)

    def _format_card(self, card_id: str) -> str:
        rank, suit = parse_card(card_id)
        suit_symbols = {'S':'♠','H':'♥','D':'♦','C':'♣'}
        if rank == 'JOKER': 
            return '🃏'
        return f"{rank}{suit_symbols.get(suit,'')}" 