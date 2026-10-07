# 「绝对时间被当倒计时」—— epoch 字段按剩余量比较, 判据方向反了恒不触发

> 摘要: qB 5.2(WebAPI 2.13.0)起 `torrents/trackers` 的 `next_announce`/`min_announce` 是 **Unix epoch 绝对秒**(qB 源码 `toSecondsSinceEpoch`, PR #23045 "seconds since epoch"), 旧汇报确认判据 `na < b_na - 60` 却按**倒计时语义**写(值应变小)—— 而汇报成功 = 重新调度 = next_announce **前跳(变大)**, 判据方向反了恒假: 不抛错、不报警, 只表现为确认窗口走满 30s **恒误报「失败」**。修法(plan 26-10-05-0923, 2026-10-05 落地): 方向反转为主判据 `next > b_next + TOL`(TOL=3.0s) + 证据门控(在途直证/status4+msg 判败/停止直判/超时落 warn 第三态) + 基线 status≥2 极值守卫 + min 窗口假瞬态守卫。
> 触发: next_announce, min_announce, epoch, 前跳, 倒计时, 绝对时间, 相对时间, 汇报确认, 强制汇报, reannounce, trackers, 确认超时, 恒误报, 误报失败, TOL, updating, 假瞬态, 判据方向

**Refs:** memory-bank/tasks/26-10-05-backend-reannounce-confirm-rework.md

### 时间字段写比较判据前, 先验证「绝对时间点还是剩余量」—— 方向反了是静默失效

- **触发**: 对任何带时间字段的 API 写「变化检测」成败判据(成功 = 值变大/变小), 或排查「确认机制恒超时/恒失败但 qB 界面里行为正常」—— 汇报确认、recheck、到期检测同族。
- **判别**: 三问。①字段语义是**绝对时间点**(epoch 秒/时间戳)还是**剩余量**(倒计时秒)? 别猜字段名 —— 看 qB 源码序列化函数(本例 `toSecondsSinceEpoch`)或拿成功路径的相邻采样相减: 值变大就是绝对时间。②判据比较方向与「成功时字段往哪走」一致吗? 方向反了的判据**恒假且零报错**, 只会表现为「永远等不到确认」。③窗口型判据有没有被瞬时态/极值欺骗的面(下面两条守卫)?
- **处置** (plan 26-10-05-0923 落地, 判定单点 `webui/commands.py::_verdict_reannounce` 纯函数):
  1. **方向反转**: 主判据改 `next > b_next + TOL`(TOL=3.0s, 限基线 `status ≥ 2` 且 `b_next` 非空的行), 成功签名 = epoch 前跳; docstring 写死「epoch 前跳=成功」的方向语义, 防「秒/毫秒通用」式臆测回潮。
  2. **证据门控**: ②updating/status==3 在途直证撞见即收 / ④status==4 且 msg 非空才判败(msg 空不判) / ①停止种子直判「未确认」/ ⑤窗口走完落「未确认」(warn 第三态诚实标签, 不与「失败」混淆)。
  3. **S0 真机探针实证**(qB 5.2.3 / WebAPI 2.15.1, 2026-10-05): 立即路径前跳 **+5466s**(基线 next=1791168212 → call+3.03s next=1791173678, ≫ TOL 3.0s, min 同向 +5427s 佐证); updating 窗口实测 **≈2.1s**(调研估 ~0.5s 偏小, 2s tick 命中率比预估高); 推迟路径 `next=min=min_e+1` 冻结 ≥104s 后于 min_e+~2.2s 同值移动 —— **min_e 就是可靠的预计发送时刻**。
  4. **两条瞬态/极值守卫**: ①前跳判据限**基线 status≥2** 的行 —— 未联系行的时间点是 libtorrent `time_point32::min()` 类极值, 参与比较会造成假前跳; ②**基线 min 在未来时 updating 不作左证** —— 推迟 item 在 call+~1s 有 ~0.9s 的 updating=True 假瞬态(endpoint 发送态钉住所致), 撞上会经「在途直证」提前误判「已确认」, 而实际汇报 min_e 后才发出。
- **守阵**: `tests/test_web_*.py` §05 十一组用例(判定矩阵 epoch/legacy、min 窗口守卫、三桶聚合、状态与前缀双契约等; 本计划净增 +7), 判定矩阵对 ==TOL 边界与「前跳不足」负样本钉死方向。
- 同族纪律单点: [effect-confirmation.md](effect-confirmation.md)(异步操作成败宣称凭正证据门控, 范本区含 `_verdict_reannounce`)。
