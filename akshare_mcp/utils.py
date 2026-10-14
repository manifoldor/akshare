"""Utility functions for formatting stock data and codes."""

from typing import Any, Dict, List, Optional, Union
import re


# 常见 A 股股票名称与代码静态快速映射（加速查询并作为离线兜底）
COMMON_A_STOCKS: Dict[str, str] = {
    "贵州茅台": "600519",
    "茅台": "600519",
    "宁德时代": "300750",
    "比亚迪": "002594",
    "平安银行": "000001",
    "中国平安": "601318",
    "五粮液": "000858",
    "招商银行": "600036",
    "中信证券": "600030",
    "东方财富": "300059",
    "中芯国际": "688981",
    "工业富联": "601138",
    "赛力斯": "601127",
    "长江电力": "600900",
    "美的集团": "000333",
    "海康威视": "002415",
    "立讯精密": "002475",
    "紫金矿业": "601899",
    "隆基绿能": "601012",
    "中兴通讯": "000063",
    "科大讯飞": "002230",
    "药明康德": "603259",
    "迈瑞医疗": "300760",
    "格力电器": "000651",
    "京东方A": "000725",
    "三花智控": "002050",
    "中际旭创": "300308",
    "天孚通信": "300394",
    "新易盛": "300502",
    "寒武纪": "688256",
}

# 常见指数代码与名称映射
INDEX_MAP: Dict[str, str] = {
    "sh000001": "上证指数",
    "000001": "上证指数",
    "上证指数": "000001",
    "大盘": "000001",
    "sz399001": "深证成指",
    "399001": "深证成指",
    "深证成指": "399001",
    "sz399006": "创业板指",
    "399006": "创业板指",
    "创业板指": "399006",
    "sh000688": "科创50",
    "000688": "科创50",
    "科创50": "000688",
    "sh000300": "沪深300",
    "000300": "沪深300",
    "沪深300": "000300",
    "sh000905": "中证500",
    "000905": "中证500",
    "中证500": "000905",
    "bj899050": "北证50",
    "899050": "北证50",
    "北证50": "899050",
}


def normalize_symbol(symbol: str) -> str:
    """标准化股票代码为 6 位数字格式。

    例如：
    - 'sh600519' -> '600519'
    - 'SZ000001' -> '000001'
    - '贵州茅台' -> '600519'
    """
    symbol = symbol.strip()
    if symbol in COMMON_A_STOCKS:
        return COMMON_A_STOCKS[symbol]

    # 去除 sh/sz/bj 前缀
    m = re.match(r"^(?:sh|sz|bj|SH|SZ|BJ)?(\d{6})$", symbol)
    if m:
        return m.group(1)

    # 提取字符串中的 6 位连续数字
    digits = re.findall(r"\b\d{6}\b", symbol)
    if digits:
        return digits[0]

    return symbol


def format_amount(val: Optional[Union[int, float]]) -> str:
    """格式化金额（自动转换为 元/万/亿）。"""
    if val is None or val == "":
        return "-"
    try:
        f = float(val)
        if abs(f) >= 1e8:
            return f"{f / 1e8:.2f} 亿元"
        elif abs(f) >= 1e4:
            return f"{f / 1e4:.2f} 万元"
        else:
            return f"{f:.2f} 元"
    except (ValueError, TypeError):
        return str(val)


def format_volume(val: Optional[Union[int, float]]) -> str:
    """格式化成交量（单位：手）。"""
    if val is None or val == "":
        return "-"
    try:
        f = float(val)
        if abs(f) >= 1e8:
            return f"{f / 1e8:.2f} 亿手"
        elif abs(f) >= 1e4:
            return f"{f / 1e4:.2f} 万手"
        else:
            return f"{f:.0f} 手"
    except (ValueError, TypeError):
        return str(val)


def format_price(val: Optional[Union[int, float]]) -> str:
    """格式化价格。"""
    if val is None or val == "":
        return "-"
    try:
        f = float(val)
        return f"{f:.2f}"
    except (ValueError, TypeError):
        return str(val)


def format_change(change_pct: Optional[Union[int, float]], change_amt: Optional[Union[int, float]] = None) -> str:
    """根据中国 A 股市场习惯格式化涨跌指示：
    - 🔴 红色上涨 (+)
    - 🟢 绿色下跌 (-)
    - ⚪ 平盘 (0.00%)
    """
    if change_pct is None or change_pct == "":
        return "-"
    try:
        pct = float(change_pct)
        amt_str = ""
        if change_amt is not None and change_amt != "":
            amt = float(change_amt)
            amt_str = f" ({'+' if amt > 0 else ''}{amt:.2f})"

        if pct > 0:
            return f"🔴 +{pct:.2f}%{amt_str}"
        elif pct < 0:
            return f"🟢 {pct:.2f}%{amt_str}"
        else:
            return f"⚪ 0.00%{amt_str}"
    except (ValueError, TypeError):
        return str(change_pct)


