FROM python:3.11-slim

WORKDIR /app

# Mesa EGL/GL packages for headless ModernGL rendering.
# Debian Trixie renamed libegl1-mesa → libegl-mesa0 and
# libosmesa6 → libosmesa6t64.  We install the virtual package
# libegl1 which pulls the correct provider on any Debian version.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libegl1 \
    libgl1-mesa-dri \
    libosmesa6t64 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/storage

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
