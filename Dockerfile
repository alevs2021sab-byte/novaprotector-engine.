
FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    git \
    cmake \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 \
    https://github.com/luau-lang/luau.git /src/luau

RUN cmake -S /src/luau -B /src/luau/build \
    -DCMAKE_BUILD_TYPE=Release

RUN cmake --build /src/luau/build \
    --target Luau.Compile.CLI -j2

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=10000

RUN useradd --create-home appuser

COPY --from=builder /src/luau/build/luau-compile /usr/local/bin/luau-compile

WORKDIR /app

COPY server.py /app/server.py

USER appuser

EXPOSE 10000

CMD ["python", "/
app/server.py"]