def render_stock_quote_markdown(data: Dict[str, Any]) -> str:
    """将个股实时行情及五档买卖盘渲染为美观的 Markdown。"""
    name = data.get("name", "未知")
    symbol = data.get("symbol", "")
    price = format_price(data.get("latest_price"))
    change_pct = data.get("change_percent")
    change_amt = data.get("change_amount")
    change_str = format_change(change_pct, change_amt)

    open_price = format_price(data.get("open"))
    prev_close = format_price(data.get("prev_close"))
    high = format_price(data.get("high"))
    low = format_price(data.get("low"))
    volume = format_volume(data.get("volume"))
    amount = format_amount(data.get("amount"))
    turnover_rate = f"{data.get('turnover_rate', '-'):.2f}%" if isinstance(data.get("turnover_rate"), (int, float)) else str(data.get("turnover_rate", "-"))
    pe = f"{data.get('pe_ratio', '-'):.2f}" if isinstance(data.get("pe_ratio"), (int, float)) else str(data.get("pe_ratio", "-"))
    pb = f"{data.get('pb_ratio', '-'):.2f}" if isinstance(data.get("pb_ratio"), (int, float)) else str(data.get("pb_ratio", "-"))
    update_time = data.get("update_time", "实时快照")

    lines = [
        f"### 📈 {name} ({symbol}) 实时行情",
        "",
        f"**最新价格**：**{price} 元** | **涨跌幅度**：**{change_str}**",
        "",
        f"- **今开**：`{open_price}` | **昨收**：`{prev_close}`",
        f"- **最高**：`{high}` | **最低**：`{low}`",
        f"- **成交量**：`{volume}` | **成交额**：`{amount}`",
        f"- **换手率**：`{turnover_rate}` | **市盈率(动)**：`{pe}` | **市净率**：`{pb}`",
        f"- **数据更新时间**：`{update_time}`",
    ]

    bid_ask = data.get("bid_ask")
    if bid_ask and isinstance(bid_ask, dict):
        lines.extend([
            "",
            "#### 📊 五档盘口",
            "| 档位 | 卖价(元) | 卖量(手) | 档位 | 买价(元) | 买量(手) |",
            "|:---|:---|:---|:---|:---|:---|",
        ])
        for i in range(5, 0, -1):
            sell_p = format_price(bid_ask.get(f"sell_{i}_price"))
            sell_v = format_volume(bid_ask.get(f"sell_{i}_volume"))
            buy_p = format_price(bid_ask.get(f"buy_{i}_price"))
            buy_v = format_volume(bid_ask.get(f"buy_{i}_volume"))
            lines.append(f"| 卖{i} | {sell_p} | {sell_v} | 买{i} | {buy_p} | {buy_v} |")

    lines.extend([
        "",
        "> 💡 *提示：红色为上涨，绿色为下跌。数据源自 AKShare 东方财富行情接口，仅供参考，不作为投资决策依据。*"
    ])

    return "\n".join(lines)


def render_kline_markdown(symbol: str, name: str, period: str, records: List[Dict[str, Any]]) -> str:
    """渲染历史 K 线数据摘要及表格。"""
    if not records:
        return f"未查询到股票 {name} ({symbol}) 的 {period} K线数据。"

    lines = [
        f"### 📊 {name} ({symbol}) 历史 {period} K线记录 (最近 {len(records)} 条)",
        "",
        "| 日期 | 开盘价 | 收盘价 | 最高价 | 最低价 | 涨跌幅 | 成交量(手) | 成交额 | 换手率 |",
        "|:---|:---|:---|:---|:---|:---|:---|:---|:---|",
    ]

    # 倒序展示最近记录（最新的在最前）
    for r in reversed(records[-15:]):
        date = r.get("日期", r.get("date", "-"))
        open_p = format_price(r.get("开盘", r.get("open")))
        close_p = format_price(r.get("收盘", r.get("close")))
        high_p = format_price(r.get("最高", r.get("high")))
        low_p = format_price(r.get("最低", r.get("low")))
        pct = format_change(r.get("涨跌幅", r.get("change_pct")))
        vol = format_volume(r.get("成交量", r.get("volume")))
        amt = format_amount(r.get("成交额", r.get("amount")))
        turnover = f"{r.get('换手率', r.get('turnover', '-'))}%"
        lines.append(f"| {date} | {open_p} | {close_p} | {high_p} | {low_p} | {pct} | {vol} | {amt} | {turnover} |")

    lines.extend([
        "",
        f"*共返回 {len(records)} 条数据，上方表格展示最近 {min(15, len(records))} 个交易日数据。*"
    ])
    return "\n".join(lines)
