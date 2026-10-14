/** @type {import('next').NextConfig} */
const nextConfig = {
  poweredByHeader: false,
  output: "standalone",
  async redirects() {
    return [{ source: "/assessment", destination: "/dashboard", permanent: false }];
  },
  async rewrites() {
    const backend = (process.env.API_PROXY_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;