/**
 * Scrolls a container element to the bottom.
 *
 * @param ref - reference to React scrollable element.
 * @param behavior - Scroll animation behavior ("auto" | "smooth"), default is "smooth".
 */

export function scrollIntoView<T extends HTMLElement>(
  ref: React.RefObject<T | null>,
  behavior: ScrollBehavior = "smooth"
): void {
  
  const element = ref.current;
  if (!element || element.scrollHeight <= element.clientHeight) return;
  
  element.scrollTo({ top: element.scrollHeight, behavior });
}