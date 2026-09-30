# 别名层处置(web-state-alias-disposal: W0 完成, W1-W3 待做)

> 摘要: plan 26-10-01-0350 拍板按推荐(D1 属性面永久保留 / D2 按模块域分批 / D3 W0 先行),
> **W0 分诊清单 + 守阵立桩完成**(纯文档与测试, 零产品代码): ①逐名分诊落 JSON 清单
> (plans/26-10-01-0350-...triage.json, 守阵直读同文件): 20 别名 + 2 dunder + 57 单行转发 +
> 7 外观属性(D1 保留) + 17 内核自有 = 106 类面成员; 波次 W1×15(src 消费方)/ W2×57(仅测试)
> / W3×5(无消费方直删)/ 保留×24, 每名带目标新名口与行级消费方。②冻结守阵上线
> tests/test_qbmanager_alias_freeze.py 4 例: AST 扫单行转发形状与清单双向比对 —— 清单外
> 新增旧名委托即红, 删名字必须同波改清单。③分诊修正计划数字: 委托成员 86(计划 81);
> 「4 个纯内部属性对」实为 1 对(_next_state_flush_at); 真实 src 消费方比 W1 原口径多
> rules 动作三域 7 处 + getattr 字符串暗消费方 1 处(context.py:32 _web_write_seq)。
> test.full 1894+3 / 91%。档案 26-10-01-backend-web-state-alias-disposal。
> 最后活动: 2026-10-01 04:43

## 正在进行

- 待用户评审分诊清单 → W1 开工(路由与 src 侧改新名): webui routes/auth/context 旧名改
  manager.web.* 口 + rules 动作三域(base.py/checking_meta.py/checking.py)改 ctx 口;
  验收 grep `manager\._`(webui)为空; 范围外注记 _hr_view_fields 处置 W1 时定。
- W2(按模块域 3-4 批迁测试面)→ W3(删别名层本体 + run() 字面量内联连守阵同波 + 回写 +
  四场景走查回放)。

## 已完成

- W0(2026-10-01): 分诊清单 JSON + 守阵 4 例 + 档案立档 + 计划标 In Progress +
  conventions/modules.md 兼容层现状节补清单/守阵指针 + 基线切片 26-10-01-0443。
