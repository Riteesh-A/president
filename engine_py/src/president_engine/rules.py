"""
Game rule configuration and validation.
"""

from pydantic import BaseModel, Field, field_validator


class RuleConfig(BaseModel):
    """Configuration for game rules and settings."""
    
    use_jokers: bool = Field(
        default=True,
        description="Whether to include jokers in the deck"
    )
    max_players: int = Field(
        default=5,
        ge=3,
        le=5,
        description="Maximum number of players allowed"
    )
    min_players: int = Field(
        default=3,
        ge=3,
        le=5,
        description="Minimum number of players required to start"
    )
    enable_bots: bool = Field(
        default=True,
        description="Whether to allow bot players"
    )
    auto_fill_bots: bool = Field(
        default=False,
        description="Automatically fill empty seats with bots when starting"
    )
    turn_timeout: int = Field(
        default=30,
        ge=10,
        le=120,
        description="Turn timeout in seconds (0 = no timeout)"
    )
    room_timeout: int = Field(
        default=3600,
        ge=300,
        le=7200,
        description="Room inactivity timeout in seconds"
    )
    
    @field_validator('max_players')
    @classmethod
    def validate_max_players(cls, v, info):
        """Validate maximum players doesn't exceed minimum."""
        min_players = info.data.get('min_players', 3)
        if v < min_players:
            raise ValueError(f'max_players ({v}) must be >= min_players ({min_players})')
        return v
    
    def validate_player_count(self, player_count: int) -> bool:
        """Check if a player count is valid for this configuration."""
        return self.min_players <= player_count <= self.max_players
    
    def get_deck_size(self) -> int:
        """Get the total number of cards in the deck."""
        base_deck = 52
        if self.use_jokers:
            base_deck += 2
        return base_deck
    
    def get_role_mapping(self, player_count: int) -> dict[int, str]:
        """Get role mapping for finish positions based on player count."""
        from .constants import (
            ROLE_PRESIDENT, ROLE_VICE_PRESIDENT, ROLE_CITIZEN,
            ROLE_SCUMBAG, ROLE_ASSHOLE
        )
        
        if player_count == 3:
            return {
                1: ROLE_PRESIDENT,
                2: ROLE_VICE_PRESIDENT,
                3: ROLE_ASSHOLE
            }
        elif player_count == 4:
            return {
                1: ROLE_PRESIDENT,
                2: ROLE_VICE_PRESIDENT,
                3: ROLE_SCUMBAG,
                4: ROLE_ASSHOLE
            }
        elif player_count == 5:
            return {
                1: ROLE_PRESIDENT,
                2: ROLE_VICE_PRESIDENT,
                3: ROLE_CITIZEN,
                4: ROLE_SCUMBAG,
                5: ROLE_ASSHOLE
            }
        else:
            raise ValueError(f"Unsupported player count: {player_count}")


# Default configuration instance
default_rules = RuleConfig()


def create_rules(**overrides) -> RuleConfig:
    """Create a RuleConfig with optional overrides."""
    config_dict = default_rules.dict()
    config_dict.update(overrides)
    return RuleConfig(**config_dict) 