import Link from "next/link";
import CatalogCard from "@/components/CatalogCard";

const TASK_CATALOG = [
  {
    id: "bandit-2arm",
    title: "Two-Armed Bandit",
    description:
      "Learn how you balance exploration vs exploitation. Choose between two options with hidden reward rates.",
    duration: "5-8 min",
    category: "Learning & Decision Making",
    icon: "\u{1F3B0}",
  },
  {
    id: "arc-grid",
    title: "ARC Pattern Puzzles",
    description:
      "Solve abstract visual pattern puzzles. Test your fluid intelligence against AI benchmarks.",
    duration: "10-15 min",
    category: "Abstract Reasoning",
    icon: "\u{1F9E9}",
  },
  {
    id: "reversal-learning",
    title: "Reversal Learning",
    description:
      "Can you adapt when the rules change? A 3-arm bandit where the best option flips halfway through.",
    duration: "8-12 min",
    category: "Cognitive Flexibility",
    icon: "\u{1F504}",
  },
  {
    id: "two-step",
    title: "Two-Step Task",
    description:
      "Are you a creature of habit or a strategic planner? Two-stage choices reveal your decision style.",
    duration: "15-20 min",
    category: "Decision Strategy",
    icon: "\u{1F680}",
  },
  {
    id: "hanabi",
    title: "Hanabi",
    description:
      "Cooperative card game with an AI partner. Can you communicate and coordinate when you can't see your own hand?",
    duration: "10-15 min",
    category: "Theory of Mind",
    icon: "\u{1F386}",
  },
  // {
  //   id: "chat-simulation",
  //   title: "Junior Software Developer at Vela",
  //   description:
  //     "Sit in on Monday's team meeting, review Marcus's prototype, then walk Alex through your development approach. Practice higher-order thinking and stakeholder communication.",
  //   duration: "15–20 min",
  //   category: "Software Engineering",
  //   icon: "💻",
  // },
];

export default function TaskCatalogPage() {
  return (
    <div className="task-container">
      <div style={{ textAlign: "center", marginBottom: 40 }}>
        <Link
          href="/"
          style={{
            textDecoration: "none",
            display: "inline-block",
            marginBottom: 8,
          }}
        >
          <h1
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontSize: 24,
              fontWeight: 700,
              color: "var(--text)",
            }}
          >
            Think
            <span style={{ color: "var(--accent)", fontStyle: "italic" }}>
              Higher
            </span>
          </h1>
        </Link>
        <p
          style={{
            fontSize: "11px",
            letterSpacing: "0.15em",
            textTransform: "uppercase" as const,
            color: "var(--muted)",
          }}
        >
          Task Catalog
        </p>
      </div>

      <div className="catalog-grid">
        {TASK_CATALOG.map((task) => {
          const href = `/tasks/${task.id}`;
          return (
            <CatalogCard
              key={task.id}
              href={href}
              icon={task.icon}
              title={task.title}
              description={task.description}
              badge={task.category}
              duration={task.duration}
            />
          );
        })}
      </div>
    </div>
  );
}
