FROM python:3.11-slim

WORKDIR /hostlife

COPY config /hostlife/config
COPY models /hostlife/models
COPY nginx /hostlife/nginx
COPY routes /hostlife/routes
COPY static /hostlife/static
COPY templates /hostlife/templates
COPY utils /hostlife/utils
COPY __init__.py run.py gunicorn.conf.py /hostlife/
COPY requirements.txt /hostlife

# Install system dependencies including Docker CLI
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --trusted-host pypi.python.org -r requirements.txt