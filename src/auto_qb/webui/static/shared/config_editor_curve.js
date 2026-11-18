/* config_editor_curve.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 配置编辑器 · 全局限速曲线与图表。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.CONFIG_EDITOR.methods, {

    /* ---------------------------------------------------------- 限速曲线编辑器 */

    cfgCurvePath() {
      return [...this.cfgConfigPath(), "global_speed_limit_curve"];
    },
    cfgCurveEnabled() {
      return this.cfgExists(this.cfgCurvePath());
    },
    cfgCurveEnable() {
      // S17/D15: 来源字段已迁到「全局流量来源」卡(config.traffic_source) —— 曲线卡不再播种
      // 来源段, 只留 curves; 取数路径由 traffic_source 单点决定。
      this.cfgSetPath(this.cfgCurvePath(), { curves: [] });
    },
    async cfgCurveDisable() {
      // 整段移除 = 无名字实体的删除: 交给同一骨架(def 不写 name, 直接对 path 动手)
      return this.cfgEntityRemove({
        path: this.cfgCurvePath(),
        title: "关闭全局限速曲线",
        body: "当前曲线配置将从配置文件中移除。",
        okText: "关闭并移除",
      });
    },
    cfgCurve() {
      return this.cfgRaw(this.cfgCurvePath()) || null;
    },
    cfgCurveItems() {
      const base = this.cfgCurvePath();
      return [
        // SPD-03 enabled 总开关: 勾 = 写 enabled:true, 取消勾 = 写 enabled:false(保留各档配置, 不删段);
        // 键缺省 = 后端默认 true, 开关按勾选显示并带"默认"角标
        { type: "field", field: { key: "enabled", label: "启用", kind: "bool", default: true, help: "关闭后曲线任务整体停用(不写 qB), 各档配置保留" }, path: [...base, "enabled"], depth: 0 },
        { type: "field", field: { key: "interval", label: "执行间隔", kind: "time", help: "曲线任务多久重算一次并套用全局限速: 读 dat、按各 period 曲线聚合查档、写 qB 全局速度限制。只管写限速 —— 历史流量图的刷新节奏见「流量来源」的「刷新间隔」, 两者独立。流量按日聚合, 不必太频繁(分钟级即可, 不必秒级)。留空 = 回退常规 → interval, 与维护 / 全局清理等内置任务同周期。", default: "" }, path: [...base, "interval"], depth: 0 },
      ];
    },
    cfgCurveList() {
      const c = this.cfgCurve();
      return c && Array.isArray(c.curves) ? c.curves : [];
    },
    cfgCurvePeriod(i) {
      const item = this.cfgCurveList()[i];
      return item && item.curve ? item.curve : {};
    },
    cfgCurvePeriodPath(i) {
      return [...this.cfgCurvePath(), "curves", i, "curve"];
    },
    /* JS 排序键复刻 —— Python 单点在 src/auto_qb/core/curves.py 的 period_sort_key(计划
     * 26-11-18-0801 D4/D12, 两侧注释互指): 归一化后 day=(0,) < {N}D=(1,N) 按 N 数值比较
     * (2D < 10D, 非字典序) < month=(2,) 恒最后。别名口径与 Python normalize_period 一致
     * (DAY/D/1D -> day; MONTH; N>=1 的 ND)。非法 period 返回 null(对应 Python 抛
     * ValueError), 调用方按 D11 整段放弃, 不部分重排。返回数组模拟 Python 元组, 字典序
     * 比较见 _cfgCurveKeyCmp; 改键序必须两侧同步。
     * 精度上限(评审 nit, 接受该边界不做 BigInt): N 经 parseInt 按 float64 解析, >2^53 天
     * 不现实 —— 超界 N 的草稿序可与后端规范序分叉(保存一次即被后端归一)。
     */
    _cfgCurvePeriodSortKey(period) {
      // 非 string 一律 null(与 Python 语义等价): YAML 可达的非字符串标量经 Python str() 后
      // 不可能命中别名/ND 模式, 故 typeof 门 == period_sort_key 对非字符串抛 ValueError。
      // 不能用 String() 强转 —— 树内 period 为数组(如 ['DAY'])时 String(['DAY'])==='DAY'
      // 会误解析出 day 键, 而 Python 侧抛 ValueError -> GET 面整段放弃排序(D8), 前端若照常
      // 重排/定位插入即两侧策略分叉(D11)。
      if (typeof period !== "string") return null;
      const s = period.trim().toUpperCase();
      if (s === "DAY" || s === "D" || s === "1D") return [0];
      if (s === "MONTH") return [2];
      const m = s.match(/^(\d+)D$/);
      if (m && parseInt(m[1], 10) >= 1) return [1, parseInt(m[1], 10)];
      // 全角数字分叉(评审 nit, 接受该边界不做 Unicode 数字类): Python \d 匹配 Unicode 数字
      // 且 int() 可解析('７D' -> (1,7) 合法, GET 面正常排序), JS \d 仅 ASCII -> 此处返回 null
      // 走 D11 放弃 —— 前端更保守, 只少排不错排, 保存一次即被后端归一自愈。
      return null;
    },
    /* 排序键字典序比较(模拟 Python 元组比较): 逐元素比, 短键缺位视为最小(键分量恒非负) */
    _cfgCurveKeyCmp(a, b) {
      for (let i = 0; i < Math.max(a.length, b.length); i++) {
        const x = a[i] === undefined ? -1 : a[i];
        const y = b[i] === undefined ? -1 : b[i];
        if (x !== y) return x - y;
      }
      return 0;
    },
    cfgCurveAddPeriod() {
      const list = [...this.cfgCurveList()];
      const item = { curve: { period: "1D" } };
      // 新增定位插入(D9, 计划 26-11-18-0801): 按天数定位(默认 1D -> day 键 -> 插最前),
      // 否决尾部追加。D11: 任一既有 period 解析不了 -> 放弃定位退回尾部追加(与 GET 面
      // _sort_tree_curve_periods 的 D8 整段放弃同策略)。
      const key = this._cfgCurvePeriodSortKey(item.curve.period);
      const keys = list.map((it) => this._cfgCurvePeriodSortKey(it && it.curve ? it.curve.period : undefined));
      let at = list.length;
      if (key !== null && keys.every((k) => k !== null)) {
        at = 0;
        while (at < list.length && this._cfgCurveKeyCmp(keys[at], key) <= 0) at++;
      }
      list.splice(at, 0, item);
      this.cfgSetPath([...this.cfgCurvePath(), "curves"], list);
      // 新曲线顺手展开(默认折叠是给已有条目的, 新加的下一步就是编辑它); openCurves 按
      // 实际插入下标记录, 插入点之后的条目序号后移 —— 展开态跟着条目身份保住
      const open = {};
      for (const [k, v] of Object.entries(this.cfg.openCurves)) {
        const idx = Number(k);
        open[idx >= at ? idx + 1 : idx] = v;
      }
      open[at] = true;
      this.cfg.openCurves = open;
    },
    /* period 输入 @change(失焦/回车)提交: 整段重排 + openCurves 按条目身份跟随搬移
     * (计划 26-11-18-0801 D10)。逐键重排被否决 —— v-for 是下标 key(traffic-card.html),
     * 重排后焦点行数据换条, 继续键入会写错条目; 故 @input 逐键写树照旧不动, 重排只挂
     * 提交时机。D11: 任一 period 解析不了 -> 整段放弃重排(树保持 @input 写下的原序)。
     */
    cfgCurvePeriodCommit(event) {
      const list = [...this.cfgCurveList()];
      const keys = list.map((it) => this._cfgCurvePeriodSortKey(it && it.curve ? it.curve.period : undefined));
      if (keys.some((k) => k === null)) return;
      const order = keys.map((k, idx) => ({ k, idx }));
      order.sort((a, b) => this._cfgCurveKeyCmp(a.k, b.k));  // Array.sort 稳定(ES2019+); 键唯一时无歧义
      if (order.every((o, pos) => o.idx === pos)) return;  // 已是规范序: 不动, 免无谓重排抖展开态
      this.cfgSetPath([...this.cfgCurvePath(), "curves"], order.map((o) => list[o.idx]));
      // 展开态按条目身份搬移(参照 cfgCurveRemovePeriod 的序号搬移模式): 旧下标 o.idx -> 新下标 pos
      const open = {};
      for (let pos = 0; pos < order.length; pos++) {
        const v = this.cfg.openCurves[order[pos].idx];
        if (v !== undefined) open[pos] = v;
      }
      this.cfg.openCurves = open;
      // 回车提交路径收口(评审 minor): change 触发时焦点仍在原输入框(下标 key 复用同一 DOM
      // 节点), 重排后该框显示的是另一条的 period, 继续键入会写进错条目 —— 提交成功重排后
      // 主动 blur, 提交触发收敛为失焦单语义(blur 触发的提交此处是 no-op; 双重 change 即使
      // 发生也无害: 二次提交遇已规范序即早退, 且 blur 对值未再变的输入框不会重发 change)。
      if (event && event.target && typeof event.target.blur === "function") event.target.blur();
    },
    cfgCurveRemovePeriod(i) {
      const list = [...this.cfgCurveList()];
      list.splice(i, 1);
      if (list.length) this.cfgSetPath([...this.cfgCurvePath(), "curves"], list);
      else this.cfgDelPath([...this.cfgCurvePath(), "curves"]);
      // 展开态按序号记录: 删中间一条后其后各条序号前移, 同步搬移保住各条的展开态
      const open = {};
      for (const [k, v] of Object.entries(this.cfg.openCurves)) {
        const idx = Number(k);
        if (idx !== i) open[idx > i ? idx - 1 : idx] = v;
      }
      this.cfg.openCurves = open;
    },
    cfgCurveOpen(i) {
      return !!this.cfg.openCurves[i];
    },
    cfgCurveToggle(i) {
      this.cfg.openCurves = { ...this.cfg.openCurves, [i]: !this.cfg.openCurves[i] };
    },
    /* 档位列表: direction 为 "upload_curve" | "download_curve" */
    cfgCurvePoints(i, direction) {
      const period = this.cfgCurvePeriod(i);
      return Array.isArray(period[direction]) ? period[direction] : [];
    },
    cfgCurvePointsPath(i, direction) {
      return [...this.cfgCurvePeriodPath(i), direction];
    },
    cfgCurvePointAdd(i, direction) {
      const directionKey = this.cfgCurveDirectionKey(direction);
      const list = [...this.cfgCurvePoints(i, direction)];
      // 阈值键为动态字符串(如 10GiB); 新增档位给空阈值由用户填写
      list.push({ "": { [directionKey]: "0KiB/s" } });
      this.cfgSetPath(this.cfgCurvePointsPath(i, direction), list);
    },
    cfgCurvePointRemove(i, direction, j) {
      const list = [...this.cfgCurvePoints(i, direction)];
      list.splice(j, 1);
      if (list.length) this.cfgSetPath(this.cfgCurvePointsPath(i, direction), list);
      else this.cfgDelPath(this.cfgCurvePointsPath(i, direction));
    },
    /* 曲线方向->限速键映射单点(收敛 issue 26-10-20-2231 / 台账 R20-C-10): 加第三方向(如双向
     * 曲线)只改这一处; 调用侧**禁止内联**同名三元。 */
    cfgCurveDirectionKey(direction) {
      return direction === "upload_curve" ? "upload_speed_limit" : "download_speed_limit";
    },
    /* 档位阈值键(动态): 改写键即重建该档对象 */
    cfgCurveThreshold(i, direction, j) {
      const entry = this.cfgCurvePoints(i, direction)[j];
      return entry ? Object.keys(entry)[0] || "" : "";
    },
    cfgCurveSpeed(i, direction, j) {
      const entry = this.cfgCurvePoints(i, direction)[j];
      if (!entry) return "";
      const key = Object.keys(entry)[0];
      const speed = entry[key] || {};
      return this.cfgScalar(speed[this.cfgCurveDirectionKey(direction)] || "");
    },
    cfgCurvePointSet(i, direction, j, threshold, speed) {
      const t = threshold === undefined ? this.cfgCurveThreshold(i, direction, j) : threshold;
      const s = speed === undefined ? this.cfgCurveSpeed(i, direction, j) : speed;
      const list = [...this.cfgCurvePoints(i, direction)];
      list[j] = { [t]: { [this.cfgCurveDirectionKey(direction)]: s } };
      this.cfgSetPath(this.cfgCurvePointsPath(i, direction), list);
    },

    /* ---------------------------------------------------------- 曲线图表(SVG 阶梯折线预览)
     *
     * 纯展示: 前端只用它画图, 解析失败不阻断保存(合法性唯一入口仍是后端 load_config)。
     * 语义与 curves.curve_speed 一致 —— 阈值是区间**上限**, 末档之后一直沿用末档速度。
     */

    cfgCurveInvalid(i, direction) {
      // 无法解析的档位数(阈值需形如 10GiB, 限速需形如 6MiB/s)
      let bad = 0;
      const points = this.cfgCurvePoints(i, direction);
      for (let j = 0; j < points.length; j++) {
        if (this._parseSizeValue(this.cfgCurveThreshold(i, direction, j)) === null ||
          this._parseSpeedValue(this.cfgCurveSpeed(i, direction, j)) === null) bad++;
      }
      return bad;
    },
    cfgCurveChartOf(i, direction) {
      return this.cfgCurveCharts[`${i}:${direction}`] || null;
    },
    /* 阶梯折线数据(纯展示)
     *
     * 语义与 curves.curve_speed 一致: 阈值是区间**上限**, 末档之后一直沿用末档速度。
     * 输出包含: 曲线 path、面积 path、X/Y 轴刻度与档位边界参考线、∞ 区水印、悬停标记点几何 —— 全部由前端算,
     * 图尺寸足够大可读(PAD 留出轴标签空间)。合法性/解析失败仍只提示不阻断(后端把关)。
     * x 轴按各档**实际流量长度**比例分段(2026-09-27 重构, 取代旧"每档等宽"): t_1..t_{n-1} 把
     * [0, 末档下限] 切成 n-1 个有限区间按长度分摊 70% 宽度; 末档与后端语义一致(X ≥ 末档下限后
     * 一直沿用末档速度, 末档阈值不改变速度函数)显示为 ∞ 区、占宽不超过 30%(仅 1 档时整图即 ∞, 独占全宽)。
     */
    _buildCurveChart(i, direction) {
      const raw = this.cfgCurvePoints(i, direction);
      const points = [];
      for (let j = 0; j < raw.length; j++) {
        const t = this._parseSizeValue(this.cfgCurveThreshold(i, direction, j));
        const s = this._parseSpeedValue(this.cfgCurveSpeed(i, direction, j));
        if (t === null || s === null || t <= 0) continue;
        points.push({ t, s });
      }
      if (!points.length) return null;
      points.sort((a, b) => a.t - b.t);

      // 几何: 左侧留 Y 轴标签, 底部留 X 轴标签; 图体明显放大(旧版 320×96 太小)
      const W = 560, H = 210, PAD_L = 58, PAD_R = 14, PAD_T = 12, PAD_B = 30, TICK_GAP = 46;
      const usableW = W - PAD_L - PAD_R;
      const maxS = Math.max(...points.map((p) => p.s), 1);
      const y = (s) => H - PAD_B - (H - PAD_B - PAD_T) * (s / maxS);

      // 末档 ∞ 区占图体 ≤30%(封顶防其它档被挤没); 其余有限区间按流量长度比例分摊剩余宽度
      const n = points.length;
      const W_inf = n === 1 ? usableW : usableW * 0.3;
      const W_finite = usableW - W_inf;
      const span = n > 1 ? points[n - 2].t : 0;  // 最后一个有限断点(= 末档下限)
      const x = (t) => PAD_L + (span > 0 ? (t / span) * W_finite : 0);

      // 阶梯线: 断点 t_k 处速度 s_k -> s_{k+1}; 末档平线一直延伸到右缘(∞)
      let line = `M ${x(0).toFixed(1)} ${y(points[0].s).toFixed(1)}`;
      for (let k = 0; k < n - 1; k++) {
        line += ` L ${x(points[k].t).toFixed(1)} ${y(points[k].s).toFixed(1)}`;
        line += ` L ${x(points[k].t).toFixed(1)} ${y(points[k + 1].s).toFixed(1)}`;
      }
      line += ` L ${(PAD_L + usableW).toFixed(1)} ${y(points[n - 1].s).toFixed(1)}`;
      const area = `${line} L ${(PAD_L + usableW).toFixed(1)} ${y(0).toFixed(1)} L ${PAD_L.toFixed(1)} ${y(0).toFixed(1)} Z`;

      // 刻度: X 取 0 + 各有限断点 + 右缘 ∞(相邻标签过近时省略, 参考线仍画); Y 取 5 个等距限速
      const xTicksRaw = [{ pos: PAD_L, label: "0" }];
      for (let k = 0; k < n - 1; k++) xTicksRaw.push({ pos: x(points[k].t), label: this._fmtBytes(points[k].t) });
      xTicksRaw.push({ pos: PAD_L + usableW, label: "∞" });
      const xTicks = [xTicksRaw[0]];
      for (let k = 1; k < xTicksRaw.length - 1; k++) {
        if (xTicksRaw[k].pos - xTicks[xTicks.length - 1].pos >= TICK_GAP) xTicks.push(xTicksRaw[k]);
      }
      xTicks.push(xTicksRaw[xTicksRaw.length - 1]);
      const yTicks = [];
      for (let k = 0; k <= 4; k++) {
        const s = (maxS * k) / 4;
        yTicks.push({ pos: y(s), label: this._fmtSpeed(s) });
      }
      // 档位边界竖参考线: 只画真正改变速度的断点(末档阈值不改变速度函数, 不画)
      const tierLines = [];
      for (let k = 0; k < n - 1; k++) tierLines.push({ x: x(points[k].t) });
      return {
        viewBox: `0 0 ${W} ${H}`,
        w: W,
        h: H,
        padL: PAD_L,
        padR: PAD_R,
        padT: PAD_T,
        padB: PAD_B,
        line: line,
        area: area,
        xTicks: xTicks,
        yTicks: yTicks,
        tierLines: tierLines,
        baseY: y(0),
        // 悬停换算所需的数据域: 有限区宽/总跨度 + 各档边界/限速
        span: span,
        W_finite: W_finite,
        W_inf: W_inf,
        maxS: maxS,
        points: points,
        note: `${n} 档 · 纵轴上限 ${this._fmtSpeed(maxS)}`,
      };
    },
    /* 鼠标在图上移动: 把像素位置换算回 (累计流量, 限速) 并高亮该档(阶梯: 找所属区间)
     *
     * 按 SVG 实际渲染缩放换算(preserveAspectRatio 居中) —— 任凭 CSS 把图改宽改窄都不偏移,
     * 修掉旧版"假设 SVG 铺满容器"在高度被压扁时的映射错位; tooltip 位置同样用真实渲染像素
     * 还原成相对容器的百分比, 不再受容器 padding 影响。
     */
    cfgChartHover(event, i, direction) {
      const chart = this.cfgCurveChartOf(i, direction);
      if (!chart) return;
      const svg = event.currentTarget.querySelector("svg");
      const rect = svg.getBoundingClientRect();
      const box = event.currentTarget.getBoundingClientRect();
      const scale = Math.min(rect.width / chart.w, rect.height / chart.h);
      const offX = (rect.width - chart.w * scale) / 2;
      const offY = (rect.height - chart.h * scale) / 2;
      const px = (event.clientX - rect.left - offX) / scale;
      const rel = Math.max(0, Math.min(chart.w - chart.padR, px) - chart.padL);
      // 第 j 档: 有限区内按流量线性映射找区间(阈值为区间上限); ∞ 区整段归末档
      const n = chart.points.length;
      let j, tLabel;
      if (chart.span <= 0 || rel >= chart.W_finite) {
        j = n - 1;
        tLabel = "∞";
      } else {
        const t = (rel / chart.W_finite) * chart.span;
        j = 0;
        while (j < n - 1 && t >= chart.points[j].t) j++;
        tLabel = this._fmtBytes(t);
      }
      // 阶梯语义: 该累计流量落入哪一档 -> 用该档的限速
      const speed = chart.points[j].s;
      const hx = chart.padL + rel;
      const hy = chart.h - chart.padB - (chart.h - chart.padB - chart.padT) * (speed / chart.maxS);
      this.cfg.chartHover = {
        key: `${i}:${direction}`,
        x: hx,
        y: hy,
        tLabel: tLabel,
        sLabel: this._fmtSpeed(speed),
        index: j + 1,
        // tooltip 位置: SVG 内绘制坐标还原到屏幕像素, 再换算成相对容器的百分比
        leftPct: ((rect.left - box.left + offX + hx * scale) / box.width) * 100,
        topPct: ((rect.top - box.top + offY + hy * scale) / box.height) * 100,
      };
    },
    cfgChartLeave() {
      this.cfg.chartHover = null;
    },
    cfgChartHovered(i, direction) {
      const h = this.cfg.chartHover;
      return !!h && h.key === `${i}:${direction}`;
    },
    /* 单位倍数: KiB/MiB/GiB... 为 1024 进制, KB/MB/GB... 为 1000 进制; 仅 B 或空 = 1 */
    _sizeMultiplier(unit) {
      const u = String(unit || "").trim();
      if (!u || /^b$/i.test(u)) return 1;
      const idx = "KMGTP".indexOf(u[0].toUpperCase());
      if (idx < 0) return null;
      return (/(i)/i.test(u) ? 1024 : 1000) ** (idx + 1);
    },
    _parseSizeValue(text) {
      const m = String(text === undefined || text === null ? "" : text).trim().match(/^([\d.]+)\s*([A-Za-z]*)$/);
      if (!m) return null;
      const mult = this._sizeMultiplier(m[2]);
      if (mult === null) return null;
      const v = parseFloat(m[1]);
      return isNaN(v) ? null : v * mult;
    },
    _parseSpeedValue(text) {
      const t = String(text === undefined || text === null ? "" : text).trim();
      if (!t) return null;
      return this._parseSizeValue(t.replace(/\s*\/\s*s\s*$/i, ""));
    },
    /* 曲线图轴标签(收敛 issue 26-10-20-2231 / 台账 R20-C-09): 档位与进制走 format.js 的单位梯
     * 数据单点(AQB_UNIT_LADDER), 精度是**设计分歧** —— 轴标要短: toFixed(1) + 取整兜底, 梯顶
     * 只到 TiB(表格侧到 PiB)。禁止在此另抄一份梯子。 */
    _fmtBytes(v) {
      return this._fmtLadder(v, "bytes", 1, true, "TiB");
    },
    _fmtSpeed(v) {
      return this._fmtLadder(v, "speed", 1, true);
    },
});
