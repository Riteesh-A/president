# engine_py/src/president_engine/rules.py

from pydantic import BaseModel, Field, ValidationError, validator

class RuleConfig(BaseModel):
    use_jokers: bool = True
    max_players: int = 5
    min_players: int = 3
    enable_bots: bool = True

    @validator('min_players')
    def validate_min_players(cls, v, values):
        if not (3 <= v <= 5):
            raise ValueError('min_players must be between 3 and 5')
        if 'max_players' in values and v > values['max_players']:
            raise ValueError('min_players cannot be greater than max_players')
        return v

    @validator('max_players')
    def validate_max_players(cls, v, values):
        if not (3 <= v <= 5):
            raise ValueError('max_players must be between 3 and 5')
        if 'min_players' in values and v < values['min_players']:
            raise ValueError('max_players cannot be less than min_players')
        return v

# Example usage/validation (for your reference, not part of the module)
if __name__ == "__main__":
    try:
        # Valid config
        config1 = RuleConfig(use_jokers=True, max_players=4, min_players=3)
        print(f"Valid config: {config1}")

        # Invalid min_players
        # config2 = RuleConfig(min_players=2) # This would raise ValidationError
        # config3 = RuleConfig(min_players=4, max_players=3) # This would raise ValidationError
    except ValidationError as e:
        print(f"Config validation error: {e}")