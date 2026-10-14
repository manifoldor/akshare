# AKShare A 股行情查询 Grokbot 插件 (akshare)

[![Standard: Agent Plugins 1.0](https://img.shields.io/badge/standard-Agent%20Plugins%201.0-blue.svg)](https://agent-plugins.org)
[![MCP: Supported](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-green.svg)](https://modelcontextprotocol.io)
[![Data: AKShare](https://img.shields.io/badge/Data%20Source-AKShare-orange.svg)](https://akshare.akfamily.xyz/)

一款专为 **Grokbot**（及遵循 Agent Plugins 1.0 标准和 MCP 协议的智能体环境）量身打造的 **A 股股票价格与行情查询插件**，插件名称为 `akshare`。

插件深度整合 [AKShare](https://github.com/akfamily/akshare) 金融数据接口，让 Grokbot 具备实时股价跟踪、买卖五档盘口分析、历史 K 线回测走势、日内分时波段及大盘指数查询的综合金融分析能力。

---

## 🌟 核心特性

1. **符合 Grokbot & Agent Plugins 1.0 规范**：
   - 完整的清单描述文件 `plugin.json`。
   - 包含 Model Context Protocol 配置 `mcp.json` 与 `mcp_config.json`。
   - 包含规范的智能体技能定义 `skills/akshare-stock/SKILL.md`，内含针对中国 A 股市场特定逻辑（如“红涨绿跌”、交易时段、停复牌等）的引导提示词。
2. **多维度 A 股行情覆盖**：
   - ⚡ **实时股价与五档买卖盘口**：查询买一至买五、卖一至卖五挂单量及价格、成交量、成交额、换手率。
   - 📈 **历史 K 线行情**：支持日线、周线、月线，支持前复权（qfq）、后复权（hfq）与不复权。
   - ⏱️ **日内分时走势**：盘中分时交易数据。
   - 🇨🇳 **大盘综合指数**：上证指数、深证成指、创业板指、科创50、沪深300等核心指数。
   - 🔍 **智能模糊检索**：支持股票简称（如“茅台”、“宁德”、“比亚迪”）与 6 位数字代码互相检索。
   - 🏢 **个股估值与资料**：总市值、流通市值、动态市盈率、市净率、所属行业等。
3. **中国股市本土化适配**：
   - 涨跌指示严格遵循内地规则：🔴 **红色代表上涨 (+)**，🟢 **绿色代表下跌 (-)**。
   - 自动化格式化大额成交量（手、万手、亿手）与成交金额（元、万元、亿元）。

---

## 📁 目录结构

```text
AKShare/
├── plugin.json                 # Grokbot / Agent Plugins 标准元数据清单
├── mcp.json                    # Model Context Protocol 服务注册配置
├── mcp_config.json             # 兼容配置
├── requirements.txt            # Python 依赖清单
├── run_server.py               # 带有虚拟环境自适应检测的 MCP 启动入口
├── skills/                     # 智能体技能定义目录
│   └── akshare-stock/
│       └── SKILL.md            # A股查询决策树、Prompt 引导与业务规范
├── akshare_mcp/                # 核心 Python 插件模块
│   ├── __init__.py
│   ├── server.py               # FastMCP 服务实现（注册各 Tool 函数）
│   ├── client.py               # AKShare 数据封装、本地缓存与容错备选逻辑
│   └── utils.py                # 标准化代码、涨跌指示器、Markdown 表格渲染
└── tests/                      # 单元与集成测试
    └── test_plugin.py
```

---

## 🛠️ 可用 MCP 工具一览

| 工具名称 (Tool) | 说明 | 核心入参 |
| :--- | :--- | :--- |
| `get_stock_quote` | 查询个股实时股价、五档买卖盘口及涨跌幅 | `symbol`: 股票代码（如 `600519`）或股票简称（如 `贵州茅台`） |
| `get_stock_history` | 获取个股历史 K 线走势记录 | `symbol`, `period`('daily'/'weekly'/'monthly'), `start_date`, `end_date`, `adjust`('qfq'/'hfq'/''), `limit` |
| `get_stock_intraday` | 查询今日个股分时成交走势 | `symbol`: 6 位股票代码 |
| `get_index_quote` | 查询大盘及重要指数行情 | `symbol`: 指数代码（如 `000001` 上证指数，`399001` 深证成指） |
| `search_stock` | 模糊搜索股票代码与基本行情 | `keyword`: 公司简称或拼音简写，`limit`: 最大数量 |
| `get_stock_info` | 查询个股总市值、市盈率、行业等基本信息 | `symbol`: 6 位股票代码 |

---

## 🚀 安装与配置指南

### 1. 运行环境准备
本插件基于 Python 3.10+ 开发，推荐在插件根目录下创建虚拟环境并安装依赖：

```bash
# 1. 创建虚拟环境
python3 -m venv .venv

# 2. 激活虚拟环境并安装依赖
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 在 Grokbot / Grok Build 中使用

#### 方式 A：通过本地插件目录加载
在运行 Grokbot 或 Grok Build CLI 时，指定插件所在目录或将其软链接至插件目录：

```bash
# 复制或链接至 Grokbot 插件目录
mkdir -p ~/.grok/plugins
ln -s /path/to/AKShare ~/.grok/plugins/akshare
```

#### 方式 B：配置 `mcp.json`
在 Grokbot 或客户端的 MCP 配置中注册服务：

```json
{
  "mcpServers": {
    "akshare": {
      "command": "python3",
      "args": ["/path/to/AKShare/run_server.py"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

---

## 💡 使用示例与提示词 (Prompts)

您可以直接向 Grokbot 提问：

1. **查询实时股价与盘口**：
   > “帮我查一下贵州茅台现在的实时价格和五档买卖盘口”
   > “查看 000001 平安银行当前涨跌幅是多少”

2. **分析历史行情走势**：
   > “查看宁德时代（300750）最近一个月的日K线走势与涨跌幅”
   > “调取比亚迪近半年的周K线数据，进行前复权分析”

3. **关注宏观大盘走势**：
   > “今天 A 股大盘行情怎么样？上证指数和创业板指当前点位是多少？”

4. **模糊搜索与个股基础分析**：
   > “帮我找一下带有'半导体'的相关股票有哪些”
   > “查询中芯国际的总市值、市盈率和所属行业”

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。数据来源于公开网络财经接口，仅供技术研究与个人参考，不构成任何投资建议。
