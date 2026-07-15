"use client";

interface MessageBubbleProps {
  sender: string;
  text: string;
  color: string;
  avatarLetter: string;
  isUser?: boolean;
}

function renderText(text: string): string {
  return text
    .replace(
      /---\n([\s\S]*?)\n---/g,
      (_, code: string) =>
        `<pre>${code.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>`
    )
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br>");
}

export default function MessageBubble({
  sender,
  text,
  color,
  avatarLetter,
  isUser = false,
}: MessageBubbleProps) {
  const avatarBg = isUser ? "rgba(240,192,96,0.15)" : `${color}22`;
  const avatarColor = isUser ? "var(--accent)" : color;
  const bubbleClass = isUser ? "user-bubble" : "ai-bubble";
  const senderLabel = isUser ? "You" : sender;

  return (
    <div className={`message ${isUser ? "user-msg" : ""}`}>
      <div
        className="msg-avatar"
        style={{ background: avatarBg, color: avatarColor }}
      >
        {isUser ? "Y" : avatarLetter}
      </div>
      <div className="msg-content">
        <div className="msg-sender">{senderLabel}</div>
        <div
          className={`msg-bubble ${bubbleClass}`}
          dangerouslySetInnerHTML={{ __html: renderText(text) }}
        />
      </div>
    </div>
  );
}
