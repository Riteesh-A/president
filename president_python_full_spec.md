# Multiplayer President (Custom Variant) – Python Implementation & Cursor Rules

**Status:** Authoritative single-source specification for implementing the custom President card game variant entirely with a **Python engine** plus a lightweight web client deployed on **Vercel**, with realtime served by a persistent Python service (Fly.io / Railway / Render). Use this document for all development, code generation (Cursor), reviews, and onboarding.

---

## 1. Vision & Objectives

1. Fast, fair, deterministic online play of a customised President (a.k.a. Asshole) variant for **2–5 players (max 5)** with optional bots. Optimal player count: 4–5.
2. Python engine containing *all* game logic, easily unit testable and framework agnostic.
3. Browser client (Next.js or static React) on Vercel consuming a websocket API directly from Python service.
4. Pluggable rule config but **defaults = custom rules in Section 4**.
5. Zero trust in clients: server authoritative state, secret hands protected.
6. Minimal latency (<200 ms perceived) and consistent behaviour under reconnects.

---

## 2. High-Level Architecture

```
Browser (React/Next.js on Vercel)
        |  (WSS JSON protocol)
        v
Persistent Python Service (FastAPI / Starlette + WebSocket, asyncio)
        |  (Redis JSON state, optional)
        v
   Redis (Upstash) – persistence / recovery
```

**Why hybrid:** Vercel cannot host long‑lived Python websocket processes. The Python engine runs elsewhere (Fly.io recommended). Vercel hosts static assets + minimal UI only.

---

## 3. Player Roles & Ranking (Custom Titles)

Finish order after a round assigns titles:

| Finish Position | Title          | Exchange Obligation Next Round                                                                       |
| --------------- | -------------- | ---------------------------------------------------------------------------------------------------- |
| 1               | President      | Receives 2 best from Asshole; chooses 2 any cards to return (after inspecting own hand, before play) |
| 2               | Vice President | Receives 1 best from Scumbag; chooses 1 any card to return                                           |
| 3..(n-2)        | Citizen        | No exchange (neutral)                                                                                |
| (n-1)           | Scumbag        | Gives 1 best card to Vice President, receives 1 chosen by Vice President                             |
| n               | Asshole        | Gives 2 best cards to President, receives 2 chosen by President                                      |

If **≤3 players**: Roles simplified (President, Asshole; no Vice roles). If **4 players**: President, Vice President, Scumbag, Asshole (no Citizens). If **5 players**: All roles as table above with exactly one Citizen.

**Best card = highest rank under *****normal***** ordering** (even if inversion occurred during prior round, exchanges at new round start always consider default ordering).

---

## 4. Custom Rule Set (Authoritative Game Mechanics)

These rules override generic President conventions.

### 4.1 Suits & Deck

- Suits **do not matter** for play comparisons.
- A standard 52‑card deck + *optional* 2 Jokers if `use_jokers = true`.
- **Suits tracked solely** to identify *who holds the 3♦* at the start of the very first round (and any new round). After start determination, suit has no effect on legality or ordering.

### 4.2 Rank Ordering

Default ascending rank list (lowest → highest):

```
3,4,5,6,7,8,9,10,J,Q,K,A,2,JOKER
```

Represent internally as: `[3,4,5,6,7,8,9,10,'J','Q','K','A',2,'JOKER']`.

### 4.3 Opening Play

- The **first game** (and each new round) starts with the player holding **3♦ (Three of Diamonds)**.
- That player **must lead** and may play **any number of 3s they possess (1–4)** as the opening combination.
- Subsequent turns must play a combination *strictly greater*:
  - Same *card count* (pattern size) and higher rank (based on current ordering; see inversion below), OR
  - Or pass.

### 4.4 Legal Patterns

- Singles, pairs, triples, quads only (no straights unless later enabled via config extension).
- All cards in a play must share the same rank (except Jokers may form a special pattern only if all Jokers; treat as that rank = `JOKER`).
- You cannot mix ranks to form sets.

