/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.BACKEND_URL || 'http://seo-analysis-backend:8000'}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
