#!/bin/bash
set -e

echo "=== QuickTrans Uninstaller ==="
echo

# 1. Stop running daemon
pkill -f "quicktrans" 2>/dev/null && echo "Stopped running daemon." || true

# 2. Remove launcher
if [ -f "/usr/local/bin/quicktrans" ]; then
    if [ -w "/usr/local/bin/quicktrans" ]; then
        rm -f "/usr/local/bin/quicktrans"
    else
        sudo rm -f "/usr/local/bin/quicktrans"
    fi
    echo "Removed /usr/local/bin/quicktrans"
fi

# 3. Ask about config
read -p "Remove config and logs (~/.config/quicktrans)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$HOME/.config/quicktrans"
    echo "Removed ~/.config/quicktrans"
else
    echo "Config preserved at ~/.config/quicktrans"
fi

# 4. Remind about shell profile
echo
echo "NOTE: Remove the QuickTrans lines from your ~/.zshrc manually:"
echo "  - export PYTHONPATH=... (QuickTrans line)"
echo "  - (quicktrans &) 2>/dev/null"
echo
echo "Uninstall complete."
