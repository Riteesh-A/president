'use client';

import { useState } from 'react';
import { useGameStore } from '@/store/gameStore';
import { Bot, Play, Users, Gamepad2 } from 'lucide-react';
import { ConnectionState } from '@/types/game';

interface QuickStartInterfaceProps {
  connectionState: ConnectionState;
  onConnect: () => void;
  wsUrl: string;
}

export function QuickStartInterface({ 
  connectionState, 
  onConnect, 
  wsUrl 
}: QuickStartInterfaceProps) {
  const { joinRoom } = useGameStore();
  const [playerName, setPlayerName] = useState('');
  const [roomId, setRoomId] = useState('game-1');

  const handleQuickStartVsBots = () => {
    if (playerName && roomId) {
      // Join as human player
      joinRoom(roomId, playerName);
      
      // Add 3 bots after a short delay
      setTimeout(() => {
        joinRoom(roomId, 'Bot Alice', true);
        setTimeout(() => joinRoom(roomId, 'Bot Bob', true), 200);
        setTimeout(() => joinRoom(roomId, 'Bot Charlie', true), 400);
      }, 500);
    }
  };

  const handleJoinRoom = () => {
    if (playerName && roomId) {
      joinRoom(roomId, playerName);
    }
  };

  if (connectionState.status !== 'connected') {
    return (
      <div className="text-center py-12">
        <div className="card p-8 max-w-md">
          <h2 className="text-xl font-semibold mb-4">Welcome to President!</h2>
          <p className="text-gray-600 mb-6">
            Connect to the game server to start playing.
          </p>
          {connectionState.status === 'disconnected' && (
            <button
              onClick={onConnect}
              className="btn-primary"
              disabled={!wsUrl}
            >
              Connect to Game
            </button>
          )}
          {connectionState.status === 'connecting' && (
            <div className="text-yellow-600">Connecting...</div>
          )}
          {connectionState.status === 'error' && (
            <div>
              <div className="text-red-600 mb-4">Connection failed</div>
              <button onClick={onConnect} className="btn-primary">
                Retry Connection
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="py-8 max-w-2xl mx-auto space-y-6">
      {/* Hero Section */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold mb-2">Ready to Play President?</h2>
        <p className="text-gray-600">Choose your game mode below</p>
      </div>

      {/* Quick Start vs Bots - Most Prominent */}
      <div className="card p-8 border-2 border-green-300 bg-gradient-to-br from-green-50 to-emerald-50">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
            <Bot className="h-8 w-8 text-green-600" />
          </div>
          <h3 className="text-2xl font-bold text-green-800 mb-2">Play vs AI Bots</h3>
          <p className="text-green-700">
            Jump straight into the action with intelligent AI opponents!
          </p>
        </div>

        <div className="space-y-4 max-w-md mx-auto">
          <div>
            <label className="block text-sm font-medium mb-1 text-green-800">Your Name</label>
            <input
              type="text"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              className="input"
              placeholder="Enter your name"
              maxLength={20}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1 text-green-800">Room ID (optional)</label>
            <input
              type="text"
              value={roomId}
              onChange={(e) => setRoomId(e.target.value)}
              className="input"
              placeholder="game-1"
            />
          </div>

          <button
            onClick={handleQuickStartVsBots}
            disabled={!playerName}
            className="btn-primary w-full text-lg py-3"
          >
            <Gamepad2 className="h-5 w-5 mr-2" />
            Start Game vs 3 AI Bots
          </button>

          <div className="text-center text-sm text-green-700">
            <p>🤖 Instantly creates a 4-player game with strategic AI</p>
            <p>⚡ Perfect for learning or solo practice</p>
          </div>
        </div>
      </div>

      {/* Manual Join Option */}
      <div className="card p-6">
        <div className="text-center mb-4">
          <Users className="h-8 w-8 text-blue-600 mx-auto mb-2" />
          <h3 className="text-xl font-semibold">Join/Create Custom Room</h3>
          <p className="text-gray-600 text-sm">
            Join an existing room or create one to invite friends
          </p>
        </div>

        <div className="max-w-md mx-auto">
          <button
            onClick={handleJoinRoom}
            disabled={!playerName}
            className="btn-secondary w-full"
          >
            <Play className="h-4 w-4 mr-2" />
            Join Room (Add bots manually)
          </button>
        </div>
      </div>

      {/* Game Features */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold mb-4 text-center">Game Features</h3>
        <div className="grid md:grid-cols-2 gap-4 text-sm">
          <div>
            <h4 className="font-medium mb-2">🎮 Gameplay</h4>
            <ul className="space-y-1 text-gray-600">
              <li>• Strategic card combinations</li>
              <li>• Role-based card exchanges</li>
              <li>• Special card effects (7s, 8s, 10s, Jacks)</li>
              <li>• Real-time multiplayer</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium mb-2">🤖 AI Opponents</h4>
            <ul className="space-y-1 text-gray-600">
              <li>• Intelligent decision making</li>
              <li>• Strategic card play</li>
              <li>• Challenging but fair</li>
              <li>• Instant responses</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
} 