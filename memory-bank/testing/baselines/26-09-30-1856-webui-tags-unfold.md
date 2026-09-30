# 1832 passed / 3 skipped —— 标签列全量展开(+N 折叠移除)

> 摘要: 用户要求 WEBUI 标签不再折叠成「+1/+2」。4 处模板去 tagSlice/slice 截断与 `+N` 徽标改全量渲染, 三皮肤 `.g-tags, .m-tags` 加 `flex-wrap: wrap`(行高逐行实测制承接变高行), 清 `.tag-more` 死样式, decorate.js 删 tagSlice()。纯前端改动(8 个静态文件), 无 Python 源改动。
> 基线时间: 2026-09-30 18:56
> 档案: tasks/26-09-30-webui-tags-unfold.md

- 合并远端 02a8e5d9 后稳态: **1832 passed / 3 skipped**, 25.98s, TOTAL **90%**(12731 语句 / 1042 未覆盖 / 4344 分支 / 431 partial)。较前基线(26-09-30-1820 同为 1832/3)数字持平; TOTAL 90% vs 旧记录 91% 系远端新增语句摊薄, 非本侧回归。
- 插曲: 首跑 1 失败 = **远端带入**的 `plans/26-09-30-1819-plan-kernel-module-refactor.html` doc-refs 写裸文件名(守卫要求仓库根相对路径)且三个被引用计划未反向声明 —— 认领链补闭环(1819 改全路径 + 三个目标补 back-ref)后全绿; 修复独立 📝 提交。
