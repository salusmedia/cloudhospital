/** @type {import('next').NextConfig} */
const nextConfig = {
  basePath: "/patient",
  output: "export",
  transpilePackages: ["@hospital/ui", "@hospital/sdk", "@hospital/shared-types"],
  images: { unoptimized: true },
};

export default nextConfig;
