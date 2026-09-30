# 别名层处置(web-state-alias-disposal: W0-W1 完成, W2-W3 待做)

> 摘要: plan 26-10-01-0350 **W1 路由与 src 侧改新名完成**(只改名零行为变更): 分诊 W1×15
> 名的 src 消费方全部改净 —— ①webui 路由域: auth(`web.token` ×2)/ system(`web.results`)/
> state + torrent_detail(`web.group_view`/`web.traffic_view`/`web.ensure_state`/`web.ensure_view`)/
> touch_web_client → `web.touch` ×26(七文件)/ context.py:32 getattr 暗消费方改 `web.write_seq`
> 直取; ②`_hr_view_fields` 公开化改名 `hr_view_fields`(范围外注记落定, 不搬 hr 口); ③rules
> 三域: checking.py 组上下文 ×4 → `host.get("grouping")._*`、base.py ×2 → `manager.ctx.state.*`、
> checking_meta 冷却 helper 宿主收敛 **StateService**(ops_mod ×3 / full_checking ×1 / 测试 ×3
> 同步); ④注释与 static 四文件旧名提法清零; ⑤test_web 假替身(SimpleNamespace 无别名层)
> 同波接线 web.* + web_env 双写 token, 真 manager 测试经别名层零改动。验收: `grep manager\._`
> (webui)为空 + test.full **1894+3 / 91%** 与 W0 持平(26 文件 +116/-122)。基线 26-10-01-0545。
> 档案 26-10-01-backend-web-state-alias-disposal。最后活动: 2026-10-01 05:45

## 正在进行

- W2(按模块域 3-4 批迁测试面, D2): 27 文件 727 处 `mgr._*` 引用按分诊清单改新名
  (模块方法 → host.get/ctx 口、状态方法 → ctx.state、别名字段 → mgr.web.*); 决策点 D2′
  状态/服务属性对按 D1 保留不改。待用户指令开工。
- W3(删别名层本体 + run() 字面量内联连守阵同波 + 回写 + 四场景走查回放)。

## 已完成

- W0(2026-10-01 04:43): 分诊清单 JSON + 守阵 4 例 + 档案立档 + 计划标 In Progress +
  conventions/modules.md 兼容层现状节补清单/守阵指针 + 基线切片 26-10-01-0443。
- W1(2026-10-01 05:45): 路由与 src 侧改新名(见摘要), 基线切片 26-10-01-0545。
