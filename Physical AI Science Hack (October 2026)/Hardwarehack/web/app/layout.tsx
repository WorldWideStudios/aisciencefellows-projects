import type { Metadata } from "next";
import { IBM_Plex_Sans, Marcellus } from "next/font/google";
import "./globals.css";

const marcellus = Marcellus({ weight: "400", subsets: ["latin"], variable: "--font-marcellus" });
const plex = IBM_Plex_Sans({ weight: ["400", "500", "600"], subsets: ["latin"], variable: "--font-plex" });

export const metadata: Metadata = {
  title: "Athelas Apothecary",
  description: "Concoctions on demand, mixed by an Opentrons Flex",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${marcellus.variable} ${plex.variable}`}>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
