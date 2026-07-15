import Link from "next/link";
import CatalogCard from "@/components/CatalogCard";

const SIMULATIONS = [
  {
    id: "vela-sde",
    href: "/simulations/vela-junior-sde-001",
    title: "Junior Software Developer at Vela",
    description:
      "Sit in on Monday's team meeting, review Marcus's prototype, then walk Alex through your development approach. Practice higher-order thinking and stakeholder communication.",
    duration: "15–20 min",
    role: "Software Engineering",
    icon: "💻",
    available: true,
  },
  {
    id: "ridgeline-analyst",
    href: "/simulations/ridgeline-university-analyst-001",
    title: "Analyst, Office of the President — Ridgeline Community College",
    description:
      "Dig into enrollment trends and budget pressures with finance and enrollment officers, then present your strategic recommendation directly to the President. Practice analytical reasoning under institutional constraints.",
    duration: "20–30 min",
    role: "Higher Education",
    icon: "🎓",
    available: true,
  },
];

export default function SimulationsPage() {
  return (
    <div className="task-container">
      <div style={{ textAlign: "center", marginBottom: 40 }}>
        <Link href="/" style={{ textDecoration: "none", display: "inline-block", marginBottom: 8 }}>
          <h1 style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 24, fontWeight: 700, color: "var(--text)" }}>
            Think<span style={{ color: "var(--accent)", fontStyle: "italic" }}>Higher</span>
          </h1>
        </Link>
        <p style={{ fontSize: "11px", letterSpacing: "0.15em", textTransform: "uppercase", color: "var(--muted)" }}>
          Work Simulations
        </p>
      </div>

      <div className="catalog-grid">
        {SIMULATIONS.map((sim) => (
          <CatalogCard
            key={sim.id}
            href={sim.href}
            icon={sim.icon}
            title={sim.title}
            description={sim.description}
            badge={sim.role}
            duration={sim.duration}
          />
        ))}
      </div>
    </div>
  );
}
