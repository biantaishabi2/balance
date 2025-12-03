# -*- coding: utf-8 -*-
"""
财务建模工具包

提供:
- 三表模型工具 (ThreeStatementModel)
- DCF估值工具 (DCFModel)
- LBO模型工具 (LBOModel)
- 高级功能 (DeferredTax, Impairment, LeaseCapitalization)
- 场景管理器 (ScenarioManager)
- 原子工具 (tools) - 独立的、可组合的计算工具

每个计算都带追溯信息，支持完整的依赖链追溯。

使用示例:
    from fin_tools import ThreeStatementModel, DCFModel, LBOModel

    # 三表模型
    model = ThreeStatementModel(base_data)
    result = model.build(assumptions)

    # DCF估值
    dcf = DCFModel()
    valuation = dcf.valuate(inputs)

    # LBO模型
    lbo = LBOModel()
    result = lbo.build(inputs)

    # 原子工具（推荐LLM使用）
    from fin_tools.tools import calc_purchase_price, calc_irr
    purchase = calc_purchase_price(100_000_000, 8.0)
    irr = calc_irr([-344_000_000, 0, 0, 0, 0, 880_000_000])
"""

from .core import ModelCell, ModelResult, FinancialModel
from .models import (
    ThreeStatementModel,
    DCFModel,
    LBOModel,
    DeferredTax,
    Impairment,
    LeaseCapitalization,
    ScenarioManager
)
from .io import ExcelWriter
from . import tools

__version__ = "0.1.0"
__all__ = [
    'ModelCell',
    'ModelResult',
    'FinancialModel',
    'ThreeStatementModel',
    'DCFModel',
    'LBOModel',
    'DeferredTax',
    'Impairment',
    'LeaseCapitalization',
    'ScenarioManager',
    'ExcelWriter',
    'tools'
]
