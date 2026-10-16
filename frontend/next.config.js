/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${process.env.BACKEND_URL || "http://127.0.0.1:8000"}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
