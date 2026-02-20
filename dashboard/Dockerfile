FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    net-tools \
    iputils-ping \
    iproute2 \
    sudo \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir streamlit docker pandas

COPY app_v2.py /app/app.py

WORKDIR /app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
