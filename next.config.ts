import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    cacheComponents: true,
  },
};

export default nextConfig;
