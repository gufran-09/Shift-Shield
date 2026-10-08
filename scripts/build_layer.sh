#!/usr/bin/env bash
# Build Lambda dependencies layer inside an Amazon Linux 2023 container
set -euo pipefail

LAYER_DIR="build/layer"
rm -rf "${LAYER_DIR}"
mkdir -p "${LAYER_DIR}/python"

echo "Building Python dependencies layer..."
docker run --rm -v "$PWD:/var/task" public.ecr.aws/sam/build-python3.12:latest \
    pip install -r backend/requirements.txt -t /var/task/${LAYER_DIR}/python --no-cache-dir

cd "${LAYER_DIR}"
zip -r9 ../shiftshield-dependencies-layer.zip python/
echo "Layer package created at build/shiftshield-dependencies-layer.zip"
