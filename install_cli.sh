#!/bin/bash

# Agent CLI Installation Script
# This script creates a symlink to make the 'agent' command available system-wide

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Installing Agent CLI...${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_PATH="$SCRIPT_DIR/src/cli.py"

# Check if the CLI script exists
if [ ! -f "$CLI_PATH" ]; then
    echo -e "${RED}❌ CLI script not found at: $CLI_PATH${NC}"
    exit 1
fi

# Check if the CLI script is executable
if [ ! -x "$CLI_PATH" ]; then
    echo -e "${YELLOW}⚠️  Making CLI script executable...${NC}"
    chmod +x "$CLI_PATH"
fi

# Create symlink in /usr/local/bin (requires sudo)
echo -e "${YELLOW}📁 Creating symlink in /usr/local/bin...${NC}"
sudo ln -sf "$CLI_PATH" /usr/local/bin/agent

# Verify installation
if command -v agent &> /dev/null; then
    echo -e "${GREEN}✅ Agent CLI installed successfully!${NC}"
    echo -e "${GREEN}📍 You can now use: agent 'your question here'${NC}"
    echo ""
    echo -e "${YELLOW}Usage examples:${NC}"
    echo "  agent 'What is a kilonova?'"
    echo "  agent --interactive"
    echo "  agent --status"
    echo "  agent --help"
else
    echo -e "${RED}❌ Installation failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Installation complete!${NC}"
