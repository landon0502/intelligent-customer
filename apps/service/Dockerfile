# ===== 阶段 1：安装依赖（含编译 asyncmy） =====
FROM python:3.14-slim AS builder

# asyncmy 0.2.11 仅提供 sdist，需 gcc 编译；libssl-dev 保险
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# uv 官方镜像方式（比 curl 安装脚本更可复现），锁定与本机一致的 0.11.23
COPY --from=ghcr.io/astral-sh/uv:0.11.23 /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 先拷贝 manifest + lock，利用层缓存
COPY apps/service/pyproject.toml apps/service/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 再拷源码，二次 sync（无 [build-system]，仅装依赖不装项目本身）
COPY apps/service/ ./
RUN uv sync --frozen --no-dev

# ===== 阶段 2：精简运行时（去掉 gcc） =====
FROM python:3.14-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.11.23 /uv /uvx /bin/
ENV UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app
# 同基础镜像，venv 内解释器绝对路径一致，可直接复用
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/ /app/

EXPOSE 8009
# 与 Makefile 一致；--no-sync 避免每次启动校验 lockfile
CMD ["uv", "run", "--no-sync", "python", "main.py"]
