"""Bot logic for AI players"""

import random
import time
from collections import defaultdict
from typing import List
from .models import RoomState, Player
from .constants import parse_card

class GreedyBot:
    def __init__(self, engine):
        self.engine = engine
    
    def make_move(self, room_id: str, player_id: str):
        """
        Make a move for the bot.
        Args:
            room_id: The ID of the room
            player_id: The ID of the player making the move
        """
        room = self.engine.get_room(room_id)
        if not room or room.turn != player_id: 
            print(f"[BOT DEBUG] Bot {player_id} cannot move - turn mismatch or room not found")
            return
        if room.pending_gift and room.pending_gift['player_id'] == player_id:
            print(f"[BOT DEBUG] Bot {player_id} handling gift")
            self._handle_gift(room_id, player_id, room.pending_gift['remaining'])
            return
        if room.pending_discard and room.pending_discard['player_id'] == player_id:
            print(f"[BOT DEBUG] Bot {player_id} handling discard")
            self._handle_discard(room_id, player_id, room.pending_discard['remaining'])
            return
        
        player = room.players[player_id]
        hand = player.hand
        print(f"[BOT DEBUG] Bot {player.name} ({player_id}) making move with {len(hand)} cards")
        valid_plays = []
        
        if room.current_rank is None:
            # Case 1: Empty pile - special rules may apply
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
                        ok, _, _ = self.engine.validate_play(room, player_id, play)
                        if ok:
                            valid_plays.append(play)
        else:
            # Normal play: must match count and be higher rank
            groups = defaultdict(list)
            for c in hand:
                r, _ = parse_card(c)
                groups[r].append(c)
            for rank, cards in groups.items():
                # Check if the number of cards in the hand is greater than or equal to the current count
                if len(cards) >= room.current_count:
                    # Try all possible plays of the current count
                    play = cards[:room.current_count]
                    ok, _, _ = self.engine.validate_play(room, player_id, play)
                    if ok:
                        valid_plays.append(play)
        
        if valid_plays:
            # Use the same scoring as before
            best = max(valid_plays, key=len)
            print(f"[BOT DEBUG] Bot {player.name} playing: {best}")
            self.engine.play_cards(room_id, player_id, best)
        else:
            print(f"[BOT DEBUG] Bot {player.name} passing turn")
            self.engine.pass_turn(room_id, player_id)

    def _handle_gift(self, room_id: str, player_id: str, rem: int):
        room = self.engine.get_room(room_id)
        if not room:
            return
        player = room.players[player_id]
        
        # Find active players to gift to
        other_players = [pl for pl in room.players.values() 
                        if pl.id != player_id and pl.id not in room.finished_order and pl.hand_count > 0]
        
        if not other_players:
            return
        
        to_gift = player.hand[:rem] if len(player.hand) >= rem else player.hand.copy()
        
        # Simple strategy: give all cards to first available player
        if other_players and to_gift:
            assignments = [{'to': other_players[0].id, 'cards': to_gift}]
            self.engine.submit_gift_distribution(room_id, player_id, assignments)
        
    def _handle_discard(self, room_id: str, player_id: str, rem: int):
        room = self.engine.get_room(room_id)
        if not room:
            return
        player = room.players[player_id]
        to_discard = player.hand[:rem] if len(player.hand) >= rem else player.hand.copy()
        self.engine.submit_discard_selection(room_id, player_id, to_discard) 