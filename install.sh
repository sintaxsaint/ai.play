#!/bin/bash
# ai.play Linux installer
# Usage: curl -sSL https://raw.githubusercontent.com/sintaxsaint/ai.play/main/install.sh | bash

set -e

echo ""
echo " ai.play v0.8 — Linux installer"
echo " github.com/sintaxsaint/ai.play"
echo ""

# Check Python version
PYTHON=$(which python3 2>/dev/null || which python 2>/dev/null)
if [ -z "$PYTHON" ]; then
    echo "Error: Python 3.10+ is required but was not found."
    exit 1
fi

VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")

if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]; }; then
    echo "Error: Python 3.10 or higher required (found $VERSION)"
    exit 1
fi

echo "Python $VERSION found."

# Install directory
INSTALL_DIR="$HOME/.aiplay"
mkdir -p "$INSTALL_DIR"

# Download Python source files directly from the repo
echo "Downloading ai.play..."
BASE="https://raw.githubusercontent.com/sintaxsaint/ai.play/main/python"
FILES=(
    aiplay.py lexer.py parser.py ast_nodes.py interpreter.py runtime.py
    format_detector.py memory_engine.py skills_engine.py module_engine.py
    user_memory.py server.py ui_server.py intent_engine.py voice_engine.py
    video_engine.py notify_engine.py vision_trainer.py ai_yes.py
    call_handler.py admin_engine.py mcp_engine.py sandbox_engine.py
)

for f in "${FILES[@]}"; do
    curl -sSL "$BASE/$f" -o "$INSTALL_DIR/$f"
done

echo "Files installed to $INSTALL_DIR"

# Install required Python dependencies
echo "Installing dependencies..."
$PYTHON -m pip install scikit-learn flask requests --quiet

# Create aip wrapper script
WRAPPER=$(cat <<'WRAPEOF'
#!/bin/bash
exec python3 "$HOME/.aiplay/aiplay.py" "$@"
WRAPEOF
)

# Try /usr/local/bin first, fall back to ~/.local/bin
if [ -w "/usr/local/bin" ]; then
    echo "$WRAPPER" > /usr/local/bin/aip
    chmod +x /usr/local/bin/aip
    echo "Installed: /usr/local/bin/aip"
else
    mkdir -p "$HOME/.local/bin"
    printf '#!/bin/bash\nexec python3 "%s/aiplay.py" "$@"\n' "$INSTALL_DIR" > "$HOME/.local/bin/aip"
    chmod +x "$HOME/.local/bin/aip"
    echo "Installed: $HOME/.local/bin/aip"

    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        SHELL_RC="$HOME/.bashrc"
        [ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"
        echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_RC"
        export PATH="$HOME/.local/bin:$PATH"
        echo "Added ~/.local/bin to PATH in $SHELL_RC"
        echo "Restart your terminal or run: source $SHELL_RC"
    fi
fi

echo ""
echo "Done. Run: aip yourfile.aip"
echo ""
echo "Quick start:"
echo "  aip hello.aip"
echo ""
echo "Module store: https://sintaxsaint.pages.dev"
echo "Docs: https://github.com/sintaxsaint/ai.play"
