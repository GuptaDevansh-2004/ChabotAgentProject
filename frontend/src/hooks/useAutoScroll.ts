import { useEffect, useRef } from "react";
import { scrollIntoView } from "../utils";

/**
 * Options for useResizeObserver hook
 */
interface UseAutoScrollOptions {
  /** The element to observe for size changes */
  observeRef: React.RefObject<HTMLElement | null>;
  /** Whether the observer is enabled. Defaults to true */
  enabled?: boolean;
  /** tThe element on which scrolling to execute */
  targetRef: React.RefObject<HTMLElement | null>;
  /** Optional delay in milliseconds before calling the callback (default: 100ms) */
  delay?: number;
}

/**
 * useResizeObserver
 * -----------------
 * A generic hook that observes size changes of an element and triggers a scroller function.
 * Useful for auto-scrolling, layout adjustments, or any logic based on element resize.
 * 
 * @param observeRef - Ref to the element to observe
 * @param enabled - Whether the callback should be triggered (default: true)
 * @param targetRef - Ref of element to execute scrolling
 * @param delay - Delay in milliseconds before calling the callback (default: 100)
 */
export function useAutoScroll({
  observeRef,
  enabled = true,
  targetRef,
  delay = 100,
}: UseAutoScrollOptions) {
  // Keep a mutable ref of the enabled flag to avoid restarting effect unnecessarily
  const enabledRef = useRef(enabled);

  // Update ref whenever enabled changes
  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  useEffect(() => {
    const el = observeRef.current;
    if (!el) return;

    let timeout: ReturnType<typeof setTimeout> | null = null;

    // Create a ResizeObserver to detect size changes
    const observer = new ResizeObserver(() => {
      if (!enabledRef.current) return;

      // Clear any pending callback
      if (timeout) clearTimeout(timeout);

      // Schedule callback after the specified delay
      timeout = setTimeout(() => {
        if (enabledRef.current) scrollIntoView(targetRef);
      }, delay);
    });

    observer.observe(el); // start observing the element

    // Cleanup on unmount or ref change
    return () => {
      observer.disconnect();
      if (timeout) clearTimeout(timeout);
    };
  }, [observeRef, targetRef, delay]);
}