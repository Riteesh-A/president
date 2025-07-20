'use client';

import { create } from 'zustand';
import toast from 'react-hot-toast';
import { 
  GameState, 
  ConnectionState, 
  UIState, 
  InboundWSEvent, 
  OutboundWSEvent,
  PatchOperation 
} from '@/types/game';

interface GameStore extends UIState {
  // Core state
  gameState: GameState | null;
  connectionState: ConnectionState;
  playerId: string | null;
  websocket: WebSocket | null;
  
  // Modal state
  showGiftModal: boolean;
  showDiscardModal: boolean;
  showExchangeModal: boolean;

  // Actions
  connect: (url: string) => void;
  disconnect: () => void;
  sendEvent: (event: OutboundWSEvent) => void;
  
  // Game actions
  joinRoom: (roomId: string, playerName: string, isBot?: boolean) => void;
  startGame: (seed?: number) => void;
  playCards: (cards: string[]) => void;
  passTurn: () => void;
  submitGiftDistribution: () => void;
  submitDiscardSelection: () => void;
  submitExchangeReturn: () => void;
  sendChatMessage: (text: string) => void;
  
  // UI actions
  selectCard: (cardId: string) => void;
  deselectCard: (cardId: string) => void;
  clearSelection: () => void;
  setGiftAssignments: (assignments: Array<{ to: string; cards: string[] }>) => void;
  setDiscardCards: (cards: string[]) => void;
  setExchangeCards: (cards: string[]) => void;
  openGiftModal: () => void;
  closeGiftModal: () => void;
  openDiscardModal: () => void;
  closeDiscardModal: () => void;
  openExchangeModal: () => void;
  closeExchangeModal: () => void;
}

const initialUIState: UIState = {
  selectedCards: [],
  giftAssignments: [],
  discardCards: [],
  exchangeCards: [],
  chatMessages: [],
};

export const useGameStore = create<GameStore>((set, get) => ({
  ...initialUIState,
  gameState: null,
  connectionState: { status: 'disconnected' },
  playerId: null,
  websocket: null,
  showGiftModal: false,
  showDiscardModal: false,
  showExchangeModal: false,

  connect: (url: string) => {
    const { websocket: currentWs } = get();
    
    if (currentWs) {
      currentWs.close();
    }

    set({ connectionState: { status: 'connecting' } });

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        set({ 
          connectionState: { status: 'connected' },
          websocket: ws 
        });
        toast.success('Connected to game server');
      };

      ws.onmessage = (event) => {
        try {
          const data: InboundWSEvent = JSON.parse(event.data);
          handleInboundEvent(data, set, get);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        set({ 
          connectionState: { status: 'disconnected' },
          websocket: null 
        });
        toast.error('Disconnected from game server');
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        set({ 
          connectionState: { 
            status: 'error', 
            error: 'Connection failed' 
          },
          websocket: null 
        });
        toast.error('Connection failed');
      };

    } catch (error) {
      set({ 
        connectionState: { 
          status: 'error', 
          error: 'Failed to create connection' 
        } 
      });
      toast.error('Failed to create connection');
    }
  },

  disconnect: () => {
    const { websocket } = get();
    if (websocket) {
      websocket.close();
    }
    set({ 
      connectionState: { status: 'disconnected' },
      websocket: null,
      gameState: null,
      playerId: null,
      showGiftModal: false,
      showDiscardModal: false,
      showExchangeModal: false,
      ...initialUIState 
    });
  },

  sendEvent: (event: OutboundWSEvent) => {
    const { websocket, connectionState } = get();
    
    if (connectionState.status !== 'connected' || !websocket) {
      toast.error('Not connected to server');
      return;
    }

    try {
      websocket.send(JSON.stringify(event));
    } catch (error) {
      console.error('Failed to send event:', error);
      toast.error('Failed to send message');
    }
  },

  // Game actions
  joinRoom: (roomId: string, playerName: string, isBot = false) => {
    console.log(`Joining room: ${roomId} as ${playerName} (bot: ${isBot})`);
    get().sendEvent({
      type: 'join',
      room_id: roomId,
      name: playerName,
      is_bot: isBot
    });
    
    if (isBot) {
      toast.success(`Adding ${playerName} to the game...`);
    }
  },

  startGame: (seed?: number) => {
    get().sendEvent({
      type: 'start',
      seed
    });
  },

  playCards: (cards: string[]) => {
    get().sendEvent({
      type: 'play',
      cards
    });
    set({ selectedCards: [] });
  },

  passTurn: () => {
    get().sendEvent({
      type: 'pass'
    });
  },

  submitGiftDistribution: () => {
    const { giftAssignments } = get();
    get().sendEvent({
      type: 'gift_select',
      assignments: giftAssignments
    });
    set({ 
      giftAssignments: [],
      showGiftModal: false 
    });
  },

  submitDiscardSelection: () => {
    const { discardCards } = get();
    get().sendEvent({
      type: 'discard_select',
      cards: discardCards
    });
    set({ 
      discardCards: [],
      showDiscardModal: false 
    });
  },

  submitExchangeReturn: () => {
    const { exchangeCards } = get();
    get().sendEvent({
      type: 'exchange_return',
      cards: exchangeCards
    });
    set({ 
      exchangeCards: [],
      showExchangeModal: false 
    });
  },

  sendChatMessage: (text: string) => {
    get().sendEvent({
      type: 'chat',
      text
    });
  },

  // UI actions
  selectCard: (cardId: string) => {
    set(state => ({
      selectedCards: state.selectedCards.includes(cardId) 
        ? state.selectedCards 
        : [...state.selectedCards, cardId]
    }));
  },

  deselectCard: (cardId: string) => {
    set(state => ({
      selectedCards: state.selectedCards.filter(id => id !== cardId)
    }));
  },

  clearSelection: () => {
    set({ selectedCards: [] });
  },

  setGiftAssignments: (assignments) => {
    set({ giftAssignments: assignments });
  },

  setDiscardCards: (cards) => {
    set({ discardCards: cards });
  },

  setExchangeCards: (cards) => {
    set({ exchangeCards: cards });
  },

  openGiftModal: () => set({ showGiftModal: true }),
  closeGiftModal: () => set({ showGiftModal: false }),
  openDiscardModal: () => set({ showDiscardModal: true }),
  closeDiscardModal: () => set({ showDiscardModal: false }),
  openExchangeModal: () => set({ showExchangeModal: true }),
  closeExchangeModal: () => set({ showExchangeModal: false }),
}));

