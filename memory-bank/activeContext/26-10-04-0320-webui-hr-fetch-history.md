# WEBUI HR 拉取历史详情表 · 计划编制轮

> 摘要: 用户要求为 WEBUI HR在线核实添加「拉取历史详情表」（什么时间拉取了什么站点/解析结果等, 参照扩展选项页表格且更详细）, 本轮只出分步实施计划。勘察两关键结论: ①后端站点文件只存最新快照无历史流水, 需新增持久化结构; ②「插件」= hr-fetch-proxy 扩展, 其表格数据在 chrome.storage WebUI 读不到, 必须后端自记。计划 [plans/26-10-04-0312-plan-webui-hr-fetch-history.html](../plans/26-10-04-0312-plan-webui-hr-fetch-history.html) 落文: HrSiteData.history 环形事件（wave/defer/confirm_empty 三类, cap 200 + 14 天, 不抬版本链）+ GET /api/hr/history + 全屏弹层表③(details 折叠段, 波次一行展开档位明细); 五项拍板(§04)待用户确认, S1-S6 未开工。档案 [tasks/26-10-04-webui-hr-fetch-history](../tasks/26-10-04-webui-hr-fetch-history.md)(Open)。零代码改动, 未提交。

> 最后活动: 2026-10-04 03:20
