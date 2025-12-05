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

# 安装 CLI 工具
echo "安装工具..."
TOOLS=(balance excel2json json2excel excel_inspect fm ac fa cf ma ri tx kp)

for tool in "${TOOLS[@]}"; do
    src="$SCRIPT_DIR/${tool}.py"
    if [[ -f "$src" ]]; then
        cp "$src" "$INSTALL_DIR/$tool"
        chmod +x "$INSTALL_DIR/$tool"
        echo "  ✓ $tool"
    else
        echo "  ✗ 缺少 $src" 1>&2
    fi
done

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
    echo "  json2excel     - 将结果写回 Excel"
    echo "  balance        - 三表配平"
    echo "  fm             - 财务建模 (LBO/MA/DCF/三表/比率)"
    echo "  ac             - 会计审计 (试算平衡/调整分录/抽样/合并)"
    echo "  fa             - 财务分析 (预算差异/弹性预算/预测/趋势)"
    echo "  cf             - 现金流 (13周预测/营运资金/驱动因素)"
    echo "  ma             - 管理会计 (成本分摊/CVP/盈亏平衡 等)"
    echo "  ri             - 风险管理 (信用/账龄/减值/汇率)"
    echo "  tx             - 税务 (增值税/企税/个税/年终奖/加计扣除)"
    echo "  kp             - 绩效 (KPI/EVA/BSC/OKR)"
    echo ""
    echo "完整流程:"
    echo "  1. excel_inspect 报表.xlsx          # 先看结构"
    echo "  2. excel2json 报表.xlsx | balance   # 提取+计算"
    echo "  3. ... | json2excel - 报表.xlsx     # 写回"
fi
