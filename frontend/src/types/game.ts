// Game state types
export interface Player {
  id: string;
  name: string;
  seat: number;
  role?: string;
  passed: boolean;
  connected: boolean;
  is_bot: boolean;
  hand_count: number;
  hand?: string[]; // Only present for current player
}

export interface CurrentPattern {
  rank?: string | number;
  count?: number;
  last_player?: string;
  cards?: string[]; // Cards currently in the pile
}

export interface PendingEffect {
  gift?: {
    player_id: string;
    remaining: number;
    original_count: number;
  };
  discard?: {
    player_id: string;
    remaining: number;
    original_count: number;
  };
}

export interface ExchangeData {
  phase: 'exchange';
  data: {
    president_id?: string;
    vice_president_id?: string;
    scumbag_id?: string;
    asshole_id?: string;
    president_cards?: string[];
    vice_president_cards?: string[];
    scumbag_cards?: string[];
    asshole_cards?: string[];
  };
}

export interface EffectLogEntry {
  effect: string;
  version: number;
  timestamp: number;
  data: any;
}

export interface GameRules {
  use_jokers: boolean;
  max_players: number;
  min_players: number;
  enable_bots: boolean;
  auto_fill_bots: boolean;
  turn_timeout: number;
  room_timeout: number;
}

export interface GameState {
  id: string;
  version: number;
  phase: 'lobby' | 'dealing' | 'exchange' | 'play' | 'finished';
  turn?: string;
  inversion_active: boolean;
  current_pattern: CurrentPattern;
  finished_order: string[];
  players: Record<string, Player>;
  pending_effects: PendingEffect;
  recent_effects: EffectLogEntry[];
  discard: string[];
  exchange_data?: ExchangeData;
  rules?: GameRules;
}

// WebSocket event types
export interface WSEvent {
  type: string;
  timestamp: number;
}

export interface StateFullEvent extends WSEvent {
  type: 'state_full';
  state: GameState;
}

export interface StatePatchEvent extends WSEvent {
  type: 'state_patch';
  version: number;
  ops: PatchOperation[];
}

export interface PatchOperation {
  op: 'replace' | 'add' | 'remove';
  path: string;
  value?: any;
}

export interface ErrorEvent extends WSEvent {
  type: 'error';
  code: string;
  message: string;
}

export interface EffectEvent extends WSEvent {
  type: 'effect';
  effect_type: string;
  data: any;
}

export interface JoinSuccessEvent extends WSEvent {
  type: 'join_success';
  player_id: string;
}

export interface ChatEvent extends WSEvent {
  type: 'chat';
  player_id: string;
  player_name: string;
  text: string;
}

export type InboundWSEvent = JoinSuccessEvent | StateFullEvent | StatePatchEvent | ErrorEvent | EffectEvent | ChatEvent;

// Outbound event types
export interface JoinEvent {
  type: 'join';
  room_id: string;
  name: string;
  is_bot?: boolean;
}

export interface StartEvent {
  type: 'start';
  seed?: number;
}

export interface PlayEvent {
  type: 'play';
  cards: string[];
}

export interface PassEvent {
  type: 'pass';
}

export interface GiftSelectEvent {
  type: 'gift_select';
  assignments: Array<{
    to: string;
    cards: string[];
  }>;
}

export interface DiscardSelectEvent {
  type: 'discard_select';
  cards: string[];
}

export interface ExchangeReturnEvent {
  type: 'exchange_return';
  cards: string[];
}

export interface RequestStateEvent {
  type: 'request_state';
}

export interface ChatMessageEvent {
  type: 'chat';
  text: string;
}

export type OutboundWSEvent = 
  | JoinEvent 
  | StartEvent 
  | PlayEvent 
  | PassEvent 
  | GiftSelectEvent 
  | DiscardSelectEvent 
  | ExchangeReturnEvent 
  | RequestStateEvent 
  | ChatMessageEvent;

// UI state types
export interface ConnectionState {
  status: 'disconnected' | 'connecting' | 'connected' | 'error';
  error?: string;
}

export interface UIState {
  selectedCards: string[];
  giftAssignments: Array<{
    to: string;
    cards: string[];
  }>;
  discardCards: string[];
  exchangeCards: string[];
  chatMessages: Array<{
    player_id: string;
    player_name: string;
    text: string;
    timestamp: number;
  }>;
}

// Card utilities
export interface Card {
  id: string;
  rank: string | number;
  suit: string;
  displayRank: string;
  color: 'red' | 'black';
}

// Game actions
export type GameAction = 
  | { type: 'CONNECT' }
  | { type: 'DISCONNECT' }
  | { type: 'CONNECTION_ERROR'; error: string }
  | { type: 'UPDATE_STATE'; state: GameState }
  | { type: 'PATCH_STATE'; ops: PatchOperation[] }
  | { type: 'SELECT_CARD'; cardId: string }
  | { type: 'DESELECT_CARD'; cardId: string }
  | { type: 'CLEAR_SELECTION' }
  | { type: 'SHOW_GIFT_MODAL' }
  | { type: 'HIDE_GIFT_MODAL' }
  | { type: 'SHOW_DISCARD_MODAL' }
  | { type: 'HIDE_DISCARD_MODAL' }
  | { type: 'SHOW_EXCHANGE_MODAL' }
  | { type: 'HIDE_EXCHANGE_MODAL' }
  | { type: 'ADD_CHAT_MESSAGE'; message: ChatEvent }
  | { type: 'SET_GIFT_ASSIGNMENTS'; assignments: Array<{ to: string; cards: string[] }> }
  | { type: 'SET_DISCARD_CARDS'; cards: string[] }
  | { type: 'SET_EXCHANGE_CARDS'; cards: string[] };

// Role information
export const ROLES = {
  President: { color: 'bg-yellow-100 text-yellow-800', order: 1 },
  VicePresident: { color: 'bg-orange-100 text-orange-800', order: 2 },
  Citizen: { color: 'bg-blue-100 text-blue-800', order: 3 },
  Scumbag: { color: 'bg-purple-100 text-purple-800', order: 4 },
  Asshole: { color: 'bg-red-100 text-red-800', order: 5 },
} as const;

export type RoleName = keyof typeof ROLES; 