# MediaCrawler — 抖音关键词批量采集工具
# 简化构建：直接使用本地构建好的前端产物（api/webui/）
# 本地构建前端：cd web && npm run build

FROM python:3.11-slim

# Install system dependencies (Chromium for headless browsing, Node.js for execjs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    chromium \
    chromium-driver \
    nodejs \
    npm \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Set Chromium as default browser for Playwright
ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium
ENV CHROME_PATH=/usr/bin/chromium

WORKDIR /app

# Copy dependency files first for cache efficiency
COPY requirements.txt ./requirements.txt
COPY api/requirements.txt ./api-requirements.txt
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r api-requirements.txt

# Copy source code
COPY . .

# Install douyin_scraper package
RUN pip install --no-cache-dir .

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Start API server (also serves Web UI via StaticFiles at /ui/)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
