# 跨文件直调 mixin 全局对象方法少写 .methods 层 —— 根对象无此键, 每行渲染 TypeError 刷屏

> 摘要: `window.AQB_*` mixin 对象的方法嵌在 `.methods` 层下, 跨文件直调写根路径(`AQB_DECORATE.hrExclClass(...)`)时根对象无此键, 调用点每次执行必抛 `is not a function`; 模板绑定走 Vue mixin 不受影响, 只有 window 直调点炸 —— pytest 静态守阵不执行 JS 调用路径, e2e 未跑即静默上线。新跨文件直调点必须同批落静态断言钉扎。
> 触发: is not a function, hrExclClass, hrExclTip, AQB_DECORATE, methods 层, 根路径直调, 跨文件调用, mixin 全局对象, 每行渲染 TypeError, 判定门单点化, window.AQB_DECORATE
**Refs:** memory-bank/tasks/26-11-14-webui-hr-excl-tip-methods-layer.md

## 本篇只回答

JS 跨文件直调 mixin 全局对象(`window.AQB_DECORATE` 等, app.js:903-937 注册)方法时**调用层级写错**的坑: 根因形态、报错信息判别、为什么静态测试拦不住、新调用点的强制配套。Vue mixin 机制本身、缓存/部署类故障不在此篇。

### 根路径直呼 methods 层方法, 每行渲染 TypeError 刷屏 (2026-11-14 实测)

- **触发**: 跨文件直调 `window.AQB_DECORATE.hrExclClass(face, member)`(hr.js:193, cd14ffe6 引入)—— 方法实际定义在 `window.AQB_DECORATE = { methods: { ... hrExclClass ... } }`(decorate.js:122-123/313)的 **methods 层内**, 根层只有 methods/computed 两键。调用点位于行渲染模板链(hrExclTip 供 4 处 chip :title), 每行渲染必抛 `TypeError: window.AQB_DECORATE.hrExclClass is not a function`; 连带 dt_table.assertLayout「行格 0」报警(行内格子渲染中断的下游症状, 非独立缺陷)。
- **判别**: 报错信息形态定层 —— 「X is not a function」= 基对象存在但键缺失(层级写错, 本坑形态); 「Cannot read properties of undefined (reading 'X')」= **链上某一跳 undefined** —— 单跳链是基对象未定义(脚本未加载/未执行), 多跳链(AQB_DECORATE.methods.hrExclClass)则含中间层缺失/改名形态, 按报错列号与链逐跳核对, 不必然是脚本未加载。报错栈列号精确到属性访问点(hr.js:193:34 的列 34 恰是 `.hrExclClass` 起始), 与定义处花括号深度核对(methods 层成员 depth=3)即可当场定位 —— 本例排查在环境侧(强刷/远端部署/304 缓存/双实例/指纹)绕了 8 轮才回到代码, 教训: **报错栈列号 + 定义处结构深度核对是第一动作, 先于一切环境侧假设**。
- **为什么静默上线**: pytest 静态守阵读文件不执行 JS(调用路径的运行时行为不可见); 现有 @fast e2e(flux-cat-chip-hr-semantics.spec.mjs 渲染同一路径, e2e/lib/errors.mjs:52-56 挂运行期零 console.error/pageerror 守卫)**当跑必拦本类错** —— 静默上线的缺口是「本批未跑 e2e」的批次流程面, 不是 e2e 覆盖面。静态断言的价值 = 把拦截面挪进每批必跑的 pytest, 不依赖有时才跑的 e2e。cd14ffe6 动机里「无断言钉扎」的缺口 + 本批 e2e 未跑, 双重失守。
- **处置**: 调用补 `.methods` 层(`window.AQB_DECORATE.methods.hrExclClass(...)`), 不改用 `this.hrExclClass`(维持原「不依赖 this」直调语义)。**新跨文件直调点必须同批落静态断言钉扎**(守阵第 5 组, 经 3 轮评审收敛的四形态): ① 切 AQB_DECORATE 顶层片段(赋值起至 `^  computed: \{` 止, re.M|re.S)锚定层级结构; ② 片段内 `methods: {` 存在性(不锚首键, 前插键不假红); ③ 定义缩进敏感锚定 `^    hrExclClass\(...`(methods 成员 4 空格, 根层键 2 空格, 挪层必红); ④ 调用走 `.methods.` + 根路径直呼归零(双向)。
- **守阵**: `tests/test_webui_static_skins_widget.py::test_frontend_hr_safety_wiring` 第 5 组断言(回退修复/删定义/挪层级/根路径直呼四形态均红, 评审员变异推演证实)。
