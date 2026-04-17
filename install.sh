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
echo
if [ -w "/usr/local/bin" ]; then
    LAUNCHER="/usr/local/bin/quicktrans"
    echo "Creating launcher at $LAUNCHER..."
    cat > "$LAUNCHER" << LAUNCH
#!/bin/bash
export PYTHONPATH="$PROJECT_DIR:\$PYTHONPATH"
exec python3 -m quicktrans "\$@"
LAUNCH
    chmod +x "$LAUNCHER"
else
    LAUNCHER="$HOME/.local/bin/quicktrans"
    echo "Creating launcher at $LAUNCHER..."
    mkdir -p "$HOME/.local/bin"
    cat > "$LAUNCHER" << LAUNCH
#!/bin/bash
export PYTHONPATH="$PROJECT_DIR:\$PYTHONPATH"
exec python3 -m quicktrans "\$@"
LAUNCH
    chmod +x "$LAUNCHER"
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
echo "Accessibility is also required to capture selected text."
echo
echo "  System Settings → Privacy & Security → Accessibility"
echo "  → Enable your Terminal app"
echo
echo "--------------------------------------"
echo "Start QuickTrans in either way:"
echo "  1. Double-click $PROJECT_DIR/QuickTrans.command"
echo "  2. Run 'quicktrans' in Terminal"
echo
if [ "$LAUNCHER" = "$HOME/.local/bin/quicktrans" ]; then
    echo "Launcher installed to $LAUNCHER"
    echo "If 'quicktrans' is not found, add this to your shell profile:"
    echo "  export PATH=\"$HOME/.local/bin:\$PATH\""
    echo
fi
echo "Auto-start is no longer enabled by default."
echo "If you want it, add this line to your shell profile manually:"
echo "  (quicktrans &) 2>/dev/null"
echo "On first run, you'll be asked to choose a provider and enter API config."
