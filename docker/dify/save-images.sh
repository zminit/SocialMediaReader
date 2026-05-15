#!/bin/bash
# Save all Dify Docker images to a tar file for offline deployment
# Usage: ./save-images.sh [output_dir]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${1:-$SCRIPT_DIR/images}"
OUTPUT_FILE="$OUTPUT_DIR/dify-images.tar"

mkdir -p "$OUTPUT_DIR"

# Get image list from docker-compose.yaml
IMAGES=(
  "langgenius/dify-api:1.14.1"
  "langgenius/dify-web:1.14.1"
  "langgenius/dify-sandbox:0.2.15"
  "langgenius/dify-plugin-daemon:0.6.0-local"
  "postgres:15-alpine"
  "redis:6-alpine"
  "nginx:latest"
  "semitechnologies/weaviate:1.27.0"
  "ubuntu/squid:latest"
  "busybox:latest"
)

echo "=== Saving Dify Docker images ==="
echo "Output: $OUTPUT_FILE"
echo ""

# Check all images exist locally
for img in "${IMAGES[@]}"; do
  if ! docker image inspect "$img" > /dev/null 2>&1; then
    echo "⚠ Image not found locally: $img"
    echo "  Run 'docker compose pull' first"
    exit 1
  fi
  echo "✓ Found: $img"
done

echo ""
echo "Saving ${#IMAGES[@]} images to $OUTPUT_FILE ..."
docker save -o "$OUTPUT_FILE" "${IMAGES[@]}"

# Show file size
SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
echo ""
echo "✓ Done! Saved $OUTPUT_FILE ($SIZE)"
echo ""
echo "To deploy on cloud server:"
echo "  1. scp $OUTPUT_FILE user@server:/path/to/"
echo "  2. On server: docker load -i /path/to/dify-images.tar"
echo "  3. On server: cd docker/dify && docker compose up -d"
