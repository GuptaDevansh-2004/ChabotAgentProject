import { configureStore, combineReducers } from "@reduxjs/toolkit";
import {
  persistStore,
  persistReducer,
  FLUSH,
  REHYDRATE,
  PAUSE,
  PERSIST,
  PURGE,
  REGISTER,
} from "redux-persist";
import storage from "redux-persist/lib/storage";
import chatReducer from "./chatSlice.ts";

const rootReducer = combineReducers({
  chat: chatReducer,
});

const persistConfig = {
  key: "root",
  storage,
  // blacklist or whitelist can be added if needed
};

const persistedReducer = persistReducer(persistConfig, rootReducer);

export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefault) =>
    getDefault({
      serializableCheck: {
        // redux-persist actions are non-serializable by default
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER],
      },
    }),
});

export const persistor = persistStore(store);

// helpers for typing
export type RootState = ReturnType<typeof rootReducer>;
export type AppDispatch = typeof store.dispatch;