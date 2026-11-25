import { useEffect } from "react";

export default function ImageModal({ src, caption, onClose }) {
  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!src) return null;

  return (
    <div className="lightbox" onClick={onClose}>
      <div className="lightbox-box" onClick={(e) => e.stopPropagation()}>
        <button className="lightbox-close" onClick={onClose} aria-label="Close">✕</button>
        <img className="lightbox-img" src={src} alt="Enlarged photo" />
        {caption && <div className="lightbox-cap">{caption}</div>}
      </div>
    </div>
  );
}
