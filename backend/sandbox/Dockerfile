# The image student code runs in. No network is ever attached to it, and it holds no secrets:
# only compilers, Python and the runner.
FROM python:3.12-slim-bookworm
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc g++ libc6-dev \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /opt/runner /sandbox \
 && chmod 755 /sandbox
COPY runner.py /opt/runner/runner.py
RUN chmod 755 /opt/runner && chmod 644 /opt/runner/runner.py
WORKDIR /sandbox
ENTRYPOINT ["python3", "/opt/runner/runner.py"]
