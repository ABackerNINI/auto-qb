/* dialogs_history.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 弹窗 · 历史流量开层与拖拽。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.AQB_DIALOGS.methods, {
    /* ---------------- 历史流量弹层(今日流量面板入口; 天/月/年切换 + 悬停取值) ---------------- */
    async openHistory() {
      this.historyOpen = true;
      await this.loadHistory();
    },
    async loadHistory() {
      await this._panelLoad(this, async () => {
        const data = await this.api("/api/traffic/history");
        this.historyData = data.history || [];
        // 26-10-17-1737 S1: 快照态随响应带回(off = 来源总开关关闭), 空态文案据此指到总开关
        this.historyState = data.state || "disabled";
      }, { loading: "historyLoading", err: "historyError", errFallback: "加载失败" });
    },
    /* 悬停追踪: 事件挂在 .hist-chart容器(mousemove), 指针 x 折算进 viewBox 坐标再换算
     * 桶索引 —— 连续无空隙; 旧版逐桶 enter/leave + 命中区只盖单柱的闪烁根因即在此 */
    histMove(ev) {
      if (!this.historyBuckets.length) return;
      const rect = ev.currentTarget.getBoundingClientRect();
      const g = this.histGeom;
      const x = ((ev.clientX - rect.left) / rect.width) * g.w;
      const idx = Math.floor((x - g.padL) / g.bw);
      this.histHoverIdx = Math.max(0, Math.min(this.historyBuckets.length - 1, idx));
    },
    histLeave() {
      this.histHoverIdx = -1;
    },
    /* 面积填充路径(折线下方淡渐染; 带参辅助放 methods —— pitfalls: computed不能加括号调用) */
    _histArea(key) {
      const pts = this.histSeries[key];
      if (!pts.length) return "";
      const base = (this.histGeom.padT + this.histGeom.chartH).toFixed(1);
      return `${this.histPaths[key]} L ${pts[pts.length - 1].x.toFixed(1)} ${base} L ${pts[0].x.toFixed(1)} ${base} Z`;
    },
});
