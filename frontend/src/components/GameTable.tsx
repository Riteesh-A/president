'use client';

import { useGameStore } from '@/store/gameStore';
import { Card } from '@/components/Card';
import { Hand, RotateCcw, SkipForward, Gift } from 'lucide-react';

export function GameTable() {
  const { 
    gameState, 
    selectedCards, 
    playCards, 
    passTurn, 
    selectCard, 
    deselectCard,
    clearSelection 
  } = useGameStore();

  if (!gameState) return null;

  const currentPlayer = Object.values(gameState.players).find(p => p.hand);
  const isMyTurn = gameState.turn === currentPlayer?.id;
  const canPlay = selectedCards.length > 0 && isMyTurn && gameState.phase === 'play';
  const canPass = isMyTurn && gameState.phase === 'play' && gameState.current_pattern.rank;

  const handleCardClick = (cardId: string) => {
    if (selectedCards.includes(cardId)) {
      deselectCard(cardId);
    } else {
      selectCard(cardId);
    }
  };

  const handlePlay = () => {
    if (canPlay) {
      playCards(selectedCards);
    }
  };

  const handlePass = () => {
    if (canPass) {
      passTurn();
    }
  };

  const getCurrentPatternDisplay = () => {
    const { rank, count } = gameState.current_pattern;
    if (!rank || !count) return 'No cards played yet';
    
    const rankDisplay = typeof rank === 'number' ? rank.toString() : rank;
    const plural = count > 1 ? 's' : '';
    return `${count} ${rankDisplay}${plural}`;
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Game Status */}
      <div className="card p-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div>
              <span className="text-sm text-gray-500">Phase:</span>
              <span className="ml-2 font-medium capitalize">{gameState.phase}</span>
            </div>
            
            {gameState.turn && (
              <div>
                <span className="text-sm text-gray-500">Turn:</span>
                <span className="ml-2 font-medium">
                  {gameState.players[gameState.turn]?.name || 'Unknown'}
                </span>
              </div>
            )}
            
            {gameState.inversion_active && (
              <div className="flex items-center text-orange-600">
                <RotateCcw className="h-4 w-4 mr-1" />
                <span className="text-sm font-medium">Rank Inverted</span>
              </div>
            )}
          </div>
          
          <div className="text-right">
            <div className="text-sm text-gray-500">Current Pattern</div>
            <div className="font-medium">{getCurrentPatternDisplay()}</div>
          </div>
        </div>
      </div>

      {/* Players Around Table */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {Object.values(gameState.players)
          .sort((a, b) => a.seat - b.seat)
          .map((player) => (
            <div 
              key={player.id}
              className={`card p-4 ${
                player.id === gameState.turn ? 'ring-2 ring-blue-500' : ''
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span className="font-medium">{player.name}</span>
                  {player.is_bot && (
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      Bot
                    </span>
                  )}
                </div>
                
                {player.role && (
                  <span className={`role-${player.role.toLowerCase()}`}>
                    {player.role}
                  </span>
                )}
              </div>
              
              <div className="flex items-center justify-between text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <Hand className="h-4 w-4" />
                  <span>{player.hand_count} cards</span>
                </div>
                
                <div className="flex items-center space-x-2">
                  {player.passed && (
                    <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                      Passed
                    </span>
                  )}
                  <div className={`w-2 h-2 rounded-full ${
                    player.connected ? 'bg-green-500' : 'bg-red-500'
                  }`} />
                </div>
              </div>
            </div>
          ))}
      </div>

      {/* Player's Hand */}
      {currentPlayer?.hand && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium">Your Hand</h3>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-500">
                {selectedCards.length} selected
              </span>
              {selectedCards.length > 0 && (
                <button 
                  onClick={clearSelection}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
          
          {/* Cards */}
          <div className="flex flex-wrap gap-2 mb-4">
            {currentPlayer.hand.map((cardId) => (
              <Card
                key={cardId}
                cardId={cardId}
                selected={selectedCards.includes(cardId)}
                onClick={() => handleCardClick(cardId)}
                disabled={!isMyTurn || gameState.phase !== 'play'}
              />
            ))}
          </div>
          
          {/* Actions */}
          <div className="flex items-center space-x-3">
            <button
              onClick={handlePlay}
              disabled={!canPlay}
              className={canPlay ? 'btn-primary' : 'btn-disabled'}
            >
              Play {selectedCards.length} Card{selectedCards.length !== 1 ? 's' : ''}
            </button>
            
            {canPass && (
              <button onClick={handlePass} className="btn-secondary">
                <SkipForward className="h-4 w-4 mr-2" />
                Pass
              </button>
            )}
            
            {/* Show pending effects */}
            {gameState.pending_effects.gift?.player_id === currentPlayer.id && (
              <div className="flex items-center text-orange-600">
                <Gift className="h-4 w-4 mr-1" />
                <span className="text-sm">
                  Gift {gameState.pending_effects.gift.remaining} cards
                </span>
              </div>
            )}
          </div>
          
          {/* Turn indicator */}
          {!isMyTurn && gameState.phase === 'play' && (
            <div className="mt-3 p-3 bg-gray-50 rounded-lg text-center">
              <span className="text-gray-600">
                Waiting for {gameState.players[gameState.turn!]?.name || 'other player'}...
              </span>
            </div>
          )}
        </div>
      )}

      {/* Phase-specific messages */}
      {gameState.phase === 'exchange' && (
        <div className="card p-4 mt-4 bg-blue-50">
          <div className="text-center">
            <h3 className="font-medium text-blue-900">Exchange Phase</h3>
            <p className="text-blue-700 text-sm">
              Players are exchanging cards based on their roles from the previous round.
            </p>
          </div>
        </div>
      )}

      {gameState.phase === 'finished' && (
        <div className="card p-6 mt-4 bg-green-50">
          <div className="text-center">
            <h3 className="text-xl font-bold text-green-900 mb-2">Round Complete!</h3>
            <div className="space-y-2">
              {gameState.finished_order.map((playerId, index) => {
                const player = gameState.players[playerId];
                const role = player?.role;
                return (
                  <div key={playerId} className="flex items-center justify-center space-x-2">
                    <span className="font-medium">#{index + 1}</span>
                    <span>{player?.name}</span>
                    {role && (
                      <span className={`role-${role.toLowerCase()}`}>
                        {role}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 