// WebSocket event handler
function handleInboundEvent(
  event: InboundWSEvent,
  set: (partial: Partial<GameStore>) => void,
  get: () => GameStore
) {
  switch (event.type) {
    case 'state_full':
      set({ gameState: event.state });
      break;

    case 'state_patch':
      const currentState = get().gameState;
      if (currentState) {
        const newState = applyPatch(currentState, event.ops);
        set({ gameState: newState });
      }
      break;

    case 'error':
      toast.error(`${event.code}: ${event.message}`);
      break;

    case 'effect':
      handleEffectEvent(event, set, get);
      break;

    case 'chat':
      const storeState = get();
      set({
        chatMessages: [
          ...storeState.chatMessages,
          {
            player_id: event.player_id,
            player_name: event.player_name,
            text: event.text,
            timestamp: event.timestamp
          }
        ].slice(-50) // Keep only last 50 messages
      });
      break;
  }
}

// Apply JSON patch operations to state
function applyPatch(state: GameState, ops: PatchOperation[]): GameState {
  let newState = { ...state };

  for (const op of ops) {
    const pathParts = op.path.split('/').filter(p => p);
    
    if (op.op === 'replace' || op.op === 'add') {
      setNestedValue(newState, pathParts, op.value);
    } else if (op.op === 'remove') {
      removeNestedValue(newState, pathParts);
    }
  }

  return newState;
}

function setNestedValue(obj: any, path: string[], value: any) {
  let current = obj;
  for (let i = 0; i < path.length - 1; i++) {
    const key = path[i];
    if (!(key in current)) {
      current[key] = {};
    }
    current = current[key];
  }
  if (path.length > 0) {
    current[path[path.length - 1]] = value;
  }
}

function removeNestedValue(obj: any, path: string[]) {
  let current = obj;
  for (let i = 0; i < path.length - 1; i++) {
    const key = path[i];
    if (!(key in current)) {
      return;
    }
    current = current[key];
  }
  if (path.length > 0) {
    delete current[path[path.length - 1]];
  }
}

// Handle special effect events
function handleEffectEvent(
  event: { effect_type: string; data: any },
  set: (partial: Partial<GameStore>) => void,
  get: () => GameStore
) {
  switch (event.effect_type) {
    case 'seven_gift':
      toast('Someone played sevens! Gift distribution required.', {
        icon: '🎁',
      });
      break;

    case 'eight_reset':
      toast('Pile reset! Same player continues.', {
        icon: '🔄',
      });
      break;

    case 'ten_discard':
      toast('Someone played tens! Discard required.', {
        icon: '🗑️',
      });
      break;

    case 'jack_inversion':
      toast('Rank order inverted!', {
        icon: '🔄',
      });
      break;

    case 'round_ended':
      toast('Round ended!', {
        icon: '🏁',
      });
      break;
  }
} 