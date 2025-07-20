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
        displayRank: '🃏',
        color: 'black' as const
      };
    }

    // Handle 10 specially
    if (id.startsWith('10')) {
      return {
        rank: '10',
        suit: id[2],
        displayRank: '10',
        color: ['H', 'D'].includes(id[2]) ? 'red' as const : 'black' as const
      };
    }

    const rank = id[0];
    const suit = id[1];
    
    return {
      rank,
      suit,
      displayRank: rank,
      color: ['H', 'D'].includes(suit) ? 'red' as const : 'black' as const
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
  
  return (
    <div
      className={`
        playing-card ${getSizeClasses()}
        ${selected ? 'selected' : ''}
        ${disabled ? 'disabled' : ''}
        flex flex-col items-center justify-center
        ${card.color === 'red' ? 'card-suit-red' : 'card-suit-black'}
      `}
      onClick={!disabled ? onClick : undefined}
    >
      {card.rank === 'JOKER' ? (
        <div className="text-2xl">🃏</div>
      ) : (
        <>
          <div className="font-bold">{card.displayRank}</div>
          <div className="text-lg">{suitSymbol}</div>
        </>
      )}
    </div>
  );
} 