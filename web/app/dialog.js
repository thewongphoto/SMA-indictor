"use client";
import { useEffect, useRef } from "react";

export default function Dialog({ children, label, onClose, sheet = false }) {
  const element = useRef(null),
    close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const previous = document.activeElement;
    const focusable = () => [
      ...element.current.querySelectorAll(
        'button:not(:disabled),input:not(:disabled),[tabindex="0"]',
      ),
    ];
    focusable()[0]?.focus();
    function keydown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        close.current?.();
      }
      if (event.key === "Tab") {
        const controls = focusable(),
          first = controls[0],
          last = controls.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    }
    const node = element.current;
    node.addEventListener("keydown", keydown);
    return () => {
      node.removeEventListener("keydown", keydown);
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  return (
    <div
      ref={element}
      className={"overlay" + (sheet ? " sheet-scrim" : "")}
      role="dialog"
      aria-modal="true"
      aria-label={label}
    >
      {children}
    </div>
  );
}