### 4.5 Special Card Effects

Triggered when a legal play of a pattern whose rank matches below is resolved.

| Rank (pattern) | Effect Name    | Effect Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| -------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 7 (x sevens)   | Seven Gift     | Current player must immediately **gift x cards total to other players**. "x" equals the number of 7s just played. They may split these gifted cards across any opponents (bots or humans) in any distribution summing to x. Gifted cards are selected from *their hand after removing the played 7s*. Recipients add gifted cards to hand. Turn then proceeds to next player (no additional play by current player).                                                                                                                                                                                                                                                                                                                                                                                                |
| 8 (x eights)   | Eight Reset    | Pile is cleared (discard current trick). The player who played the 8s **immediately starts a new trick**, may lead any legal pattern from remaining hand (cannot reuse the just‑played 8s).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 10 (x tens)    | Ten Discard    | Player must **discard x additional cards** (of any ranks) face down into discard pile (not visible). Those cards leave the game for this round. (If hand has < x cards, discard all remaining.) Turn then ends; next player continues over a cleared pile (new trick started by next player).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| J (x jacks)    | Jack Inversion | Immediately **invert rank ordering** for the remainder of the *current trick cycle* until the trick ends (i.e., until a reset by Eight or trick completion by passes). During inversion: ordering becomes reversed: `JOKER,2,A,K,...,4,3` descending considered lowest→highest reversed. **Additional Rule:** After inversion begins, the *next player may only play ranks strictly lower than Jack under normal ordering*, i.e. in inverted ordering they must play a card that would have been *lower* pre-inversion. Practical simplification: After a Jack play, only lower pre-Jack ranks are legal (10 downward). **If a 3 is played while inversion is active and all other players pass**, the round ends (accelerated termination). After the trick ends (normal completion), ordering reverts to default. |

Clarifications:

- Effects stack only sequentially; an Eight reset clears inversion if active (since trick ended).
- Seven Gift & Ten Discard actions are *mandatory* auxiliary phases and must complete before advancing turn.

### 4.6 Passing & Trick End

- A player may pass instead of playing a higher pattern.
- Trick ends when all *active* players except the last one to have played have passed consecutively.
- After trick end (or Eight Reset), last successful player leads new trick (unless effect states otherwise).

### 4.7 Round End

- Round ends when all but one player have emptied hands. Remaining player is **Asshole**.
- Assign roles, then initiate **Exchange Phase** (Section 4.8) for next round.

### 4.8 Exchange Phase (Start of New Round)

Order of operations:

1. Deal new shuffled deck.
2. Identify roles from previous round.
3. **Asshole -> President:** Asshole automatically selects (highest rank) top 2 cards; these transfer. President chooses any 2 cards from their *current* hand to return.
4. **Scumbag -> Vice President:** Scumbag automatically gives highest single card; Vice President chooses any 1 card to return.
5. Citizens skip.
6. Start round: Player with 3♦ leads as per Opening Play. (If 3♦ traded during exchange, still opening anchor is whoever **currently holds** it.)

Edge cases: If players have fewer cards than required to give (rare with standard deck unless altered future variants) they give all available.

### 4.9 Jokers

- If `use_jokers = true`, Jokers are highest rank unless inversion active (then they become lowest logically for comparison). Jokers are treated as their own rank `JOKER`.
- Jokers count toward set sizes only if playing a pure Joker set (cannot combine with other ranks).

### 4.10 Invalid Plays

Reject with a structured error code (see Section 11): wrong card count, insufficient rank, not your turn, ownership mismatch, effect phase pending, etc.

---

## 5. Python Project Structure

