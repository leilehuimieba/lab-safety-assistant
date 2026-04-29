# LabSafe Assistant — 产品化容器镜像
# ===================================
# 构建：docker build -t lab-safe-assistant:latest .
# 运行：docker run -d -p 8088:8088 --env-file .env.web_demo lab-safe-assistant:latest
#
# 多阶段构建：
#   - builder 阶段：编译安装依赖（含 torch 等二进制包）
#   - runtime 阶段：最小化运行镜像，剔除编译工具

# ------------------------------------------------------------------
# Stage 1: Builder
# ------------------------------------------------------------------
FROM python:3.13-slim AS builder

WORKDIR /build

# 安装构建依赖（部分 Python 包需要编译）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖声明，利用 Docker 缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ------------------------------------------------------------------
# Stage 2: Runtime
# ------------------------------------------------------------------
FROM python:3.13-slim AS runtime

LABEL org.opencontainers.image.title="LabSafe Assistant"
LABEL org.opencontainers.image.description="实验室安全助手 Web Demo"
LABEL org.opencontainers.image.source="https://github.com/leilehuimieba/lab-safety-assistant"

WORKDIR /app

# 安装运行时必要的系统包
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制已安装的 Python 包
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 复制项目代码（按变更频率排序，尽量命中缓存）
COPY web_demo/ ./web_demo/
COPY libs/ ./libs/
COPY scripts/ ./scripts/
COPY data_sources/ ./data_sources/
COPY knowledge_base_curated.csv .
COPY safety_rules.yaml .
COPY eval_set_v1.csv .
COPY retrieval_tuning_report.md .
COPY pytest.ini .

# 创建运行时目录
RUN mkdir -p logs artifacts .cache/embedding .cache/embedding_emergency

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:8088/health || exit 1

# 暴露服务端口
EXPOSE 8088

# 默认启动命令
CMD ["python", "-m", "uvicorn", "web_demo.app:app", "--host", "0.0.0.0", "--port", "8088"]
