/** @type {import('next').NextConfig} */
function normalizeBaseUrl(url) {
  if (!url) return ''
  return url.endsWith('/') ? url.slice(0, -1) : url
}

const backendUrl = normalizeBaseUrl(process.env.API_URL || process.env.BACKEND_URL || 'http://localhost:8000')

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/:path*`,
      },
    ]
  },
}

module.exports = nextConfig;
