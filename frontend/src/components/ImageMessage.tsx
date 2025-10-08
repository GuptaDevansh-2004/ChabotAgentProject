import { motion, type Variants } from "framer-motion";
import ImageModal from "./ImageModal.tsx";
import { useDispatch } from "react-redux";
import { markMessageTyped, type ChatImage } from "../store/chatSlice";
import { scrollIntoView } from "../utils";

/**
 * Generic image grid for displaying model or user images.
 * Preserves:
 * - Staggered Framer animation for model images
 * - Immediate display for user images
 * - markMessageTyped dispatch after model images animate
 */
export const ImageMessage = ({
  images,
  showImages,
  isUser,
  typed,
  sessionId,
  messageId,
  relatedPaths,
  scrollRef,
  onToggleImage,
  handleImageClick,
  dispatchedMarkRef,
}: {
  images?: ChatImage[];
  showImages: boolean;
  isUser: boolean;
  typed?: boolean;
  sessionId?: string;
  messageId?: string;
  relatedPaths: string[];
  onToggleImage: (path: string) => void;
  handleImageClick: (src: string) => void;
  scrollRef: React.RefObject<HTMLElement | null>;
  dispatchedMarkRef: { current: boolean };
}) => {
  const dispatch = useDispatch();

  // Framer variants for model images
  const ContainerVariants: Variants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.2, when: "beforeChildren" } },
  };

  const ItemVariants: Variants = {
    hidden: { opacity: 0, y: 8 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
  };

  if (!images || images.length === 0) return null;

  // model images with animation
  if (!isUser && showImages) {
    return (
      <div className="max-w-full">
        <motion.div
          className="flex gap-2 overflow-x-auto scrollbar-ambient snap-x snap-mandatory overflow-y-hidden"
          variants={ContainerVariants}
          initial={typed ? "show" : "hidden"}
          animate={typed ? "show" : showImages ? "show" : "hidden"}
          onAnimationComplete={() => {
            // Only dispatch once for newly-typed model messages
            if (!dispatchedMarkRef?.current && !typed && sessionId && messageId) {
              dispatchedMarkRef.current = true;
              dispatch(markMessageTyped({ sessionId, messageId }));
              // Final scroll after images loads
              scrollIntoView(scrollRef);
            }
          }}
        >
          {images.map((img) => (
            <motion.div 
              key={img.path} 
              variants={ItemVariants} 
              className="flex-shrink-0 snap-start w-40"
            >
              <ImageModal
                image={img}
                relatedPaths={relatedPaths}
                onToggleImage={onToggleImage}
                handleImageClick={handleImageClick}
              />
            </motion.div>
          ))}
        </motion.div>
      </div>
    );
  }

  // User images displayed immediately (no animation)
  if (isUser && !showImages) {
    return (
      <div className="flex gap-2 overflow-x-auto scrollbar-ambient snap-x snap-mandatory overflow-y-hidden">
        {images.map((img) => (
          <div className="flex-shrink-0 snap-start w-40">
            <ImageModal
              key={img.path}
              image={img}
              relatedPaths={relatedPaths}
              onToggleImage={onToggleImage}
              handleImageClick={handleImageClick}
            />
          </div>
        ))}
      </div>
    );
  }

  return null;
}