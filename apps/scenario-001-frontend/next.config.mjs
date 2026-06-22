/** @type {import('next').NextConfig} */
// 每个场景前端挂载在 /scenario-001 路径下，由网关聚合托管（静态导出）。
const nextConfig = {
  basePath: "/scenario-001",
  output: "export",
  transpilePackages: ["@hospital/ui", "@hospital/sdk", "@hospital/shared-types"],
  images: { unoptimized: true },
};
export default nextConfig;
