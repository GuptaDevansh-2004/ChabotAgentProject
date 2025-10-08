import { useState, useRef, useLayoutEffect } from "react";
import { type ChatMessage } from "../store/chatSlice";
import { TextMessage } from "./TextMessage.tsx";
import { ImageMessage } from "./ImageMessage.tsx";
import { ImageViewer } from "./ImageViewer.tsx";
import { useAutoScroll, useTyping } from "../hooks";
import { motion } from "framer-motion";

interface MessageBubbleProps {
  m: ChatMessage;
  sessionId: string;
  relatedPaths: string[];
  onToggleImage: (path: string) => void;
  scrollContainerRef: React.RefObject<HTMLDivElement | null>;
  isAtBottom: boolean;
}

export default function MessageBubble({
  m,
  sessionId,
  relatedPaths,
  onToggleImage,
  scrollContainerRef,
  isAtBottom,
}: MessageBubbleProps) {
  const isUser = m.role === "user";
  const isNew = !isUser && !m.typed;

  const bubbleRef = useRef<HTMLDivElement | null>(null);

  const textRef = useRef<HTMLDivElement | null>(null);
  const [textWidth, setTextWidth] = useState<number | null>(null);

  useLayoutEffect(() => {
    const el = textRef.current;
    if (!el) return;

    const update = () => {
      const w = Math.round(el.getBoundingClientRect().width);
      setTextWidth(w);
    };
    update();

    // observe future size changes (responsive, font load, etc)
    const ro = new ResizeObserver(update);
    ro.observe(el);

    return () => ro.disconnect();
  }, []);

  const {
    typedText,
    isTypingComplete,
    showImages,
    dispatchedMarkRef,
  } = useTyping({ m, sessionId, isAtBottom, scrollContainerRef });

  useAutoScroll({
    observeRef: bubbleRef,
    enabled: isAtBottom,
    targetRef: scrollContainerRef,
    delay: 50,
  });

  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const handleImageClick = (src: string) => setImageSrc(src);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`} ref={bubbleRef}>
      <div
        className={`self-start max-w-[60%] rounded-2xl px-4 py-3 font-noto-serif text-[0.951rem]/[1.4rem] shadow-lg space-y-4
          ${isUser ? "bg-blue-500 text-zinc-50" : "bg-gradient-to-br from-white via-white to-gray-50 text-slate-800"}`}
        style={{
          opacity: !isUser && isNew && typedText.length === 0 ? 0.85 : 1,
          transform: !isUser && isNew && typedText.length === 0 ? "scale(0.993)" : "scale(1)",
          transition: "opacity 180ms linear, transform 200ms ease-out",
          willChange: "transform, opacity",
          contain: "layout paint"
        }}
      >
        <div className="leading-relaxed flex" ref={textRef}>
          <TextMessage text={typedText} isUser={isUser} />
        </div>
        
        {(isTypingComplete || isUser) && m.images?.length !== 0 && (
          <motion.div
            className={`
              ${isUser ? "bg-blue-100" : "bg-neutral-100"}
              overflow-x-auto flex gap-3 px-3 py-3 rounded-2xl scrollbar-ambient
            `}
            initial={isNew ? { height: 0, opacity: 0 } : { height: "auto", opacity: 1 }}
            animate={isNew ? { height: "auto", opacity: 1 } : { height: "auto", opacity: 1 }}
            transition={
              isNew
                ? { height: { duration: 0.1, ease: "linear" }, opacity: { duration: 0.3 } }
                : { duration: 0 }
            }
            style={{ 
              overflowY: "hidden",
              maxWidth: textWidth !== null ? `${textWidth + 10}px` : "100%",
            }}
            layout={false}
          >
            <ImageMessage
              sessionId={sessionId}
              messageId={m.id}
              images={m.images}
              showImages={showImages}
              isUser={isUser}
              typed={m.typed}
              relatedPaths={relatedPaths}
              onToggleImage={onToggleImage}
              handleImageClick={handleImageClick}
              scrollRef={scrollContainerRef}
              dispatchedMarkRef={dispatchedMarkRef}
            />
          </motion.div>
        )}
      </div>

      {imageSrc && <ImageViewer src={imageSrc} onClose={() => setImageSrc(null)} />}
    </div>
  );
}