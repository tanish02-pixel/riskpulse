FROM node:24-alpine AS dashboard
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY data/ ./data/
COPY run.py ./
COPY frontend/public/ ./frontend/public/
COPY --from=dashboard /web/dist ./frontend/dist
ENV HOST=0.0.0.0 PORT=8000 SENTIMENT_BACKEND=lexicon
EXPOSE 8000
CMD ["python","run.py"]