```
/engine_py/
  pyproject.toml
  src/president_engine/
    __init__.py
    constants.py
    models.py          # dataclasses for core state
    rules.py           # RuleConfig (pydantic) + defaults
    state.py           # creation, cloning, sanitisation
    shuffle.py
    validate.py        # pattern detection & validation
    effects.py         # seven_gift, eight_reset, ten_discard, jack_inversion
    engine.py          # public mutation functions (play, pass, gift, discard, start_round, exchange)
    ranking.py         # determine finish order & roles
    exchange.py        # exchange phase orchestration
    bots/
      __init__.py
      base.py
      greedy.py        # basic heuristic
    storage/
      __init__.py
      memory.py
      redis_store.py
    ws/
      server.py        # FastAPI app & websocket route
      events.py        # Pydantic event models & error enums
    diff.py            # state diff computation
    serialization.py   # sanitise_state
    comparator.py      # rank comparison (handles inversion)
    errors.py          # error codes
    tests/
      test_shuffle.py
      test_validate.py
      test_effects.py
      test_exchange.py
      test_round_flow.py
      test_bots.py
      test_inversion.py
      test_roles.py
```

---

## 6. Data & State Modeling

### 6.1 Core Dataclasses (`models.py`)

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal

Rank = int | Literal['J','Q','K','A',2,'JOKER']

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

@dataclass
class EffectLogEntry:
    effect: str
    data: dict
    version: int

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
    deck: List[str] = field(default_factory=list)  # remaining undealt (rarely needed post deal)
    discard: List[str] = field(default_factory=list)
    finished_order: List[str] = field(default_factory=list)
    effects_log: List[EffectLogEntry] = field(default_factory=list)
    pending_gift: Optional[dict] = None   # {'count': x, 'player_id': ...}
    pending_discard: Optional[dict] = None
    rule_config: 'RuleConfig' = None  # injected post-creation
```

### 6.2 Card Encoding

Use compact string id: `"<RANK><SUIT>"` where RANK tokens: `3..10,J,Q,K,A,2` and suit: `S,H,D,C`. Jokers: `JOKERa`, `JOKERb`. Keep suit for start detection only.

---

## 7. RuleConfig (`rules.py`)

```python
from pydantic import BaseModel, Field

class RuleConfig(BaseModel):
    use_jokers: bool = True
    max_players: int = 5
    min_players: int = 2
    enable_bots: bool = True
```

(Default covers custom variant; additional toggles can be added later.) Enforce `2 <= min_players <= max_players <= 5`.

---

## 8. Rank Comparator (`comparator.py`)

```python
NORMAL_ORDER = [3,4,5,6,7,8,9,10,'J','Q','K','A',2,'JOKER']
INVERTED_ORDER = list(reversed(NORMAL_ORDER))

def order(inversion: bool):
    return INVERTED_ORDER if inversion else NORMAL_ORDER

def compare(rank_a, rank_b, inversion: bool) -> int:
    o = order(inversion)
    return o.index(rank_a) - o.index(rank_b)
