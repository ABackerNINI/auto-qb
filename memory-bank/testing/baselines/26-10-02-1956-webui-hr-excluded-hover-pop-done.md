# 基线 · 2292 passed + 3 skipped / 99% —— webui HR 排除辅种悬停弹窗轮

> 摘要: 命中 HR 排除表的辅种补悬停弹窗轮(排除态 hover 真空补全, 档案 26-10-02-webui-hr-excluded-hover-pop)。record.py 排除匹配收敛单点 _hr_exclusion_hits + hr_excluded_by 来源 token, hrPopData 排除行分支 + 三主题 excluded 灰档; 测试全是既有用例扩展, 用例数持平。切片 activeContext/26-10-02-1956。
> 基线时间: 2026-10-02 19:56, develop @ f0c0f0ed(功能改动未提交工作树, test.full 实测)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2292 passed + 3 skipped / 99%**(13,368 语句 / 86 未覆盖 / 4,444 分支 / 81 partial,
test.full 27.5s, rc=0)。
相对上一切片(26-10-02-1925: 2292 passed + 3 skipped / 99%, 13,259 语句 / 4,442 分支, @ 2a9932d9)
**passed 持平** —— 本轮测试改动全是既有用例扩展(testhr_view_fields_excluded / record 排除三测 /
接线守阵 CSS 清单), 未新增用例; 语句/分支 +109/+2 为本轮源码(record.py 两个新方法 + views.py
分支)与 2a9932d9 → f0c0f0ed 间远端推进的合计, 未逐项拆分。
