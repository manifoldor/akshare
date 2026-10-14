"""AKShare API wrapper providing robust A-share market data query methods."""

import datetime
import logging
import re
import time
from typing import Any, Dict, List, Optional
import pandas as pd
import requests

from .utils import (
    COMMON_A_STOCKS,
    INDEX_MAP,
    format_amount,
    format_change,
    format_price,
    format_volume,
    normalize_symbol,
    render_kline_markdown,
    render_stock_quote_markdown,
)

logger = logging.getLogger(__name__)

# 全局补丁：为 requests 请求注入真实浏览器 User-Agent，防止东方财富等接口拒绝连接
_orig_session_request = requests.Session.request


def _patched_session_request(self, method, url, **kwargs):
    headers = kwargs.setdefault("headers", {})
    if "User-Agent" not in headers and "user-agent" not in headers:
        headers["User-Agent"] = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    return _orig_session_request(self, method, url, **kwargs)


requests.Session.request = _patched_session_request

# 全市场实时数据本地缓存 (TTL = 30秒)
_SPOT_CACHE: Optional[pd.DataFrame] = None
_SPOT_CACHE_TIME: float = 0
_SPOT_CACHE_TTL: float = 30.0


def _get_akshare_module():
    """动态导入 akshare。"""
    try:
        import akshare as ak
        return ak
    except ImportError:
        raise ImportError(
            "未安装 akshare 依赖。请运行 'pip install akshare'。"
        )


def _get_tencent_realtime_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """通过腾讯财经实时行情通道获取极速 L1 实时盘口与股价（毫秒级响应，作为主备高可用通道）。"""
    norm_symbol = normalize_symbol(symbol)
    prefix = "sh" if norm_symbol.startswith(("6", "9")) else ("bj" if norm_symbol.startswith(("8", "4")) else "sz")
    secid = f"{prefix}{norm_symbol}"
    url = f"http://qt.gtimg.cn/q={secid}"

    try:
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            text = resp.content.decode("gbk", errors="ignore").strip()
            # 格式：v_sh600519="1~贵州茅台~600519~1286.00~1274.89~1270.10~..."
            m = re.search(r'="([^"]+)"', text)
            if m:
                parts = m.group(1).split("~")
                if len(parts) > 30 and parts[1]:
                    name = parts[1]
                    latest_price = float(parts[3]) if parts[3] else None
                    prev_close = float(parts[4]) if parts[4] else None
                    open_price = float(parts[5]) if parts[5] else None
                    volume = float(parts[6]) if parts[6] else None  # 手
                    change_amount = float(parts[31]) if parts[31] else None
                    change_percent = float(parts[32]) if parts[32] else None
                    high = float(parts[33]) if parts[33] else None
                    low = float(parts[34]) if parts[34] else None
                    amount = float(parts[37]) * 10000 if parts[37] else None  # 万元 -> 元
                    turnover_rate = float(parts[38]) if parts[38] else None
                    pe_ratio = float(parts[39]) if parts[39] else None
                    pb_ratio = float(parts[46]) if len(parts) > 46 and parts[46] else None

                    # 五档买卖盘
                    bid_ask = {
                        "buy_1_price": float(parts[9]) if parts[9] else None,
                        "buy_1_volume": float(parts[10]) if parts[10] else None,
                        "buy_2_price": float(parts[11]) if parts[11] else None,
                        "buy_2_volume": float(parts[12]) if parts[12] else None,
                        "buy_3_price": float(parts[13]) if parts[13] else None,
                        "buy_3_volume": float(parts[14]) if parts[14] else None,
                        "buy_4_price": float(parts[15]) if parts[15] else None,
                        "buy_4_volume": float(parts[16]) if parts[16] else None,
                        "buy_5_price": float(parts[17]) if parts[17] else None,
                        "buy_5_volume": float(parts[18]) if parts[18] else None,
                        "sell_1_price": float(parts[19]) if parts[19] else None,
                        "sell_1_volume": float(parts[20]) if parts[20] else None,
                        "sell_2_price": float(parts[21]) if parts[21] else None,
                        "sell_2_volume": float(parts[22]) if parts[22] else None,
                        "sell_3_price": float(parts[23]) if parts[23] else None,
                        "sell_3_volume": float(parts[24]) if parts[24] else None,
                        "sell_4_price": float(parts[25]) if parts[25] else None,
                        "sell_4_volume": float(parts[26]) if parts[26] else None,
                        "sell_5_price": float(parts[27]) if parts[27] else None,
                        "sell_5_volume": float(parts[28]) if parts[28] else None,
                    }

                    # 更新时间
                    raw_time = parts[30] if len(parts) > 30 else ""
                    update_time = (
                        f"{raw_time[:4]}-{raw_time[4:6]}-{raw_time[6:8]} {raw_time[8:10]}:{raw_time[10:12]}:{raw_time[12:14]}"
                        if len(raw_time) == 14
                        else datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )

                    return {
                        "symbol": norm_symbol,
                        "name": name,
                        "latest_price": latest_price,
                        "change_amount": change_amount,
                        "change_percent": change_percent,
                        "open": open_price,
                        "prev_close": prev_close,
                        "high": high,
                        "low": low,
                        "volume": volume,
                        "amount": amount,
                        "turnover_rate": turnover_rate,
                        "pe_ratio": pe_ratio,
                        "pb_ratio": pb_ratio,
                        "bid_ask": bid_ask,
                        "update_time": update_time,
                    }
    except Exception as e:
        logger.debug(f"腾讯实时通道降级: {e}")
    return None


