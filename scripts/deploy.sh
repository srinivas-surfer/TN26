#!/usr/bin/env bash
# deploy.sh — Complete EC2 t2.micro setup script
# Run as: bash deploy.sh
# Assumes: Amazon Linux 2023 or Ubuntu 22.04

set -euo pipefail
echo "═══════════════════════════════════════════════════"
echo "  TN26 Election Intelligence — EC2 Deployment"
echo "═══════════════════════════════════════════════════"

# ── 1. System update ──────────────────────────────────────
echo "[1/7] Updating system..."
sudo apt-get update -qq && sudo apt-get upgrade -y -qq 2>/dev/null || \
sudo yum update -y -q 2>/dev/null || true

# ── 2. Install Docker ─────────────────────────────────────
echo "[2/7] Installing Docker..."
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  sudo systemctl enable docker --now
fi

# Install Docker Compose v2
if ! docker compose version &>/dev/null; then
  sudo mkdir -p /usr/local/lib/docker/cli-plugins
  COMPOSE_VER="2.27.1"
  ARCH=$(uname -m)
  sudo curl -SL \
    "https://github.com/docker/compose/releases/download/v${COMPOSE_VER}/docker-compose-linux-${ARCH}" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

echo "Docker version: $(docker --version)"
echo "Compose version: $(docker compose version)"

# ── 3. Configure swap (CRITICAL for t2.micro) ────────────
echo "[3/7] Configuring 1GB swap (essential for t2.micro)..."
if [ ! -f /swapfile ]; then
  sudo fallocate -l 1G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  sudo sysctl vm.swappiness=10
  echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
  echo "Swap configured."
else
  echo "Swap already exists."
fi
free -h

# ── 4. Open firewall ports ────────────────────────────────
echo "[4/7] Configuring firewall..."
sudo ufw allow 80/tcp 2>/dev/null || true
sudo ufw allow 22/tcp 2>/dev/null || true
# Note: Configure EC2 Security Group to allow port 80 from 0.0.0.0/0

# ── 5. Clone / copy project ──────────────────────────────
echo "[5/7] Setting up project..."
PROJECT_DIR="$HOME/TN26"
if [ ! -d "$PROJECT_DIR" ]; then
  echo "  ERROR: Project directory not found at $PROJECT_DIR"
  echo "  Please upload project files first:"
  echo "    scp -r ./TN26 ec2-user@<IP>:~/"
  exit 1
fi
cd "$PROJECT_DIR"

# ── 6. Train models (offline, before API starts) ─────────
echo "[6/7] Training ML models..."
# Remove old image to force fresh build
docker rmi tn2026_backend 2>/dev/null || true
docker compose build --no-cache backend
docker compose run --rm backend python train.py
echo "  ✓ Models trained and saved"

# ── 7. Launch all services ────────────────────────────────
echo "[7/7] Launching containers..."
docker compose up -d

# Wait for health
echo "  Waiting for services to be healthy..."
sleep 15
docker compose ps

# ── Final status ──────────────────────────────────────────
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "<your-ip>")
echo ""
echo "═══════════════════════════════════════════════════"
echo "  ✓ TN26 deployed successfully!"
echo ""
echo "  Dashboard:  http://${PUBLIC_IP}"
echo "  API docs:   http://${PUBLIC_IP}/api/docs"
echo "  Health:     http://${PUBLIC_IP}/api/health"
echo ""
echo "  View logs:  docker compose logs -f backend"
echo "  Stop:       docker compose down"
echo "═══════════════════════════════════════════════════"
