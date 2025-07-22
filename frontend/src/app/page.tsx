'use client';

import { useState, useEffect } from 'react';
import { useGameStore } from '@/store/gameStore';
import { ConnectionStatus } from '@/components/ConnectionStatus';
import { Lobby } from '@/components/Lobby';
import { GameTable } from '@/components/GameTable';
import { QuickStartInterface } from '@/components/QuickStartInterface';
import toast, { Toaster } from 'react-hot-toast';

export default function Home() {
  const { gameState, connectionState, connect, disconnect, joinRoom } = useGameStore();
  const [playerName, setPlayerName] = useState('');
  const [roomId, setRoomId] = useState('');
  const [isConnecting, setIsConnecting] = useState(false);

  useEffect(() => {
    // Auto-connect on mount
    if (connectionState.status === 'disconnected') {
      handleConnect();
    }
  }, []);

  const handleConnect = async () => {
    setIsConnecting(true);
    try {
      // Use environment variable for WebSocket URL or fallback to localhost
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
      connect(wsUrl);
      toast.success('Connecting to game server...');
    } catch (error) {
      toast.error('Failed to connect to game server');
    } finally {
      setIsConnecting(false);
    }
  };

  const handleCreateRoom = () => {
    if (!playerName.trim()) {
      toast.error('Please enter your name');
      return;
    }
    // Join with empty room_id to create new room
    joinRoom('', playerName.trim());
  };

  const handleJoinRoom = () => {
    if (!playerName.trim()) {
      toast.error('Please enter your name');
      return;
    }
    if (!roomId.trim()) {
      toast.error('Please enter room ID');
      return;
    }
    joinRoom(roomId.trim().toUpperCase(), playerName.trim());
  };

  const handleQuickStart = (name: string) => {
    setPlayerName(name);
    // Create room and add bots
    joinRoom('', name);
  };

  const addBot = () => {
    const botNames = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'];
    const existingBots = gameState?.players ? Object.values(gameState.players).filter(p => p.is_bot).length : 0;
    if (existingBots < botNames.length) {
      const botName = botNames[existingBots];
      joinRoom(gameState?.id || '', botName, true);
    }
  };

  // Render based on game state
  if (connectionState.status === 'connecting' || isConnecting) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-900 via-blue-900 to-purple-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-white mb-4"></div>
          <h2 className="text-white text-xl">Connecting to game server...</h2>
        </div>
        <Toaster position="top-center" />
      </div>
    );
  }

  if (connectionState.status === 'error') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-900 via-purple-900 to-blue-900 flex items-center justify-center">
        <div className="text-center bg-black/20 backdrop-blur-sm rounded-lg p-8">
          <h2 className="text-white text-xl mb-4">Connection Failed</h2>
          <p className="text-gray-300 mb-4">{connectionState.error}</p>
          <button 
            onClick={handleConnect}
            className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg"
          >
            Retry Connection
          </button>
        </div>
        <Toaster position="top-center" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-900 via-blue-900 to-purple-900">
      <ConnectionStatus />
      
      {!gameState ? (
        // Lobby/Join screen
        <div className="container mx-auto px-4 py-8">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-white mb-2">President Card Game</h1>
            <p className="text-gray-300">Join a room or start a quick game with bots</p>
          </div>

          <div className="max-w-4xl mx-auto grid md:grid-cols-2 gap-8">
            {/* Multiplayer Section */}
            <div className="bg-black/20 backdrop-blur-sm rounded-lg p-6">
              <h2 className="text-2xl font-semibold text-white mb-4">🌐 Multiplayer</h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Your Name
                  </label>
                  <input
                    type="text"
                    value={playerName}
                    onChange={(e) => setPlayerName(e.target.value)}
                    placeholder="Enter your name"
                    className="w-full px-3 py-2 bg-black/30 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
                    maxLength={16}
                  />
                </div>

                <div className="space-y-2">
                  <button
                    onClick={handleCreateRoom}
                    disabled={!playerName.trim()}
                    className="w-full bg-green-500 hover:bg-green-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium"
                  >
                    🆕 Create New Room
                  </button>

                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={roomId}
                      onChange={(e) => setRoomId(e.target.value.toUpperCase())}
                      placeholder="Room ID"
                      className="flex-1 px-3 py-2 bg-black/30 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
                      maxLength={8}
                    />
                    <button
                      onClick={handleJoinRoom}
                      disabled={!playerName.trim() || !roomId.trim()}
                      className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium"
                    >
                      Join
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Start Section */}
            <div className="bg-black/20 backdrop-blur-sm rounded-lg p-6">
              <h2 className="text-2xl font-semibold text-white mb-4">⚡ Quick Start</h2>
              <QuickStartInterface onQuickStart={handleQuickStart} />
            </div>
          </div>
        </div>
      ) : gameState.phase === 'lobby' ? (
        // In lobby, waiting for players
        <Lobby onAddBot={addBot} />
      ) : (
        // In game
        <GameTable />
      )}

      <Toaster position="top-center" />
    </div>
  );
} 