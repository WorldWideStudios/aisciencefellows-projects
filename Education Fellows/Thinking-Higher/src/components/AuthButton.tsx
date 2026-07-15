"use client";

import { useSession, signOut } from "next-auth/react";
import Link from "next/link";

export default function AuthButton() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return (
      <div
        style={{
          fontSize: "11px",
          color: "var(--muted)",
          fontFamily: "'IBM Plex Mono', monospace",
        }}
      >
        ...
      </div>
    );
  }

  if (session?.user) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "10px",
        }}
      >
        {session.user.image && (
          <img
            src={session.user.image}
            alt=""
            width={24}
            height={24}
            style={{
              borderRadius: "50%",
              border: "1px solid var(--border)",
            }}
          />
        )}
        <span
          style={{
            fontSize: "11px",
            color: "var(--text)",
            fontFamily: "'IBM Plex Mono', monospace",
            maxWidth: "120px",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {session.user.name || session.user.email}
        </span>
        <button
          onClick={() => signOut()}
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            color: "var(--muted)",
            padding: "4px 10px",
            borderRadius: "6px",
            fontSize: "10px",
            fontFamily: "'IBM Plex Mono', monospace",
            cursor: "pointer",
            transition: "border-color 0.2s, color 0.2s",
            letterSpacing: "0.04em",
          }}
          onMouseEnter={(e) => {
            const btn = e.currentTarget;
            btn.style.borderColor = "var(--accent)";
            btn.style.color = "var(--accent)";
          }}
          onMouseLeave={(e) => {
            const btn = e.currentTarget;
            btn.style.borderColor = "var(--border)";
            btn.style.color = "var(--muted)";
          }}
        >
          Sign Out
        </button>
      </div>
    );
  }

  return (
    <Link
      href="/auth/signin"
      style={{
        fontSize: "11px",
        color: "var(--accent)",
        fontFamily: "'IBM Plex Mono', monospace",
        textDecoration: "none",
        padding: "4px 10px",
        border: "1px solid var(--accent)",
        borderRadius: "6px",
        transition: "background 0.2s, color 0.2s",
        letterSpacing: "0.04em",
      }}
      onMouseEnter={(e) => {
        const link = e.currentTarget;
        link.style.background = "var(--accent)";
        link.style.color = "var(--bg)";
      }}
      onMouseLeave={(e) => {
        const link = e.currentTarget;
        link.style.background = "transparent";
        link.style.color = "var(--accent)";
      }}
    >
      Sign In
    </Link>
  );
}
