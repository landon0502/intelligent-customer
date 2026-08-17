# ===== 构建阶段：pnpm install + next build =====
FROM node:22-slim AS builder
WORKDIR /repo

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm install -g pnpm@10.33.4

# 仅拷贝 manifest，先装依赖（层缓存友好）
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/ packages/
RUN pnpm install --frozen-lockfile

# 拷贝源码（.dockerignore 已排除 .next/node_modules/.env*）
COPY apps/web ./apps/web

# NEXT_PUBLIC_* 编译期注入，必须作为 build ARG
ARG NEXT_PUBLIC_API_URL=http://localhost:8009
ARG NEXT_PUBLIC_API_BASE_URL=/api
ENV NODE_ENV=production \
    NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

RUN pnpm --filter web build

# ===== 运行阶段：standalone 自包含 =====
FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000

# Next 16（Turbopack）+ pnpm monorepo 的 standalone 输出保留 apps/web 子路径，
# server.js 位于 <standalone>/apps/web/server.js，.next/static 与 public 同理
COPY --from=builder /repo/apps/web/.next/standalone ./
COPY --from=builder /repo/apps/web/.next/static ./apps/web/.next/static
# 项目目录名是 pubilc（拼写如此），standalone 期望 public
COPY --from=builder /repo/apps/web/pubilc ./apps/web/public
WORKDIR /app/apps/web

EXPOSE 3000
CMD ["node", "server.js"]
