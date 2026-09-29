"""BTSchool (pt.btschool.club) 的 myhr.php 标准形态 + 页头 H&R 计数 adapter。

页面事实(2026-09-29 两份样张核对, 样本: C:/Users/11059/Desktop/Projects/PT页/BTSchool/HR,
含考察中页 1 行数据与已达标页 50 行数据):
- 表格 / 翻页 / 状态参数 = 标准 nexusphp 形态(见 nexusphp.py 模块 docstring), 唯一差异是计数
- 页头计数条(摘要形, 每页都有, 与分页解耦): 标签在 <a> 内 ——
  `<a href="myhr.php"><font class="color_bonus">&nbsp;&nbsp;H&amp;R:</font>考察中/<span style="color:red">未达标</span></a>`
  共 2 个数字, 未达标位红色加粗
- 口径(用户拍板 26-09-29): 2 个数 = 考察中 / 未达标; 已达标位页头没有 ⇒ B 档无声明(不猜)

计数口径校准记录(铁律要求的证据链, 计划 26-09-29-2036 §2.1):
- 实证(2026-09-29, 项目 parser 实抓): 考察中样例 页头第 1 位 1 == A 档全深度实抓 1 行 ✓;
  已达标样例 50 行而页头第 1 位是 1 ⇒ 第 1 位不是已达标(A 无声明的反证排除)
- 第 2 位(未达标)语义来自用户拍板: 样张里恒 0 且无未达标档样张, 未做行数级实证
- ⚠ 三档声明不全(A/C 有、B 无): §2.5 的「站点自证空集」永不触发(None 参与全称量词即为假),
  零行波仍走 --hr-confirm-empty 人工戳 —— 载体缺已达标位的结构后果, 设计内

配置写法: trackers.btschool.hr_check 档案已内置(adapter="btschool"), 用户无需配置。
"""
from typing import Dict, Optional

from .nexusphp import NexusPhpMyhrAdapter, header_hr_numbers

#: 页头计数条位数与档位映射(样张钉死): 2 个数 = 考察中(A) / 未达标(C)
COUNTER_ARITY = 2
COUNTER_LANES = ("A", "C")


class BtschoolMyhrAdapter(NexusPhpMyhrAdapter):
    """BTSchool 形态: 标准 myhr 表格 + 页头 H&R 计数条(2 数)"""
    def parse_counters(self, html: str) -> Dict[str, Optional[int]]:
        """页头摘要形计数(载体与校准证据见模块 docstring): 2 数 = A 考察中 / C 未达标。"""
        nums = header_hr_numbers(html)
        if nums is None or len(nums) != COUNTER_ARITY:
            return {}  # 位数不对 = 载体变了 = 无证据降级(铁律: 宁可不用, 不可错用)
        return {lane: nums[i] for i, lane in enumerate(COUNTER_LANES)}


__all__ = ["BtschoolMyhrAdapter", "COUNTER_ARITY", "COUNTER_LANES"]
