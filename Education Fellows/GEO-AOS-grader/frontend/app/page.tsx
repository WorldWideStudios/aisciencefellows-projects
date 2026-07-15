import AosBgCanvas from "./AosBgCanvas"
import AosScanForm from "./AosScanForm"
import styles from "./page.module.css"

const shiftItems = [
  { num: "01", label: "Discovering products" },
  { num: "02", label: "Comparing services" },
  { num: "03", label: "Executing workflows" },
  { num: "04", label: "Making transactions autonomously" },
]

const scoringBlocks = [
  {
    pts: 30,
    title: "Machine Interface",
    desc: "MCP servers, OpenAPI specs, and structured API surfaces that agents can discover and call.",
  },
  {
    pts: 25,
    title: "Browser Operability",
    desc: "Whether an AI browser agent can navigate, interact, and complete tasks on your site.",
  },
  {
    pts: 25,
    title: "Agent Discovery",
    desc: "llms.txt, robots.txt agent permissions, and Schema.org markup that orient AI agents.",
  },
  {
    pts: 20,
    title: "Auth & Security",
    desc: "OAuth flows, CORS policy, and security posture for programmatic agent access.",
  },
]

export default function HomePage() {
  return (
    <>
      <div className={styles.bgFallback} />
      <AosBgCanvas />
      <div className={styles.overlay} />

      <div className={styles.page}>

        {/* ── Nav ── */}
        <div className={styles.navWrap}>
          <nav className={styles.nav}>
            <a href="/" className={styles.brand}>
              <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">
                <circle cx="13" cy="13" r="11.5" stroke="#15110d" strokeWidth="1.4" opacity="0.5" />
                <circle cx="13" cy="13" r="6.5" stroke="#ff5722" strokeWidth="1.6" />
                <circle cx="13" cy="13" r="2" fill="#15110d" />
              </svg>
              <span className={styles.wordmark}>AOS Grader</span>
            </a>

            <div className={styles.navLinks}>
              <a href="#the-shift">The Shift</a>
              <a href="#scoring">Scoring</a>
              <a href="#grader">Grader</a>
            </div>

            <a href="#scan-input" className={styles.navCta}>Run scan</a>
          </nav>
        </div>

        {/* ── Hero ── */}
        <main className={styles.hero}>
          <h1 className={styles.heroH1}>
            See how AI-agents interact with your platform.
          </h1>
          <p className={styles.heroP}>
            AOS Grader probes your platform for machine-readable interfaces, agent
            discovery signals, and authentication flows — then scores how ready it
            is for AI agents to operate.
          </p>
          <div className={styles.formWrap}>
            <AosScanForm inputId="scan-input" />
          </div>
        </main>

        {/* ── The Shift ── */}
        <section className={styles.shift} id="the-shift">
          <div className={styles.shiftInner}>
            <span className={styles.eyebrow}>The Shift</span>
            <h2 className={styles.shiftH2}>A new platform shift is happening</h2>
            <p className={styles.shiftSub}>
              The internet was built for humans. The next generation of platforms
              will be built for <strong>AI agents</strong>.
            </p>

            <p className={styles.layerLabel}>
              AI agents are rapidly becoming a new layer of the internet:
            </p>

            <div className={styles.shiftItems}>
              {shiftItems.map(item => (
                <div key={item.num} className={styles.shiftItem}>
                  <span className={styles.shiftNum}>{item.num}</span>
                  <span className={styles.shiftLabel}>{item.label}</span>
                </div>
              ))}
            </div>

            <div className={styles.shiftClosing}>
              <p className={styles.shiftClosingP}>
                Platforms optimized for AI agents will{" "}
                <span className={styles.hl}>capture the next wave of digital growth</span>.
              </p>
            </div>
          </div>
        </section>

        {/* ── Scoring ── */}
        <section className={styles.scoring} id="scoring">
          <div className={styles.scoringInner}>
            <div className={styles.scoringHead}>
              <div>
                <span className={styles.eyebrow}>Scoring</span>
                <h2 className={styles.scoringH2}>Four dimensions of agent readiness</h2>
              </div>
              <div className={styles.scoringTotal}>
                Weighted to <span className={styles.scoringTotalPts}>100 pts</span> total
              </div>
            </div>

            <div className={styles.scoreGrid}>
              {scoringBlocks.map(block => (
                <div key={block.title} className={styles.scoreCard}>
                  <div className={styles.scorePts}>
                    {block.pts}
                    <span className={styles.scorePtsUnit}>pts</span>
                  </div>
                  <div className={styles.scoreTitle}>{block.title}</div>
                  <p className={styles.scoreDesc}>{block.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Final CTA ── */}
        <section className={styles.cta}>
          <div className={styles.ctaInner}>
            <span className={styles.eyebrow}>Run a scan</span>
            <h2 className={styles.ctaH2}>
              Find out if your platform is ready for the agent era
            </h2>
            <div className={styles.formWrap}>
              <AosScanForm inputId="scan-input-2" />
            </div>
          </div>
        </section>

        {/* ── Footer ── */}
        <footer className={styles.footer}>
          <div className={styles.footerInner}>
            <div className={styles.footerBrand}>
              <svg width="24" height="24" viewBox="0 0 26 26" fill="none" aria-hidden="true">
                <circle cx="13" cy="13" r="11.5" stroke="#15110d" strokeWidth="1.4" opacity="0.45" />
                <circle cx="13" cy="13" r="6.5" stroke="#15110d" strokeWidth="1.5" opacity="0.7" />
                <circle cx="13" cy="13" r="2" fill="#15110d" />
              </svg>
              <span className={styles.footerWordmark}>AOS Grader</span>
            </div>
            <div className={styles.footerTag}>Agent operability scan</div>
          </div>
        </footer>
      </div>
    </>
  )
}
