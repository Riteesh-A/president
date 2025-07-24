# President Card Game - Multiplayer Edition

A real-time multiplayer version of the classic President card game, built with Next.js and FastAPI.

## 🎮 Play Now

**Frontend**: Deploy to Vercel  
**Backend**: Deploy to Koyeb/Railway/Render

See [MULTIPLAYER_SETUP.md](./MULTIPLAYER_SETUP.md) for detailed deployment instructions.

## 🚀 Quick Start

### 1. Deploy Backend

```bash
cd engine_py
./deploy.sh
```

Choose your deployment platform:
- **Koyeb** (Recommended): `koyeb app init president-game-backend --docker president-engine:latest`
- **Railway**: `railway up`
- **Render**: Create Web Service pointing to Dockerfile

### 2. Deploy Frontend

```bash
cd frontend
vercel --prod
```

Set environment variable `NEXT_PUBLIC_WS_URL` to your backend WebSocket URL.

## 🎯 Features

- ✅ **Real-time multiplayer** - Play with friends anywhere
- ✅ **Automatic bots** - Fill empty slots with AI players
- ✅ **Card exchange** - Role-based card trading between games
- ✅ **Special effects** - 7s, 8s, 10s, Jacks have unique powers
- ✅ **Mobile responsive** - Works on phones and tablets
- ✅ **WebSocket sync** - Live game state updates

## 🎲 Game Rules

**Objective**: Get rid of all your cards first!

- **First Play**: Must be 3s (whoever has 3♦ starts)
- **Valid Plays**: Same rank cards (pairs, triplets, etc.)
- **Special Cards**:
  - **7s**: Gift cards to other players
  - **8s**: Clear the pile, same player continues
  - **10s**: Discard cards
  - **Jacks**: Invert rank order
  - **2s/Jokers**: Automatic round win

**Card Exchange** (between games):
- President ↔ Asshole: Exchange 2 cards
- Vice President ↔ Scumbag: Exchange 1 card

## 🏗️ Architecture

```
Frontend (Next.js + TypeScript)
    ↕ WebSocket
Backend (FastAPI + WebSocket)
    ↕ Game Logic
President Engine (Python)
```

## 🔧 Development

### Local Development

1. **Backend:**
   ```bash
   cd engine_py
   pip install -e .
   python -m president_engine.start
   ```

2. **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Environment:**
   ```bash
   # frontend/.env.local
   NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
   ```

### Project Structure

```
president/
├── engine_py/                 # Backend
│   ├── src/president_engine/
│   │   ├── engine.py         # Game logic
│   │   ├── websocket_server.py # WebSocket handling
│   │   ├── models.py         # Data models
│   │   └── main.py           # FastAPI app
│   └── Dockerfile            # Container config
├── frontend/                  # Frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── store/           # State management
│   │   └── types/           # TypeScript types
│   └── vercel.json          # Vercel config
└── app.py                    # Original single-player version
```

## 🐛 Troubleshooting

- **Connection issues**: Check `NEXT_PUBLIC_WS_URL` environment variable
- **Game not starting**: Need at least 3 players
- **Cards not playing**: Check if it's your turn and valid play

## 📱 Supported Platforms

- **Backend**: Koyeb, Railway, Render, Heroku, DigitalOcean
- **Frontend**: Vercel, Netlify, GitHub Pages
- **Browsers**: Chrome, Firefox, Safari, Edge
- **Devices**: Desktop, tablet, mobile

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - feel free to use and modify!

---

**Ready to play? Check out [MULTIPLAYER_SETUP.md](./MULTIPLAYER_SETUP.md) for deployment instructions! 🃏** 