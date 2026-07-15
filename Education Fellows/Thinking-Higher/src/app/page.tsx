import Link from "next/link";

export default function Home() {
  return (
    <div className="start-screen">
      <div className="start-card">
        {/* <div className="start-tag">COGNITIVE SCIENCE LEARNING PLATFORM</div> */}
        <h1 className="start-title" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
          Think<em>Higher</em>
        </h1>
        <p className="start-desc">
          Play cognitive tasks, immerse in work simulations, see your data modeled in real-time, and get feedback on higher-order thinking and communication skills.
        </p>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <Link
            href="/tasks"
            className="start-btn"
            style={{ textDecoration: "none" }}
          >
            Explore Tasks
          </Link>
          <Link
            href="/simulations"
            className="start-btn"
            style={{
              textDecoration: "none",
              background: "transparent",
              border: "1px solid var(--accent)",
              color: "var(--accent)",
            }}
          >
            Try Work Simulations
          </Link>
        </div>
      </div>
    </div>
  );
}
