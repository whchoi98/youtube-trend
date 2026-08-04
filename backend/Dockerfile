# 스테이지 1: 프론트 빌드
FROM node:22-slim AS fe
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 스테이지 2: 런타임 (ARM64 — CDK가 platform 지정)
FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=fe /fe/dist ./static
ENV STATIC_DIR=/srv/static
EXPOSE 8000
# --factory: create_app 팩토리 사용. dev_app은 Settings.from_env()를 읽는다.
CMD ["uvicorn", "app.main:dev_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
