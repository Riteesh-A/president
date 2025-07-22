'use client';

import { useState } from 'react';

interface QuickStartInterfaceProps {
  onQuickStart: (playerName: string) => void;
}

export function QuickStartInterface({ onQuickStart }: QuickStartInterfaceProps) {
  const [playerName, setPlayerName] = useState('');

  const handleQuickStart = () => {
    if (!playerName.trim()) {
      return;
    }
    onQuickStart(playerName.trim());
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleQuickStart();
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-gray-300 text-sm">
        Start a game instantly with AI bots for practice
      </p>
      
      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Your Name
          </label>
          <input
            type="text"
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter your name"
            className="w-full px-3 py-2 bg-black/30 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
            maxLength={16}
          />
        </div>

        <button
          onClick={handleQuickStart}
          disabled={!playerName.trim()}
          className="w-full bg-orange-500 hover:bg-orange-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium transition-colors"
        >
          🚀 Start with Bots
        </button>
      </div>

      <div className="text-xs text-gray-400 space-y-1">
        <p>• Instant game with 3 AI opponents</p>
        <p>• Perfect for learning the rules</p>
        <p>• Same game logic as multiplayer</p>
      </div>
    </div>
  );
} 