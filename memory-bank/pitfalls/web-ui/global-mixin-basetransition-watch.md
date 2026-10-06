# 全局 mixin 写 watch 选项会被 `<transition>` 的 BaseTransition 假实例吃掉, getter 求值即抛 TypeError

> 摘要: `app.mixin()` 全局注入的对象若带 `watch: { someState() {} }`, Vue 会把该 watcher 注册进**一切**
> 组件实例 —— 包括内置 `<transition>` 在内部渲染时创建的 BaseTransition **假实例**(无 data 面)。
> 这些假实例上求值 watch getter(如 `this.qbCurData`)即抛 TypeError, 且**每个 transition 抛一条**
> (实测 13 个 `<transition>` = 13 条报错), 页面功能不受影响但控制台刷屏、pageerror 巡检全红。
> 全局 mixin 需要响应某状态的场合, 改在根实例 `mounted()` 里 `$watch` 单发注册(带数据面守卫
> `if (!this.drawer) return` 跳过假实例), `beforeUnmount` 摘除。
> 触发: 全局 mixin, app.mixin, watch 选项, transition, BaseTransition, TypeError, drawerTpl, 变体, 根实例 $watch
> 收口: 2026-10-06, drawer_templates.js 改根实例 mounted $watch 单发注册(数据面守卫), 见文件头「S6 接入说明」

## 条目

### 全局 mixin 的 watch/computed 会被无 data 面的假实例求值

- **触发**: `window.AQB_DRAWER_TPL` 走 `app.mixin()` 全局注入(详情面板模板核心层, 计划
  26-10-06-0838 S6); traffic 变体需要「`qbCurData` 引用替换即重渲染」的落袋通知, 直觉写法是
  mixin 里加 `watch: { qbCurData() { … } }` —— 编译期/装载期无任何异常, 纯运行期爆。
- **判别**: 页面一加载控制台出现**成批 TypeError**, 数量 == 模板里 `<transition>` 个数
  (实测 13 个 transition = 13 条报错); 栈指向 watch getter 求值, 顶层组件功能看似正常 ——
  抛错的是**假实例**, 真实例的 watch 照跑。黑盒巡检(pageerror / console.error 收集)直接判红,
  肉眼走查完全无感。根因: Vue 全局 mixin 对**所有**组件实例生效, `<transition>` /
  `<transition-group>` 渲染时创建的 BaseTransition 内部假实例**没有业务 data 面**
  (无 `drawer` / `qbCurData` 等字段), watch getter 拿到这种实例一求值, 依赖链即断。
- **处置**: **全局 mixin 对象里不写 `watch` 选项**(computed 同理慎放 —— 假实例虽不渲染,
  访问求值同样可能炸)。需要根级响应的场合: 真根实例 `mounted()` 里 `this.$watch(...)` 单发
  注册, 注册前加**数据面守卫**(`if (!this.drawer) return` —— 真根实例恒有, 假实例恒无, 以业务
  字段在场与否区分); `beforeUnmount` 摘除。参照实现: `shared/drawer_templates.js` 的
  `mounted()` / `beforeUnmount()` 与文件头「S6 接入说明」。替代路线(未采用但可行): 不进 mixin,
  在挂载单点(app.js 末尾一次性 init)直接对根实例 $watch。
