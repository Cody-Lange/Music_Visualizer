FROM python:3.11-slim

WORKDIR /app

# Mesa EGL/GL for headless ModernGL rendering (EGL backend).
# OSMesa is not needed — the code uses backend="egl" explicitly.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libegl1 \
    libgles2 \
    libgl1-mesa-dri \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/storage

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
