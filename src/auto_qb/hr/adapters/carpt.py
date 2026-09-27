"""CarPT (carpt.net) 的 myhr.php 变体 adapter。

页面事实(2026-09-27 两份样张核对, 样本见用户提供: C:/Users/11059/Desktop/Projects/PT页/CarPT/HR,
含空表页与 status=2 已达标页 17 行数据):
- HR 表仍在 `myhr.php`, 但状态参数是 `?status=N` 而非标准 `?hrtype=X`:
  1 考察中 / 2 已达标 / 3 未达标 / 4 已免罪(tab 文字逐一核对)
- 表头锚点首列是「H&R ID」(非标准「HR编号」), 表头格为 `<td class="colhead">`(十列):
  H&R ID | 种子名称 | 上传量 | 下载量 | 分享率 | 还需做种时间 | 下载完成时间 | 剩余考察时间 |
  备注 | 操作 —— 末尾比标准多两列, 解析按表头名取列不受影响
- 列名差异: 「下载完成时间」(标准: 完成时间) / 「剩余考察时间」(标准: 剩余达标时间);
  完成时间形态 "YYYY-MM-DD HH:MM"(无秒, parse_datetime 已认)
- ❗**H&R ID 与种子 id 是两个 id 空间**(已达标页实证: H&R ID=8017746 的行, 名称列详情链接是
  details.php?id=173107) ⇒ 取 .torrent 必须用行内链接里的种子 id(基类 `_dl_id_of` 提取,
  download.php 优先 / details.php 兜底), 走 `HrEntry.dl_id`; 操作列在已达标页为空, 无站内下载链接
- B/C 档「还需做种时间/剩余考察时间」显示 `---`(非空白 ⇒ 不计字段缺失, parse 成 None = 展示层不显示)
- 分页仍是 nexus-pagination 形态, 翻页参数 `?page=N`; 服务端渲染, 无异步取数

配置写法: trackers.carpt.hr_check.adapter = "carpt", 其余同 nexusphp。
"""
from .nexusphp import NexusPhpMyhrAdapter

#: 档位字母 -> CarPT status 参数值(样张 tab 核对: 1 考察中 / 2 已达标 / 3 未达标 / 4 已免罪)
SCOPE_STATUS = {"A": "1", "B": "2", "C": "3", "D": "4"}

HEADER_KEY = "H&R ID"

COLUMN_NAMES = {
    "tid": "H&R ID",
    "name": "种子名称",
    "uploaded": "上传量",
    "downloaded": "下载量",
    "ratio": "分享率",
    "need_seed": "还需做种时间",
    "done": "下载完成时间",
    "remain": "剩余考察时间",
}


class CarPtMyhrAdapter(NexusPhpMyhrAdapter):
    """CarPT 形态: 标准 myhr 表格 + status 参数 + 变体表头名"""
    def looks_like_login(self, html: str) -> bool:
        # 基类用标准表头「HR编号」排除误判, CarPT 页面没有这个词, 换本站表头锚点
        return ("takelogin.php" in html or 'name="password"' in html) and HEADER_KEY not in html


__all__ = ["CarPtMyhrAdapter", "COLUMN_NAMES", "HEADER_KEY", "SCOPE_STATUS"]
