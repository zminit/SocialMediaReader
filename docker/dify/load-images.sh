#!/bin/bash
# Load Dify Docker images from a tar file (for offline/cloud deployment)
# Usage: ./load-images.sh [tar_file]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAR_FILE="${1:-$SCRIPT_DIR/images/dify-images.tar}"

if [ ! -f "$TAR_FILE" ]; then
  echo "✗ Image tar file not found: $TAR_FILE"
  echo ""
  echo "Usage: $0 [path/to/dify-images.tar]"
  echo ""
  echo "Generate it on your local machine first:"
  echo "  ./save-images.sh"
  exit 1
fi

SIZE=$(du -h "$TAR_FILE" | cut -f1)
echo "=== Loading Dify Docker images ==="
echo "Source: $TAR_FILE ($SIZE)"
echo ""

docker load -i "$TAR_FILE"

echo ""
echo "✓ All images loaded!"
echo ""
echo "Loaded images:"
docker images --format "  {{.Repository}}:{{.Tag}}\t{{.Size}}" | grep -E "(dify|postgres|redis|nginx|weaviate|squid|busybox)" || true
echo ""
echo "Next step: cd $SCRIPT_DIR && docker compose up -d"
