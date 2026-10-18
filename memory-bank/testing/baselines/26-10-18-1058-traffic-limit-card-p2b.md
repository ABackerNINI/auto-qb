# 3587 passed + 4 skipped(根, 覆盖率 98.09%) —— P2-B 合并卡落地后全量基线

> 摘要: P2-B 合并卡落地后全量基线
> 基线时间: 2026-10-18 10:58
**Refs:** memory-bank/tasks/26-10-18-backend-traffic-snapshot-merge.md, memory-bank/plans/26-10-18-0813-plan-global-traffic-source-phase2.html

## 验收数字

`commands run test.full`(2026-10-18 10:51 实测):

```
3587 passed, 4 skipped in 34.12s
TOTAL   18146   266   6146   193   98.09%
```

口径: 根套件(pytest.ini 的 8 worker); `TOTAL` 列序 = 语句数 / 未覆盖 / 分支数 / 部分分支 / 覆盖率。
相对上一条基线(26-10-18 10:19 traffic-snapshot-decouple-p2a)两处增量: +9 用例(P2-B 新增
`tests/test_web_traffic_limit_card.py` 的 9 条结构守阵), 覆盖率持平。e2e 侧另跑了两轮:
`--grep @fast` 170 passed; 新增的合并卡用例(三区/折叠/历史图入口)两皮肤各 1 条绿。

回写后复验(2026-10-18 11:05 / 11:09 连跑两次): 补完本切片的反向 `Refs` 后重跑 `commands run test.full`
得 **3587 passed, 4 skipped**(40.53s / 33.67s), `TOTAL 18146 / 266 / 6146 / 193` 与上表逐位一致
(覆盖率同 98.09%, 耗时差为机器负载, 不影响数字)。

### 中途两红归因(均已消, 非遗留)

- `test_docs_forms::test_claim_chain_is_bidirectional`(真红, 本轮引入): 任务档案 `Refs` 增列本切片,
  但切片侧未反向声明任务 ⇒ 认领链单向。补 `**Refs:**` 后 `tests/test_docs_forms.py` 16 passed 全绿。
  教训: 新切片入池必须与 `Refs` 同一次写, 否则纯文档改动也能把链断开。
- `test_hr_discovery::test_start_all_busy_returns_false_and_retries`(flake, 与本轮零关系): `-n 8` 并行下
  候选端口争用 / 退避窗口超时; 单跑即过, 复跑全量亦过。同型先例见 26-10-17-0721 基线切片注(WinError 10048)。

## 本改动面

- schema: `config/schema/groups.py` —— 「流量图」「全局流量来源」「限速曲线」三组并成 `traffic_limit`
  (「流量与限速」, 8 -> 6 组, 字段序 = 卡内区序: `traffic_source` -> `global_speed_limit_curve`
  -> `qb_traffic`); 组 key 与配置段名无关, 各模块 `sections()` 未动。
- 前端新件: `webui/static/shared/traffic_card.js`(组件壳, inject/provide 透传 `ce`) +
  `webui/static/shared/tpl/traffic-card.html`(卡内三区模板, `into: body`); 三皮肤 `index.html`
  清单各加一条分片与一条脚本; `app.js` 注册 `aq-traffic-card`。
- 前端改件: `settings.html`(来源分支 418 -> 318 行, 只剩一行挂载) / `settings-detail.html`
  (删 `speed` 分支, 543 -> 420 行) / `config_hub.js`(HUB_GROUP_META 换键、`HUB_SKIP_PATHS` 单点、
  `HUB_VIEW_ALIAS` 旧值映射、LED/读数/徽标改键、`tmProviderItems` 改走 `cfgVisible`、合并卡
  折叠态 `hub.sub` 与方法域) / `config_editor.js`(`visible()` 不再对 group/section 短路) /
  `console_hub.css`(`.hb-tl-dep` 依赖提示条) / `popovers.html`(关源空态文案指路新房卡名)。
- 后端文案: `core/traffic_source/paths.py` 两处指路文案改到「流量与限速 → 数据来源」。
- 测试: 新增 `tests/test_web_traffic_limit_card.py`(9 条: 组并合、组件接线、三区/折叠、历史图入口、
  提示条同源、旧视图映射、`show_if` 下移、排除表单点、分片体量回落);
  改 `test_web_traffic_monitor.py`(模板取数改经 `_tm_tpl()` 单点, `$root` 前缀断言, 组 key 改
  `traffic_limit`) / `test_web_backend_misc.py`(组清单) / `test_webui_static_skins.py`
  (删 `settings.html` 的 440 例外额度, 回落 400)。
- e2e: `e2e/views.spec.mjs` 卡名改「流量与限速」、工具参数块取最内层(`.hb-blk.hb-sub` 嵌套)、
  新增合并卡三区 + 折叠 + 历史图入口用例(prism/atlas 各 1)。
- 文档: `docs/configuration.md` 四处「设置页『全局流量来源』」指路改成「流量与限速 → 数据来源」。
- 变异红验(计划 B5 四条): 去掉子区 / 去掉折叠头 / 恢复 `visible()` 非叶子短路 / 排除表改回
  硬编码 —— 逐条跑对应守阵均为红, 还原后文件字节一致(SHA256 校验)。
