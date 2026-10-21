# TOTAL                                                20719      73   7012      89    99% —— 3982 passed + 2 skipped —— 合流远端六笔收敛轮后(aq-modal 单点已并入)全量基线

> 摘要: 3982 passed + 2 skipped —— 合流远端六笔收敛轮后(aq-modal 单点已并入)全量基线
> 基线时间: 2026-10-21 14:59
**Refs:** memory-bank/tasks/26-10-21-webui-dialog-shell-single-point.md

## 验收数字

```text
TOTAL                                                20719      73   7012      89    99%
3982 passed, 2 skipped in 146.64s (0:02:26)
```

口径注记:

- 上表是 pytest 全量口径(含覆盖率门槛 99%), 在**合流树**上实测: 本专题 aq-modal 收敛提交(b2ff7f94 重放为 708e26d4)落在远端 eaecbee6(同专题另一 clone 的六笔: Phase 3 收口 + 四族小控件/抽屉 fetcher/列表外壳/三皮肤 CSS 分层)之上。
- 真浏览器 e2e 同轮全绿: **336 passed + 10 skipped / 0 failed**(10.1m, dev.e2e 全量集)。
- 合流冲突手写件 5 处的处置: 三 shell 清单行双侧条目都保留(本侧 dialog-shell + 远侧 list-shell/ctl-bits); app.js 两侧注册块都保留(aq-switch/fold/seg + aq-modal/aq-modal-head); popovers 历史 Header = 本侧 aq-modal 壳 + 远侧粒度三档 aq-seg 填入 #extra 槽; 生成物(issues 索引/_archive)取远侧后重跑 kb.index 回归一致。
- 裸数字只写基线切片这一处; 档案与报告正文引它而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- 合流轮无新增生产改动 —— 本切片记录的是**合流树**的验证结果: 上一切片(26-10-21-1408)的改动面在 rebase 后与远端六笔语义拼合, 全量与 e2e 复绿即合流等价性证据。
- popovers.html 历史流量段为本侧/远侧唯一同片冲突区: 模板现为 aq-modal 壳(#extra 插槽内放远侧 aq-seg 粒度三档, 清单单点 HIST_GRAN_ITEMS 在 dialogs.js —— 远侧该轮引入), 其余五处冲突均为机械拼接。
- 远端新增 4 例测试随合流入账(passed 3978 → 3982); 本专题守阵(test_frontend_dialog_shell_single_point 等)与远侧新守阵同树全绿。
