const api = {
  async get(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(await errorText(res));
    return res.json();
  },
  async post(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await errorText(res));
    return res.json();
  },
};

let state = {
  instances: [],
  tasks: [],
  selectedTaskId: "",
};

const els = {
  summary: document.querySelector("#summary"),
  refreshBtn: document.querySelector("#refreshBtn"),
  instanceForm: document.querySelector("#instanceForm"),
  taskForm: document.querySelector("#taskForm"),
  instancesBody: document.querySelector("#instancesBody"),
  tasksBody: document.querySelector("#tasksBody"),
  taskInstanceSelect: document.querySelector("#taskInstanceSelect"),
  instanceHint: document.querySelector("#instanceHint"),
  taskHint: document.querySelector("#taskHint"),
  logsBox: document.querySelector("#logsBox"),
  artifactsList: document.querySelector("#artifactsList"),
};

function statusPill(value) {
  return `<span class="pill ${escapeHtml(value)}">${escapeHtml(value)}</span>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function parseJson(value, fallback = {}) {
  const text = value.trim();
  if (!text) return fallback;
  return JSON.parse(text);
}

async function errorText(res) {
  try {
    const data = await res.json();
    return data.detail || res.statusText;
  } catch {
    return res.statusText;
  }
}

async function refreshAll() {
  const [status, instances, tasks] = await Promise.all([
    api.get("/api/scheduler/status"),
    api.get("/api/scheduler/instances"),
    api.get("/api/scheduler/tasks?limit=100"),
  ]);
  state.instances = instances;
  state.tasks = tasks;
  renderStatus(status);
  renderInstances();
  renderTasks();
  renderTaskSelect();
  if (state.selectedTaskId) await loadTaskDetail(state.selectedTaskId);
}

function renderStatus(status) {
  els.summary.textContent =
    `实例 ${status.instances_total} 个，运行中 ${status.running_instances} 个，` +
    `排队任务 ${status.queued_tasks} 个，运行任务 ${status.running_tasks} 个`;
}

function renderInstances() {
  els.instanceHint.textContent = `${state.instances.length} 个实例`;
  els.instancesBody.innerHTML = state.instances
    .map((item) => {
      const canRun = !["running", "stopping"].includes(item.status);
      return `
        <tr>
          <td><strong>${escapeHtml(item.name)}</strong><br><small>${escapeHtml(item.id)}</small></td>
          <td>${escapeHtml(item.platform)}</td>
          <td>${statusPill(item.status)}</td>
          <td>${escapeHtml(item.cdp_debug_port)}</td>
          <td>${escapeHtml(item.current_task_id || "-")}</td>
          <td>
            <div class="actions">
              <button class="secondary" data-action="login" data-id="${escapeHtml(item.id)}" ${canRun ? "" : "disabled"}>登录</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

function renderTaskSelect() {
  els.taskInstanceSelect.innerHTML = state.instances
    .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} (${escapeHtml(item.platform)})</option>`)
    .join("");
}

function renderTasks() {
  els.taskHint.textContent = `${state.tasks.length} 个最近任务`;
  els.tasksBody.innerHTML = state.tasks
    .map((item) => {
      const instance = state.instances.find((it) => it.id === item.instance_id);
      const canCancel = ["queued", "running"].includes(item.status);
      return `
        <tr>
          <td><button class="secondary" data-action="select-task" data-id="${escapeHtml(item.id)}">${escapeHtml(item.id.slice(0, 8))}</button></td>
          <td>${escapeHtml(instance ? instance.name : item.instance_id)}</td>
          <td>${escapeHtml(item.crawler_type)}</td>
          <td>${statusPill(item.status)}</td>
          <td>${escapeHtml(item.target_text || "-")}</td>
          <td>
            <div class="actions">
              <button class="secondary" data-action="select-task" data-id="${escapeHtml(item.id)}">查看</button>
              <button class="danger" data-action="cancel-task" data-id="${escapeHtml(item.id)}" ${canCancel ? "" : "disabled"}>停止</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function loadTaskDetail(taskId) {
  const [logs, artifacts] = await Promise.all([
    api.get(`/api/scheduler/tasks/${taskId}/logs?limit=300`),
    api.get(`/api/scheduler/tasks/${taskId}/artifacts`),
  ]);
  els.logsBox.textContent = logs.length
    ? logs.map((log) => `[${log.timestamp}] [${log.level}] ${log.message}`).join("\n")
    : "暂无日志。";
  els.artifactsList.innerHTML = artifacts.length
    ? artifacts
        .map((item) => {
          const sizeKb = (item.size / 1024).toFixed(1);
          const count = item.record_count == null ? "" : `，${item.record_count} 条`;
          return `<li><strong>${escapeHtml(item.type)}</strong> ${escapeHtml(sizeKb)} KB${count}<br>${escapeHtml(item.path)}</li>`;
        })
        .join("")
    : "<li>暂无产物。</li>";
}

els.refreshBtn.addEventListener("click", () => {
  refreshAll().catch((err) => alert(err.message));
});

els.instanceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const body = {
    name: data.get("name"),
    platform: data.get("platform"),
    login_type: data.get("login_type"),
    save_option: data.get("save_option"),
    headless: data.get("headless") === "on",
    browser_profile_dir: data.get("browser_profile_dir") || "",
    default_params: parseJson(String(data.get("default_params") || ""), {}),
  };
  const port = String(data.get("cdp_debug_port") || "").trim();
  if (port) body.cdp_debug_port = Number(port);
  await api.post("/api/scheduler/instances", body);
  event.currentTarget.reset();
  await refreshAll();
});

els.taskForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  await api.post("/api/scheduler/tasks", {
    instance_id: data.get("instance_id"),
    crawler_type: data.get("crawler_type"),
    target_text: data.get("target_text") || "",
    params: parseJson(String(data.get("params") || ""), {}),
  });
  event.currentTarget.reset();
  await refreshAll();
});

document.addEventListener("click", async (event) => {
  const target = event.target.closest("button[data-action]");
  if (!target) return;
  const action = target.dataset.action;
  const id = target.dataset.id;
  try {
    if (action === "login") {
      const task = await api.post(`/api/scheduler/instances/${id}/login`, {});
      state.selectedTaskId = task.id;
      await refreshAll();
    }
    if (action === "select-task") {
      state.selectedTaskId = id;
      await loadTaskDetail(id);
    }
    if (action === "cancel-task") {
      await api.post(`/api/scheduler/tasks/${id}/cancel`, {});
      state.selectedTaskId = id;
      await refreshAll();
    }
  } catch (err) {
    alert(err.message);
  }
});

refreshAll().catch((err) => {
  els.summary.textContent = `读取失败：${err.message}`;
});

setInterval(() => {
  refreshAll().catch(() => {});
}, 5000);
