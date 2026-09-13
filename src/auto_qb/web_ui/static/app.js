/* auto-qb WEB UI 前端(Vue 3 CDN, 无构建链): 轮询快照 + 命令投递 + 列宽记忆 */
/* global Vue, localStorage, confirm, alert */  // 声明浏览器全局, 消除编辑器 no-undef 红线
const { createApp } = Vue;

const GROUP_DEFAULT_COLS = [
  "minmax(180px, 2fr)", "minmax(90px, 1fr)", "minmax(90px, 1fr)", "minmax(90px, 1fr)",
  "minmax(90px, 1fr)", "minmax(200px, 2fr)", "52px",
];
const DETAIL_DEFAULT_COLS = [
  "110px", "70px", "minmax(90px, 1fr)", "minmax(90px, 1fr)", "minmax(90px, 1fr)",
  "minmax(90px, 1fr)", "minmax(80px, 1fr)", "minmax(100px, 1fr)", "80px",
];
const COLS_STORE_KEY = "autoqb_colwidths_v1";

function loadColWidths() {
  try {
    return JSON.parse(localStorage.getItem(COLS_STORE_KEY)) || {};
  } catch {
    return {};
  }
}

createApp({
  data() {
    return {
      token: localStorage.getItem("autoqb_token") || "",
      tokenInput: "",
      authRequired: true,
      authError: "",
      page: "groups",
      groups: [],
      status: {},
      pollSec: 2,
      expandedKey: null,
      sortKey: "uploaded",
      sortDir: -1,
      groupColumns: [
        { key: "name", sortable: true },
        { key: "dlspeed", sortable: true },
        { key: "upspeed", sortable: true },
        { key: "uploaded", sortable: true },
        { key: "size", sortable: true },
        { key: "sites", sortable: false },
        { key: "count", sortable: true },
      ],
      detailColumns: ["站点", "状态", "下载", "上传", "总上传", "种子大小", "进度", "做种时长", "Hash"],
      colWidths: loadColWidths(),  // {group: [..px..], detail: [..px..]}, localStorage 记忆
      resizing: null,              // {page, idx, startX, startVal}
      menu: { visible: false, x: 0, y: 0, key: null, hash: null },
      settingsText: "",
      saving: false,
      saveMsg: "",
      saveOk: false,
      serviceDown: false,  // 服务不可达(程序退出): 显示全局横幅, 轮询继续以便恢复后自动接上
      pollTimer: null,
    };
  },
  computed: {
    statusBadge() {
      if (this.status.paused) return { text: "已暂停", kind: "warn" };
      if (this.status.connected === false) return { text: "qB 断开", kind: "error" };
      if (this.status.connected === true) return { text: "运行中", kind: "ok" };
      return { text: "连接中…", kind: "warn" };
    },
    sortedGroups() {
      const key = this.sortKey, dir = this.sortDir;
      return [...this.groups].sort((a, b) => {
        const va = a[key], vb = b[key];
        if (typeof va === "string") return dir * va.localeCompare(vb || "");
        return dir * ((va || 0) - (vb || 0));
      });
    },
    expandedGroup() {
      return this.groups.find((g) => g.key === this.expandedKey) || null;
    },
    totalTorrents() {
      return this.groups.reduce((n, g) => n + g.count, 0);
    },
    totalDl() {
      return this.groups.reduce((n, g) => n + g.dlspeed, 0);
    },
    totalUl() {
      return this.groups.reduce((n, g) => n + g.upspeed, 0);
    },
  },
  async mounted() {
    window.addEventListener("click", () => (this.menu.visible = false));
    if (!this.token) return;
    await this.bootstrap();
  },
  methods: {
    async api(path, options = {}) {
      const resp = await fetch(path, {
        ...options,
        headers: { Authorization: `Bearer ${this.token}`, "Content-Type": "application/json", ...(options.headers || {}) },
      });
      if (resp.status === 401) {
        // 401 = 密钥无效/轮换: 清除本地旧密钥, 强制回到密钥输入界面(防"连接中"死锁)
        this.authRequired = true;
        this.token = "";
        localStorage.removeItem("autoqb_token");
        const err = new Error("unauthorized");
        err.auth = true;
        throw err;
      }
      if (!resp.ok) {
        const detail = await resp.json().catch(() => ({}));
        throw new Error(detail.detail || `HTTP ${resp.status}`);
      }
      return resp.json();
    },
    async bootstrap() {
      try {
        this.authError = "";
        await this.refreshOnce();
        this.authRequired = false;
        localStorage.setItem("autoqb_token", this.token);
        this.startPolling();
      } catch {
        this.authError = "密钥无效或服务不可用";
      }
    },
    saveToken() {
      this.token = this.tokenInput.trim();
      this.bootstrap();
    },
    startPolling() {
      if (this.pollTimer) clearInterval(this.pollTimer);
      this.pollTimer = setInterval(() => this.refresh(), this.pollSec * 1000);
      this.refresh();
    },
    async refresh() {
      try {
        const [status, groups] = await Promise.all([this.api("/api/status"), this.api("/api/groups")]);
        this.status = status;
        this.groups = groups.groups;
        this.serviceDown = false;
      } catch (e) {
        // 服务不可达(程序退出/网络失败): 置 serviceDown 显示横幅; 轮询继续, 服务恢复后自动消失。
        // 401(密钥无效)不算服务不可达——已由登录框提示。
        if (!e.auth) this.serviceDown = true;
      }
    },
    async refreshOnce() {
      const [status, groups] = await Promise.all([this.api("/api/status"), this.api("/api/groups")]);
      this.status = status;
      this.groups = groups.groups;
      this.serviceDown = false;
    },
    async openSettings() {
      this.page = "settings";
      await this.reloadSettings();
    },
    async saveSettings() {
      this.saving = true;
      this.saveMsg = "";
      try {
        const result = await this.api("/api/config/raw", {
          method: "PUT",
          body: JSON.stringify({ content: this.settingsText }),
        });
        this.saveOk = true;
        this.saveMsg = `已保存并热重载(变更 ${result.changes} 项)`
          + (result.restart_required.length ? `;需重启进程: ${result.restart_required.join(", ")}` : "");
      } catch (e) {
        this.saveOk = false;
        this.saveMsg = "保存失败: " + e.message;
      } finally {
        this.saving = false;
      }
    },
    async reloadSettings() {
      const data = await this.api("/api/config/raw");
      this.settingsText = data.content;
      this.saveMsg = "";
    },
    fmtSpeed(v) {
      if (!v) return "0 B/s";
      for (const [unit, div] of [["GiB/s", 1073741824], ["MiB/s", 1048576], ["KiB/s", 1024]]) {
        if (v >= div) return (v / div).toFixed(2) + " " + unit;
      }
      return v + " B/s";
    },
    fmtSize(v) {
      if (v === null || v === undefined) return "-";
      if (!v) return "0 B";
      for (const [unit, div] of [["PiB", 2 ** 50], ["TiB", 2 ** 40], ["GiB", 2 ** 30], ["MiB", 2 ** 20], ["KiB", 2 ** 10]]) {
        if (v >= div) return (v / div).toFixed(2) + " " + unit;
      }
      return v + " B";
    },
    fmtDuration(sec) {
      sec = Math.floor(sec || 0);
      if (sec < 3600) return `${Math.floor(sec / 60)}分${String(sec % 60).padStart(2, "0")}秒`;
      if (sec < 86400) return `${Math.floor(sec / 3600)}时${String(Math.floor((sec % 3600) / 60)).padStart(2, "0")}分`;
      return `${Math.floor(sec / 86400)}天${String(Math.floor((sec % 86400) / 3600)).padStart(2, "0")}时`;
    },
    kindText(kind) {
      return { seeding: "做种", downloading: "下载", checking: "校验中", paused: "已暂停", error: "错误", other: "其他" }[kind] || kind;
    },
    sumField(members, key) {
      return members.reduce((n, m) => n + (m[key] || 0), 0);
    },
    sumDl(g) {
      return this.sumField(g.members, "dlspeed");
    },
    sumUl(g) {
      return this.sumField(g.members, "upspeed");
    },
    setSort(key) {
      if (this.sortKey === key) {
        this.sortDir = -this.sortDir;
      } else {
        this.sortKey = key;
        this.sortDir = -1;
      }
    },
    sortArrow(key) {
      if (this.sortKey !== key) return "";
      return this.sortDir === 1 ? "▲" : "▼";
    },
    toggleExpand(key) {
      this.expandedKey = this.expandedKey === key ? null : key;
      this.menu.visible = false;
    },
    openMenu(event, group) {
      event.preventDefault();
      this.menu = { visible: true, x: event.clientX, y: event.clientY, key: group.key, hash: null };
      this.expandedKey = group.key;
    },
    openMemberMenu(event, member) {
      event.preventDefault();
      event.stopPropagation();
      this.menu = { visible: true, x: event.clientX, y: event.clientY, key: null, hash: member.hash };
    },
    async act(action) {
      this.menu.visible = false;
      if (!this.menu.key) return;
      try {
        await this.api(`/api/groups/${this.menu.key}/${action}`, { method: "POST" });
      } catch (e) {
        alert("命令发送失败: " + e.message);
      }
    },
    async delWithFiles(deleteFiles) {
      this.menu.visible = false;
      if (!this.menu.key) return;
      if (!confirm(deleteFiles ? "确认删除整组并删除磁盘文件?此操作不可恢复!" : "确认删除整组(保留文件)?")) return;
      try {
        await this.api(`/api/groups/${this.menu.key}/delete`, {
          method: "POST",
          body: JSON.stringify({ delete_files: deleteFiles }),
        });
      } catch (e) {
        alert("删除命令发送失败: " + e.message);
      }
    },
    async actTorrent(action) {
      this.menu.visible = false;
      if (!this.menu.hash) return;
      try {
        await this.api(`/api/torrents/${this.menu.hash}/${action}`, { method: "POST" });
      } catch (e) {
        alert("命令发送失败: " + e.message);
      }
    },
    async delTorrent(deleteFiles) {
      this.menu.visible = false;
      if (!this.menu.hash) return;
      if (!confirm(deleteFiles ? "确认删除该种子并删除磁盘文件?此操作不可恢复!" : "确认删除该种子(保留文件)?")) return;
      try {
        await this.api(`/api/torrents/${this.menu.hash}/delete`, {
          method: "POST",
          body: JSON.stringify({ delete_files: deleteFiles }),
        });
      } catch (e) {
        alert("删除命令发送失败: " + e.message);
      }
    },
    gridStyle(page) {
      const defaults = page === "group" ? GROUP_DEFAULT_COLS : DETAIL_DEFAULT_COLS;
      const cols = (this.colWidths[page] || []).filter((v) => /^\d+px$/.test(v));
      // 记忆列数与默认列数不一致(结构变更)时回退默认, 防非法模板破坏布局
      const template = cols.length === defaults.length ? cols.join(" ") : null;
      return { gridTemplateColumns: template || defaults.join(" ") };
    },
    startResize(event, page, idx) {
      // 列宽拖拽: 从列头行(真正的 grid 容器)读取渲染列宽固化为 px, 拖动更新并写入 localStorage(记忆)
      const headEl = event.target.closest(".group-head") || event.target.closest(".detail-head");
      if (!headEl) return;
      const rendered = (getComputedStyle(headEl).gridTemplateColumns || "")
        .split(" ")
        .map((v) => parseFloat(v))
        .filter((v) => !isNaN(v) && v > 0);
      if (!rendered.length || idx >= rendered.length) return;
      const startX = event.clientX;
      const cols = this.colWidths[page] && this.colWidths[page].length === rendered.length
        ? [...this.colWidths[page]]
        : rendered.map((v) => `${Math.round(v)}px`);
      const startVal = parseFloat(cols[idx]) || rendered[idx] || 100;
      this.resizing = { page, idx, startX, startVal };
      const move = (e) => {
        const width = Math.max(60, Math.round(this.resizing.startVal + e.clientX - this.resizing.startX));
        cols[this.resizing.idx] = `${width}px`;
        this.colWidths = { ...this.colWidths, [page]: [...cols] };
      };
      const up = () => {
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", up);
        localStorage.setItem(COLS_STORE_KEY, JSON.stringify(this.colWidths));
      };
      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    },
  },
}).mount("#app");
