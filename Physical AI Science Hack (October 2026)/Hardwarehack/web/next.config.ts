import type { NextConfig } from "next";

// The Python API runs on loopback only; the browser talks to this app's own
// origin and Next proxies /api/* to it, so no CORS and nothing on the LAN.
const API_ORIGIN = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // A separate output folder (NEXT_DIST_DIR=.next-test) lets a test build run without
  // touching the .next folder a running `npm run dev` is using.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/:path*` }];
  },
};

export default nextConfig;
