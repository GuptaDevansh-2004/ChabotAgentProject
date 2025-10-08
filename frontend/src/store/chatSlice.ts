import { createSlice, type PayloadAction, nanoid } from "@reduxjs/toolkit";

export type Role = "user" | "model";

export interface ChatImage {
  path: string;
  data: string; // data:image/...;base64,...
}

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  images?: ChatImage[];
  animated?: boolean;
  typed?: boolean;
  createdAt: number;
}

export interface Session {
  id: string;
  title: string;
  prev_context: string;
  was_context_valid_old: boolean;
  is_follow_up_old: boolean;
  related_images: string[]; // array of paths
  messages: ChatMessage[]; // full conversation (both sides)
  createdAt: number;
  updatedAt: number;
  loading?: boolean;
  new?: boolean;
}

interface ChatState {
  sessions: Session[];
  activeSessionId: string | null;
}

const DEFAULT_GREETING = "Hello! I'm ready to help. Ask me anything to start this chat.";

const initialState: ChatState = {
  sessions: [],
  activeSessionId: null,
};

function createNewSession(title?: string): Session {
  const id = nanoid();
  const now = Date.now();
  return {
    id,
    title: title ?? "New Chat",
    prev_context: DEFAULT_GREETING,
    was_context_valid_old: true,
    is_follow_up_old: true,
    related_images: [],
    messages: [],
    createdAt: now,
    updatedAt: now,
    new: true,
  };
}

const slice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    bootstrapFirstSession(state) {
      if (!state.activeSessionId && state.sessions.length === 0) {
        const s = createNewSession("First Chat");
        state.sessions.push(s);
        state.activeSessionId = s.id;
      }
    },
    addSession(state, action: PayloadAction<{ title?: string } | undefined>) {
      const s = createNewSession(action?.payload?.title);
      state.sessions.unshift(s);
      state.activeSessionId = s.id;
    },
    switchSession(state, action: PayloadAction<string>) {
      const found = state.sessions.find((s) => s.id === action.payload);
      if (found) {
        state.activeSessionId = action.payload;
      }
    },
    removeSession(state, action: PayloadAction<string>) {
      state.sessions = state.sessions.filter((s) => s.id !== action.payload);
      if (state.activeSessionId === action.payload) {
        state.activeSessionId = state.sessions[0]?.id ?? null;
      }
    },
    addUserMessage(
      state,
      action: PayloadAction<{ sessionId: string; content: string; images?: ChatImage[] }>
    ) {
      const s = state.sessions.find((x) => x.id === action.payload.sessionId);
      if (!s) return;
      const msg: ChatMessage = {
        id: nanoid(),
        role: "user",
        content: action.payload.content,
        images: action.payload.images ?? [],
        animated: false,
        createdAt: Date.now(),
      };
      s.messages.push(msg);
      s.updatedAt = Date.now();
    },
    addModelMessage(
      state,
      action: PayloadAction<{ sessionId: string; content: string; images?: ChatImage[]; typed?: boolean; }>
    ) {
      const s = state.sessions.find((x) => x.id === action.payload.sessionId);
      if (!s) return;
      const msg: ChatMessage = {
        id: nanoid(),
        role: "model",
        content: action.payload.content,
        images: action.payload.images ?? [],
        createdAt: Date.now(),
        typed: action.payload.typed,
      };
      s.messages.push(msg);
      s.updatedAt = Date.now();
    },
    setSessionMeta(
      state,
      action: PayloadAction<{
        sessionId: string;
        prev_context?: string;
        was_context_valid_old?: boolean;
        is_follow_up_old?: boolean;
        related_images?: string[];
        title?: string;
      }>
    ) {
      const s = state.sessions.find((x) => x.id === action.payload.sessionId);
      if (!s) return;
      if (action.payload.prev_context !== undefined) s.prev_context = action.payload.prev_context;
      if (action.payload.was_context_valid_old !== undefined)
        s.was_context_valid_old = action.payload.was_context_valid_old;
      if (action.payload.is_follow_up_old !== undefined)
        s.is_follow_up_old = action.payload.is_follow_up_old;
      if (action.payload.related_images !== undefined) s.related_images = action.payload.related_images;
      if (action.payload.title !== undefined) s.title = action.payload.title;
      s.updatedAt = Date.now();
    },
    setSessionStatus(state, action: PayloadAction<string>) {
      const s = state.sessions.find((x) => x.id === action.payload);
      if (!s) return;
      s.new = false;
      s.updatedAt = Date.now();
    },
    toggleTaggedImage(state, action: PayloadAction<{ sessionId: string; path: string }>) {
      const s = state.sessions.find((x) => x.id === action.payload.sessionId);
      if (!s) return;
      const idx = s.related_images.indexOf(action.payload.path);
      if (idx >= 0) s.related_images.splice(idx, 1);
      else s.related_images.push(action.payload.path);
      s.updatedAt = Date.now();
    },
    clearTaggedImages(state, action: PayloadAction<{ sessionId: string }>) {
      const s = state.sessions.find((x) => x.id === action.payload.sessionId);
      if (!s) return;
      s.related_images = [];
      s.updatedAt = Date.now();
    },
    setSessionLoading(state, action: PayloadAction<{ sessionId: string; loading: boolean }>) {
      const s = state.sessions.find(x => x.id === action.payload.sessionId);
      if (!s) return;
      s.loading = action.payload.loading;
      s.updatedAt = Date.now();
    },
    markMessageTyped(state, action: PayloadAction<{ sessionId: string; messageId: string }>) {
      const s = state.sessions.find((x) => x.id === action.payload.sessionId);
      if (s) {
        const msg = s.messages.find((m) => m.id === action.payload.messageId);
        if (msg) msg.typed = true;
        s.loading = false;
      }
    },
    markMessageAnimated(state, action: PayloadAction<{ sessionId: string; messageId: string }>) {
      const session = state.sessions.find(s => s.id === action.payload.sessionId);
      if (!session) return;
      const msg = session.messages.find(m => m.id === action.payload.messageId);
      if (msg) msg.animated = true;
    },
  },
});

export const {
  bootstrapFirstSession,
  addSession,
  switchSession,
  removeSession,
  addUserMessage,
  addModelMessage,
  setSessionMeta,
  setSessionStatus,
  toggleTaggedImage,
  clearTaggedImages,
  setSessionLoading,
  markMessageTyped,
  markMessageAnimated,
} = slice.actions;

export default slice.reducer;