import type { Metadata } from "next";
import Providers from "./providers";
import ThemeToggle from "@/components/ThemeToggle";
import "./globals.css";

export const metadata: Metadata = {
  title: "ThinkHigher — Cognitive Simulation Platform",
  description:
    "AI-driven workplace simulations for practicing higher-order thinking and communication skills.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Syne:wght@400;500;600;700&family=IBM+Plex+Mono:wght@300;400;500&display=swap"
          rel="stylesheet"
        />
        {/* Prevent flash of wrong theme on load */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var t=localStorage.getItem('theme');if(t!=='dark')document.documentElement.setAttribute('data-theme','light');})();`,
          }}
        />
      </head>
      <body>
        <Providers>{children}</Providers>
        <ThemeToggle />
      </body>
    </html>
  );
}
