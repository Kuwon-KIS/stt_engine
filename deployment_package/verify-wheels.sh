#!/bin/bash
# RHEL 8.9 Offline Deployment - Wheel Installation Verification

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "RHEL 8.9 Offline STT Engine - Wheel Installation Script"
echo "═══════════════════════════════════════════════════════════════"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
WHEELS_DIR="${1:-.}"
PYTHON_CMD="python3.11"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check Python version
echo -e "\n${YELLOW}[1/5]${NC} Checking Python version..."
if command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    print_status "Python found: $PYTHON_VERSION"
else
    print_error "Python 3.11 not found. Install with: sudo yum install python3.11"
    exit 1
fi

# Check pip
echo -e "\n${YELLOW}[2/5]${NC} Checking pip..."
if $PYTHON_CMD -m pip --version &> /dev/null; then
    PIP_VERSION=$($PYTHON_CMD -m pip --version)
    print_status "pip found: $PIP_VERSION"
else
    print_error "pip not found"
    exit 1
fi

# Count wheels
echo -e "\n${YELLOW}[3/5]${NC} Checking wheel files in $WHEELS_DIR..."
WHEEL_COUNT=$(find "$WHEELS_DIR" -maxdepth 1 -name "*.whl" -type f | wc -l)
if [ $WHEEL_COUNT -gt 0 ]; then
    print_status "Found $WHEEL_COUNT wheel files"
    TOTAL_SIZE=$(du -sh "$WHEELS_DIR" | cut -f1)
    print_status "Total size: $TOTAL_SIZE"
else
    print_warning "No wheel files found in $WHEELS_DIR"
    echo "Make sure to extract wheels-all.tar.gz first:"
    echo "  tar xzf wheels-all.tar.gz"
    exit 1
fi

# Test installation (dry-run)
echo -e "\n${YELLOW}[4/5]${NC} Testing offline installation (dry-run)..."
if $PYTHON_CMD -m pip install --no-index --find-links="$WHEELS_DIR" --dry-run torch fastapi faster-whisper &> /dev/null; then
    print_status "Offline installation test passed"
else
    print_warning "Some packages might have dependency issues"
fi

# Display installation command
echo -e "\n${YELLOW}[5/5]${NC} Installation command:"
echo -e "${GREEN}───────────────────────────────────────────────────${NC}"
echo "$PYTHON_CMD -m pip install --no-index --find-links=\"$WHEELS_DIR\" \\"
echo "  torch torchaudio faster-whisper \\"
echo "  librosa scipy numpy fastapi uvicorn \\"
echo "  requests pydantic huggingface-hub"
echo -e "${GREEN}───────────────────────────────────────────────────${NC}"

# Summary
echo -e "\n${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo "Summary:"
echo "  Python: $(echo $PYTHON_VERSION | awk '{print $NF}')"
echo "  Wheels: $WHEEL_COUNT files, $TOTAL_SIZE"
echo "  Location: $WHEELS_DIR"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"

echo -e "\n${GREEN}Next steps:${NC}"
echo "1. If wheels directory contains split files (wheels-part-*), extract first:"
echo "   cat wheels-part-* | tar xzf -"
echo ""
echo "2. Run pip install (as root or with sudo):"
echo "   $PYTHON_CMD -m pip install --no-index --find-links=. *.whl"
echo ""
echo "3. Verify installation:"
echo "   $PYTHON_CMD -c 'import torch; print(torch.__version__)'"
echo "   $PYTHON_CMD -c 'import faster_whisper; print(\"OK\")'"
echo ""

print_status "Pre-installation check complete!"
