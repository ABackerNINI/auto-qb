/* 迁移路径链浮窗(计划 26-11-04-1042 P2-2/P2-3)
 *
 * 事实来源是后端 `GET /api/relocate/chain?hash=...`(服务端派生起点, 客户端只传 hash)。
 * **列表渲染期零探测**: 本文件只在浮窗打开或点「重新探测」时发请求, 任何 decorate/row 路径
 * 都不调用它 —— 否则一屏几十行就是几十次 lstat。
 *
 * 交互可达性: 徽标 / 详情段「路径链」按钮 >= 点击打开; Esc 关闭走 lifecycle 退栈链;
 * 打开时焦点进浮窗, 关闭时回退到触发钮; 透明背板承接点外关闭(触屏 tap 同一路径)。
 */
(function () {
  "use strict";

  // 全局监听惰性挂一次(与 hr.js 同式): 滚动/缩放即关, 浮窗不会留在旧锚点位置漂移
  let relChainGlobalsHooked = false;

  const REL_CHAIN_TYPE_TEXT = {
    junction: "junction",
    symlink: "符号链接",
    hardlink: "硬链接",
    dir: "普通目录",
    file: "文件",
    mount: "挂载点",
    other: "其它类型",
    unknown: "未知类型",
  };

  const REL_CHAIN_STATUS_TEXT = {
    ok: "已确认",
    unknown: "未确认",
    missing: "路径不存在",
    permission: "权限不足",
    cycle: "检测到环",
    outside_scope: "范围外",
    limit: "链路过长",
  };

  // job phase -> 用户状态词(与 P1 状态词表同口径; S4 相位模型): watching 归「迁移中」,
  // moved/armed/rewritten 归「待收尾」(旧收尾窗三相位已退役, 旧账在加载侧已映射)
  const REL_CHAIN_PHASE_TEXT = {
    moving: "迁移中",
    watching: "迁移中",
    moved: "待收尾",
    armed: "待收尾",
    rewritten: "待收尾",
    failed: "迁移失败",
    done: "已完成",
    cancelled: "已取消",
  };

  window.AQB_RELOCATE_CHAIN = {
    data() {
      return {
        relChain: {
          open: false,
          hash: "",
          loading: false,
          error: "",
          data: null,
          left: 0,
          top: 0,
          width: 460,
          subtitle: "",
          seq: 0,
          finalizing: false,
        },
      };
    },
    methods: {
      relChainOpen(hash, anchor) {
        if (!hash) return;
        if (this.relChain.open && this.relChain.hash === hash) {
          this.relChainClose();
          return;
        }
        this._relChainOpener = anchor || null;
        this.relChain = {
          open: true,
          hash,
          loading: false,
          error: "",
          data: null,
          left: 8,
          top: 8,
          width: Math.min(460, window.innerWidth - 16),
          subtitle: hash.slice(0, 12),
          seq: this.relChain.seq + 1,
          finalizing: false,
        };
        this._relChainGlobals();
        this.relChainPlace(anchor);
        this._relChainFetch(hash, false);
      },

      _relChainGlobals() {
        if (relChainGlobalsHooked) return;
        relChainGlobalsHooked = true;
        // capture 阶段接滚动: 行内滚动容器滚动时同样关闭(浮窗定位相对旧锚点必然漂移)
        window.addEventListener("scroll", (ev) => {
          if (!this.relChain.open) return;
          // 浮窗自身可滚(长链): 内部滚动不关, 否则长链永远滚不动
          const pop = this.$refs && this.$refs.relChainPop;
          const t = ev && ev.target;
          if (pop && t && (t === pop || (t.nodeType === 1 && pop.contains(t)))) return;
          this.relChainClose(false);
        }, true);
        window.addEventListener("resize", () => {
          if (this.relChain.open) this.relChainClose(false);
        });
      },

      relChainClose(restoreFocus) {
        const opener = this._relChainOpener;
        this._relChainOpener = null;
        this.relChain.open = false;
        this.relChain.loading = false;
        if (restoreFocus !== false && opener && typeof opener.focus === "function") {
          try { opener.focus(); } catch (e) { /* 触发钮可能已随行卸载 */ }
        }
      },

      relChainRefresh() {
        if (!this.relChain.open || this.relChain.loading) return;
        this._relChainFetch(this.relChain.hash, true);
      },

      async _relChainFetch(hash, refresh) {
        const seq = ++this.relChain.seq;
        this.relChain.loading = true;
        this.relChain.error = "";
        const url = "/api/relocate/chain?hash=" + encodeURIComponent(hash) + (refresh ? "&refresh=1" : "");
        try {
          const data = await this.api(url);
          if (seq !== this.relChain.seq || !this.relChain.open) return;
          this.relChain.data = data;
          this.relChain.loading = false;
          this.$nextTick(() => this.relChainPlace(this._relChainOpener));
        } catch (e) {
          if (seq !== this.relChain.seq || !this.relChain.open) return;
          this.relChain.loading = false;
          this.relChain.error = "路径链读取失败: " + this.relChainErrorText(e);
        }
      },

      relChainErrorText(e) {
        const msg = (e && e.message) || "";
        if (msg === "unauthorized") return "密钥无效或已更换";
        return msg || "网络或服务端错误";
      },

      relChainPlace(anchor) {
        if (!this.relChain.open) return;
        const vw = window.innerWidth || 1024;
        const vh = window.innerHeight || 768;
        const width = Math.min(460, vw - 16);
        const pad = 8;
        let left = pad;
        let top = pad;
        if (anchor && anchor.getBoundingClientRect) {
          const r = anchor.getBoundingClientRect();
          left = r.left + r.width - width;
          top = r.bottom + 8;
          if (left < pad) left = pad;
          if (left + width > vw - pad) left = vw - width - pad;
          // 下方放不下就翻到触发钮上方(高度未知时按 360 估, 渲染后再按实测高度校正)
          if (top + 360 > vh - pad) top = Math.max(pad, r.top - 360);
        } else {
          left = Math.max(pad, (vw - width) / 2);
          top = Math.max(pad, (vh - 400) / 2);
        }
        this.relChain.width = width;
        this.relChain.left = left;
        this.relChain.top = top;
        this.$nextTick(() => {
          const el = this.$refs && this.$refs.relChainPop;
          if (!el || !anchor || !anchor.getBoundingClientRect) {
            if (el && typeof el.focus === "function") el.focus();
            return;
          }
          const r = anchor.getBoundingClientRect();
          const h = el.offsetHeight || 0;
          if (this.relChain.top + h > vh - pad && r.top - h - pad >= pad) {
            this.relChain.top = r.top - h - pad;
          }
          if (typeof el.focus === "function") el.focus();
        });
      },

      relChainTypeText(type) {
        return REL_CHAIN_TYPE_TEXT[type] || REL_CHAIN_TYPE_TEXT.unknown;
      },

      relChainStatusText(node) {
        const text = REL_CHAIN_STATUS_TEXT[node && node.status] || REL_CHAIN_STATUS_TEXT.unknown;
        if (node && node.status === "unknown" && node.reason) return text + ": " + node.reason;
        return text;
      },

      relChainPhaseText(phase) {
        return REL_CHAIN_PHASE_TEXT[phase] || this.relocateStateText(phase);
      },

      relChainProbedText() {
        const ts = this.relChain.data && this.relChain.data.probed_at;
        const when = ts ? this.fmtTs(ts) : "—";
        return this.relChain.data && this.relChain.data.cached ? "缓存结果 · 探测于 " + when : "探测于 " + when;
      },

      relChainCopyAll() {
        const nodes = (this.relChain.data && this.relChain.data.nodes) || [];
        const text = nodes.map((n) => n.path).filter(Boolean).join(" -> ");
        if (text) this.copyText(text, " 路径链");
      },

      /* ---------------- D14「立即收尾」+ S3 失败反馈面(计划 26-11-05-0808) ----------------
       * 数据源 = 链结果的 finalize 段(后端 relocate_chain.finalize_face, 不进缓存现读);
       * 可见性判据单点在后端(window = FINALIZE_WINDOW_PHASES), 前端只渲染不重判。
       * 确认框带现场说明(关闭 qB / 改写 / 需手动重启, §07 按钮误触行); 调用失败
       * (缺失/被拒/断连)降级为提示手动重启 qB —— 不重试、不自动重启(保守默认)。 */
      relChainFinalizeFace() {
        return (this.relChain.data && this.relChain.data.finalize) || null;
      },

      relChainFinalizeWindow() {
        const face = this.relChainFinalizeFace();
        return !!(face && face.window);
      },

      relChainFinalizePending() {
        const face = this.relChainFinalizeFace();
        return !!(face && face.pending > 0 && face.daemon_stale);
      },

      async relChainFinalizeNow() {
        const face = this.relChainFinalizeFace();
        if (!face || this.relChain.finalizing) return;
        const ok = await this.confirmDialog("立即收尾",
          "将向 qB 下达关闭指令: qB 退出后, 回收 daemon 会在下线窗口改写成员 fastresume 指向新位置; "
          + "改写完成后需要你手动重启 qB。期间该组不可用。确认关闭 qB?",
          { okText: "关闭 qB", danger: true });
        if (!ok) return;
        this.relChain.finalizing = true;
        try {
          const resp = await this.api("/api/relocate/finalize-now", {
            method: "POST",
            body: JSON.stringify({ confirm: true, job_id: face.job_id }),
          });
          this.relChain.finalizing = false;
          if (resp && resp.cls === "ok") {
            this.toast(resp.note || "已下达关闭指令, 待收尾改写完成后请手动重启 qB", "ok", 10000);
          } else {
            /* blocked(窗口已推进)/degraded(shutdown 缺失或被拒)统一降级提示 */
            this.toast((resp && resp.note) || "立即收尾未执行, 请手动重启 qB 完成收尾", "warn", 10000);
          }
        } catch (e) {
          this.relChain.finalizing = false;
          const msg = (e && e.message) || "网络或服务端错误";
          this.toast("立即收尾不可用: " + msg + ", 请手动重启 qB 完成收尾", "warn", 10000);
        }
      },
    },
  };
})();
