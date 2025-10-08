import { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { type RootState, type AppDispatch } from "../store";
import {
  addSession,
  switchSession,
  addUserMessage,
  addModelMessage,
  setSessionMeta,
  setSessionStatus,
  toggleTaggedImage,
  clearTaggedImages,
  bootstrapFirstSession,
  removeSession,
  setSessionLoading,
} from "../store/chatSlice";
import ChatWindow from "./ChatWindow.tsx";
import Sidebar from "./Sidebar.tsx";

const API_URL = "http://127.0.0.1:8000/chat/api/search-service/v1";

export default function ChatApp() {
  const dispatch = useDispatch<AppDispatch>();
  const chat = useSelector((s: RootState) => s.chat);
  const active = chat.sessions.find((s) => s.id === chat.activeSessionId) ?? null;

  useEffect(() => {
    dispatch(bootstrapFirstSession());
  }, [dispatch]);

  const createNew = () => {
    dispatch(addSession({ title: "New Chat" }));
  };

  // send message: note we capture previous messages before dispatching the user message
  const sendMessage = async (sessionId: string, text: string) => {
    const session = chat.sessions.find((s) => s.id === sessionId);
    if (!session || session.loading) return; // prevent double send

    dispatch(setSessionLoading({ sessionId, loading: true }));

    const previousMessageHistory = session.messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    const userImages = session.related_images && session.related_images.length > 0 ? (
      session.related_images.map((path) => {
        // find image data from previous messages and return a copy
        for (const m of session.messages) {
          if (m.images && m.images.length > 0) {
            const found = m.images.find((img) => img.path === path);
            if (found) return { path: found.path ?? path, data: found.data ?? "" };
          }
        }
        // fallback to an object that satisfies ChatImage shape
        return { path: "", data: "" };
      })
      .filter((it) => it && it.path)
      .map((it) => ({ path: it.path, data: it.data ?? "" }))
    ) : [];

    const relatedImages = structuredClone(session.related_images);

    // clear tagged images 
    dispatch(clearTaggedImages({ sessionId }));
    // show user message immediately
    dispatch(addUserMessage({ sessionId, content: text, images: userImages }));

    const payload = {
      prev_context: session.prev_context,
      message_history: previousMessageHistory,
      query: text,
      was_context_valid_old: session.was_context_valid_old,
      is_follow_up_old: session.is_follow_up_old,
      related_images: relatedImages, // array of paths
    };

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // normalize images shape
      const images = Array.isArray(data.images)
        ? data.images.map((it: any) => ({ path: it.path ?? "", data: it.data ?? "" }))
        : [];

      dispatch(
        addModelMessage({
          sessionId,
          content: data.answer ?? "",
          images,
          typed: false,
        })
      );

      dispatch(
        setSessionMeta({
          sessionId,
          prev_context: data.context ?? "",
          was_context_valid_old: Boolean(data.was_context_valid),
          is_follow_up_old: Boolean(data.is_follow_up),
        })
      );
    } catch (err) {
      console.error(err);
      dispatch(
        addModelMessage({
          sessionId,
          content: "**Sorry!** - *service currently unavailable. Please try again later.*",
          typed: false,
        })
      );
    }
  };

  return (
    <div key={active?.id} className="flex h-full w-full gap-0.5">
      <div className="w-[16.2%] max-w[16.2%] flex bg-gray-50 rounded shadow">
        <Sidebar
          sessions={chat.sessions}
          activeId={chat.activeSessionId}
          onCreate={createNew}
          onSwitch={(id) => dispatch(switchSession(id))}
          onDelete={(id) => dispatch(removeSession(id))} 
          updateStatus={(id) => dispatch(setSessionStatus(id))}
        />
      </div>
      <div key={active?.id} className="flex-1 w-[83.8%] max-w-[83.8%] rounded shadow bg-gradient-to-br from-indigo-50 via-neutral-50 to-indigo-50">
        {active ? (
          <ChatWindow
            key={active.id}
            session={active}
            onSend={(text) => sendMessage(active.id, text)}
            onToggleImage={(path) =>
              dispatch(toggleTaggedImage({ sessionId: active.id, path }))
            }
          />
        ) : (
          <div className="p-6 text-gray-500">
            No chat sessions. Click on New Chat to create one...
          </div>
        )}
      </div>
    </div>
  );
}