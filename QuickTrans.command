#!/bin/bash
set -u

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}"

cd "$PROJECT_DIR" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 未安装，无法启动 QuickTrans。"
    echo "请先安装 Python 3.9+：https://www.python.org/downloads/"
    echo
    read -n 1 -s -r -p "按任意键关闭..."
    echo
    exit 1
fi

python3 -m quicktrans "$@"
STATUS=$?

if [ "$STATUS" -ne 0 ]; then
    echo
    echo "QuickTrans 已退出，状态码：$STATUS"
    read -n 1 -s -r -p "按任意键关闭..."
    echo
fi

exit "$STATUS"
