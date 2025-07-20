# Multiplayer President (Custom Variant) – Python Implementation & Cursor Rules

**Status:** Authoritative single-source specification for implementing the custom President card game variant entirely with a **Python engine** plus a lightweight web client deployed on **Vercel**, with realtime served by a persistent Python service. Use this document for all development, code generation (Cursor), reviews, and onboarding. 

---

## 1. Vision & Objectives

1. Fast, fair, deterministic online play of a customised President (a.k.a. Asshole) variant for **3–5 players (max 5)** with optional bots. Optimal player count: 4–5.
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
Koyeb Web Service (FastAPI + WebSocket)
        |  (Optional: Redis for persistence)
        v
   Upstash Redis (Serverless Redis)
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

If **3 players**: Roles simplified (President, Vice President, Asshole; no Scumbag). If **4 players**: President, Vice President, Scumbag, Asshole (no Citizens). If **5 players**: All roles as table above with exactly one Citizen.

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
| 8 (x eights)   | Eight Reset    | Pile is cleared (discard current round). The player who played the 8s **immediately starts a new round**, the current pile is discarded the and round starts again.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 10 (x tens)    | Ten Discard    | Player must **discard x additional cards** (of any ranks) face down into discard pile (not visible). Those cards leave the game for the entirety of the game. (If hand has < x cards, discard all remaining.) Turn then ends; next player continues over a cleared pile (new round started by next player).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| J (x jacks)    | Jack Inversion | Immediately **invert rank ordering** for the remainder of the *current round cycle* until the round ends (i.e., until a reset by Eight or round completion by passes). During inversion: ordering becomes reversed: `JACK,10,9,8,...,4,3` descending considered lowest→highest reversed. **Additional Rule:** After inversion begins, the *next player may only play ranks strictly lower than Jack under normal ordering*, i.e. in inverted ordering they must play a card that would have been *lower* pre-inversion. Practical simplification: After a Jack play, only lower pre-Jack ranks are legal (10 downward). **If a 3 is played while inversion is active and all other players pass**, the round ends (accelerated termination). After the round ends (normal completion), ordering reverts to default. |

Clarifications:

- Effects stack only sequentially; an Eight reset clears inversion if active (since round ended).
- Seven Gift & Ten Discard actions are *mandatory* auxiliary phases and must complete before advancing turn.

### 4.6 Passing & Round End

- A player may pass instead of playing a higher pattern.
- Round ends when all *active* players except the last one to have played have passed consecutively.
- After round end (or Eight Reset), last successful player leads new round (unless effect states otherwise).

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
6. Start round: On the very first game in the session, the player with 3♦ leads as per Opening Play. (If 3♦ traded during exchange, still opening anchor is whoever **currently holds** it.). For all subsequent games, the Asshole begins the round.

Edge cases: If players have fewer cards than required to give (rare with standard deck unless altered future variants) they give all available.

### 4.9 Jokers

- If `use_jokers = true`, Jokers are treated as any other rank. So a Joker is higher than a 2 in rank order (for the Scumbag and Asshole to give to the Vice President and President respectively), but can be used as any value in a set. For example, a Joker can be used as a 3, 4, 5, 6, 7, 8, 9, 10, Jack, Queen, King, or Ace. So a player can play 2, Joker (which equates to a pair of 2s) on top of a Ace pair and win the round. The same applies to any other value. A Joker can also be played individually as a single card with any other rank. So a player can play a Joker pair or 2,Joker together on top of an Ace pair (where its value is higher than the Ace, therefore 2) and win the round.

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
    min_players: int = 3
    enable_bots: bool = True
