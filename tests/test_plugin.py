"""Verification tests for AKShare Grokbot Plugin."""

import sys
import unittest
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from akshare_mcp.utils import (
    COMMON_A_STOCKS,
    format_amount,
    format_change,
    format_price,
    format_volume,
    normalize_symbol,
)
from akshare_mcp import client


class TestAKShareUtils(unittest.TestCase):
    """测试工具函数与标准化逻辑。"""

    def test_normalize_symbol(self):
        self.assertEqual(normalize_symbol("600519"), "600519")
        self.assertEqual(normalize_symbol("sh600519"), "600519")
        self.assertEqual(normalize_symbol("SZ000001"), "000001")
        self.assertEqual(normalize_symbol("贵州茅台"), "600519")
        self.assertEqual(normalize_symbol("宁德时代"), "300750")

    def test_format_change(self):
        # 中国 A 股：红涨绿跌
        res_up = format_change(2.5, 1.2)
        self.assertIn("🔴", res_up)
        self.assertIn("+2.50%", res_up)

        res_down = format_change(-1.8, -0.9)
        self.assertIn("🟢", res_down)
        self.assertIn("-1.80%", res_down)

        res_flat = format_change(0.0)
        self.assertIn("⚪", res_flat)

    def test_format_amount(self):
        self.assertEqual(format_amount(150000000), "1.50 亿元")
        self.assertEqual(format_amount(25000), "2.50 万元")
        self.assertEqual(format_amount(350), "350.00 元")

    def test_format_volume(self):
        self.assertEqual(format_volume(500000000), "5.00 亿手")
        self.assertEqual(format_volume(20000), "2.00 万手")
        self.assertEqual(format_volume(500), "500 手")


class TestAKShareClient(unittest.TestCase):
    """测试 AKShare 接口封装（包含网络查询）。"""

    def test_get_stock_quote_maotai(self):
        """测试贵州茅台行情查询。"""
        res = client.get_stock_quote("600519")
        self.assertIsNotNone(res)
        self.assertEqual(res["symbol"], "600519")
        self.assertIn("markdown", res)
        print("\n--- 茅台实时行情 Markdown 输出样例 ---")
        print(res["markdown"][:400])

    def test_get_index_quote(self):
        """测试上证指数大盘行情查询。"""
        res = client.get_index_quote("000001")
        self.assertIsNotNone(res)
        self.assertEqual(res["symbol"], "000001")
        self.assertIn("markdown", res)
        print("\n--- 上证指数 Markdown 输出样例 ---")
        print(res["markdown"])

    def test_search_stock(self):
        """测试股票模糊搜索。"""
        res = client.search_stock("茅台", limit=3)
        self.assertIsNotNone(res)
        self.assertGreaterEqual(res["count"], 1)
        self.assertIn("markdown", res)
        print("\n--- 搜索股票 Markdown 输出样例 ---")
        print(res["markdown"])

    def test_get_stock_history(self):
        """测试历史日K线查询。"""
        res = client.get_stock_history("600519", limit=5)
        self.assertIsNotNone(res)
        self.assertIn("markdown", res)
        print("\n--- 历史K线 Markdown 输出样例 ---")
        print(res["markdown"])


if __name__ == "__main__":
    unittest.main()
