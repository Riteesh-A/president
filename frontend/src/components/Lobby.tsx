'use client';

import { useState } from 'react';
import { useGameStore } from '@/store/gameStore';
import { Users, Play, Bot, Crown } from 'lucide-react';

export function Lobby() {
  const { gameState, joinRoom, startGame } = useGameStore();
  const [roomId, setRoomId] = useState('game-1');
  const [playerName, setPlayerName] = useState('');
  const [hasJoined, setHasJoined] = useState(false);

  const handleJoinRoom = () => {
    if (roomId && playerName) {
      joinRoom(roomId, playerName);
      setHasJoined(true);
    }
  };

  const handleAddBot = () => {
    if (roomId && gameState && Object.keys(gameState.players).length < (gameState.rules?.max_players || 5)) {
      const botNumber = Object.values(gameState.players).filter(p => p.is_bot).length + 1;
      console.log('Adding bot:', `Bot ${botNumber}`);
      joinRoom(roomId, `Bot ${botNumber}`, true);
    } else {
      console.log('Cannot add bot - room full or no game state');
    }
  };

  const handleQuickStartWithBots = () => {
    if (roomId && playerName) {
      // Join as human player first
      joinRoom(roomId, playerName);
      setHasJoined(true);
      
      // Add bots after a short delay to ensure room is created
      setTimeout(() => {
        // Add 3 bots for a 4-player game
        joinRoom(roomId, 'Bot 1', true);
        setTimeout(() => joinRoom(roomId, 'Bot 2', true), 200);
        setTimeout(() => joinRoom(roomId, 'Bot 3', true), 400);
      }, 500);
    }
  };

  const handleStartGame = () => {
    startGame();
  };

  const canStartGame = gameState && 
    Object.keys(gameState.players).length >= (gameState.rules?.min_players || 3);

  if (!hasJoined && !gameState) {
    return (
      <div className="card p-8 max-w-md">
        <h2 className="text-2xl font-bold mb-6 text-center">Join Game</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Room ID</label>
            <input
              type="text"
              value={roomId}
              onChange={(e) => setRoomId(e.target.value)}
              className="input"
              placeholder="Enter room ID"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Your Name</label>
            <input
              type="text"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              className="input"
              placeholder="Enter your name"
              maxLength={20}
            />
          </div>
          
          <button
            onClick={handleJoinRoom}
            disabled={!roomId || !playerName}
            className="btn-primary w-full"
          >
            Join Room
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">or</span>
            </div>
          </div>

          <button
            onClick={handleQuickStartWithBots}
            disabled={!roomId || !playerName}
            className="btn-secondary w-full flex items-center justify-center"
          >
            <Bot className="h-4 w-4 mr-2" />
            Quick Start vs Bots
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Room Info */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Room: {gameState?.id}</h2>
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <Users className="h-4 w-4" />
            <span>
              {Object.keys(gameState?.players || {}).length} / {gameState?.rules?.max_players || 5} players
            </span>
          </div>
        </div>

        {/* Players List */}
        <div className="space-y-2 mb-6">
          {Object.values(gameState?.players || {})
            .sort((a, b) => a.seat - b.seat)
            .map((player) => (
              <div 
                key={player.id} 
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  <div className="flex items-center space-x-2">
                    {player.is_bot && <Bot className="h-4 w-4 text-blue-500" />}
                    {player.role === 'President' && <Crown className="h-4 w-4 text-yellow-500" />}
                    <span className="font-medium">{player.name}</span>
                  </div>
                  {player.role && (
                    <span className={`role-${player.role.toLowerCase()}`}>
                      {player.role}
                    </span>
                  )}
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-500">Seat {player.seat + 1}</span>
                  <div className={`w-2 h-2 rounded-full ${
                    player.connected ? 'bg-green-500' : 'bg-red-500'
                  }`} />
                </div>
              </div>
            ))}
        </div>

        {/* Game Rules */}
        {gameState?.rules && (
          <div className="mb-6 p-4 bg-blue-50 rounded-lg">
            <h3 className="font-medium mb-2">Game Settings</h3>
            <div className="text-sm text-gray-600 space-y-1">
              <div>Players: {gameState.rules.min_players} - {gameState.rules.max_players}</div>
              <div>Jokers: {gameState.rules.use_jokers ? 'Enabled' : 'Disabled'}</div>
              <div>Bots: {gameState.rules.enable_bots ? '✅ Allowed' : '❌ Not allowed'}</div>
              <div>Phase: {gameState.phase}</div>
              <div>Current players: {Object.keys(gameState.players).length}</div>
            </div>
          </div>
        )}

        {/* Debug Info (remove in production) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mb-4 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
            <h3 className="font-medium text-yellow-800 mb-2">Debug Info</h3>
            <div className="text-xs text-yellow-700 space-y-1">
              <div>Game State: {gameState ? 'Loaded' : 'Not loaded'}</div>
              <div>Rules: {gameState?.rules ? 'Loaded' : 'Not loaded'}</div>
              <div>Bot Support: {gameState?.rules?.enable_bots ? 'Yes' : 'No'}</div>
              <div>Player Count: {Object.keys(gameState?.players || {}).length}</div>
              <div>Bot Count: {Object.values(gameState?.players || {}).filter(p => p.is_bot).length}</div>
            </div>
          </div>
        )}

        {/* Bot Controls */}
        {gameState?.rules?.enable_bots && (
          <div className="mb-4 p-4 bg-green-50 rounded-lg border border-green-200">
            <h3 className="font-medium mb-2 text-green-800">Play with AI Bots</h3>
            <p className="text-sm text-green-700 mb-3">
              Add AI opponents to play immediately! Bots will make strategic moves and provide a challenging game.
            </p>
            <div className="flex space-x-2">
              <button
                onClick={handleAddBot}
                disabled={Object.keys(gameState?.players || {}).length >= (gameState?.rules?.max_players || 5)}
                className="btn-secondary"
              >
                <Bot className="h-4 w-4 mr-2" />
                Add Bot
              </button>
              {Object.keys(gameState?.players || {}).length === 1 && (
                <button
                  onClick={() => {
                    // Add multiple bots for quick 4-player game
                    handleAddBot();
                    setTimeout(() => handleAddBot(), 200);
                    setTimeout(() => handleAddBot(), 400);
                  }}
                  className="btn-secondary"
                >
                  <Bot className="h-4 w-4 mr-2" />
                  Add 3 Bots
                </button>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex space-x-3">
          <button
            onClick={handleStartGame}
            disabled={!canStartGame}
            className="btn-primary flex-1"
          >
            <Play className="h-4 w-4 mr-2" />
            Start Game
            {!canStartGame && (
              <span className="ml-2 text-xs">
                (Need {(gameState?.rules?.min_players || 3) - Object.keys(gameState?.players || {}).length} more players)
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Instructions */}
      <div className="card p-4">
        <h3 className="font-medium mb-2">How to Play</h3>
        <div className="text-sm text-gray-600 space-y-1">
          <p>• Play higher card combinations than the previous player</p>
          <p>• Special effects: 7s (gift), 8s (reset), 10s (discard), Jacks (invert)</p>
          <p>• First to empty hand becomes President, last becomes Asshole</p>
          <p>• Exchange cards between rounds based on roles</p>
        </div>
        
        <div className="mt-4 p-3 bg-purple-50 rounded-lg border border-purple-200">
          <h4 className="font-medium text-purple-800 mb-1">Playing with Bots</h4>
          <div className="text-xs text-purple-700 space-y-1">
            <p>🤖 Use "Quick Start vs Bots" to instantly play against AI</p>
            <p>🎯 Or manually add bots one by one in the lobby</p>
            <p>🧠 Bots use strategic thinking and provide challenging gameplay</p>
            <p>⚡ Perfect for solo practice or when friends aren't available</p>
          </div>
        </div>
      </div>
    </div>
  );
} 