```

(Default covers custom variant; additional toggles can be added later.) Enforce `3 <= min_players <= max_players <= 5`.

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
4. If starting new round (no current\_rank): auto-accept.
5. Else require same `count` and strictly higher rank (respect inversion) **unless** inversion rules after Jack apply (only lower pre-Jack ranks allowed). Maintain flag capturing if inversion active *within* same round.
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
- `apply_jack_inversion(state)` sets `inversion_active = True` until round end or Eight reset.

---

## 11. Error Codes (`errors.py`)

`ROOM_FULL, NOT_YOUR_TURN, OWNERSHIP, PATTERN_MISMATCH, RANK_TOO_LOW, EFFECT_PENDING, INVALID_GIFT_DISTRIBUTION, INVALID_DISCARD_SELECTION, ALREADY_PASSED, ACTION_NOT_ALLOWED, INTERNAL`.

---

## 12. Engine API (`engine.py`)

Pure functions (except timestamp):

- `start_round(state, seed=None)` → shuffles, deals, assigns opening turn (player with 3♦) sets phase `play` after optional exchange.
- `play_cards(state, player_id, card_ids)` → validate, apply pattern, queue effect or round progression.
- `pass_turn(state, player_id)` → mark passed; if round end conditions met: reset round & assign new leader; clear inversion flag.
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
6. Jack Inversion flips ordering & reverts after round end.
7. Inversion early termination when 3 ends inverted round.
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
- A player's `passed` resets after round end.
- `inversion_active` false outside an active round.
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
4. Implement pass logic and round termination.
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

## Validation & Architectural Improvements for Koyeb Deployment

After reviewing your comprehensive President game specification, I can provide validation and specific improvements for deploying on Koyeb's free tier.

### ✅ **Current Architecture Validation**

The specification is well-structured with several strengths:
- **Separation of concerns**: Python engine + lightweight web client
- **Framework-agnostic engine**: Pure game logic separate from transport
- **Comprehensive rule specification**: Custom variant clearly defined
- **Testing strategy**: Good coverage of edge cases and invariants

### 🚀 **Improved Architecture for Koyeb**

Here's an enhanced architecture specifically optimized for Koyeb:

```
Browser (React/Next.js on Vercel)
        |  (WSS JSON protocol)
        v
Koyeb Web Service (FastAPI + WebSocket)
        |  (Optional: Redis for persistence)
        v
   Upstash Redis (Serverless Redis)
```

### **Key Improvements for Koyeb Deployment**

#### 1. **Leverage Koyeb's Autoscaling**
```python
# In ws/server.py - Enhanced for Koyeb
import os
import signal
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="President Game Engine")

# Add CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.vercel.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def main():
    port = int(os.environ.get("PORT", "8000"))
    # Koyeb provides PORT env variable
    
    # Health check endpoint for Koyeb
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "1.0.0"}
    
    # Graceful shutdown for Koyeb's SIGTERM
    def signal_handler():
        print("Received shutdown signal")
        # Clean up active games, notify clients
        
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
    
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=port,
        access_log=True,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()
```

#### 2. **Enhanced State Management with Persistence**
```python
# In storage/koyeb_store.py
from typing import Optional
import os
import json
import redis.asyncio as redis

class KoyebStateStore:
    def __init__(self):
        # Use Upstash Redis for persistence
        redis_url = os.environ.get("REDIS_URL")
        self.redis = redis.from_url(redis_url) if redis_url else None
        self.memory_store = {}  # Fallback to memory
        
    async def save_room(self, room_id: str, state: RoomState):
        serialized = self._serialize_state(state)
        
        if self.redis:
            await self.redis.setex(
                f"room:{room_id}", 
                3600,  # 1 hour TTL
                serialized
            )
        else:
            self.memory_store[room_id] = serialized
            
    async def load_room(self, room_id: str) -> Optional[RoomState]:
        if self.redis:
            data = await self.redis.get(f"room:{room_id}")
        else:
            data = self.memory_store.get(room_id)
            
        return self._deserialize_state(data) if data else None
        
    async def cleanup_expired(self):
        """Koyeb autoscaling cleanup"""
        if not self.redis:
            # Clean memory store
            current_time = time.time()
            expired = [
                k for k, v in self.memory_store.items() 
                if current_time - v.get('last_activity', 0) > 3600
            ]
            for key in expired:
                del self.memory_store[key]
```

#### 3. **Optimized Deployment Configuration**

**Dockerfile** (optimized for Koyeb):
```dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port (Koyeb will override with PORT env var)
EXPOSE 8000

# Run the application
CMD ["python", "-m", "president_engine.ws.server"]
```

**requirements.txt**:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
pydantic==2.5.0
redis[hiredis]==5.0.1
orjson==3.9.10
python-multipart==0.0.6
```

