# Stage 1: 构建前端资源
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# 复制前端依赖文件
COPY frontend/package*.json ./frontend/

# 安装依赖
RUN cd frontend && \
    npm config set registry https://registry.npmjs.org/ && \
    npm ci --only=production

# 复制前端源码
COPY frontend/ ./frontend/

# 复制模板文件供 Tailwind 扫描
COPY templates/ ./templates/

# 构建前端（输出到 blog/static/blog/dist）
RUN cd frontend && npm run build

# 验证构建产物
RUN ls -la /app/blog/static/blog/dist/ && \
    find /app/blog/static/blog/dist -type f | head -10

# Stage 2: 最终镜像
FROM python:3.11-slim  # 使用 slim 版本减小镜像体积

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /code/djangoblog/

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        default-libmysqlclient-dev \
        gettext \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn[gevent]

# 复制应用代码
COPY . .

# 删除可能存在的旧构建产物
RUN rm -rf blog/static/blog/dist

# 从前端构建阶段复制构建好的资源
COPY --from=frontend-builder /app/blog/static/blog/dist /code/djangoblog/blog/static/blog/dist

# 验证前端资源
RUN if [ ! -d "blog/static/blog/dist/css" ]; then \
        echo "ERROR: Frontend assets missing!" && exit 1; \
    fi && \
    echo "Frontend assets verified: $(ls blog/static/blog/dist/ | tr '\n' ' ')"

# 确保 entrypoint 可执行
RUN chmod +x deploy/entrypoint.sh

ENTRYPOINT ["/code/djangoblog/deploy/entrypoint.sh"]
