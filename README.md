# President Card Game

A full-stack multiplayer President (Asshole) card game implementation with custom rules, special effects, and real-time gameplay.

## Features

### 🎮 Game Features
- **Custom President Variant**: Implements the full specification with unique rules
- **3-5 Players**: Optimal gameplay for 4-5 players
- **Special Card Effects**: 
  - 7s: Gift cards to other players
  - 8s: Reset pile and continue playing
  - 10s: Discard additional cards
  - Jacks: Invert rank ordering
- **Role System**: President, Vice President, Citizen, Scumbag, Asshole
- **Exchange Phase**: Role-based card exchanges between rounds
- **Bot Players**: Intelligent AI opponents with strategic gameplay

### 🏗️ Technical Features
- **Real-time Multiplayer**: WebSocket-based communication
- **Server Authoritative**: All game logic validated server-side
- **Efficient Updates**: JSON Patch-based state synchronization
- **Scalable Architecture**: Microservices design with separate frontend/backend
- **Modern Stack**: Python FastAPI backend, Next.js React frontend

## Architecture

```
┌─────────────────┐    WebSocket     ┌──────────────────┐
│  React Frontend │ ◄─────────────► │ Python Backend   │
│  (Vercel)       │                 │ (Koyeb)          │
└─────────────────┘                 └──────────────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │ Redis (Optional) │
                                    │ (Upstash)        │
                                    └──────────────────┘
```

## Quick Start

### Backend Setup

1. **Install Python Dependencies**:
```bash
cd engine_py
pip install -e .
```

2. **Run the Server**:
```bash
python -m president_engine.ws.server
# Server starts on http://localhost:8000
```

3. **Health Check**:
```bash
curl http://localhost:8000/health
```

### Frontend Setup

1. **Install Node Dependencies**:
```bash
cd frontend
npm install
```

2. **Set Environment Variables**:
```bash
# .env.local
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

3. **Run Development Server**:
```bash
npm run dev
# Frontend available at http://localhost:3000
```

## Game Rules

### Basic Gameplay
1. Players take turns playing card combinations
2. Each play must be higher rank than the previous
3. Players can pass if they cannot or choose not to play
4. Round ends when all but one player pass
5. First to empty hand becomes President, last becomes Asshole

### Special Effects
- **Seven Gift (7s)**: Must gift cards equal to number of 7s played
- **Eight Reset (8s)**: Clear pile, same player continues
- **Ten Discard (10s)**: Must discard additional cards (removed from game)
- **Jack Inversion (Jacks)**: Reverses rank order for remainder of round

### Role System
| Finish Position | Role           | Exchange Next Round                    |
|----------------|----------------|---------------------------------------|
| 1st            | President      | Receives 2 best, returns 2 chosen    |
| 2nd            | Vice President | Receives 1 best, returns 1 chosen    |
| Middle         | Citizen        | No exchange                           |
| 2nd Last       | Scumbag        | Gives 1 best, receives 1 back        |
| Last           | Asshole        | Gives 2 best, receives 2 back        |

## API Reference

### WebSocket Events

#### Inbound (Client → Server)
```typescript
// Join a room
{
  "type": "join",
  "room_id": "game-1",
  "name": "Player Name",
  "is_bot": false
}

// Start game
{
  "type": "start",
  "seed": 12345  // optional
}

// Play cards
{
  "type": "play",
  "cards": ["3D", "3H"]
}

// Pass turn
{
  "type": "pass"
}
```

#### Outbound (Server → Client)
```typescript
// Full state update
{
  "type": "state_full",
  "state": { /* complete game state */ },
  "timestamp": 1640995200
}

// Incremental update
{
  "type": "state_patch",
  "version": 15,
  "ops": [
    {"op": "replace", "path": "/turn", "value": "player-2"}
  ],
  "timestamp": 1640995200
}

// Error response
{
  "type": "error",
  "code": "NOT_YOUR_TURN",
  "message": "It's not your turn",
  "timestamp": 1640995200
}
```

## Deployment

### Backend (Koyeb)

1. **Push to GitHub**:
```bash
git add .
git commit -m "Deploy backend"
git push origin main
```

2. **Deploy on Koyeb**:
   - Connect GitHub repository
   - Set working directory: `engine_py`
   - Use Dockerfile for build
   - Configure health check: `/health`

3. **Environment Variables**:
```bash
LOG_LEVEL=info
MAX_ROOMS=500
CORS_ORIGINS=*
```

### Frontend (Vercel)

1. **Deploy to Vercel**:
```bash
cd frontend
vercel --prod
```

2. **Environment Variables**:
```bash
NEXT_PUBLIC_WS_URL=wss://your-backend.koyeb.app/ws
```

## Testing

### Backend Tests
```bash
cd engine_py
pytest src/president_engine/tests/ -v
```

### Game Simulation
```bash
# Run 100 simulated games
python -m president_engine.tests.simulation --games 100
```

## Development

### Project Structure
```
president/
├── engine_py/                 # Python backend
│   ├── src/president_engine/
│   │   ├── constants.py       # Game constants
│   │   ├── models.py          # Data models
│   │   ├── engine.py          # Core game logic
│   │   ├── effects.py         # Special card effects
│   │   ├── validate.py        # Input validation
│   │   ├── bots/              # AI players
│   │   ├── ws/                # WebSocket server
│   │   └── tests/             # Test suite
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/                  # React frontend
│   ├── src/
│   │   ├── app/               # Next.js app directory
│   │   ├── components/        # React components
│   │   ├── store/             # Zustand state management
│   │   └── types/             # TypeScript definitions
│   ├── package.json
│   └── vercel.json
└── README.md
```

### Code Quality
- **Backend**: Black formatting, Ruff linting, pytest testing
- **Frontend**: ESLint, TypeScript strict mode, Tailwind CSS
- **Architecture**: Clean separation of concerns, pure game logic

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes with tests
4. Run quality checks:
   ```bash
   # Backend
   cd engine_py && black . && ruff . && pytest
   
   # Frontend  
   cd frontend && npm run lint && npm run type-check
   ```
5. Submit a Pull Request

## License

MIT License - see LICENSE file for details.

## Support

- **Issues**: GitHub Issues tracker
- **Discussions**: GitHub Discussions
- **Documentation**: See `president_python_full_spec.md` for complete specification

---

**Built with ❤️ using Python, FastAPI, React, and Next.js** 