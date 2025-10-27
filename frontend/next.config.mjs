/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    turbo: {
      loaders: {}
    }
  },
  images: {
    unoptimized: true
  }
};

export default nextConfig;
