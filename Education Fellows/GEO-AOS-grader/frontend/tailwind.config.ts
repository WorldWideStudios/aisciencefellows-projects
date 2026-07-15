import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        cream: "#FAF9F5",
        ink: "#0D0D0D",
        navy: "#10101C",
        orange: {
          DEFAULT: "#FA520F",
          bright: "#FF8205",
          red: "#E2330C",
          deep: "#B0190A",
        },
      },
      fontFamily: {
        display: ["var(--font-space-grotesk)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-space-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
