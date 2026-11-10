# 5945 —— 全量绿基线: search-hit 停靠点收紧 220px + 必显列守阵全矩阵

> 摘要: 全量绿基线: search-hit 停靠点收紧 220px + 必显列守阵全矩阵
> 基线时间: 2026-11-11 03:46

## 验收数字

`commands run test.full` 实测(2026-11-11, 166.5s):

- TOTAL: 26307 statements / 50 missed / 9176 branches / 62 partial / **99%**
- 汇总: **5945 passed, 2 skipped**(163.88s)

行为守阵矩阵 spec(commands run dev.e2e -- e2e/main-table-pinned-matrix.spec.mjs)实测: **24 passed**(1.7m-1.9m, 六上下文 × 四用例)。

## 本改动面

- `src/auto_qb/webui/static/{atlas,console,flux}/css/components.css` + 四皮肤 `views.css` + `shared/row_lang.css`: 主表 search-hit 渐层停靠点 `transparent 46%` → `transparent 220px`(行板 + 首格镜像双侧, row_lang flat/wave 含 zebra 三层共 6 处)+ 定案注释。
- `tests/test_webui_static_skins_table.py::test_frontend_pinned_first_cell_bg_per_face`: 静态守阵改钉 220px(四皮肤镜像 + 行板规则双侧)+ 新增 1b 段(row_lang.css 生效层逐规则块恰 6 处 220px 且全文件禁 46%)。
- `e2e/main-table-pinned-matrix.spec.mjs`(新): 必显列悬停行为守阵全矩阵(四皮肤 flat + prism/flux wave × 状态行逐帧+稳态像素地面真值 × 选中真手势/search-hit 斑马+非斑马双条/展开行)。
- `memory-bank/pitfalls/web-ui/frozen-column.md` + `attachments/frozen-column-constraints.md`: ⑦ 收紧定案 + 停靠点判据推广 + 量法教训 + 守阵清单回写。
