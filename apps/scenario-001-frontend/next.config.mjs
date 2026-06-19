/** @type {import('next').NextConfig} */
// 每个场景前端挂载在 /scenario-001 路径下，由门户/网关聚合。
const nextConfig = {
  basePath: "/scenario-001",
  output: "standalone",
};
export default nextConfig;
