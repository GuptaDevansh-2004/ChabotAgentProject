import React, { useEffect } from "react";

interface ImageViewerProps {
  src: string;
  alt?: string;
  onClose: () => void;
}

export const ImageViewer: React.FC<ImageViewerProps> = ({ src, alt, onClose }) => {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-70 flex justify-center items-center z-50"
      onClick={onClose}
    >
      <img
        src={src}
        alt={alt || "image"}
        className="max-w-[90%] max-h-[90%] rounded-lg shadow-lg animate-fadeIn"
        onClick={(e) => e.stopPropagation()} // prevent closing when clicking image
      />
    </div>
  );
};