```

Provide helper `is_higher(a,b,inversion)`.

---

## 9. Pattern Validation (`validate.py`)

Responsibilities:

1. Confirm player owns all proposed cards.
2. Uniform rank (except pure Joker set).
3. Determine `count` and `rank`.
4. If starting new trick (no current\_rank): auto-accept.
5. Else require same `count` and strictly higher rank (respect inversion) **unless** inversion rules after Jack apply (only lower pre-Jack ranks allowed). Maintain flag capturing if inversion active *within* same trick.
6. Apply special effect classification if rank ∈ {7,8,10,'J'}.
7. Return structured result:

```python
{
 'ok': True,
 'pattern': {'rank': rank, 'count': n},
 'effect': 'seven_gift'|'eight_reset'|'ten_discard'|'jack_inversion'|None
}
```

Or error with code + message.

---

## 10. Effects (`effects.py`)

Each effect function mutates a cloned state or returns a delta object for `engine` to apply.

- `apply_seven_gift(state, player_id, count)` sets `pending_gift = {'remaining': count, 'player_id': player_id}`. Client then sends `gift_select` events distributing cards (server validates total).
- `apply_eight_reset(state, player_id)` clears pile (current\_rank/count null), same player retains turn.
- `apply_ten_discard(state, player_id, count)` sets `pending_discard = {'remaining': count, 'player_id': player_id}`. Client chooses discard cards; remove silently.
- `apply_jack_inversion(state)` sets `inversion_active = True` until trick end or Eight reset.

---

## 11. Error Codes (`errors.py`)

`ROOM_FULL, NOT_YOUR_TURN, OWNERSHIP, PATTERN_MISMATCH, RANK_TOO_LOW, EFFECT_PENDING, INVALID_GIFT_DISTRIBUTION, INVALID_DISCARD_SELECTION, ALREADY_PASSED, ACTION_NOT_ALLOWED, INTERNAL`.

---

## 12. Engine API (`engine.py`)

Pure functions (except timestamp):

- `start_round(state, seed=None)` → shuffles, deals, assigns opening turn (player with 3♦) sets phase `play` after optional exchange.
- `play_cards(state, player_id, card_ids)` → validate, apply pattern, queue effect or trick progression.
- `pass_turn(state, player_id)` → mark passed; if trick end conditions met: reset trick & assign new leader; clear inversion flag.
- `submit_gift_distribution(state, player_id, assignments)` → validate counts, transfer cards, clear pending.
- `submit_discard_selection(state, player_id, cards)` → remove & clear pending; clear rank if pile emptied.
- `check_round_end(state)` → if player empties reduce active count, set finished\_order when complete, assign roles (`ranking.py`).
- `prepare_exchange(state)` & `apply_exchange_responses(state)`. Version increment on every mutation.

---

## 13. Exchange Logic (`exchange.py`)

- Identify roles.
- Auto-select best cards from Asshole (2) and Scumbag (1) using default ordering.
- Apply transfers to President & Vice President hands.
- Await their chosen returns via events: `exchange_return` (President) and `exchange_return_vice` (Vice President).
- After both returns processed, proceed to `play` phase. Turn = player with 3♦.

---

## 14. Ranking (`ranking.py`)

On round end produce finish order. Map to titles (see Section 3). For ≤3 players adjust mapping automatically. Store in `finished_order`. Use this for next round exchanges.

---

## 15. Sanitisation (`serialization.py`)

`sanitize_state(state, viewer_id)` returns JSON excluding other players' card identities, only `hand_count`. Include: room id, version, phase, turn, current pattern (rank,count), inversion flag, roles per player, pending effect types (not secret specifics), recent effects (last 5 with anonymised data if revealing hidden info).

---

## 16. Diffing (`diff.py`)

Provide `compute_diff(old, new, viewer_id)` producing list of ops:

```
[{"op":"replace","path":"/turn","value":"p2"}, ...]
```

Only include changed top-level fields or per-player changes (hand\_count, role, passed). If an effect clears pattern include removal op.

---

## 17. WebSocket Protocol (`ws/events.py` & `ws/server.py`)

### 17.1 Inbound Events

| Event                  | Payload                         | Phase            | Notes                                      |
| ---------------------- | ------------------------------- | ---------------- | ------------------------------------------ |
| join                   | room\_id, name (opt bot flag)   | lobby            | create or join                             |
| start                  | —                               | lobby            | transitions to dealing -> exchange or play |
| play                   | cards:[card\_id]                | play             | triggers validation & possible effect      |
| pass                   | —                               | play             | pass action                                |
| gift\_select           | assignments: [{to, cards:[id]}] | pending\_gift    | must sum lengths to required count         |
| discard\_select        | cards:[id]                      | pending\_discard | length ≤ remaining                         |
| exchange\_return       | cards:[id]                      | exchange         | President return 2                         |
| exchange\_return\_vice | cards:[id]                      | exchange         | Vice President return 1                    |
| request\_state         | —                               | any              | resend full sanitized state                |
| chat                   | text                            | any              | broadcast (sanitize length)                |

### 17.2 Outbound Events

| Event        | Payload                |
| ------------ | ---------------------- |
| state\_full  | sanitized state        |
| state\_patch | version, ops:[...]     |
| effect       | {type, data}           |
| error        | {code, message}        |
| chat         | {player\_id, text, ts} |

Use Pydantic models for validation.

---

## 18. Bots (`bots/`)

Implement `choose_action(sanitized_state, player_id)` returning one:

- `{type:'play', cards:[...]}` highest *legal* minimal winning pattern (avoid triggering Ten Discard if large hand unless necessary; prefer shedding many low cards).
- `{type:'pass'}` if no legal or strategic pass (e.g., holding powerful effect combos for later). During pending gift/discard phases bots must respond promptly using deterministic heuristic.

Schedule bot turn after 300–700 ms random delay to simulate thinking.

---

## 19. Testing Strategy (`tests/`)

Use `pytest` + `hypothesis` (optional) for property tests. **Required tests:**

1. Deterministic shuffle with seed returns expected sequence.
2. Validation rejects ownership mismatch.
3. Seven Gift distribution enforce correct totals.
4. Eight Reset gives same player next lead.
5. Ten Discard removes correct number & cannot exceed hand size.
6. Jack Inversion flips ordering & reverts after trick end.
7. Inversion early termination when 3 ends inverted trick.
8. Round role assignment for 3,4,5 player counts.
9. Exchange transfers correct highest cards.
10. President / Vice return correct card counts.
11. Full simulated game (random legal bot plays) ends with all unique roles and invariant checks (sum of all hand + discard + current pile = total deck minus jokers if disabled).
12. No duplicate card ids at any stage.

CI simulation: Run 500 games with a mix of bots/humans (mock) verifying no crashes & invariants hold.

---

## 20. Deployment (Python Service)

1. **Dockerfile** (python:3.12-slim). Install deps (fastapi, uvicorn, pydantic, redis, orjson). Use `--no-cache-dir` and multi-stage if needed.
2. Expose port 8000. Entrypoint: `uvicorn president_engine.ws.server:app --host 0.0.0.0 --port 8000`.
3. Deploy to Fly.io (`fly launch`), set `REDIS_URL` secret (if using persistence).
4. Configure scaling: 1 shared CPU, 256–512MB RAM is fine initially.
5. Add health check endpoint `/healthz` returning `{ "ok": true }`.
6. Record public WSS endpoint (e.g. `wss://president-engine.fly.dev/ws`).

