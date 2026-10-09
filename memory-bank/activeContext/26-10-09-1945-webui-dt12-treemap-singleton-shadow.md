# WEBUI 空间树图变体(dt12)单点遮蔽致渲染抛错回落 classic 修复

> 摘要: 用户报「WEBUI种子详情内容页的空间树图异常: 选择后无显示, 切换种子后回到经典模板」。根因单点 = `12-content-space-treemap-collapsed.js` layoutMap 内局部 `H`(clientHeight)遮蔽文件头 helpers 单点 `const H = reg.helpers`, 同函数尾 `H.rowFocusKey(...)` 对数字取属性抛 TypeError —— 图块只在 layoutMap 绘制故「选择后无显示」; 抛错经核心 `_dtRender` catch 复位 `drawerTplSel.content = classic` 并落盘故「换种子后回到经典」且跨会话生效。修复 = layoutMap 局部改名 mapW/mapH; 同文件 squarify 局部 H 一并改名 RH(同坑类, 让守阵不变式无例外); 新增守阵 `test_drawer_tpl_variant_no_singleton_shadowing`(凡变体声明 T/R/H 单点, 全文件禁再绑定同名, 含多声明符列表与解构两形态; 守阵正则自证能抓旧根因行、放过修复行)。坑档 `pitfalls/web-ui/variant-singleton-shadow.md` 已入池并重建索引。
> 最后活动: 2026-10-09 19:45

## 状态

- 已完成: dt12 修复(node --check 过 + drawer_tpl 守阵 12 passed); 守阵测试 + 文件头测试计划清单同步; 坑档入池 + `kb.index` 重建; 全量测试基线 `testing/baselines/26-10-09-1955-webui-dt12-treemap-singleton-shadow.md`(2871+4 / 0 failed / 覆盖率 99%)。
- 未做: 变体「渲染成功路径逐函数 node 真跑」电池仍是缺口(见坑档条目尾)。
- 下一步: 用户真机复核空间树图(选择后块图出现、换种子保持选择不再回落); 用户说「提交」即走 ship.commit。

**Refs:** memory-bank/pitfalls/web-ui/variant-singleton-shadow.md,memory-bank/pitfalls/web-ui/template-render.md
