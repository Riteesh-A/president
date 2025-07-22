'use client';

interface CardProps {
  cardId: string;
  selected?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  size?: 'sm' | 'md' | 'lg';
}

export function Card({ cardId, selected = false, disabled = false, onClick, size = 'md' }: CardProps) {
  const parseCard = (id: string) => {
    if (id.startsWith('JOKER')) {
      return {
        rank: 'JOKER',
        suit: '',
        displayRank: '��',
        color: 'purple' as const
      };
    }

    // Handle 10 specially (like in app.py)
    if (id.startsWith('10')) {
      const suit = id.slice(-1);
      return {
        rank: '10',
        suit: suit,
        displayRank: '10',
        color: ['H', 'D'].includes(suit) ? 'red' as const : 'black' as const
      };
    }

    // Handle face cards and numbers
    if (id.length >= 2) {
      const suit = id.slice(-1);
      const rank = id.slice(0, -1);
      
      return {
        rank,
        suit,
        displayRank: rank,
        color: ['H', 'D'].includes(suit) ? 'red' as const : 'black' as const
      };
    }

    // Fallback
    return {
      rank: id,
      suit: '',
      displayRank: id,
      color: 'black' as const
    };
  };

  const getSuitSymbol = (suit: string) => {
    switch (suit) {
      case 'H': return '♥';
      case 'D': return '♦';
      case 'C': return '♣';
      case 'S': return '♠';
      default: return '';
    }
  };

  const getSizeClasses = () => {
    switch (size) {
      case 'sm': return 'w-12 h-16 text-xs';
      case 'lg': return 'w-20 h-28 text-lg';
      default: return 'w-16 h-24 text-sm';
    }
  };

  const card = parseCard(cardId);
  const suitSymbol = getSuitSymbol(card.suit);
  
  const handleClick = () => {
    console.log(`🖱️ NUCLEAR OPTION: Card ${cardId} clicked (onClick: ${!!onClick})`);
    if (onClick) {
      onClick();
    }
  };
  
  return (
    <div
      className={`
        relative bg-white border-2 rounded-lg shadow-sm transition-all duration-200 flex flex-col items-center justify-center font-bold cursor-pointer
        ${getSizeClasses()}
        ${card.color === 'red' ? 'text-red-600' : card.color === 'purple' ? 'text-purple-600' : 'text-gray-900'}
        ${!disabled ? 'hover:shadow-md hover:-translate-y-1' : ''}
        ${selected ? 'border-orange-500 bg-orange-50 shadow-lg -translate-y-2 ring-2 ring-orange-300' : 'border-gray-300'}
      `}
      onClick={handleClick}
    >
      {card.rank === 'JOKER' ? (
        <div className="text-2xl">🃏</div>
      ) : (
        <>
          {/* Top left corner */}
          <div className="absolute top-1 left-1 text-xs leading-none">
            <div>{card.displayRank}</div>
            {suitSymbol && <div>{suitSymbol}</div>}
          </div>
          
          {/* Center */}
          <div className="text-center">
            <div className="text-lg font-bold">{card.displayRank}</div>
            {suitSymbol && <div className="text-xl">{suitSymbol}</div>}
          </div>
          
          {/* Bottom right corner (upside down) */}
          <div className="absolute bottom-1 right-1 text-xs leading-none transform rotate-180">
            <div>{card.displayRank}</div>
            {suitSymbol && <div>{suitSymbol}</div>}
          </div>
        </>
      )}
    </div>
  );
} 