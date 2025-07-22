'use client';

import { useGameStore } from '@/store/gameStore';
import { Card } from '@/components/Card';
import { Hand, RotateCcw, SkipForward, Gift } from 'lucide-react';

// Card sorting order from app.py
const NORMAL_ORDER = [3,4,5,6,7,8,9,10,'J','Q','K','A',2,'JOKER'];

export function GameTable() {
  const { 
    gameState, 
    playerId,
    selectedCards, 
    playCards, 
    passTurn, 
    selectCard, 
    deselectCard,
    clearSelection 
  } = useGameStore();

  if (!gameState || !playerId) return null;

  const currentPlayer = gameState.players[playerId];
  
  // CRITICAL FIX: If we don't have our own player data, find it by hand presence
  let actualPlayer = currentPlayer;
  let correctedPlayerId = playerId;
  
  if (!currentPlayer || !currentPlayer.hand) {
    console.log(`🚨 CRITICAL: Player ${playerId} not found or has no hand. Searching...`);
    
    // Find the player that has hand data (that's us!)
    const playerWithHand = Object.values(gameState.players).find(p => p.hand && p.hand.length > 0);
    if (playerWithHand) {
      console.log(`🔧 OVERRIDE: Using player ${playerWithHand.id} (${playerWithHand.name}) instead`);
      actualPlayer = playerWithHand;
      correctedPlayerId = playerWithHand.id;
      
      // Update the store with the correct player ID
      useGameStore.setState({ playerId: playerWithHand.id });
    }
  }
  
  if (!actualPlayer) return null;

  const isMyTurn = gameState.turn === correctedPlayerId && gameState.phase === 'play' && actualPlayer.hand && actualPlayer.hand.length > 0 && !actualPlayer.passed;
  const canPlay = selectedCards.length > 0 && isMyTurn;
  const canPass = isMyTurn;

  // Emergency debug and fix
  console.log(`🚨 EMERGENCY DEBUG:`, {
    'gameState.turn': gameState.turn,
    'original_playerId': playerId,
    'corrected_playerId': correctedPlayerId,
    'currentPlayer.name': actualPlayer.name,
    'isMyTurn': isMyTurn,
    'gameState.phase': gameState.phase,
    'hands': Object.entries(gameState.players).map(([id, p]) => ({ id, name: p.name, hasHand: !!p.hand }))
  });

  // FORCE ENABLE if it's your turn by name match (temporary fix)
  const isMyTurnByName = Object.values(gameState.players).find(p => p.name === actualPlayer.name && p.id === gameState.turn);
  const shouldAllowClicks = isMyTurn || !!isMyTurnByName;

  console.log(`🔧 FORCE FIX: shouldAllowClicks = ${shouldAllowClicks} (isMyTurn: ${isMyTurn}, isMyTurnByName: ${!!isMyTurnByName})`);

  // Parse card function from app.py
  const parseCard = (cardId: string) => {
    if (cardId.startsWith('JOKER')) {
      return { rank: 'JOKER', suit: null };
    }
    if (['J', 'Q', 'K', 'A'].includes(cardId[cardId.length - 1])) {
      return { rank: cardId.slice(0, -1), suit: cardId.slice(-1) };
    }
    if (cardId.startsWith('10')) {
      return { rank: 10, suit: cardId.slice(-1) };
    }
    return { rank: parseInt(cardId.slice(0, -1)), suit: cardId.slice(-1) };
  };

  // Sort hand by game order like in app.py
  const sortHand = (hand: string[]) => {
    return [...hand].sort((a, b) => {
      const rankA = parseCard(a).rank;
      const rankB = parseCard(b).rank;
      
      try {
        const indexA = NORMAL_ORDER.indexOf(rankA);
        const indexB = NORMAL_ORDER.indexOf(rankB);
        return indexA - indexB;
      } catch {
        return 0;
      }
    });
  };

  const handleCardClick = (cardId: string) => {
    // ALWAYS allow card clicks if it's the current player's turn by any logic
    console.log(`🖱️ Card ${cardId} clicked - shouldAllowClicks: ${shouldAllowClicks}`);
    
    if (selectedCards.includes(cardId)) {
      console.log(`Deselecting card: ${cardId}`);
      deselectCard(cardId);
    } else {
      console.log(`Selecting card: ${cardId}`);
      selectCard(cardId);
    }
  };

  const handlePlay = () => {
    if (canPlay) {
      console.log(`Playing cards: ${selectedCards.join(', ')}`);
      playCards(selectedCards);
    } else {
      console.log(`Cannot play - canPlay: ${canPlay}, selectedCards: ${selectedCards.length}`);
    }
  };

  const handlePass = () => {
    if (canPass) {
      console.log('Passing turn');
      passTurn();
    } else {
      console.log(`Cannot pass - canPass: ${canPass}`);
    }
  };

  const getCurrentPatternDisplay = () => {
    const { rank, count } = gameState.current_pattern;
    if (!rank || !count) return 'No cards played yet';
    
    const countDisplay = count.toString();
    const rankDisplay = typeof rank === 'number' ? rank : rank;
    const plural = count > 1 ? 's' : '';
    return `${countDisplay} ${rankDisplay}${plural} played`;
  };

  const getCurrentPileCards = () => {
    return gameState.current_pattern?.cards || [];
  };

  // Get sorted hand
  const sortedHand = actualPlayer.hand ? sortHand(actualPlayer.hand) : [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-900 via-blue-900 to-purple-900 p-4">
      <div className="max-w-6xl mx-auto">
        {/* Game Status */}
        <div className="bg-black/20 backdrop-blur-sm rounded-lg p-4 mb-6 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div>
                <span className="text-sm text-gray-300">Phase:</span>
                <span className="ml-2 font-medium capitalize">{gameState.phase}</span>
              </div>
              
              {gameState.turn && (
                <div>
                  <span className="text-sm text-gray-300">Turn:</span>
                  <span className="ml-2 font-medium">
                    {gameState.players[gameState.turn]?.name || 'Unknown'}
                    {gameState.turn === playerId && ' (YOU!)'}
                  </span>
                </div>
              )}
              
              {gameState.inversion_active && (
                <div className="flex items-center text-orange-400">
                  <RotateCcw className="h-4 w-4 mr-1" />
                  <span className="text-sm font-medium">Rank Inverted</span>
                </div>
              )}
            </div>
            
            <div className="text-right">
              <div className="text-sm text-gray-300">Current Pattern</div>
              <div className="font-medium">{getCurrentPatternDisplay()}</div>
            </div>
          </div>
        </div>

        {/* Current Pile */}
        <div className="bg-black/20 backdrop-blur-sm rounded-lg p-6 mb-6 text-white">
          <h3 className="text-xl font-semibold text-center mb-4">🎯 Current Pile</h3>
          <div className="min-h-32 flex items-center justify-center bg-gradient-to-br from-green-600/20 to-blue-600/20 rounded-lg border-2 border-dashed border-gray-400">
            {getCurrentPileCards().length > 0 ? (
              <div className="flex flex-wrap gap-2 justify-center">
                {getCurrentPileCards().map((cardId, index) => (
                  <Card
                    key={`pile-${cardId}-${index}`}
                    cardId={cardId}
                    selected={false}
                    onClick={() => {}}
                    disabled={true}
                    size="md"
                  />
                ))}
              </div>
            ) : (
              <div className="text-center text-gray-400">
                <div className="text-2xl mb-2">🃏</div>
                <div>Empty</div>
              </div>
            )}
          </div>
        </div>

        {/* Players Around Table */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {Object.values(gameState.players)
            .sort((a, b) => a.seat - b.seat)
            .map((player) => (
              <div 
                key={player.id}
                className={`bg-black/20 backdrop-blur-sm rounded-lg p-4 text-white ${
                  player.id === gameState.turn ? 'ring-2 ring-yellow-400' : ''
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium">{player.name}</span>
                    {player.is_bot && (
                      <span className="text-xs bg-purple-500/20 text-purple-200 px-2 py-1 rounded">
                        Bot
                      </span>
                    )}
                  </div>
                  
                  {player.id === gameState.turn && (
                    <span className="text-yellow-400 text-sm">▶</span>
                  )}
                </div>
                
                {player.role && (
                  <div className="mb-2">
                    <span className={`text-xs px-2 py-1 rounded ${
                      player.role === 'President' ? 'bg-yellow-500/20 text-yellow-200' :
                      player.role === 'VicePresident' ? 'bg-orange-500/20 text-orange-200' :
                      player.role === 'Citizen' ? 'bg-blue-500/20 text-blue-200' :
                      player.role === 'Scumbag' ? 'bg-purple-500/20 text-purple-200' :
                      'bg-red-500/20 text-red-200'
                    }`}>
                      {player.role}
                    </span>
                  </div>
                )}
                
                <div className="flex items-center justify-between text-sm text-gray-300">
                  <div className="flex items-center space-x-1">
                    <Hand className="h-4 w-4" />
                    <span>{player.hand_count} cards</span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {player.passed && (
                      <span className="text-xs bg-gray-500/20 text-gray-300 px-2 py-1 rounded">
                        Passed
                      </span>
                    )}
                    <div className={`w-2 h-2 rounded-full ${
                      player.connected ? 'bg-green-400' : 'bg-red-400'
                    }`} />
                  </div>
                </div>
              </div>
            ))}
        </div>

        {/* Player's Hand */}
        <div className="bg-black/20 backdrop-blur-sm rounded-lg p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold">🃏 {actualPlayer.name}'s Hand</h3>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-300">
                {selectedCards.length} selected
              </span>
              {selectedCards.length > 0 && (
                <button 
                  onClick={clearSelection}
                  className="text-sm text-blue-400 hover:text-blue-300"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
          
          {/* Turn Status */}
          {shouldAllowClicks ? (
            <div className="mb-4 p-3 bg-green-500/20 border border-green-500/30 rounded-lg text-center">
              <div className="text-green-300 font-semibold">🎯 YOUR TURN!</div>
              <div className="text-sm text-green-200">Select cards and click Play, or Pass your turn</div>
              <div className="text-xs text-green-100 mt-1">Debug: Turn={gameState.turn}, You={correctedPlayerId}</div>
            </div>
          ) : (
            <div className="mb-4 p-3 bg-gray-500/20 border border-gray-500/30 rounded-lg text-center">
              <div className="text-gray-300">⏳ Wait for your turn</div>
              {gameState.turn && gameState.players[gameState.turn] && (
                <div className="text-sm text-gray-400">
                  Waiting for {gameState.players[gameState.turn].name}...
                </div>
              )}
              <div className="text-xs text-gray-400 mt-1">Debug: Turn={gameState.turn}, You={correctedPlayerId}</div>
            </div>
          )}
          
          {/* Cards */}
          {sortedHand.length > 0 ? (
            <div className="flex flex-wrap gap-2 mb-4 justify-center">
              {sortedHand.map((cardId) => (
                <Card
                  key={cardId}
                  cardId={cardId}
                  selected={selectedCards.includes(cardId)}
                  onClick={() => handleCardClick(cardId)}
                  disabled={!shouldAllowClicks}
                  size="md"
                />
              ))}
            </div>
          ) : (
            <div className="text-center text-gray-400 mb-4">
              🚫 No cards
            </div>
          )}
          
          {/* Actions */}
          <div className="flex items-center justify-center space-x-3">
            <button
              onClick={handlePlay}
              disabled={!shouldAllowClicks || selectedCards.length === 0}
              className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                shouldAllowClicks && selectedCards.length > 0
                  ? 'bg-blue-500 hover:bg-blue-600 text-white' 
                  : 'bg-gray-600 text-gray-400 cursor-not-allowed'
              }`}
            >
              🎯 Play {selectedCards.length} Card{selectedCards.length !== 1 ? 's' : ''}
            </button>
            
            <button 
              onClick={handlePass}
              disabled={!shouldAllowClicks}
              className={`px-6 py-3 rounded-lg font-medium transition-colors flex items-center ${
                shouldAllowClicks
                  ? 'bg-gray-500 hover:bg-gray-600 text-white' 
                  : 'bg-gray-700 text-gray-500 cursor-not-allowed'
              }`}
            >
              <SkipForward className="h-4 w-4 mr-2" />
              ⏭️ Pass
            </button>
            
            {/* Show pending effects */}
            {gameState.pending_effects.gift?.player_id === actualPlayer.id && (
              <div className="flex items-center text-orange-400 px-4 py-2 bg-orange-500/20 rounded-lg">
                <Gift className="h-4 w-4 mr-2" />
                <span className="text-sm">
                  Gift {gameState.pending_effects.gift.remaining} cards
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Phase-specific messages */}
        {gameState.phase === 'finished' && (
          <div className="mt-6 bg-green-500/20 backdrop-blur-sm rounded-lg p-6 text-white">
            <div className="text-center">
              <h3 className="text-2xl font-bold text-green-300 mb-4">🎉 Game Finished!</h3>
              <div className="space-y-2">
                {gameState.finished_order.map((playerId, index) => {
                  const player = gameState.players[playerId];
                  const role = player?.role;
                  return (
                    <div key={playerId} className="flex items-center justify-center space-x-2">
                      <span className="font-medium">#{index + 1}</span>
                      <span>{player?.name}</span>
                      {role && (
                        <span className={`px-2 py-1 rounded text-xs ${
                          role === 'President' ? 'bg-yellow-500/20 text-yellow-200' :
                          role === 'VicePresident' ? 'bg-orange-500/20 text-orange-200' :
                          role === 'Citizen' ? 'bg-blue-500/20 text-blue-200' :
                          role === 'Scumbag' ? 'bg-purple-500/20 text-purple-200' :
                          'bg-red-500/20 text-red-200'
                        }`}>
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
    </div>
  );
}