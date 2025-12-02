# -*- coding: utf-8 -*-
"""
财务建模工具包

提供:
- 三表模型工具 (ThreeStatementModel)
- DCF估值工具 (DCFModel)
- 高级功能 (DeferredTax, Impairment, LeaseCapitalization)
- 场景管理器 (ScenarioManager)

每个计算都带追溯信息，支持完整的依赖链追溯。

使用示例:
    from financial_model import ThreeStatementModel, DCFModel, ScenarioManager

    # 三表模型
    model = ThreeStatementModel(base_data)
    result = model.build(assumptions)

    # DCF估值
    dcf = DCFModel()
    valuation = dcf.valuate(inputs)

    # 场景管理
    sm = ScenarioManager(base_data)
    sm.add_scenario("base_case", assumptions)
    comparison = sm.compare_scenarios()
"""

from .core import ModelCell, ModelResult, FinancialModel
from .models import (
    ThreeStatementModel,
    DCFModel,
    DeferredTax,
    Impairment,
    LeaseCapitalization,
    ScenarioManager
)
from .io import ExcelWriter

__version__ = "0.1.0"
__all__ = [
    'ModelCell',
    'ModelResult',
    'FinancialModel',
    'ThreeStatementModel',
    'DCFModel',
    'DeferredTax',
    'Impairment',
    'LeaseCapitalization',
    'ScenarioManager',
    'ExcelWriter'
]
