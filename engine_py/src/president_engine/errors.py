# engine_py/src/president_engine/errors.py

class GameError(Exception):
    """Base exception for game-related errors."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

# Specific error codes
ROOM_FULL = "ROOM_FULL"
NOT_YOUR_TURN = "NOT_YOUR_TURN"
OWNERSHIP_MISMATCH = "OWNERSHIP_MISMATCH"
PATTERN_MISMATCH = "PATTERN_MISMATCH"
RANK_TOO_LOW = "RANK_TOO_LOW"
EFFECT_PENDING = "EFFECT_PENDING"
INVALID_GIFT_DISTRIBUTION = "INVALID_GIFT_DISTRIBUTION"
INVALID_DISCARD_SELECTION = "INVALID_DISCARD_SELECTION"
ALREADY_PASSED = "ALREADY_PASSED"
ACTION_NOT_ALLOWED = "ACTION_NOT_ALLOWED"
INTERNAL_ERROR = "INTERNAL_ERROR"

# Helper function to raise common errors
def raise_error(code: str, message: str):
    raise GameError(code, message)