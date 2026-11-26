import type { NextConfig } from 'next';

/** The six product pages became three modules on 2026-11-27. Old links keep working. */
const retiredProducts: Record<string, string> = {
  cases: '/products/verify/',
  audit: '/products/verify/',
  literature: '/products/radar/',
  reports: '/products/dossier/',
  signal: '/products/',
  os: '/platform/',
};

const nextConfig: NextConfig = {
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
  async redirects() {
    return Object.entries(retiredProducts).map(([slug, destination]) => ({
      source: `/products/${slug}`,
      destination,
      permanent: true,
    }));
  },
};

export default nextConfig;
