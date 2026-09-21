import { useState } from "react";
import { createPortal } from "react-dom";

// Ảnh nhỏ trong bảng — rê chuột là phóng to xem ngay, không cần bấm mới thấy. Bấm vẫn mở ảnh gốc ở
// tab mới. Preview to render thẳng vào document.body (qua portal) để không bị table-wrap cha
// (overflow: hidden, để cuộn ngang trên mobile) cắt mất phần ảnh phóng to.
export default function ImageThumb({ src, size = 24 }) {
  const [hovering, setHovering] = useState(false);
  if (!src) return null;
  return (
    <>
      <a
        href={src}
        target="_blank"
        rel="noreferrer"
        onMouseEnter={() => setHovering(true)}
        onMouseLeave={() => setHovering(false)}
      >
        <img
          src={src}
          alt=""
          style={{ width: size, height: size, objectFit: "cover", borderRadius: 4, border: "1px solid var(--line)" }}
        />
      </a>
      {hovering &&
        createPortal(
          <div
            style={{
              position: "fixed",
              top: 16,
              right: 16,
              zIndex: 1000,
              pointerEvents: "none",
              background: "var(--surface)",
              padding: 6,
              borderRadius: 10,
              border: "1px solid var(--line)",
              boxShadow: "var(--shadow-lg)",
            }}
          >
            <img src={src} alt="" style={{ maxWidth: 320, maxHeight: 320, display: "block", borderRadius: 6 }} />
          </div>,
          document.body
        )}
    </>
  );
}
