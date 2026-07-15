"use client";

interface TypingIndicatorProps {
  color: string;
  avatar: string;
  name: string;
}

export default function TypingIndicator({
  color,
  avatar,
  name,
}: TypingIndicatorProps) {
  return (
    <div className="message">
      <div
        className="msg-avatar"
        style={{ background: `${color}22`, color }}
      >
        {avatar}
      </div>
      <div className="msg-content">
        <div className="msg-sender">{name}</div>
        <div className="msg-bubble ai-bubble">
          <div className="typing-indicator">
            <div className="typing-dot" />
            <div className="typing-dot" />
            <div className="typing-dot" />
          </div>
        </div>
      </div>
    </div>
  );
}
