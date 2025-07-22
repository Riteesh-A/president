'use client';

import { useGameStore } from '@/store/gameStore';
import { Users, Bot, Play, Copy, CheckCircle2, Plus } from 'lucide-react';
import { useState } from 'react';
import toast from 'react-hot-toast';

interface LobbyProps {
  onAddBot: () => void;
}

export function Lobby({ onAddBot }: LobbyProps) {
  const { gameState, startGame } = useGameStore();
  const [roomIdCopied, setRoomIdCopied] = useState(false);

  if (!gameState) return null;

  const players = Object.values(gameState.players);
  const humanPlayers = players.filter(p => !p.is_bot);
  const botPlayers = players.filter(p => p.is_bot);
  const canStart = players.length >= 3;
  const canAddBots = players.length < 5;

  const copyRoomId = async () => {
    try {
      await navigator.clipboard.writeText(gameState.id);
      setRoomIdCopied(true);
      toast.success('Room ID copied to clipboard!');
      setTimeout(() => setRoomIdCopied(false), 2000);
    } catch (err) {
      toast.error('Failed to copy room ID');
    }
  };

  const handleStartGame = () => {
    startGame();
    toast.success('Starting game...');
  };

  const handleAddBot = () => {
    onAddBot();
    toast.success('Adding bot player...');
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Game Lobby</h1>
          <div className="flex items-center justify-center gap-2 mb-4">
            <span className="text-gray-300">Room ID:</span>
            <code className="bg-black/30 px-3 py-1 rounded-lg text-white font-mono text-lg">
              {gameState.id}
            </code>
            <button
              onClick={copyRoomId}
              className="p-2 bg-blue-500 hover:bg-blue-600 rounded-lg text-white transition-colors"
              title="Copy Room ID"
            >
              {roomIdCopied ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </button>
          </div>
          <p className="text-gray-300">
            Share the room ID with friends to invite them!
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Players List */}
          <div className="bg-black/20 backdrop-blur-sm rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <Users className="h-5 w-5" />
              Players ({players.length}/5)
            </h2>

            <div className="space-y-3">
              {/* Human Players */}
              {humanPlayers.map((player, index) => (
                <div key={player.id} className="flex items-center gap-3 p-3 bg-blue-500/20 rounded-lg">
                  <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center text-white font-bold">
                    {player.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-white">{player.name}</div>
                    <div className="text-sm text-gray-300">
                      {player.connected ? '🟢 Connected' : '🔴 Disconnected'}
                    </div>
                  </div>
                  <div className="text-xs text-gray-400">
                    Seat {player.seat + 1}
                  </div>
                </div>
              ))}

              {/* Bot Players */}
              {botPlayers.map((player, index) => (
                <div key={player.id} className="flex items-center gap-3 p-3 bg-purple-500/20 rounded-lg">
                  <div className="w-10 h-10 bg-purple-500 rounded-full flex items-center justify-center text-white">
                    <Bot className="h-5 w-5" />
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-white">{player.name}</div>
                    <div className="text-sm text-gray-300">🤖 AI Bot</div>
                  </div>
                  <div className="text-xs text-gray-400">
                    Seat {player.seat + 1}
                  </div>
                </div>
              ))}

              {/* Empty Slots */}
              {Array.from({ length: 5 - players.length }).map((_, index) => (
                <div key={`empty-${index}`} className="flex items-center gap-3 p-3 bg-gray-500/20 rounded-lg border-2 border-dashed border-gray-600">
                  <div className="w-10 h-10 bg-gray-600 rounded-full flex items-center justify-center">
                    <Plus className="h-5 w-5 text-gray-400" />
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-gray-400">Waiting for player...</div>
                    <div className="text-sm text-gray-500">Seat {players.length + index + 1}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Game Controls */}
          <div className="bg-black/20 backdrop-blur-sm rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Game Setup</h2>

            <div className="space-y-4">
              {/* Player Count Status */}
              <div className="p-4 bg-gray-500/20 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-300">Player Count:</span>
                  <span className="text-white font-bold">{players.length}/5</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-300 ${
                      players.length >= 3 ? 'bg-green-500' : 'bg-yellow-500'
                    }`}
                    style={{ width: `${(players.length / 5) * 100}%` }}
                  />
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {players.length < 3 ? 'Need at least 3 players' : 'Ready to start!'}
                </div>
              </div>

              {/* Add Bot Button */}
              {canAddBots && (
                <button
                  onClick={handleAddBot}
                  className="w-full bg-purple-500 hover:bg-purple-600 text-white px-4 py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition-colors"
                >
                  <Bot className="h-5 w-5" />
                  Add AI Bot
                </button>
              )}

              {/* Start Game Button */}
              <button
                onClick={handleStartGame}
                disabled={!canStart}
                className="w-full bg-green-500 hover:bg-green-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-4 py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition-colors"
              >
                <Play className="h-5 w-5" />
                {canStart ? 'Start Game' : `Need ${3 - players.length} more player(s)`}
              </button>

              {/* Game Rules Summary */}
              <div className="mt-6 p-4 bg-blue-500/10 rounded-lg">
                <h3 className="text-sm font-medium text-blue-300 mb-2">Quick Rules:</h3>
                <ul className="text-xs text-gray-300 space-y-1">
                  <li>• Play cards higher than the current pile</li>
                  <li>• First to empty hand becomes President</li>
                  <li>• Special effects: 7s (gift), 8s (reset), 10s (discard), Jacks (invert)</li>
                  <li>• 3-5 players supported</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 