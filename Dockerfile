FROM rust:1.90-slim AS aion

RUN cargo install aion-context --locked

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080 \
    CARE_COMPASS_MODEL=gemma4:e4b \
    OLLAMA_HOST=http://host.docker.internal:11434

WORKDIR /app

COPY --from=aion /usr/local/cargo/bin/aion /usr/local/bin/aion
COPY app ./app
COPY care_compass ./care_compass
COPY care-pack ./care-pack
COPY scripts ./scripts
COPY tests ./tests
COPY README.md ./README.md

EXPOSE 8080

CMD ["python3", "app/server.py"]
