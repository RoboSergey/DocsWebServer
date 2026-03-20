#!/bin/bash
# Setup DocsWebServer on a Proxmox LXC (no Docker)
set -e

APP_DIR=/opt/docswebserver
DATA_DIR=/data
SERVICE=/etc/systemd/system/docswebserver.service

echo "=== Installing system dependencies ==="
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv git

echo "=== Copying app files ==="
mkdir -p "$APP_DIR"
cp -r app pyproject.toml "$APP_DIR/"

echo "=== Creating Python venv ==="
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install -q --upgrade pip
"$APP_DIR/venv/bin/pip" install -q "$APP_DIR"

echo "=== Creating data directory ==="
mkdir -p "$DATA_DIR"

echo "=== Generating secret key ==="
SECRET=$("$APP_DIR/venv/bin/python3" -c "import secrets; print(secrets.token_hex(32))")

echo "=== Writing systemd service ==="
cat > "$SERVICE" << SERVICE_EOF
[Unit]
Description=DocsWebServer
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment=DATABASE_PATH=$DATA_DIR/documents.db
Environment=SECRET_KEY=$SECRET
ExecStart=$APP_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE_EOF

echo "=== Enabling and starting service ==="
systemctl daemon-reload
systemctl enable docswebserver
systemctl start docswebserver
systemctl status docswebserver

echo ""
echo "Done! App running at http://$(hostname -I | awk '{print $1}'):8000"
echo "Secret key saved in: $SERVICE"
