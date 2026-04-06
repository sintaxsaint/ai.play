#!/bin/bash
# ai.play Linux installer
# Usage: curl -sSL https://raw.githubusercontent.com/sintaxsaint/ai.play/main/install.sh | bash

set -e

echo ""
echo " ai.play v0.8 — Linux installer"
echo " github.com/sintaxsaint/ai.play"
echo ""

# Check Python version
PYTHON=$(which python3 || which python)
VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")

if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]; }; then
    echo "Error: Python 3.10 or higher required (found $VERSION)"
    exit 1
fi

echo "Python $VERSION found."

# Install via pip
echo "Installing ai.play..."
$PYTHON -m pip install aiplay --upgrade --quiet

# Verify install
if command -v aip &> /dev/null; then
    echo "Done. Run: aip yourfile.aip"
else
    # pip installed but not in PATH — add it
    PIP_BIN=$($PYTHON -m site --user-base)/bin
    if [ -f "$PIP_BIN/aip" ]; then
        SHELL_RC="$HOME/.bashrc"
        [ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"
        echo "export PATH=\"$PIP_BIN:\$PATH\"" >> "$SHELL_RC"
        export PATH="$PIP_BIN:$PATH"
        echo "Added $PIP_BIN to PATH in $SHELL_RC"
        echo "Done. Restart your terminal or run: source $SHELL_RC"
        echo "Then run: aip yourfile.aip"
    else
        echo "Install complete. If 'aip' is not found, run:"
        echo "  python3 -m aiplay yourfile.aip"
    fi
fi

echo ""
echo "Quick start:"
echo "  echo 'ai.enable()\nai.web(yes)\ntest.ui(yes)' > hello.aip"
echo "  aip hello.aip"
echo ""
echo "Module store: https://sintaxsaint.pages.dev"
echo "Docs: https://github.com/sintaxsaint/ai.play"
