import { useState, useEffect, useRef } from "react";
import { useDispatch } from "react-redux";
import { markMessageTyped, type ChatMessage } from "../store/chatSlice";
import { scrollIntoView } from "../utils";

/**
 * Hook to handle typing effect for model messages.
 * Gradually reveals text character by character.
 *
 * @param m - Chat message object
 * @param sessionId - Current session ID
 * @param isAtBottom - Whether the chat is scrolled to bottom
 * @param scrollContainerRef - Ref to the scrollable chat container
 */
export function useTyping({
  m,
  sessionId,
  isAtBottom,
  scrollContainerRef,
}: {
  m: ChatMessage;
  sessionId: string;
  isAtBottom: boolean;
  scrollContainerRef: React.RefObject<HTMLDivElement | null>;
}) {
  const dispatch = useDispatch();

  const isUser = m.role === "user";
  const isNew = !isUser && !m.typed; // New model message

  // State to track typed text
  const [typedText, setTypedText] = useState<string>(isUser || !isNew ? m.content : "");
  // State to track if typing is finished
  const [isTypingComplete, setIsTypingComplete] = useState<boolean>(!isNew);
  // State to show images after typing
  const [showImages, setShowImages] = useState<boolean>(!!m.typed);

  const charIndex = useRef<number>(0); // Current character index
  const rafRef = useRef<number | null>(null); // requestAnimationFrame reference
  const dispatchedMarkRef = useRef<boolean>(false); // Prevent multiple dispatches

  // Keep a mutable ref of isAtBottom to use inside animation loop
  const isAtBottomRef = useRef<boolean>(isAtBottom);
  useEffect(() => {
    isAtBottomRef.current = isAtBottom;
  }, [isAtBottom]);

  useEffect(() => {
    if (!isNew) {
      // Already typed messages
      setTypedText(m.content);
      setIsTypingComplete(true);
      if (m.typed) setShowImages(true);
      return;
    }

    // Reset state for new messages
    setTypedText("");
    setIsTypingComplete(false);
    setShowImages(false);
    dispatchedMarkRef.current = false;
    charIndex.current = 0;

    let prevTime = performance.now();

    const step = (time: number) => {
      const currentChar = m.content[charIndex.current - 1];

      // Dynamic delay based on punctuation/space/newline
      let dynamicDelay = 12;
      if (currentChar === "." || currentChar === "!" || currentChar === "?") dynamicDelay = 100;
      else if (currentChar === "," || currentChar === ";") dynamicDelay = 40;
      else if (currentChar === " ") dynamicDelay = 8;
      else if (currentChar === "\n") dynamicDelay = 60;

      // Add small randomization for natural typing feel
      dynamicDelay += (Math.random() - 0.5) * dynamicDelay * 0.25;

      if (time - prevTime >= dynamicDelay) {
        charIndex.current += 1;
        setTypedText(m.content.slice(0, charIndex.current));
        prevTime = time;
      }

      if (charIndex.current < m.content.length) {
        rafRef.current = requestAnimationFrame(step);
        return;
      }

      // Finished typing
      setTypedText(m.content);
      setIsTypingComplete(true);

      // Show images and mark message as typed
      setTimeout(() => {
        if (m.images?.length) {
          setShowImages(true);
        } else if (!dispatchedMarkRef.current) {
          dispatch(markMessageTyped({ sessionId, messageId: m.id }));
          dispatchedMarkRef.current = true;
          if (isAtBottomRef.current) scrollIntoView(scrollContainerRef);
        }
      }, 300);
    };

    rafRef.current = requestAnimationFrame(step);

    // Cleanup on unmount
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    };
  }, [m.content, m.id, m.typed, sessionId, dispatch, scrollContainerRef, isNew]);

  return {
    typedText,
    isTypingComplete,
    showImages,
    setShowImages,
    dispatchedMarkRef,
  };
}
