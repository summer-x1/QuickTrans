#!/bin/bash
set -e

echo "=== QuickTrans Installer ==="
echo

# 1. Check Python 3.9+
if ! python3 -c "import sys; assert sys.version_info >= (3,9)" 2>/dev/null; then
    echo "Error: Python 3.9+ is required."
    echo "Install via: https://www.python.org/downloads/"
    exit 1
fi
PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python $PYTHON_VER detected."

# 2. Install dependencies
echo "Installing PyObjC..."
pip3 install --user pyobjc-framework-Cocoa pyobjc-framework-Quartz 2>&1 | tail -1

# 3. Create config directory
CONFIG_DIR="$HOME/.config/quicktrans"
mkdir -p "$CONFIG_DIR"

# 4. Determine project directory
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 5. Create launcher script
LAUNCHER="/usr/local/bin/quicktrans"
echo
echo "Creating launcher at $LAUNCHER..."
if [ -w "/usr/local/bin" ]; then
    cat > "$LAUNCHER" << LAUNCH
#!/bin/bash
exec python3 -m quicktrans "\$@"
LAUNCH
    chmod +x "$LAUNCHER"
else
    sudo tee "$LAUNCHER" > /dev/null << LAUNCH
#!/bin/bash
export PYTHONPATH="$PROJECT_DIR:\$PYTHONPATH"
exec python3 -m quicktrans "\$@"
LAUNCH
    sudo chmod +x "$LAUNCHER"
fi

# 6. Add PYTHONPATH to shell profile if needed
SHELL_RC="$HOME/.zshrc"
if [ -f "$HOME/.bashrc" ] && [ "$SHELL" = "/bin/bash" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if ! grep -q "QUICKTRANS" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# QuickTrans" >> "$SHELL_RC"
    echo "export PYTHONPATH=\"$PROJECT_DIR:\$PYTHONPATH\"" >> "$SHELL_RC"
    echo "# Auto-start QuickTrans daemon (singleton via PID lock)" >> "$SHELL_RC"
    echo "(quicktrans &) 2>/dev/null" >> "$SHELL_RC"
    echo "Added auto-start to $SHELL_RC"
fi

echo
echo "=== Installation Complete ==="
echo
echo "IMPORTANT: macOS Permissions Required"
echo "--------------------------------------"
echo "QuickTrans needs Input Monitoring to detect text selection."
echo
echo "  System Settings → Privacy & Security → Input Monitoring"
echo "  → Enable your Terminal app (Terminal.app / iTerm2)"
echo
echo "For Accessibility API text capture (optional but recommended):"
echo
echo "  System Settings → Privacy & Security → Accessibility"
echo "  → Enable your Terminal app"
echo
echo "--------------------------------------"
echo "Run 'quicktrans' to start."
echo "On first run, you'll be asked for your DeepL API key."
