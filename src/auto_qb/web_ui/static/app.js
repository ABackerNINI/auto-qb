/* auto-qb WEB UI 前端(Vue 3 CDN, 无构建链): 轮询快照 + 命令投递 */
const { createApp, ref, computed, onMounted } = Vue;

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
      menu: { visible: false, x: 0, y: 0, key: null },
      settingsText: "",
      saving: false,
      saveMsg: "",
      saveOk: false,
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
    if (!this.token) {
      this.authRequired = true;
      return;
    }
    await this.bootstrap();
  },
  methods: {
    async api(path, options = {}) {
      const resp = await fetch(path, {
        ...options,
        headers: { Authorization: `Bearer ${this.token}`, "Content-Type": "application/json", ...(options.headers || {}) },
      });
      if (resp.status === 401) {
        this.authRequired = true;
        throw new Error("unauthorized");
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
      } catch (e) {
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
    async refreshOnce() {
      const [status, groups] = await Promise.all([this.api("/api/status"), this.api("/api/groups")]);
      this.status = status;
      this.groups = groups.groups;
    },
    async refresh() {
      try {
        const [status, groups] = await Promise.all([this.api("/api/status"), this.api("/api/groups")]);
        this.status = status;
        this.groups = groups.groups;
      } catch (e) {
        /* 网络抖动: 下一轮重试 */
      }
    },
    async openSettings() {
      this.page = "settings";
      try {
        const data = await this.api("/api/config/raw");
        this.settingsText = data.content;
        this.saveMsg = "";
      } catch (e) {
        this.saveMsg = "载入配置失败: " + e.message;
        this.saveOk = false;
      }
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
    toggleExpand(key) {
      this.expandedKey = this.expandedKey === key ? null : key;
      this.menu.visible = false;
    },
    openMenu(event, group) {
      event.preventDefault();
      this.menu = { visible: true, x: event.clientX, y: event.clientY, key: group.key };
      this.expandedKey = group.key;
    },
    async act(action) {
      this.menu.visible = false;
      if (!this.menu.key) return;
      try {
        await this.api(`/api/groups/${this.menu.key}/${action}`, { method: "POST" });
      } catch (e) {
        this.saveMsg = "命令发送失败: " + e.message;
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
  },
}).mount("#app");

// 全局点击关闭右键菜单
document.addEventListener("click", () => {
  const menus = document.querySelectorAll(".ctx-menu");
  menus.forEach((m) => (m.style.display = "none"));
});
