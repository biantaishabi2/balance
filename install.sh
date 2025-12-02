#!/bin/bash
# 安装财务三表配平工具到 ~/.local/bin

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.local/bin"

# 检查依赖
echo "检查依赖..."
if ! python3 -c "import openpyxl" 2>/dev/null; then
    echo "  安装 openpyxl..."
    pip install openpyxl -q
fi
echo "  ✓ openpyxl"

# 创建目录
mkdir -p "$INSTALL_DIR"

# 安装三个工具
echo "安装工具..."

cp "$SCRIPT_DIR/balance.py" "$INSTALL_DIR/balance"
chmod +x "$INSTALL_DIR/balance"
echo "  ✓ balance"

cp "$SCRIPT_DIR/excel2json.py" "$INSTALL_DIR/excel2json"
chmod +x "$INSTALL_DIR/excel2json"
echo "  ✓ excel2json"

cp "$SCRIPT_DIR/json2excel.py" "$INSTALL_DIR/json2excel"
chmod +x "$INSTALL_DIR/json2excel"
echo "  ✓ json2excel"

cp "$SCRIPT_DIR/excel_inspect.py" "$INSTALL_DIR/excel_inspect"
chmod +x "$INSTALL_DIR/excel_inspect"
echo "  ✓ excel_inspect"

# 检查 PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo ""
    echo "提示: 请将 $INSTALL_DIR 加入 PATH"
    echo "运行: echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
else
    echo ""
    echo "✓ 安装成功！"
    echo ""
    echo "可用命令:"
    echo "  excel_inspect  - 查看 Excel 结构"
    echo "  excel2json     - 从 Excel 提取数据"
    echo "  balance        - 配平计算"
    echo "  json2excel     - 将结果写回 Excel"
    echo ""
    echo "完整流程:"
    echo "  1. excel_inspect 报表.xlsx          # 先看结构"
    echo "  2. excel2json 报表.xlsx | balance   # 提取+计算"
    echo "  3. ... | json2excel - 报表.xlsx     # 写回"
fi
