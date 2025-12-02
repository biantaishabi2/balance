# 数据源接入工具设计文档

## 概述

为 fm CLI 添加 `data` 命令，支持从多个金融数据源获取实时/历史数据，为 DCF、LBO、M&A 等模型提供输入。

```
fm data - 金融数据获取

用法: fm data <subcommand> [options]

子命令:
  fetch      获取数据
  search     搜索标的
  sources    列出支持的数据源
```

---

## 1. 命令结构

### 1.1 总体架构

```
fm data
├── fetch                  # 获取数据
│   ├── --source           # 数据源 (yahoo/eastmoney/tushare/akshare)
│   ├── --ticker           # 股票代码
│   ├── --metric           # 指标类型
│   └── --period           # 时间范围
│
├── search                 # 搜索标的
│   ├── --source           # 数据源
│   └── --query            # 搜索关键词
│
└── sources                # 列出数据源
    └── --verbose          # 详细信息
```

### 1.2 支持的数据源

| 数据源 | 覆盖范围 | 认证方式 | 限制 |
|--------|----------|----------|------|
| `yahoo` | 美股/港股/部分A股 | 无需 | 免费，有频率限制 |
| `eastmoney` | A股/港股/基金 | 无需 | 免费 |
| `akshare` | A股/港股/期货/宏观 | 无需 | 开源免费 |
| `tushare` | A股全面数据 | Token | 积分制，需注册 |

---

## 2. fm data fetch

### 2.1 基本用法

```bash
# 获取股票行情
fm data fetch --source yahoo --ticker AAPL --metric price

# 获取财务数据
fm data fetch --source eastmoney --ticker 600519 --metric financial

# 获取历史数据
fm data fetch --source yahoo --ticker MSFT --metric price --period 1y
```

### 2.2 指标类型 (--metric)

#### 行情数据 (price)
```bash
fm data fetch --source yahoo --ticker AAPL --metric price
```

**输出:**
```json
{
  "ticker": "AAPL",
  "source": "yahoo",
  "timestamp": "2025-12-02T10:30:00Z",
  "data": {
    "price": 234.56,
    "change": 2.34,
    "change_pct": 0.0101,
    "volume": 45678900,
    "market_cap": 3560000000000,
    "pe_ratio": 28.5,
    "eps": 8.23,
    "52w_high": 245.00,
    "52w_low": 168.00
  }
}
```

#### 财务报表 (financial)
```bash
fm data fetch --source eastmoney --ticker 600519 --metric financial --period 3y
```

**输出:**
```json
{
  "ticker": "600519",
  "source": "eastmoney",
  "data": {
    "income_statement": [
      {
        "period": "2024",
        "revenue": 150000000000,
        "gross_profit": 135000000000,
        "operating_income": 105000000000,
        "net_income": 85000000000,
        "eps": 67.68
      }
    ],
    "balance_sheet": [
      {
        "period": "2024",
        "total_assets": 280000000000,
        "total_liabilities": 85000000000,
        "total_equity": 195000000000,
        "cash": 180000000000
      }
    ],
    "cash_flow": [
      {
        "period": "2024",
        "operating_cf": 90000000000,
        "investing_cf": -5000000000,
        "financing_cf": -70000000000,
        "free_cash_flow": 85000000000
      }
    ]
  }
}
```

#### 估值指标 (valuation)
```bash
fm data fetch --source yahoo --ticker AAPL --metric valuation
```

**输出:**
```json
{
  "ticker": "AAPL",
  "data": {
    "pe_ttm": 28.5,
    "pe_forward": 25.2,
    "pb": 45.3,
    "ps": 7.8,
    "ev_ebitda": 21.4,
    "ev_revenue": 7.2,
    "dividend_yield": 0.0052,
    "peg_ratio": 2.1
  }
}
```

#### 历史价格 (history)
```bash
fm data fetch --source yahoo --ticker AAPL --metric history --period 1y --interval daily
```

**输出:**
```json
{
  "ticker": "AAPL",
  "data": [
    {"date": "2025-12-01", "open": 232.0, "high": 235.5, "low": 231.0, "close": 234.56, "volume": 45678900},
    {"date": "2025-11-29", "open": 230.0, "high": 233.0, "low": 229.5, "close": 232.22, "volume": 38900000}
  ]
}
```

### 2.3 时间范围选项

```bash
--period 1d    # 1天
--period 5d    # 5天
--period 1m    # 1个月
--period 3m    # 3个月
--period 6m    # 6个月
--period 1y    # 1年
--period 3y    # 3年
--period 5y    # 5年
--period max   # 全部历史
```

