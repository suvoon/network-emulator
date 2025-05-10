FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    net-tools \
    iputils-ping \
    iproute2 \
    openvswitch-switch \
    openvswitch-common \
    openvswitch-testcontroller \
    mininet \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/media /app/staticfiles && \
    chmod -R 755 /app/media /app/staticfiles && \
    mkdir -p /var/run/openvswitch && \
    mkdir -p /etc/openvswitch

# Add Mininet to Python path
ENV PYTHONPATH="${PYTHONPATH}:/usr/lib/python3/dist-packages"

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["/start.sh"]
