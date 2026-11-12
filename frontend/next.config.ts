import type { NextConfig } from "next";

// The browser only talks to this origin. /api/* is forwarded to FastAPI so the
// auth cookies stay first-party (no CORS, no cross-site cookie rules).
const BACKEND = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8010";

const nextConfig: NextConfig = {
  output: "standalone",
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Referrer-Policy", value: "same-origin" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
      ],
    }];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND}/api/:path*` }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