---

## 21. Deployment (Vercel Frontend)

1. Create Next.js project (optional; could be static). Env var: `NEXT_PUBLIC_ENGINE_WS_URL` = Python WSS URL.
2. Simple connection hook: opens websocket, listens for `state_full` then patches for `state_patch`.
3. Provide UI components: Lobby (join, list players), Table (hand, current pile), Effect Modals (gift/discard), Role Badges, Chat.
4. Build & deploy; preview deployments auto-provide test environments.

---

## 22. Security & Fair Play

- Server revalidates *every* play; card ids must exist in player hand.
- Exchange automation for giving *best* cards prevents client manipulation.
- Rate-limit chat messages (e.g. 5 per 10 s) to avoid spam.
- Use per-room asyncio locks to serialize state mutations.

---

## 23. Performance

- Maintain small sanitized state (<3 KB typical) by truncating discard and effect logs.
- Use diff patches after initial sync.
- Avoid O(n^2) scans: maintain per-rank counts in player hand if needed for efficiency (micro-optimization later).

---

## 24. Logging & Monitoring

- Structured logs: `{room, event, player, action, duration_ms}`.
- Sample full sanitized state only on ERROR level (with redaction of card identities except acting player).
- Add metrics: active\_rooms, messages\_per\_minute, average\_turn\_ms.

---

## 25. Invariants (Assert Frequently)

- Total distinct card ids across all player hands + discard + (pile being considered) == 52 (+2 Jokers if enabled).
- No negative card counts.
- A player's `passed` resets after trick end.
- `inversion_active` false outside an active trick.
- `pending_gift` and `pending_discard` mutually exclusive & only during `play` phase.

---

## 26. Error Handling Strategy

