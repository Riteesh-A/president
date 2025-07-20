'use client';

import { useState, useEffect } from 'react';
import { useGameStore } from '@/store/gameStore';
import { Lobby } from '@/components/Lobby';
import { GameTable } from '@/components/GameTable';
import { ConnectionStatus } from '@/components/ConnectionStatus';
import { QuickStartInterface } from '@/components/QuickStartInterface';

export default function HomePage() {
  const { gameState, connectionState, connect, disconnect } = useGameStore();
  const [wsUrl, setWsUrl] = useState<string>('');

  useEffect(() => {
    // Get WebSocket URL from environment or default to localhost
    const url = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
    setWsUrl(url);
  }, []);

  const handleConnect = () => {
    if (wsUrl) {
      connect(wsUrl);
    }
  };

  const handleDisconnect = () => {
    disconnect();
  };

  return (
    <div className="min-h-screen p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            President Card Game
          </h1>
          <p className="text-lg text-gray-600">
            Multiplayer card game with custom rules and special effects
          </p>
        </header>

        {/* Connection Status */}
        <div className="mb-6">
          <ConnectionStatus
            status={connectionState.status}
            error={connectionState.error}
            onConnect={handleConnect}
            onDisconnect={handleDisconnect}
            wsUrl={wsUrl}
            onWsUrlChange={setWsUrl}
          />
        </div>

        {/* Game Content */}
        <div className="flex justify-center">
          {!gameState ? (
            <QuickStartInterface connectionState={connectionState} onConnect={handleConnect} wsUrl={wsUrl} />
          ) : gameState.phase === 'lobby' ? (
            <Lobby />
          ) : (
            <GameTable />
          )}
        </div>

        {/* Rules Summary */}
        {!gameState && (
          <div className="mt-12 max-w-4xl mx-auto">
            <div className="card p-6">
              <h3 className="text-xl font-semibold mb-4">Game Rules</h3>
              <div className="grid md:grid-cols-2 gap-6 text-sm">
                <div>
                  <h4 className="font-medium mb-2">Basic Rules:</h4>
                  <ul className="space-y-1 text-gray-600">
                    <li>• 3-5 players (optimal: 4-5)</li>
                    <li>• Play higher card combinations</li>
                    <li>• First to empty hand becomes President</li>
                    <li>• Last player becomes Asshole</li>
                    <li>• Exchange cards between rounds</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium mb-2">Special Effects:</h4>
                  <ul className="space-y-1 text-gray-600">
                    <li>• <strong>7s:</strong> Gift cards to other players</li>
                    <li>• <strong>8s:</strong> Reset the pile, play again</li>
                    <li>• <strong>10s:</strong> Discard additional cards</li>
                    <li>• <strong>Jacks:</strong> Invert rank ordering</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 