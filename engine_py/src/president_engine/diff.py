"""
State diff computation for efficient updates.
"""

from typing import Any, Dict, List, Optional

from .serialization import sanitize_state


def compute_diff(
    old_state,
    new_state,
    viewer_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Compute a JSON Patch-style diff between two states.
    
    Args:
        old_state: Previous room state
        new_state: New room state
        viewer_id: ID of the player viewing the state
    
    Returns:
        List of patch operations
    """
    if old_state is None:
        # First state, no diff needed
        return []
    
    # Sanitize both states for the viewer
    old_sanitized = sanitize_state(old_state, viewer_id)
    new_sanitized = sanitize_state(new_state, viewer_id)
    
    ops = []
    
    # Check top-level fields
    top_level_fields = [
        "version", "phase", "turn", "inversion_active",
        "finished_order"
    ]
    
    for field in top_level_fields:
        old_value = old_sanitized.get(field)
        new_value = new_sanitized.get(field)
        
        if old_value != new_value:
            ops.append({
                "op": "replace",
                "path": f"/{field}",
                "value": new_value
            })
    
    # Check current pattern
    old_pattern = old_sanitized.get("current_pattern", {})
    new_pattern = new_sanitized.get("current_pattern", {})
    
    for pattern_field in ["rank", "count", "last_player"]:
        old_value = old_pattern.get(pattern_field)
        new_value = new_pattern.get(pattern_field)
        
        if old_value != new_value:
            ops.append({
                "op": "replace",
                "path": f"/current_pattern/{pattern_field}",
                "value": new_value
            })
    
    # Check players
    old_players = old_sanitized.get("players", {})
    new_players = new_sanitized.get("players", {})
    
    # Check for player changes
    all_player_ids = set(old_players.keys()) | set(new_players.keys())
    
    for player_id in all_player_ids:
        old_player = old_players.get(player_id)
        new_player = new_players.get(player_id)
        
        if old_player is None and new_player is not None:
            # Player added
            ops.append({
                "op": "add",
                "path": f"/players/{player_id}",
                "value": new_player
            })
        elif old_player is not None and new_player is None:
            # Player removed
            ops.append({
                "op": "remove",
                "path": f"/players/{player_id}"
            })
        elif old_player != new_player:
            # Player changed - check individual fields
            player_fields = [
                "name", "seat", "role", "passed", "connected",
                "is_bot", "hand_count"
            ]
            
            # Special handling for hand (only for viewer)
            if player_id == viewer_id:
                player_fields.append("hand")
            
            for field in player_fields:
                old_value = old_player.get(field)
                new_value = new_player.get(field)
                
                if old_value != new_value:
                    ops.append({
                        "op": "replace",
                        "path": f"/players/{player_id}/{field}",
                        "value": new_value
                    })
    
    # Check pending effects
    old_effects = old_sanitized.get("pending_effects", {})
    new_effects = new_sanitized.get("pending_effects", {})
    
    if old_effects != new_effects:
        ops.append({
            "op": "replace",
            "path": "/pending_effects",
            "value": new_effects
        })
    
    # Check recent effects (only add if new effects were added)
    old_recent = old_sanitized.get("recent_effects", [])
    new_recent = new_sanitized.get("recent_effects", [])
    
    if len(new_recent) > len(old_recent):
        # New effects added, send the new ones
        new_effects_only = new_recent[len(old_recent):]
        ops.append({
            "op": "add",
            "path": "/new_effects",
            "value": new_effects_only
        })
    elif old_recent != new_recent:
        # Effects list changed completely, replace
        ops.append({
            "op": "replace",
            "path": "/recent_effects",
            "value": new_recent
        })
    
    return ops


def apply_diff(state: Dict[str, Any], ops: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply a diff to a state dictionary.
    
    Args:
        state: Current state dictionary
        ops: List of patch operations to apply
    
    Returns:
        Updated state dictionary
    """
    import copy
    
    new_state = copy.deepcopy(state)
    
    for op in ops:
        op_type = op["op"]
        path = op["path"]
        value = op.get("value")
        
        path_parts = [p for p in path.split("/") if p]
        
        if op_type == "replace":
            _set_nested_value(new_state, path_parts, value)
        elif op_type == "add":
            _set_nested_value(new_state, path_parts, value)
        elif op_type == "remove":
            _remove_nested_value(new_state, path_parts)
    
    return new_state


def _set_nested_value(obj: Dict[str, Any], path: List[str], value: Any):
    """Set a value at a nested path in a dictionary."""
    current = obj
    
    for i, key in enumerate(path[:-1]):
        if key not in current:
            current[key] = {}
        current = current[key]
    
    if path:
        current[path[-1]] = value


def _remove_nested_value(obj: Dict[str, Any], path: List[str]):
    """Remove a value at a nested path in a dictionary."""
    current = obj
    
    for key in path[:-1]:
        if key not in current:
            return  # Path doesn't exist
        current = current[key]
    
    if path and path[-1] in current:
        del current[path[-1]]


def should_send_full_state(ops: List[Dict[str, Any]], threshold: int = 10) -> bool:
    """
    Determine if a full state should be sent instead of a diff.
    
    Args:
        ops: List of patch operations
        threshold: Maximum number of operations before sending full state
    
    Returns:
        True if full state should be sent
    """
    if len(ops) > threshold:
        return True
    
    # Check for complex operations that might be better as full state
    complex_ops = 0
    for op in ops:
        if op["op"] == "add" and "/players/" in op["path"]:
            complex_ops += 1
        elif op["op"] == "replace" and op["path"] == "/pending_effects":
            complex_ops += 1
    
    return complex_ops > 3


def get_changed_fields(ops: List[Dict[str, Any]]) -> List[str]:
    """
    Get a list of top-level fields that changed.
    
    Args:
        ops: List of patch operations
    
    Returns:
        List of changed field names
    """
    changed_fields = set()
    
    for op in ops:
        path = op["path"]
        if path.startswith("/"):
            path = path[1:]
        
        # Get the top-level field
        top_field = path.split("/")[0]
        changed_fields.add(top_field)
    
    return list(changed_fields) 