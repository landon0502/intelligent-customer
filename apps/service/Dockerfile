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
    PYTHONUNBUFFERED=1 \
    # models/embedding.py 的默认值是 mps（macOS 专用），容器里必须显式覆盖成 cpu：
    # 否则不经 compose 直接 docker run 时，首次请求加载 embedding 会因 MPS 不可用而失败
    EMBEDDING_DEVICE=cpu \
    # HF_HOME 必须与 docker-compose 里 hf_cache 卷的挂载点一致：
    # 构建期预下载的权重会随命名卷首次创建被播种进卷里，运行时才不会重新联网拉取。
    # 若两处不一致，预下载就落到了镜像的 /root/.cache 里，被卷挂载挡住，等于白做。
    HF_HOME=/app/.cache/huggingface \
    # 国内直连 huggingface.co 不稳，走镜像站
    HF_ENDPOINT=https://hf-mirror.com

WORKDIR /app
# 同基础镜像，venv 内解释器绝对路径一致，可直接复用
COPY --from=builder /app/.venv /app/.venv
COPY apps/service/ /app/

# data/ 被 .dockerignore 排除（上传文件走 volume），这里建空目录兜底：
# app/lifespan.py 启动时 StaticFiles(directory="data") 要求该目录存在
RUN mkdir -p /app/data/uploads


EXPOSE 8009
# 与 Makefile 一致；--no-sync 避免每次启动校验 lockfile
CMD ["uv", "run", "--no-sync", "python", "main.py"]
