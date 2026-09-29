# 1748 passed / 4 skipped —— HR 粗配判据收紧(剔技术噪声整词)

> 摘要: 用户指令修「`FUZZY_NAME_K = 12` 的假重合」。只读取证: 50 条活跃行 × 108 本地名 ⇒ 旧判据
> 159 对命中里 128 对是纯技术噪声段(`1080pwebdlh26` / `0pwebdlh265aac` / `2026s01complete1080p`),
> 真命中只有 Futsutsuka 与 Cat&Dragon 两族。修法: K 仍 12, 改为**剔技术噪声整词后**再算重合
> (`FUZZY_NOISE_TOKEN` + `_fuzzy_signal`), 保留「信号串完全相等」这条不受 K 约束的短标题通路。
> 同批数据复算 159 → 31 对、按行 13 → 4 条、**新增 0**。真机效果待用户拉取后确认(下载次数应显著下降)。
> 基线时间: 2026-09-29 19:38 (develop @ afe8c50, 本次改动未提交)
> 档案: tasks/26-09-29-backend-hr-release-deadend.md(第五轮)

- test.full: **1748 passed / 4 skipped**, TOTAL **91%**(12,432 语句 / 999 未覆盖 / 4,178 分支 /
  409 partial; 较上一条基线 26-09-29-1920 多 1 条用例 —— 新增真实数据回归用例)。
- 红验实测: 仅 stash `src/auto_qb/hr/service.py`(保留测试) ⇒ `test_fuzzy_name_match_unit` 与
  `test_fuzzy_name_match_rejects_noise_only_overlap` **双红**; 恢复后全绿。
- 只读取证脚本落在 `R:/Temp/auto-qb/`(不入库): `probe_fuzzy_evidence.py`(旧判据重合段构成)、
  `probe_fuzzy_newrule.py`(旧/新对照 + 新增检查)、`probe_fuzzy_v3.py`(三档变体对照)、
  `probe_fuzzy_accept.py`(落地实现复算)。
- 未提交(等用户显式指令)。
- 覆盖率口径见 [baseline.md](../../testing/baseline.md)。
