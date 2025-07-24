# President Card Game - Multiplayer Setup

This guide will help you deploy the multiplayer version of the President card game to play with your friends.

## 🎮 Game Overview

The President card game is a strategic card game where players compete to get rid of their cards first. The game includes special effects for certain cards (7s, 8s, 10s, Jacks) and role-based card exchanges between games.

## 🏗️ Architecture

- **Frontend**: Next.js with TypeScript, deployed on Vercel
- **Backend**: FastAPI with WebSocket support, deployed on Koyeb/Railway/Render
- **Real-time Communication**: WebSocket for live game updates

## 🚀 Quick Deployment

### Option 1: Deploy Backend to Koyeb (Recommended)

1. **Deploy the Backend:**
   ```bash
   cd engine_py
   ./deploy.sh
   ```

2. **Deploy to Koyeb:**
   ```bash
   # Install Koyeb CLI
   curl -fsSL https://cli.koyeb.com/install.sh | bash
   
   # Login and deploy
   koyeb login
   koyeb app init president-game-backend --docker president-engine:latest --ports 8000:http --routes /:8000
   ```

3. **Get your backend URL** (e.g., `https://president-game-backend-yourname.koyeb.app`)

### Option 2: Deploy Backend to Railway

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Deploy:**
   ```bash
   cd engine_py
   railway login
   railway init
   railway up
   ```

### Option 3: Deploy Backend to Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set build command: `cd engine_py && pip install -e .`
4. Set start command: `cd engine_py && python -m president_engine.start`
5. Set environment variables:
   - `HOST`: `0.0.0.0`
   - `PORT`: `8000`
   - `PYTHONPATH`: `/opt/render/project/src/engine_py/src`

## 🌐 Deploy Frontend to Vercel

1. **Set up environment variables:**
   - Go to your Vercel project settings
   - Add environment variable: `NEXT_PUBLIC_WS_URL`
   - Set value to your backend WebSocket URL (replace `https://` with `wss://`)

2. **Deploy:**
   ```bash
   cd frontend
   vercel --prod
   ```

## 🎯 How to Play

### Creating a Game

1. **Host creates a room:**
   - Enter your name
   - Click "Create New Room"
   - Share the Room ID with friends

2. **Friends join:**
   - Enter their names
   - Enter the Room ID
   - Click "Join"

3. **Start the game:**
   - Host clicks "Start Game" when ready
   - Game automatically deals cards

### Game Rules

- **Objective**: Get rid of all your cards first
- **First Play**: Must be 3s (whoever has 3♦ goes first)
- **Valid Plays**: Same rank cards (pairs, triplets, etc.)
- **Special Cards**:
  - **7s**: Must gift cards to other players
  - **8s**: Clears the pile, same player continues
  - **10s**: Must discard cards
  - **Jacks**: Inverts rank order
  - **2s/Jokers**: Automatic round win

### Card Exchange (Between Games)

After each game, players exchange cards based on their roles:
- **President** ↔ **Asshole**: Exchange 2 cards
- **Vice President** ↔ **Scumbag**: Exchange 1 card

## 🔧 Development

### Running Locally

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

3. **Set environment variable:**
   ```bash
   # In frontend/.env.local
   NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
   ```

### Project Structure

```
president/
├── engine_py/                 # Backend (FastAPI + WebSocket)
│   ├── src/president_engine/
│   │   ├── engine.py         # Game logic
│   │   ├── websocket_server.py # WebSocket handling
│   │   ├── models.py         # Data models
│   │   └── main.py           # FastAPI app
│   └── Dockerfile            # Container config
├── frontend/                  # Frontend (Next.js)
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── store/           # State management
│   │   └── types/           # TypeScript types
│   └── vercel.json          # Vercel config
└── app.py                    # Original single-player version
```

## 🐛 Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Check if backend is running
   - Verify `NEXT_PUBLIC_WS_URL` is correct
   - Ensure backend supports WebSocket

2. **Game Not Starting**
   - Need at least 3 players
   - Check browser console for errors
   - Verify all players are connected

3. **Cards Not Playing**
   - Check if it's your turn
   - Verify card selection is valid
   - Check game rules for valid plays

### Debug Mode

Enable debug logging by setting environment variables:
```bash
LOG_LEVEL=debug
```

## 📱 Features

- ✅ Real-time multiplayer gameplay
- ✅ Automatic bot players
- ✅ Card exchange between games
- ✅ Special card effects
- ✅ Role-based gameplay
- ✅ Mobile-responsive UI
- ✅ WebSocket reconnection
- ✅ Game state synchronization

## 🎨 Customization

### Adding Bots

Bots are automatically added when you use the "Quick Start" feature. You can also manually add bots by clicking "Add Bot" in the lobby.

### Styling

The frontend uses Tailwind CSS. Customize styles in:
- `frontend/src/app/globals.css`
- Component-specific styles in each component

### Game Rules

Modify game logic in `engine_py/src/president_engine/engine.py`:
- Card effects in `_apply_effect()`
- Validation rules in `validate_play()`
- Role assignment in `_assign_roles_dynamic()`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - feel free to use and modify as needed!

## 🆘 Support

If you encounter issues:
1. Check the troubleshooting section
2. Look at browser console for errors
3. Verify backend logs
4. Create an issue with detailed information

---

**Happy gaming! 🃏** 