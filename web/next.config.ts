import type { NextConfig } from "next";

// A static export: `next build` writes plain HTML/CSS/JS into web/out, which the FastAPI process serves (python -m api).
// No server features are used (data comes from /api in the browser). Cache Components is a server-caching feature, so it is off.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true, // /en/doctor/ -> out/en/doctor/index.html, which a plain static server can serve
  images: { unoptimized: true },
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
