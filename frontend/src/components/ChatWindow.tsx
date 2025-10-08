import React, { useRef, useState, useEffect } from "react";
import { markMessageTyped, markMessageAnimated, type Session } from "../store/chatSlice";
import MessageBubble from "./MessageBubble.tsx";
import { Send } from "lucide-react";
import { useDispatch } from "react-redux";
import { AnimatePresence, motion } from "framer-motion";

export default function ChatWindow({
  session,
  onSend,
  onToggleImage,
}: {
  session: Session;
  onSend: (text: string) => void;
  onToggleImage: (path: string) => void;
}) {
  const [input, setInput] = useState("");
  const dispatch = useDispatch();

  const inputRef = useRef<string>(input);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const [isAtBottom, setIsAtBottom] = useState(true); // Checks if at bottom of chat window
  const msgContainerRef = useRef<HTMLDivElement>(null);

  // Attaches a scroll event to element handling scroll
  useEffect(() => {
    const container = msgContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const threshold = 50; // px from bottom
      const distanceFromBottom =
        container.scrollHeight - container.scrollTop - container.clientHeight;
      setIsAtBottom(distanceFromBottom < threshold);
    };

    container.addEventListener("scroll", handleScroll);
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    // When session changes (new sessionId), mark all old model messages as typed
    session.messages.forEach((m) => {
      if (m.role === "model" && !m.typed) {
        dispatch(markMessageTyped({ sessionId: session.id, messageId: m.id }));
      }
    });

    // Scroll to bottom of chat window when session changes
    scrollRef.current?.scrollIntoView({ behavior: "auto" }); 
  }, [session.id]);

  // Handles change in content of input
  useEffect(() => {
    inputRef.current = input;
  }, [input]);

  // Auto-focus textarea
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const textarea = textareaRef.current;
      if (!textarea || document.activeElement === textarea) return;

      // Trigger if a alphanumeric character and NO modifier keys
      const isPrintableChar = e.key.length === 1 && !e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey;
      // Refocus if Backspace/Delete pressed and non-empty textarea is not active
      const isBackspaceOrDelete = ["Backspace", "Delete"].includes(e.key) && inputRef.current.length > 0;

      if (isPrintableChar || isBackspaceOrDelete) textarea.focus();
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleSend = (e?: React.FormEvent) => {
    e?.preventDefault();
    const t = input.trim();
    if (!t) return;
    onSend(t);
    // Delay input reset so bubble animates first
    setTimeout(() => setInput(""), 200);
  };

  const onKeyDownInputArea = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const { key, shiftKey, currentTarget } = e;
    // Enter key (send message)
    if (key === "Enter" && !shiftKey) {
      e.preventDefault();
      if (!session.loading) {
        handleSend();
        currentTarget.blur();
      }
    }
    else if (["Backspace", "Delete"].includes(key) && input.length === 0) {
      // Keys that blur when textarea is empty
      currentTarget.blur();
    }
    else if (key === "Escape") {
      currentTarget.blur();
    }
  };

  return (
    <div key={session.id} className="flex flex-col h-full gap-0.5">
      <div 
        key={session.id} 
        ref={msgContainerRef}
        className="flex-1 overflow-auto p-4 space-y-3 bg-gradient-to-br from-slate-50 via-sky-50 to-slate-50 scrollbar-ambient shadow-inner"
      >
        {session.messages.length === 0 && <div className="text-gray-500">Please type message to start conversation....</div>}
        {/* If last message has images, show modals as well */}
        {session.messages.map((m, num) => {
          const isLatestUserMsg = m.role === "user" && !m.animated;
          const prev = num > 0 ? session.messages[num - 1] : null;
          const isNewTurn = m.role === "user" && prev?.role === "model";

          const messageBubble = (
            <div key={m.id} className={`${isNewTurn && "mt-13"} ${m.role === "user" && "mb-4"}`}>
              <MessageBubble 
                key={m.id}
                m={m} 
                sessionId={session.id} 
                relatedPaths={session.related_images} 
                onToggleImage={(path) => onToggleImage(path)}
                scrollContainerRef={msgContainerRef}
                isAtBottom={isAtBottom}
              />
            </div>
          );

          if (isLatestUserMsg) { 
            return (
              <AnimatePresence initial={false}>
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, translateY: 30 }}
                  animate={{ opacity: 1, translateY: 0 }}
                  transition={{ duration: 0.4, ease: "easeInOut", delay: 0.1 }}
                  onAnimationComplete={() => {
                    dispatch(markMessageAnimated({ sessionId: session.id, messageId: m.id }));
                    // Smoothly autoscroll to bottom of window new user message added with delay
                    setTimeout(() => {
                      scrollRef.current?.scrollIntoView({ behavior: "smooth" });
                    }, 50);
                  }}
                >
                  {messageBubble}
                </motion.div>
              </AnimatePresence>
            );
          }

          return messageBubble;

        })}
        <div ref={scrollRef} />
      </div>

      <motion.div>
        <form onSubmit={handleSend} className="p-3 flex gap-2 rounded transition-all duration-300 border-l border-r border-t-2 border-b border-white items-end bg-gradient-to-br from-blue-100 via-blue-100 to-blue-300">
          <div className="w-full flex gap-2 items-center bg-white rounded-xl shadow p-2">
            <textarea
              ref={textareaRef}
              className="flex-1 border-none rounded-xl p-3 transition-all duration-300 min-h-[48px] h-13 focus:h-20 max-h-40 resize-none focus:outline-none overflow-y-auto font-sans text-[0.99rem] ease-in-out"
              placeholder="Type your message…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDownInputArea}
            />
            <button 
              type="submit"  
              className="px-4.5 py-3.5 rounded-lg bg-[color:var(--color-primary)] text-white flex items-center justify-center hover:bg-[color:var(--color-secondary)] disabled:bg-gray-400 cursor-pointer disabled:cursor-not-allowed active:scale-96 transition shadow-md hover:shadow-lg" 
              disabled={session.loading || input.trim() === ""}>
              <Send className="w-6.5 h-6.5" />
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
