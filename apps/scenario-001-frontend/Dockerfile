# 场景 001 前端镜像（Next.js standalone）。由 CI 构建，离线包导入院内。
FROM node:20-alpine AS deps
WORKDIR /app
RUN corepack enable
COPY . .
RUN pnpm install --frozen-lockfile --filter @hospital/scenario-001-frontend...

FROM deps AS build
RUN pnpm --filter @hospital/scenario-001-frontend build

FROM node:20-alpine AS run
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/apps/scenario-001-frontend/.next/standalone ./
COPY --from=build /app/apps/scenario-001-frontend/.next/static ./apps/scenario-001-frontend/.next/static
EXPOSE 3001
CMD ["node", "apps/scenario-001-frontend/server.js"]
