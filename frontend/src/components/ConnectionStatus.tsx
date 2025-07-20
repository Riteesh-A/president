'use client';

import { useState } from 'react';
import { Wifi, WifiOff, AlertCircle, Loader2 } from 'lucide-react';

interface ConnectionStatusProps {
  status: 'disconnected' | 'connecting' | 'connected' | 'error';
  error?: string;
  onConnect: () => void;
  onDisconnect: () => void;
  wsUrl: string;
  onWsUrlChange: (url: string) => void;
}

export function ConnectionStatus({ 
  status, 
  error, 
  onConnect, 
  onDisconnect, 
  wsUrl, 
  onWsUrlChange 
}: ConnectionStatusProps) {
  const [showSettings, setShowSettings] = useState(false);

  const getStatusColor = () => {
    switch (status) {
      case 'connected': return 'text-green-600';
      case 'connecting': return 'text-yellow-600';
      case 'error': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'connected': 
        return <Wifi className="h-5 w-5" />;
      case 'connecting': 
        return <Loader2 className="h-5 w-5 animate-spin" />;
      case 'error': 
        return <AlertCircle className="h-5 w-5" />;
      default: 
        return <WifiOff className="h-5 w-5" />;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'connected': return 'Connected';
      case 'connecting': return 'Connecting...';
      case 'error': return 'Connection Error';
      default: return 'Disconnected';
    }
  };

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className={getStatusColor()}>
            {getStatusIcon()}
          </div>
          <div>
            <div className="font-medium">{getStatusText()}</div>
            {error && (
              <div className="text-sm text-red-600">{error}</div>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="btn-secondary text-sm"
          >
            Settings
          </button>
          
          {status === 'connected' ? (
            <button onClick={onDisconnect} className="btn-error">
              Disconnect
            </button>
          ) : (
            <button 
              onClick={onConnect} 
              className="btn-primary"
              disabled={!wsUrl || status === 'connecting'}
            >
              Connect
            </button>
          )}
        </div>
      </div>

      {showSettings && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex items-center space-x-2">
            <label className="font-medium text-sm">WebSocket URL:</label>
            <input
              type="text"
              value={wsUrl}
              onChange={(e) => onWsUrlChange(e.target.value)}
              className="input flex-1 text-sm"
              placeholder="ws://localhost:8000/ws"
              disabled={status === 'connected'}
            />
          </div>
        </div>
      )}
    </div>
  );
} 