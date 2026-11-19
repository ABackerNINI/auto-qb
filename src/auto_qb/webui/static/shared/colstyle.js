/* auto-qb WEB UI · 列风格引擎(计划 26-11-20-0009 S1, mixin 方法域, 与 ui_prefs.js 同范式)
 *
 * 主种子表五维「列风格」(进度条样式/进度条颜色/速度色阶/数值色阶/单位色组)的运行时单点:
 * localStorage 单键 autoqb.colstyle.v1(键名/值域/默认档/读取容错在 app.js COLSTYLE_* 单点)
 * -> state.colStyle(Vue 响应式, state.js 注入) -> 本文件把状态同步到 <html> 的五枚
 * data-cs-barstyle/-barramp/-speedramp/-numeric/-units 属性上, CSS 按 html[data-cs-*] 派生
 * 颜色/形状映射(S3-S5 落; JS 只同步属性, 永不产颜色值, R4)。变更免刷新: watch colStyle
 * (state.js 派发)即改属性。
 *
 * 时序纪律(无 FOUC, R7): state.js data() 里 loadColStyle() 先于首渲染(theme/timeFmt 同判据),
 * lifecycle.js created() 首帧同步把五枚属性写上 <html> —— 首帧即终态。
 *
 * 跨标签: storage 事件 -> adoptColStyle 整份采用(幂等, 监听在 lifecycle.js, R8); 标签被冻结 /
 * 事件丢失 -> 回到可见时补对齐一次(timeFmt 同款)。写入口单点 setColStyle(菜单写链 S2 调):
 * 校验 -> 改 state(watch 派发属性同步) -> 落盘 try/catch(隐私模式降级会话内生效, 不抛错)。
 *
 * S1 落点说明: 五枚 data-cs-* 挂在 html 上但尚无任何 CSS/渲染消费 —— 预期(默认值=现状,
 * 零视觉变化); 消费面随 S3-S5 落地。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾 app.mixin 要读 window.AQB_COLSTYLE);
 *   方法体内的 COLSTYLE_* / loadColStyle 是运行时引用(app.js 顶层定义, 全局词法域共用), 无装载序依赖。
 */
window.AQB_COLSTYLE = {
  methods: {
    /* 首帧同步(created)与 watch 派发的共用写面: 把当前五维逐枚写到 <html> data-cs-* 属性。
     * 逐字段过枚举闸: 状态被绕开 setColStyle 的路径改坏(手滑直赋未来代码)时属性面回落默认档,
     * 而不是把无效值写进 DOM 造出永不命中的 CSS 选择器 —— html[data-cs-*] 派生面恒为合法枚举。 */
    _colStyleSyncAttrs() {
      const el = document.documentElement;
      for (const k of COLSTYLE_FIELDS) {
        const v = COLSTYLE_ENUMS[k].indexOf(this.colStyle[k]) >= 0 ? this.colStyle[k] : COLSTYLE_DEFAULTS[k];
        el.setAttribute("data-cs-" + k, v);
      }
    },
    /* 菜单写链(S2)的引擎入口: setColStyle(dim, value) -> boolean(是否已应用)。
     * dim ∈ COLSTYLE_FIELDS(barstyle/barramp/speedramp/numeric/units), value ∈ 该维枚举;
     * 同值重入幂等(不落盘、不惊动 watch); 非法 dim/value 静默拒绝(状态面恒合法, 不抛错)。
     * 落盘 try/catch: 隐私模式/配额满时本轮仍生效(属性已随 watch 派发同步), 只是刷新后回落
     * —— 偏好类写入失败不该打断操作(timeFmt 写链同款)。版本戳 v 只标形态, 读取侧不做版本闸
     * (loadColStyle 逐字段容错, 未知字段忽略)。 */
    setColStyle(dim, value) {
      if (COLSTYLE_FIELDS.indexOf(dim) < 0) return false;
      if (COLSTYLE_ENUMS[dim].indexOf(value) < 0) return false;
      if (this.colStyle[dim] === value) return true;  // 同值幂等: 存储与 watch 都不动
      this.colStyle[dim] = value;                     // watch colStyle 派发 -> <html> 属性即时跟随
      try {
        localStorage.setItem(COLSTYLE_STORE_KEY, JSON.stringify(Object.assign({ v: 1 }, this.colStyle)));
      } catch (e) {
        /* 隐私模式/配额满: 会话内仍生效, 刷新后回落默认 */
      }
      return true;
    },
    /* 跨标签整份采用(F2/R8, 范式同 adoptTimeFmt): 别的标签改了任一维 -> storage 事件触发本方法
     * **整份替换**为存储值(watch 派发属性同步); 标签被冻结 / storage 事件丢失 -> 回到可见时
     * 补对齐一次(lifecycle.js visibilitychange)。整份采用而非逐维合并: 同一维的后写赢, 半合并
     * 反而会让两个标签各留一半旧值(timeFmt/列偏好踩过)。替换即使值相同也会走一次 watch(新对象
     * 身份), 属性同步幂等, 零视觉副作用。 */
    adoptColStyle() {
      this.colStyle = loadColStyle();
    },
  },
};
