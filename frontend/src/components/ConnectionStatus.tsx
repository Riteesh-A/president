'use client';

import { useGameStore } from '@/store/gameStore';
import { Wifi, WifiOff, AlertCircle, Loader } from 'lucide-react';

export function ConnectionStatus() {
  const { connectionState, gameState } = useGameStore();

  const getStatusIcon = () => {
    switch (connectionState.status) {
      case 'connected':
        return <Wifi className="h-4 w-4 text-green-400" />;
      case 'connecting':
        return <Loader className="h-4 w-4 text-yellow-400 animate-spin" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-400" />;
      default:
        return <WifiOff className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusText = () => {
    switch (connectionState.status) {
      case 'connected':
        return gameState ? `Connected • Room ${gameState.id}` : 'Connected';
      case 'connecting':
        return 'Connecting...';
      case 'error':
        return `Error: ${connectionState.error || 'Connection failed'}`;
      default:
        return 'Disconnected';
    }
  };

  const getStatusColor = () => {
    switch (connectionState.status) {
      case 'connected':
        return 'bg-green-500/20 border-green-500/30 text-green-300';
      case 'connecting':
        return 'bg-yellow-500/20 border-yellow-500/30 text-yellow-300';
      case 'error':
        return 'bg-red-500/20 border-red-500/30 text-red-300';
      default:
        return 'bg-gray-500/20 border-gray-500/30 text-gray-300';
    }
  };

  // Only show if there's a connection issue or we're in a game
  if (connectionState.status === 'connected' && !gameState) {
    return null;
  }

  return (
    <div className="fixed top-4 right-4 z-50">
      <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border backdrop-blur-sm ${getStatusColor()}`}>
        {getStatusIcon()}
        <span className="text-sm font-medium">{getStatusText()}</span>
      </div>
    </div>
  );
} 