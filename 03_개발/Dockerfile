FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
# CPU 전용 torch를 먼저 깔아 이미지가 커지는 걸 막는다
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# 모델 파일은 저장소에 올리지 않으므로 빌드할 때 내려받는다
WORKDIR /app/ml
RUN python -c "from ultralytics import YOLO; YOLO('yolo26n-pose.pt')"
WORKDIR /app/backend
COPY backend/app ./app
COPY --from=web /web/dist /app/frontend/dist
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
