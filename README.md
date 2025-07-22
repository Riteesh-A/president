# President Card Game

A real-time multiplayer implementation of the President card game with WebSocket support, AI bots, and modern web UI.

## Features

- 🌐 **Real-time Multiplayer**: Play with friends using WebSocket connections
- 🤖 **AI Bots**: Practice against intelligent AI opponents
- 🎯 **Complete Game Logic**: All President rules implemented including special effects
- 📱 **Responsive UI**: Beautiful, modern interface built with Next.js and Tailwind CSS
- ⚡ **Fast & Scalable**: FastAPI backend with async WebSocket handling
- 🚀 **Easy Deployment**: Ready for Vercel (frontend) and Koyeb (backend)

## Game Rules

President is a card climbing game where players try to get rid of all their cards:

- **Objective**: Be the first to empty your hand to become President
- **Ranking**: President → Vice President → Citizen → Scumbag → Asshole
- **Playing**: Play higher card combinations than the previous player
- **Special Effects**:
  - **7s**: Gift cards to other players
  - **8s**: Reset the pile, continue playing
  - **10s**: Discard additional cards
  - **Jacks**: Invert rank ordering (low beats high)

## Quick Start

### Local Development

1. **Start the Backend**:
```bash
cd engine_py
pip install -e .
python -m uvicorn src.president_engine.main:app --reload --host 0.0.0.0 --port 8000
```

2. **Start the Frontend**:
```bash
cd frontend
npm install
npm run dev
```

3. **Play**: Open http://localhost:3000 and start a game!

### Deploy to Production

#### Backend (Koyeb)

1. **Push to GitHub**: Ensure your code is in a GitHub repository
2. **Connect Koyeb**: Link your GitHub repo to Koyeb
3. **Deploy**: Koyeb will use the `koyeb.yaml` configuration
4. **Get URL**: Note your deployed backend URL (e.g., `https://your-app.koyeb.app`)

#### Frontend (Vercel)

1. **Connect Repository**: Link your GitHub repo to Vercel
2. **Set Environment Variable**:
   ```
   NEXT_PUBLIC_WS_URL=wss://your-backend-url.com/ws
   ```
3. **Deploy**: Vercel will build and deploy automatically
4. **Play**: Share your Vercel URL with friends!

## Project Structure

```
president/
├── engine_py/                 # FastAPI backend
│   ├── src/president_engine/
│   │   ├── main.py           # FastAPI app
│   │   ├── engine.py         # Game logic (from app.py)
│   │   ├── websocket_server.py # WebSocket handling
│   │   ├── models.py         # Data structures
│   │   ├── bots.py           # AI logic
│   │   └── constants.py      # Game constants
│   ├── Dockerfile
│   ├── koyeb.yaml           # Deployment config
│   └── pyproject.toml
├── frontend/                # Next.js frontend
│   ├── src/
│   │   ├── app/page.tsx     # Main game interface
│   │   ├── components/      # UI components
│   │   ├── store/          # Game state management
│   │   └── types/          # TypeScript types
│   ├── vercel.json         # Deployment config
│   └── package.json
└── app.py                  # Original Dash implementation
```

## API Endpoints

- `GET /`: API info
- `GET /health`: Health check
- `WebSocket /ws`: Game connection
- `WebSocket /ws/{player_id}`: Game connection with player ID

## WebSocket Events

### Client → Server
- `join`: Join/create room
- `start`: Start game
- `play`: Play cards
- `pass`: Pass turn
- `gift_select`: Distribute gifts
- `discard_select`: Discard cards

### Server → Client
- `join_success`: Successfully joined
- `state_full`: Complete game state
- `error`: Error message

## Environment Variables

### Backend
- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)
- `LOG_LEVEL`: Logging level (default: info)

### Frontend
- `NEXT_PUBLIC_WS_URL`: WebSocket backend URL

## Technology Stack

- **Backend**: Python 3.12, FastAPI, WebSockets, Uvicorn
- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS
- **State Management**: Zustand
- **Deployment**: Koyeb (backend), Vercel (frontend)

## Development

### Backend Development
```bash
cd engine_py
pip install -e ".[dev]"
python -m pytest                    # Run tests
black src/                          # Format code
ruff check src/                     # Lint code
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev                         # Development server
npm run build                       # Production build
npm run lint                        # Lint code
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

---

**Ready to play?** Deploy your own instance and challenge your friends to a game of President! 🃏👑 