def _get_cached_spot_data() -> pd.DataFrame:
    """获取全市场 A 股实时行情缓存。"""
    global _SPOT_CACHE, _SPOT_CACHE_TIME
    now = time.time()
    if _SPOT_CACHE is not None and (now - _SPOT_CACHE_TIME) < _SPOT_CACHE_TTL:
        return _SPOT_CACHE

    ak = _get_akshare_module()
    try:
        df = ak.stock_zh_a_spot_em()
        _SPOT_CACHE = df
        _SPOT_CACHE_TIME = now
        return df
    except Exception as e:
        logger.warning(f"获取 stock_zh_a_spot_em 失败: {e}")
        if _SPOT_CACHE is not None:
            return _SPOT_CACHE
        raise


def get_stock_quote(symbol: str) -> Dict[str, Any]:
    """查询指定 A 股个股的实时行情与五档买卖盘口。"""
    norm_symbol = normalize_symbol(symbol)

    # 1. 优先使用极速低延迟实时盘口通道
    data = _get_tencent_realtime_quote(norm_symbol)
    if data and data.get("latest_price") is not None:
        data["markdown"] = render_stock_quote_markdown(data)
        return data

    # 2. 备选方案：通过 AKShare 接口获取
    ak = _get_akshare_module()
    result: Dict[str, Any] = {
        "symbol": norm_symbol,
        "name": "未知",
        "latest_price": None,
        "change_amount": None,
        "change_percent": None,
        "open": None,
        "prev_close": None,
        "high": None,
        "low": None,
        "volume": None,
        "amount": None,
        "turnover_rate": None,
        "pe_ratio": None,
        "pb_ratio": None,
        "bid_ask": {},
        "update_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        df_bid_ask = ak.stock_bid_ask_em(symbol=norm_symbol)
        if df_bid_ask is not None and not df_bid_ask.empty:
            data_map = {}
            for _, row in df_bid_ask.iterrows():
                k = str(row.iloc[0]).strip()
                v = row.iloc[1]
                data_map[k] = v

            result["latest_price"] = data_map.get("最新") or data_map.get("最新价")
            result["change_amount"] = data_map.get("涨跌") or data_map.get("涨跌额")
            result["change_percent"] = data_map.get("涨幅") or data_map.get("涨跌幅")
            result["open"] = data_map.get("今开")
            result["prev_close"] = data_map.get("昨收")
            result["high"] = data_map.get("最高")
            result["low"] = data_map.get("最低")
            result["volume"] = data_map.get("总手") or data_map.get("成交量")
            result["amount"] = data_map.get("金额") or data_map.get("成交额")
            result["turnover_rate"] = data_map.get("换手") or data_map.get("换手率")
            result["pe_ratio"] = data_map.get("市盈率")
            result["pb_ratio"] = data_map.get("市净率")

            bid_ask = {}
            for i in range(1, 6):
                bid_ask[f"buy_{i}_price"] = data_map.get(f"买{i}") or data_map.get(f"买{i}价")
                bid_ask[f"buy_{i}_volume"] = data_map.get(f"买{i}量")
                bid_ask[f"sell_{i}_price"] = data_map.get(f"卖{i}") or data_map.get(f"卖{i}价")
                bid_ask[f"sell_{i}_volume"] = data_map.get(f"卖{i}量")
            result["bid_ask"] = bid_ask
    except Exception as e:
        logger.debug(f"stock_bid_ask_em 降级备选 ({norm_symbol}): {e}")

    # 静态名称补全
    if result["name"] == "未知":
        for k, v in COMMON_A_STOCKS.items():
            if v == norm_symbol:
                result["name"] = k
                break

    result["markdown"] = render_stock_quote_markdown(result)
    return result


def get_stock_history(
    symbol: str,
    period: str = "daily",
    start_date: str = "",
    end_date: str = "",
    adjust: str = "qfq",
    limit: int = 30,
) -> Dict[str, Any]:
    """查询指定 A 股个股的历史 K 线行情数据。"""
    ak = _get_akshare_module()
    norm_symbol = normalize_symbol(symbol)

    if not end_date:
        end_date = "20500101"
    if not start_date:
        start_date = "20200101"

    df = ak.stock_zh_a_hist(
        symbol=norm_symbol,
        period=period,
        start_date=start_date,
        end_date=end_date,
        adjust=adjust,
    )

    records = []
    name = norm_symbol
    for k, v in COMMON_A_STOCKS.items():
        if v == norm_symbol:
            name = k
            break

    if df is not None and not df.empty:
        df_recent = df.tail(limit)
        records = df_recent.to_dict(orient="records")

    md = render_kline_markdown(norm_symbol, name, period, records)

    return {
        "symbol": norm_symbol,
        "name": name,
        "period": period,
        "adjust": adjust,
        "start_date": start_date,
        "end_date": end_date,
        "total_records": len(records),
        "records": records,
        "markdown": md,
    }


def get_stock_intraday(symbol: str) -> Dict[str, Any]:
    """获取指定个股今日分时走势。"""
    ak = _get_akshare_module()
    norm_symbol = normalize_symbol(symbol)

    records = []
    try:
        df = ak.stock_intraday_em(symbol=norm_symbol)
        if df is not None and not df.empty:
            records = df.tail(30).to_dict(orient="records")
    except Exception as e:
        logger.warning(f"stock_intraday_em 获取失败: {e}")
        try:
            df_min = ak.stock_zh_a_hist_min_em(symbol=norm_symbol, period="5", adjust="")
            if df_min is not None and not df_min.empty:
                records = df_min.tail(30).to_dict(orient="records")
        except Exception as e2:
            logger.error(f"分时备选接口失败: {e2}")

    return {
        "symbol": norm_symbol,
        "total_records": len(records),
        "records": records,
    }


def get_index_quote(symbol: str = "000001") -> Dict[str, Any]:
    """获取大盘及重要指数的实时行情。"""
    norm_symbol = normalize_symbol(symbol)
    index_name = INDEX_MAP.get(norm_symbol, "大盘指数")

    # 尝试腾讯大盘简要接口 (s_sh000001 / s_sz399001 / s_sz399006)
    prefix = "s_sh" if norm_symbol in ("000001", "000300", "000688", "000905") else "s_sz"
    url = f"http://qt.gtimg.cn/q={prefix}{norm_symbol}"
    result: Dict[str, Any] = {
        "symbol": norm_symbol,
        "name": index_name,
        "latest_price": None,
        "change_amount": None,
        "change_percent": None,
        "open": None,
        "prev_close": None,
        "high": None,
        "low": None,
        "volume": None,
        "amount": None,
    }

    try:
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            text = resp.content.decode("gbk", errors="ignore").strip()
            m = re.search(r'="([^"]+)"', text)
            if m:
                parts = m.group(1).split("~")
                if len(parts) >= 8:
                    result["name"] = parts[1]
                    result["latest_price"] = float(parts[3]) if parts[3] else None
                    result["change_amount"] = float(parts[4]) if parts[4] else None
                    result["change_percent"] = float(parts[5]) if parts[5] else None
                    result["volume"] = float(parts[6]) if parts[6] else None  # 手
                    result["amount"] = float(parts[7]) * 10000 if len(parts) > 7 and parts[7] else None  # 万元 -> 元
    except Exception as e:
        logger.warning(f"大盘指数腾讯通道异常: {e}")

    # 如果未获取到，使用 AKShare 备选
    if result["latest_price"] is None:
        try:
            ak = _get_akshare_module()
            df = ak.stock_zh_index_spot_em(symbol=norm_symbol)
            if df is not None and not df.empty:
                row = df.iloc[0]
                result["name"] = str(row.get("名称", index_name))
                result["latest_price"] = row.get("最新价")
                result["change_amount"] = row.get("涨跌额")
                result["change_percent"] = row.get("涨跌幅")
                result["open"] = row.get("今开")
                result["prev_close"] = row.get("昨收")
                result["high"] = row.get("最高")
                result["low"] = row.get("最低")
                result["volume"] = row.get("成交量")
                result["amount"] = row.get("成交额")
        except Exception as e:
            logger.warning(f"stock_zh_index_spot_em 失败: {e}")

    price_str = format_price(result["latest_price"])
    change_str = format_change(result["change_percent"], result["change_amount"])
    lines = [
        f"### 🇨🇳 {result['name']} ({norm_symbol}) 实时大盘指数",
        "",
        f"**点位**：**{price_str} 点** | **涨跌**：**{change_str}**",
        "",
        f"- **成交量**：`{format_volume(result['volume'])}` | **成交额**：`{format_amount(result['amount'])}`",
        "",
        f"*数据更新时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
    ]
    result["markdown"] = "\n".join(lines)
    return result


def search_stock(keyword: str, limit: int = 10) -> Dict[str, Any]:
    """根据股票名称或代码模糊搜索匹配的 A 股股票。"""
    kw = keyword.strip()
    matched_list: List[Dict[str, Any]] = []

    # 1. 优先匹配常用股票映射
    for name, code in COMMON_A_STOCKS.items():
        if kw in name or kw == code:
            matched_list.append({
                "symbol": code,
                "name": name,
                "source": "quick_map"
            })

    # 为前几个匹配项获取实时价格
    for item in matched_list[:3]:
        q = _get_tencent_realtime_quote(item["symbol"])
        if q:
            item["latest_price"] = q.get("latest_price")
            item["change_percent"] = q.get("change_percent")

    final_matches = matched_list[:limit]

    lines = [
        f"### 🔍 股票搜索结果 (关键词: '{kw}')",
        "",
        "| 股票代码 | 股票名称 | 最新价格(元) | 今日涨跌幅 |",
        "|:---|:---|:---|:---|",
    ]
    for item in final_matches:
        code = item["symbol"]
        name = item["name"]
        price = format_price(item.get("latest_price"))
        pct = format_change(item.get("change_percent"))
        lines.append(f"| `{code}` | **{name}** | {price} | {pct} |")

    lines.append(f"\n*共找到 {len(final_matches)} 条匹配结果*")

    return {
        "keyword": kw,
        "count": len(final_matches),
        "matches": final_matches,
        "markdown": "\n".join(lines),
    }


def get_stock_info(symbol: str) -> Dict[str, Any]:
    """查询指定 A 股个股的基础公司资料与估值概况。"""
    ak = _get_akshare_module()
    norm_symbol = normalize_symbol(symbol)

    info_dict = {"symbol": norm_symbol}
    try:
        df = ak.stock_individual_info_em(symbol=norm_symbol)
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                item = str(row.iloc[0]).strip()
                val = row.iloc[1]
                info_dict[item] = val
    except Exception as e:
        logger.debug(f"stock_individual_info_em 备选触发: {e}")

    # 尝试从实时行情补充市值与市盈率
    q = _get_tencent_realtime_quote(norm_symbol)
    if q:
        if "股票简称" not in info_dict and q.get("name"):
            info_dict["股票简称"] = q["name"]
        if "最新价" not in info_dict and q.get("latest_price"):
            info_dict["最新价"] = f"{q['latest_price']} 元"
        if "市盈率(动)" not in info_dict and q.get("pe_ratio"):
            info_dict["市盈率(动)"] = f"{q['pe_ratio']}"
        if "市净率" not in info_dict and q.get("pb_ratio"):
            info_dict["市净率"] = f"{q['pb_ratio']}"

    lines = [
        f"### 🏢 股票基本信息与公司资料 ({norm_symbol})",
        "",
    ]
    for k, v in info_dict.items():
        if k != "symbol":
            lines.append(f"- **{k}**：{v}")

    info_dict["markdown"] = "\n".join(lines)
    return info_dict
