"""
State serialization and sanitization utilities.
"""

import copy
from typing import Any, Dict, Optional

from .models import RoomState


def sanitize_state(state: RoomState, viewer_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Sanitize room state for transmission to clients.
    
    Args:
        state: Room state to sanitize
        viewer_id: ID of the player viewing the state (to show their cards)
    
    Returns:
        Sanitized state dictionary safe for JSON transmission
    """
    # Create base sanitized state
    sanitized = {
        "id": state.id,
        "version": state.version,
        "phase": state.phase,
        "turn": state.turn,
        "inversion_active": state.inversion_active,
        "current_pattern": {
            "rank": state.current_pattern.rank,
            "count": state.current_pattern.count,
            "last_player": state.current_pattern.last_player
        },
        "finished_order": state.finished_order.copy(),
        "players": {},
        "pending_effects": {},
        "recent_effects": [],
        "rules": _serialize_rule_config(state.rule_config) if state.rule_config else None
    }
    
    # Sanitize players
    for player_id, player in state.players.items():
        sanitized_player = {
            "id": player.id,
            "name": player.name,
            "seat": player.seat,
            "role": player.role,
            "passed": player.passed,
            "connected": player.connected,
            "is_bot": player.is_bot,
            "hand_count": len(player.hand)
        }
        
        # Show full hand only to the viewer
        if player_id == viewer_id:
            sanitized_player["hand"] = player.hand.copy()
        
        sanitized["players"][player_id] = sanitized_player
    
    # Add pending effects (without revealing hidden information)
    if state.pending_gift:
        sanitized["pending_effects"]["gift"] = {
            "player_id": state.pending_gift.player_id,
            "remaining": state.pending_gift.remaining,
            "original_count": state.pending_gift.original_count
        }
    
    if state.pending_discard:
        sanitized["pending_effects"]["discard"] = {
            "player_id": state.pending_discard.player_id,
            "remaining": state.pending_discard.remaining,
            "original_count": state.pending_discard.original_count
        }
    
    # Add recent effects (last 5, anonymized)
    recent_effects = state.effects_log[-5:] if state.effects_log else []
    for effect in recent_effects:
        sanitized_effect = {
            "effect": effect.effect,
            "version": effect.version,
            "timestamp": effect.timestamp,
            "data": _sanitize_effect_data(effect.data, viewer_id)
        }
        sanitized["recent_effects"].append(sanitized_effect)
    
    return sanitized


def _serialize_rule_config(rule_config) -> Dict[str, Any]:
    """Serialize rule configuration."""
    return {
        "use_jokers": rule_config.use_jokers,
        "max_players": rule_config.max_players,
        "min_players": rule_config.min_players,
        "enable_bots": rule_config.enable_bots,
        "auto_fill_bots": rule_config.auto_fill_bots,
        "turn_timeout": rule_config.turn_timeout,
        "room_timeout": rule_config.room_timeout
    }


def _sanitize_effect_data(data: Dict[str, Any], viewer_id: Optional[str]) -> Dict[str, Any]:
    """Sanitize effect data to hide sensitive information."""
    sanitized = data.copy()
    
    # Remove specific card information unless it's for the viewer
    if "cards" in sanitized:
        # Replace with count unless this effect involves the viewer
        if data.get("player_id") != viewer_id:
            sanitized["card_count"] = len(sanitized["cards"])
            del sanitized["cards"]
    
    # Remove detailed gift assignments unless viewer is involved
    if "assignments" in sanitized:
        if data.get("gifter") != viewer_id:
            # Show only recipient counts, not specific cards
            sanitized["assignment_summary"] = [
                {"to": assignment["to"], "count": assignment["count"]}
                for assignment in sanitized["assignments"]
            ]
            del sanitized["assignments"]
    
    return sanitized


def serialize_player_for_list(player) -> Dict[str, Any]:
    """Serialize player for lobby player list."""
    return {
        "id": player.id,
        "name": player.name,
        "seat": player.seat,
        "is_bot": player.is_bot,
        "connected": player.connected
    }


def get_public_room_info(state: RoomState) -> Dict[str, Any]:
    """Get public information about a room for listings."""
    return {
        "id": state.id,
        "phase": state.phase,
        "player_count": len(state.players),
        "max_players": state.rule_config.max_players if state.rule_config else 5,
        "players": [
            serialize_player_for_list(player)
            for player in state.players.values()
        ]
    }


def create_minimal_state_update(state: RoomState, viewer_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a minimal state update with only essential information."""
    return {
        "id": state.id,
        "version": state.version,
        "phase": state.phase,
        "turn": state.turn,
        "player_count": len(state.players),
        "has_pending_effects": bool(state.pending_gift or state.pending_discard)
    } 