On validation failure: send `error` event (code + message) without mutating state/version. Client may re-request state. Internal exceptions: log, send generic `INTERNAL` error, do not leak stack trace to clients.

---

## 27. Cursor Rules File (Embed for Convenience)

Create `.cursor/rules/president-python.mdc` with:

```markdown
---
description: Cursor rules for Python President engine & deployment.
globs:
  - "engine_py/src/president_engine/**"
  - "engine_py/src/president_engine/tests/**"
alwaysApply: true
---
# Core Principles
- All game logic pure & framework agnostic (engine, validate, effects, ranking).
- WebSocket layer only: validate -> lock -> load -> mutate -> diff -> persist -> broadcast.
- Enforce special effects: Seven Gift, Eight Reset, Ten Discard, Jack Inversion exactly as spec.
- Start round: player owning 3♦ leads and may play 1..4 threes.

# Mandatory Steps For New Mutation
1. Add function in engine.py.
2. Update pydantic event model.
3. Add tests covering success + at least one failure.
4. Update diff logic if new state fields appear.

# Testing Requirements
- Keep deterministic seeds for reproducible shuffles.
- Simulation test to ensure invariants hold.

# Security
- Never trust client card ownership claims.
- No revealing other hands.

# Style
- Functions ≤ 60 lines; extract helpers.
- Snake case; dataclasses for state; pydantic for transport.

# Errors
- Use standardized error codes from errors.py; extend tests upon addition.

# Prohibited
- No suits logic beyond start player.
- No mixed-rank sets.
```

---

## 28. Minimal Development Sequence

1. Implement models, rules, comparator, shuffle.
2. Engine: join room, add players, deal, start round, opening lead.
3. Validate singles only; add multi-card sets.
4. Implement pass logic and trick termination.
5. Add special effects progressively (7,8,10,J).
6. Add role assignment & round end detection; exchange phase.
7. Add bots (greedy baseline).
8. Add diffing & websocket broadcasting.
9. Add gift/discard UI modals & exchange UI.
10. Harden with tests & simulations.
11. Deploy Python service; integrate frontend.
12. Optimise & polish UI.

---

## 29. Example WebSocket Handler Skeleton (`ws/server.py` excerpt)

```python
@app.websocket('/ws')
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    ctx = ClientContext(ws)
    try:
        while True:
            raw = await ws.receive_text()
            evt = parse_event(raw)  # pydantic dispatch
            await dispatch_event(ctx, evt)
    except WebSocketDisconnect:
        await handle_disconnect(ctx)
```

---

## 30. Example Play Flow

1. Client sends `play {cards:["7H","7C"]}`.
2. Server validates ownership & pattern (pair 7s) -> effect seven\_gift (count=2).
3. State updated: pending\_gift.remaining=2; broadcast patch.
4. Acting client UI prompts distribution; sends `gift_select {assignments:[{to:"p2",cards:["5D"]},{to:"p3",cards:["9S"]}]}`.
5. Server validates total (2) and ownership, transfers cards, clears pending; next player's turn; broadcasts patch.

---

## 31. Simulation Scenario (Test Fixture Outline)

Write JSON fixture: sequence of events with expected post-conditions (version increments, pattern resets, inversion toggling) to guard regressions across refactors.

---

## 32. Maintenance Checklist

Before merging:

-

---

## 33. Future Extensions (Optional)

- Timed turns (AFK auto-pass)
- Spectator mode (read-only connection)
- Analytics (average round length, effect frequency)
- Additional variants (straight sequences, bombs, revolutions) guarded by new config flags.

---

## 34. Summary

This single markdown file encapsulates **all** required specifications: custom rules, Python architecture, websocket protocol, bots, testing, deployment, and integrated Cursor rules. Treat deviations as changes requiring explicit review. Begin with core engine purity, then layer effects, then protocol & UI. Maintain deterministic, well-tested logic to ensure long-term stability.

Happy building – proceed to scaffold the Python engine now.

