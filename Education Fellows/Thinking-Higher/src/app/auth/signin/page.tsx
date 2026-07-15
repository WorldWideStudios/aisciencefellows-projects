"use client";

import { signIn } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function SignInContent() {
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/";

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg)",
        padding: "24px",
      }}
    >
      <div
        style={{
          maxWidth: "400px",
          width: "100%",
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontFamily: "'Syne', sans-serif",
            fontWeight: 700,
            fontSize: "24px",
            letterSpacing: "0.05em",
            color: "var(--accent)",
            marginBottom: "8px",
          }}
        >
          Think<span style={{ color: "var(--text)" }}>Higher</span>
        </div>

        <h1
          style={{
            fontFamily: "'Syne', sans-serif",
            fontSize: "20px",
            fontWeight: 600,
            color: "var(--text)",
            marginBottom: "8px",
            marginTop: "32px",
          }}
        >
          Sign in to ThinkHigher
        </h1>

        <p
          style={{
            fontSize: "12px",
            color: "var(--muted)",
            marginBottom: "32px",
            lineHeight: 1.6,
          }}
        >
          Sign in to save your results and get email reports
        </p>

        <button
          onClick={() => signIn("google", { callbackUrl })}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "12px",
            width: "100%",
            padding: "12px 24px",
            background: "#ffffff",
            color: "#3c4043",
            border: "1px solid #dadce0",
            borderRadius: "8px",
            fontSize: "14px",
            fontFamily: "'IBM Plex Mono', monospace",
            fontWeight: 500,
            cursor: "pointer",
            transition: "box-shadow 0.2s",
          }}
          onMouseEnter={(e) => {
            (e.target as HTMLButtonElement).style.boxShadow =
              "0 1px 3px rgba(0,0,0,0.2)";
          }}
          onMouseLeave={(e) => {
            (e.target as HTMLButtonElement).style.boxShadow = "none";
          }}
        >
          <svg width="18" height="18" viewBox="0 0 48 48">
            <path
              fill="#EA4335"
              d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
            />
            <path
              fill="#4285F4"
              d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
            />
            <path
              fill="#FBBC05"
              d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
            />
            <path
              fill="#34A853"
              d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
            />
          </svg>
          Continue with Google
        </button>

        <p
          style={{
            fontSize: "10px",
            color: "var(--muted)",
            marginTop: "24px",
            lineHeight: 1.6,
          }}
        >
          You can also use ThinkHigher without signing in.
          <br />
          <a
            href="/"
            style={{
              color: "var(--accent)",
              textDecoration: "none",
            }}
          >
            Continue as guest
          </a>
        </p>
      </div>
    </div>
  );
}

export default function SignInPage() {
  return (
    <Suspense
      fallback={
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "var(--bg)",
            color: "var(--muted)",
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: "12px",
          }}
        >
          Loading...
        </div>
      }
    >
      <SignInContent />
    </Suspense>
  );
}
