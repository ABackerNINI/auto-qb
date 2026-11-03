"""搜索索引/匹配视图域: SearchMixin(从 views.py 拆出, 仅搬移)"""

from typing import List, Tuple

from ..torrents import TorrentRecord

from .views_common import _parse_query, _search_norm


class SearchMixin:
    def search_torrents(self, q: str) -> dict:
        """WEB 线程调用: 按 q 搜索种子 —— **全站唯一文本匹配点**(辅种/种子/追剧三页统一消费其结果)。

        匹配口径(**正词逐词跨行 AND + 负词种子级**, 拍板 2026-09-27): q 经 _parse_query 解析为正/负词
        (词已是归一后的子串口径); **候选行** = 种子名/站点/分类/保存路径/每个标签/每个文件名 各
        归一为一行。**负词优先级高于正词, 按「单个种子」统一计算**: 该种子的任一候选行(名字/
        站点/分类/路径/标签/文件行, 单个种子内包含的合集即季包文件统一计算)含任一负词 ⇒ 整颗
        种子直接排除 —— 「-mteam」类站点/标签排除、「cat and -11」类名字/路径排除都必须在这一层
        生效; 辅种组/追剧页等多种子集合里的**每个种子单独计算**(带负词的种子被排除, 干净种子
        留下, 组/剧不连带)。正词**逐词跨行 AND**: 每个正词/短语命中任一候选行即可、行可不同 ——
        「minions mteam」(标题在名字行、站点/标签在标签行)与「delta 03」(包名 Gamma.Delta 在
        名字行、集号 03 只在集文件行)类跨字段查询由此命中; 26-09-26 的「多词须同行、文件行不
        参与跨行」口径随 26-09-27 实测报障作废(已知代价: 季包文件行多, 附加词可被包内任一
        文件名吸收)。排序两层: 全称行全覆盖的在前, 需文件行补词的以 file 兜底排后; 旧「整句
        连续子串」口径的「恶女 10」失配修复保持不变。

        候选行 26-09-26 起**收敛为服务端单点**并覆盖全部文本面: 此前种子页(名字/站点/分类/
        路径/标签的客户端过滤)与追剧页(剧名整句 includes)各持一份匹配实现, 同一语义(恶女 10 /
        季包"cat 12")前后端修了三遍; 现在前端三页一律消费本结果的 hash 集合(searchHits),
        不再持有任何文本匹配代码。站点/分类/路径/标签行只读 store(无 qB API, 与名字行同轮
        即时); 文件行依赖 _search_index 缓存。剧名不单设候选行 —— 追剧视图的展示名本就是
        成员种子名解析出的标题(tvshows.parse_release), 名字行命中天然覆盖。

        返回 {"results": [..], "building": bool, "negative_only": bool}——building 为 True 表示文件
        索引已过期/缺失(只影响**文件行**: 文件行就位前, 其正词命中与负词否决都未生效 —— 即时行
        看似命中的种子可能因文件行负词在就位后被剔除), 已投递构建命令, 前端应稍后重查以获取完整
        匹配结果; negative_only 为 True
        表示查询只含排除词(无正判据, 「只说不要什么」无从起搜, 与 Google 一致返回空, 前端据此前端
        提示)。结果项 = 分组成员视图(_member_view)全字段 + by —— 行构造不另建字段子集(与
        _seed_view 同范式收敛, issue b-r16b01-search-row-view-converge: 自建子集曾缺
        eta/num_*/downloaded 等 19 键, 未归组命中种子的虚拟行展开明细默认列全空白;
        seeding_time 也未走 view_field_value 分钟量化, 与重建脏判定契约脱钩), 供前端完整展示
        命中种子信息(by = 首个含正词的全称行类别, 文件行兜底命中时为 file; 供测试定位,
        前端不消费)。
        """
        def _view(rec, by):
            # 行构造单点在 _member_view(issue b-r16b01-search-row-view-converge): 此前这里
            # 自建一份字段子集 —— seeding_time 原始秒未走 view_field_value(与 torrents.view
            # 的重建量化契约脱钩, hr.js 60s 边界本地比色翻色), 且缺 eta/num_*/downloaded 等
            # 19 键(搜索虚拟行 searchUncovered 展开明细的默认列全空白)。与 _seed_view 同范式:
            # 同名字段一律以 _member_view 为准, 这里只叠加搜索语义键 by(守阵
            # test_search_row_view_converged_on_member_view 钉两边同名字段等值 + 键集关系)。
            return {**self._member_view(rec), "by": by}

        # 搜索数据版本(plan 26-11-03-0120 S4): 在读取任何快照**之前**取值 —— 之后若主循环
        # 再自增, 本次响应返回的仍是旧版本, 前端下一轮 /api/state 会再触发一次静默重查,
        # 不会把"旧结果 + 新版本号"配对(避免漏更新)。快照读取本身不加锁, 该顺序给出
        # 单调保证: rev 落后 ⇒ 结果不新, rev 相等 ⇒ 结果至少覆盖到该版本。
        rev = self.web.search_rev
        pos, neg = _parse_query(q or "")
        if not pos:
            return {"results": [], "building": False, "negative_only": bool(neg), "rev": rev}

        def _instant_rows(rec: TorrentRecord) -> List[Tuple[str, str]]:
            """即时候选行(只读 store, 不依赖文件索引): 名字/站点/分类/保存路径/每个标签各归一为一行;
            空值字段不构成候选行。"""
            return [
                (by, _search_norm(raw)) for by, raw in (
                    ("name", rec.name),
                    ("site", rec.tracker_name),
                    ("category", rec.category),
                    ("path", rec.save_path),
                    *(("tag", t) for t in rec.tags_set),
                ) if raw
            ]

        results = []
        file_hits = []
        idx = self.web.search_index
        for h, rec in tuple(self.store.by_hash.items()):  # 读侧快照(见 _build_group_view): /api/search 每请求必迭代
            rows = _instant_rows(rec)
            file_rows = idx[h]["files_q"] if idx is not None and h in idx else []
            # 负词优先于一切正词, 按「单个种子」统一计算: 任一候选行(名字/站点/分类/路径/标签/
            # 文件行)含任一负词 ⇒ 该种子整体排除(2026-09-27 定案: 「cat and -11」名字行作废被
            # 路径行捞回 + 「-mteam」站点行拦不住名字行正词命中; 辅种组/追剧页等多种子集合
            # 逐个种子计算, 互不牵连)
            if neg and (
                any(any(t in row for t in neg)
                    for _, row in rows) or any(any(t in fq for t in neg) for fq in file_rows)
            ):
                continue
            # 正词逐词跨行 AND(2026-09-27 二次定案, 推翻 26-09-26「多词须同行、文件行不参与跨行」):
            # 每个正词命中任一候选行(全称行或文件行)即可, 行可不同 —— 「minions mteam」(名字×
            # 标签)与「delta 03」(包名在名字行、集号只在集文件行)类跨字段查询都命中; 已知代价
            # (季包文件行多, 附加词可被包内任一文件名吸收)由用户知情拍板接受。全称行全覆盖的
            # 排前(by 定位首个含正词的全称行), 需文件行补词的以 file 兜底排后。
            if all(any(t in row for _, row in rows) for t in pos):
                results.append(_view(rec, next(b for b, row in rows if any(t in row for t in pos))))
            elif all(any(t in row for _, row in rows) or any(t in fq for fq in file_rows) for t in pos):
                file_hits.append(_view(rec, "file"))
        results.extend(file_hits)
        building = self.web.search_index_dirty
        if building:
            self.web.post_command("build_search_index")
        return {"results": results, "building": building, "negative_only": False, "rev": rev}
