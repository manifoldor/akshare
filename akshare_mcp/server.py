"""MCP Server implementation for AKShare A-share stock price query plugin."""

import json
import logging
import sys
from typing import Optional

# 尝试导入 FastMCP（支持独立 fastmcp 库或 official mcp 库内置 fastmcp）
try:
    from fastmcp import FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        raise ImportError(
            "未能导入 FastMCP。请确保已安装 fastmcp 或 mcp：pip install fastmcp mcp"
        )

from . import client

# 配置日志（输出到 stderr 避免干扰 stdio json-rpc 通信）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("akshare-mcp")

# 初始化 FastMCP 服务实例
mcp = FastMCP("akshare")


@mcp.tool()
def get_stock_quote(symbol: str) -> str:
    """查询指定 A 股个股的最新实时行情、价格变动与五档买卖盘口。

    参数:
        symbol: 股票代码（例如 '600519', '000001'）或股票简称（例如 '贵州茅台', '宁德时代'）

    返回:
        格式化的实时行情与五档盘口 Markdown 文本。
    """
    try:
        data = client.get_stock_quote(symbol)
        return data.get("markdown") or json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"get_stock_quote 错误 ({symbol}): {e}")
        return f"❌ 查询股票行情失败 ({symbol})：{str(e)}"


@mcp.tool()
def get_stock_history(
    symbol: str,
    period: str = "daily",
    start_date: str = "",
    end_date: str = "",
    adjust: str = "qfq",
    limit: int = 30,
) -> str:
    """查询指定 A 股个股的历史 K 线行情数据（日/周/月K线）。

    参数:
        symbol: 股票代码（例如 '600519' 或 '000001'）
        period: K线周期，可选：'daily'（日K线，默认）、'weekly'（周K线）、'monthly'（月K线）
        start_date: 开始日期，格式 'YYYYMMDD'（如 '20240101'），默认自动选取前30个交易日
        end_date: 结束日期，格式 'YYYYMMDD'（如 '20241231'），默认今天
        adjust: 复权方式，可选：'qfq'（前复权，推荐用于分析，默认）、'hfq'（后复权）、''（不复权）
        limit: 最大返回交易日数（默认 30 条）

    返回:
        历史 K 线走势列表与 Markdown 表格。
    """
    try:
        data = client.get_stock_history(
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
            limit=limit,
        )
        return data.get("markdown") or json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"get_stock_history 错误 ({symbol}): {e}")
        return f"❌ 查询历史K线数据失败 ({symbol})：{str(e)}"


@mcp.tool()
def get_stock_intraday(symbol: str) -> str:
    """获取指定 A 股个股今日最新的日内分时成交数据。

    参数:
        symbol: 股票代码（例如 '600519'）

    返回:
        分时行情数据。
    """
    try:
        data = client.get_stock_intraday(symbol)
        records = data.get("records", [])
        if not records:
            return f"暂无股票 {symbol} 今日分时成交数据。"
        return f"### ⏱️ 股票 {symbol} 今日分时走势\n共获取最近 {len(records)} 个分时数据点。\n\n" + json.dumps(
            records, ensure_ascii=False, indent=2
        )
    except Exception as e:
        logger.error(f"get_stock_intraday 错误 ({symbol}): {e}")
        return f"❌ 查询分时走势失败 ({symbol})：{str(e)}"


@mcp.tool()
def get_index_quote(symbol: str = "000001") -> str:
    """获取 A 股重要市场指数的实时行情点位与涨跌幅。

    参数:
        symbol: 指数代码或别名，常见如下：
            - '000001' 或 'sh000001'：上证指数（大盘）
            - '399001' 或 'sz399001'：深证成指
            - '399006' 或 'sz399006'：创业板指
            - '000688' 或 'sh000688'：科创50
            - '000300' 或 'sh000300'：沪深300
            - '000905' 或 'sh000905'：中证500

    返回:
        指数最新点位、涨跌额、涨跌幅及成交量信息。
    """
    try:
        data = client.get_index_quote(symbol)
        return data.get("markdown") or json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"get_index_quote 错误 ({symbol}): {e}")
        return f"❌ 查询大盘指数失败 ({symbol})：{str(e)}"


@mcp.tool()
def search_stock(keyword: str, limit: int = 10) -> str:
    """根据公司名称或股票代码模糊检索 A 股股票信息。

    参数:
        keyword: 检索词（如 '茅台', '比亚迪', '芯片', '600519'）
        limit: 最大返回结果数量（默认 10）

    返回:
        包含股票代码、名称、最新价与涨跌幅的候选列表。
    """
    try:
        data = client.search_stock(keyword, limit=limit)
        return data.get("markdown") or json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"search_stock 错误 ({keyword}): {e}")
        return f"❌ 检索股票失败 ({keyword})：{str(e)}"


@mcp.tool()
def get_stock_info(symbol: str) -> str:
    """查询指定 A 股个股的公司资料、行业板块及股本市值估值信息。

    参数:
        symbol: 股票代码（例如 '600519'）

    返回:
        公司所属行业、总市值、流通市值、上市时间等基础资料。
    """
    try:
        data = client.get_stock_info(symbol)
        return data.get("markdown") or json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"get_stock_info 错误 ({symbol}): {e}")
        return f"❌ 查询个股资料失败 ({symbol})：{str(e)}"


def main():
    """MCP 服务启动入口（支持 stdio 传输）。"""
    logger.info("启动 AKShare MCP 服务端...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