#### 4. **Environment-Based Configuration**
```python
# In config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Koyeb provides these automatically
    port: int = int(os.environ.get("PORT", "8000"))
    host: str = "0.0.0.0"
    
    # Optional Redis for persistence
    redis_url: str = os.environ.get("REDIS_URL", "")
    
    # CORS settings for Vercel
    allowed_origins: list[str] = [
        "https://*.vercel.app",
        "http://localhost:3000",
        "http://localhost:8000"
    ]
    
    # Game settings
    max_rooms: int = int(os.environ.get("MAX_ROOMS", "1000"))
    room_ttl: int = int(os.environ.get("ROOM_TTL", "3600"))
    
    # Logging
    log_level: str = os.environ.get("LOG_LEVEL", "info")
    
    class Config:
        env_file = ".env"

settings = Settings()
```

#### 5. **Koyeb-Specific Deployment Files**

**koyeb.yaml** (Infrastructure as Code):
```yaml
services:
  - name: president-engine
    git:
      repository: github.com/yourusername/president-engine
      branch: main
    build:
      buildpack: docker
    instance:
      type: free
    ports:
      - port: 8000
        protocol: http
    health_checks:
      - path: /health
        port: 8000
        protocol: http
    scaling:
      min: 0  # Scale to zero when not in use
      max: 1  # Free tier limit
    env:
      - name: LOG_LEVEL
        value: info
      - name: MAX_ROOMS
        value: "500"
      # Add REDIS_URL as secret if using persistence
```

#### 6. **Enhanced WebSocket Handler with Connection Management**
```python
# In ws/server.py
import asyncio
from collections import defaultdict
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, set[WebSocket]] = defaultdict(set)
        self.connection_rooms: dict[WebSocket, str] = {}
        
    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        self.active_connections[room_id].add(websocket)
        self.connection_rooms[websocket] = room_id
        
    def disconnect(self, websocket: WebSocket):
        room_id = self.connection_rooms.pop(websocket, None)
        if room_id:
            self.active_connections[room_id].discard(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
                
    async def broadcast_to_room(self, room_id: str, message: str):
        connections = self.active_connections.get(room_id, set()).copy()
        if connections:
            await asyncio.gather(
                *[self._send_safe(conn, message) for conn in connections],
                return_exceptions=True
            )
            
    async def _send_safe(self, websocket: WebSocket, message: str):
        try:
            await websocket.send_text(message)
        except:
            # Connection closed, clean up
            self.disconnect(websocket)

manager = ConnectionManager()

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            await handle_message(room_id, websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # Handle player disconnect logic
        await handle_player_disconnect(room_id, websocket)
```

### **Deployment Advantages with Koyeb**

1. **Cost Efficiency**: Free tier supports your use case perfectly
2. **Zero Configuration**: Built-in HTTPS, global CDN, autoscaling
3. **Scale to Zero**: No costs when not in use
4. **Fast Cold Starts**: Typically <1s boot time
5. **Global Edge**: Reduced latency worldwide
6. **Built-in Monitoring**: Logs, metrics, and alerts included

### **Recommended Deployment Steps**

1. **Prepare Repository**:
   ```bash
   git init
   git add .
   git commit -m "Initial President game implementation"
   git push origin main
   ```

2. **Deploy to Koyeb**:
   - Connect GitHub repository
   - Set run command: `python -m president_engine.ws.server`
   - Configure health check: `/health`
   - Enable autoscaling (0-1 instances for free tier)

3. **Configure Frontend** (Vercel):
   ```env
   NEXT_PUBLIC_WS_URL=wss://your-app.koyeb.app
   ```

### **Production Readiness Enhancements**

- **Rate Limiting**: Built into Koyeb
- **Monitoring**: Use Koyeb's built-in metrics
- **Logging**: Structured JSON logs for better debugging
- **Error Tracking**: Integration with Sentry/monitoring services
- **Performance**: Connection pooling and efficient JSON serialization

This architecture leverages Koyeb's strengths while maintaining your game's requirements. The autoscaling ensures cost-effectiveness, while the global edge network provides excellent performance for your multiplayer game.