---

## 3. fm data search

搜索股票/基金代码

```bash
fm data search --source eastmoney --query "贵州茅台"
fm data search --source yahoo --query "Apple"
```

**输出:**
```json
{
  "results": [
    {"ticker": "600519", "name": "贵州茅台", "exchange": "SH", "type": "stock"},
    {"ticker": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "type": "stock"}
  ]
}
```

---

## 4. 原子工具

### 4.1 工具列表

| 工具名 | 功能 | 所需参数 |
|--------|------|----------|
| `fetch_price` | 获取实时行情 | ticker, source |
| `fetch_financial` | 获取财务报表 | ticker, source, period |
| `fetch_valuation` | 获取估值指标 | ticker, source |
| `fetch_history` | 获取历史价格 | ticker, source, period, interval |
| `search_ticker` | 搜索标的 | query, source |
| `fetch_macro` | 获取宏观数据 | indicator, source |
| `fetch_industry` | 获取行业数据 | industry, metric |

### 4.2 工具详情

#### fetch_price
```bash
fm tool run fetch_price <<EOF
{
  "ticker": "AAPL",
  "source": "yahoo"
}
EOF
```

#### fetch_financial
```bash
fm tool run fetch_financial <<EOF
{
  "ticker": "600519",
  "source": "eastmoney",
  "period": "3y",
  "statements": ["income", "balance", "cashflow"]
}
EOF
```

#### fetch_macro
```bash
fm tool run fetch_macro <<EOF
{
  "indicator": "gdp_growth",
  "country": "CN",
  "source": "akshare"
}
EOF
```

---

## 5. 与其他命令集成

### 5.1 管道用法

```bash
# 获取数据 → DCF估值
fm data fetch --source yahoo --ticker AAPL --metric financial | fm dcf calc

# 获取数据 → 比率分析
fm data fetch --source eastmoney --ticker 600519 --metric financial | fm ratio calc --type all

# 批量获取 → 对比分析
for ticker in AAPL MSFT GOOGL; do
  fm data fetch --source yahoo --ticker $ticker --metric valuation
done | jq -s '.'
```

### 5.2 LLM 调用示例

```
用户: 帮我分析苹果公司的估值

LLM 调用:
1. fm data fetch --source yahoo --ticker AAPL --metric financial
2. fm data fetch --source yahoo --ticker AAPL --metric valuation
3. fm ratio calc --type profitability < financial.json
4. fm dcf calc < prepared_input.json
```

---

## 6. 实现架构

### 6.1 模块结构

```
balance/
├── fm.py                      # CLI 入口
├── data_sources/
│   ├── __init__.py
│   ├── base.py               # 基础类
│   ├── yahoo.py              # Yahoo Finance
│   ├── eastmoney.py          # 东方财富
│   ├── akshare_source.py     # AKShare
│   └── tushare_source.py     # Tushare
└── tools/
    └── data_tools.py         # 原子工具
```

### 6.2 基础类设计

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class DataSource(ABC):
    """数据源基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """数据源名称"""
        pass

    @abstractmethod
    def fetch_price(self, ticker: str) -> Dict:
        """获取实时行情"""
        pass

    @abstractmethod
    def fetch_financial(self, ticker: str, period: str) -> Dict:
        """获取财务报表"""
        pass

    @abstractmethod
    def search(self, query: str) -> List[Dict]:
        """搜索标的"""
        pass
```

### 6.3 依赖库

```
yfinance>=0.2.0      # Yahoo Finance
akshare>=1.10.0      # AKShare (A股/宏观)
tushare>=1.2.0       # Tushare (可选，需Token)
requests>=2.28.0     # HTTP请求
```

---

## 7. 错误处理

```json
{
  "error": true,
  "code": "TICKER_NOT_FOUND",
  "message": "找不到股票代码: INVALID",
  "source": "yahoo"
}
```

| 错误码 | 说明 |
|--------|------|
| `TICKER_NOT_FOUND` | 股票代码不存在 |
| `SOURCE_UNAVAILABLE` | 数据源不可用 |
| `RATE_LIMITED` | 请求频率超限 |
| `AUTH_REQUIRED` | 需要认证 |
| `NETWORK_ERROR` | 网络错误 |

---

## 8. 配置文件

`~/.fm/config.yaml`:
```yaml
data_sources:
  tushare:
    token: "your_tushare_token"

  default_source: yahoo

  cache:
    enabled: true
    ttl: 300  # 缓存5分钟
```
