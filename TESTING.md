# President Card Game - Testing Guide

This document explains how to use the comprehensive test suites for the President Card Game.

## Test Files Overview

### 1. `tests.py` - Core Game Logic Tests
- **Purpose**: Tests the fundamental game mechanics and rules
- **Coverage**: 
  - Auto-win scenarios (2s, Jokers)
  - Joker wildcard functionality
  - Last card effects (7s, 10s)
  - Partial effects handling
  - Role assignment
  - New game continuation
  - Bot behavior
  - Bot effects handling
  - Card exchange mechanics
  - Role preservation in subsequent games

### 2. `tests_ui.py` - UI Simulation Tests
- **Purpose**: Tests complete game flows and UI logic simulation
- **Coverage**:
  - Complete game flow from start to finish
  - Card exchange phase in subsequent games
  - Special card effects (7s, 10s, Jokers)
  - Bot behavior and AI logic
  - Game rules validation
  - UI state consistency

### 3. `ci_test.py` - Continuous Integration Script
- **Purpose**: Runs all test suites with clear output for CI/CD pipelines
- **Features**:
  - Timeout protection (5 minutes per test)
  - Clear pass/fail reporting
  - Duration tracking
  - Summary output

### 4. `run_all_tests.py` - Comprehensive Test Runner
- **Purpose**: Runs all test suites with detailed output
- **Features**:
  - Full test output display
  - Error reporting
  - Success/failure summary

## Running Tests

### Quick Test (Recommended for development)
```bash
python ci_test.py
```
This runs all tests with minimal output and clear pass/fail status.

### Detailed Test Output
```bash
python run_all_tests.py
```
This shows full test output for debugging.

### Individual Test Suites
```bash
# Core game logic tests
python tests.py

# UI simulation tests
python tests_ui.py
```

## Test Coverage

### Core Game Logic (`tests.py`)
- ✅ **79 tests** covering all game mechanics
- ✅ Auto-win scenarios (2s, Jokers)
- ✅ Joker wildcard behavior
- ✅ Special card effects (7s, 10s)
- ✅ Role assignment and preservation
- ✅ Bot behavior and effects handling
- ✅ Card exchange mechanics
- ✅ Game continuation logic

### UI Simulation (`tests_ui.py`)
- ✅ **57 tests** covering complete game flows
- ✅ Full game simulation from start to finish
- ✅ Card exchange phase testing
- ✅ Special card effects testing
- ✅ Bot AI behavior testing
- ✅ Game rules validation
- ✅ UI state consistency

## Continuous Integration

### For CI/CD Pipelines
Use `ci_test.py` in your CI pipeline:

```yaml
# Example GitHub Actions step
- name: Run Tests
  run: python ci_test.py
```

### Exit Codes
- `0`: All tests passed
- `1`: Some tests failed

## Test Requirements

### Dependencies
- Python 3.7+
- Required modules: `dash`, `dataclasses`, `typing`, `random`, `time`

### File Structure
```
president/
├── app.py              # Main game application
├── tests.py            # Core game logic tests
├── tests_ui.py         # UI simulation tests
├── ci_test.py          # CI test runner
├── run_all_tests.py    # Comprehensive test runner
└── TESTING.md          # This file
```

## Test Scenarios Covered

### Game Rules
- ✅ Card validation and play rules
- ✅ Turn management and advancement
- ✅ Special card effects (7s, 10s)
- ✅ Auto-win conditions (2s, Jokers)
- ✅ Inversion mechanics
- ✅ Last card handling

### Role System
- ✅ Role assignment (President, Vice President, Scumbag, Asshole)
- ✅ Role preservation across games
- ✅ Card exchange between roles
- ✅ Human players can choose which cards to give (President/Vice President only)
- ✅ Automatic exchanges: Asshole→President, Scumbag→Vice President (all players, truly automatic)
- ✅ Manual exchanges: President→Asshole, Vice President→Scumbag (humans only, bots automatic)
- ✅ Asshole starting subsequent games

### Bot AI
- ✅ Bot move generation
- ✅ Bot effect handling (gift, discard)
- ✅ Bot card exchange participation
- ✅ Bot turn management

### Game Flow
- ✅ Game start and initialization
- ✅ Game progression and turn management
- ✅ Game end and role assignment
- ✅ New game continuation
- ✅ Card exchange phase
- ✅ Bot exchange automation
- ✅ Exchange phase completion

### UI Logic
- ✅ State consistency
- ✅ Turn indication
- ✅ Card display and selection
- ✅ Effect handling UI
- ✅ Exchange phase UI with manual card selection for humans (President/Vice President only)
- ✅ Automatic card selection for bots and automatic exchanges
- ✅ Play validation disabled during exchange phase
- ✅ Bot exchanges automatically triggered by game updater
- ✅ Human automatic exchanges triggered by game updater (no UI interaction needed)
- ✅ Role display reset for new games (roles hidden during play, shown during exchange)
- ✅ Gift distribution UI fixed (can select which player to give cards to)
- ✅ Joker wildcard functionality preserved (can be played with any cards, beat any cards)

## Troubleshooting

### Common Issues

1. **Test Timeouts**
   - Tests have 5-minute timeout protection
   - If tests timeout, check for infinite loops in game logic

2. **Random Test Failures**
   - Some tests depend on random card distribution
   - Tests are designed to handle missing cards gracefully
   - Look for warning messages indicating expected behavior

3. **Import Errors**
   - Ensure all required modules are installed
   - Check Python version compatibility

### Debugging Failed Tests

1. **Run individual test suites** to isolate issues
2. **Check test output** for specific failure messages
3. **Verify game logic** in `app.py` matches test expectations
4. **Check for recent changes** that might have broken functionality

## Best Practices

### For Development
1. **Run `ci_test.py`** before committing changes
2. **Add new tests** when adding new features
3. **Update tests** when changing game rules
4. **Keep tests independent** and self-contained

### For Testing
1. **Run all tests** after any code changes
2. **Check both test suites** for comprehensive coverage
3. **Monitor test duration** for performance issues
4. **Review test output** for unexpected behavior

## Test Maintenance

### Adding New Tests
1. Add tests to appropriate test file (`tests.py` or `tests_ui.py`)
2. Follow existing test patterns and naming conventions
3. Ensure tests are independent and don't affect other tests
4. Update this documentation if adding new test categories

### Updating Tests
1. Update tests when changing game rules or mechanics
2. Ensure tests reflect current game behavior
3. Maintain backward compatibility where possible
4. Document any breaking changes in test logic

---

**Note**: These test suites ensure the President Card Game works correctly across all scenarios and edge cases. Run them regularly to maintain game quality and catch issues early. 