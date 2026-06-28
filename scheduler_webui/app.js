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
  filterRows: {
    instance: [],
    task: [],
  },
};

const filterFields = {
  xhs: [
    ["liked_count", "点赞数"],
    ["collected_count", "收藏数"],
    ["comment_count", "评论数"],
    ["share_count", "转发数"],
  ],
  dy: [
    ["liked_count", "点赞数"],
    ["collected_count", "收藏数"],
    ["comment_count", "评论数"],
    ["share_count", "转发数"],
  ],
  ks: [
    ["liked_count", "点赞数"],
    ["view_count", "播放数"],
  ],
  bili: [
    ["liked_count", "点赞数"],
    ["disliked_count", "点踩数"],
    ["play_count", "播放数"],
    ["favorite_count", "收藏数"],
    ["share_count", "分享数"],
    ["coin_count", "投币数"],
    ["danmaku_count", "弹幕数"],
    ["comment_count", "评论数"],
  ],
  wb: [
    ["liked_count", "点赞数"],
    ["comment_count", "评论数"],
    ["share_count", "转发数"],
  ],
  tieba: [
    ["reply_count", "回复数"],
    ["reply_page_count", "回复页数"],
  ],
  zhihu: [
    ["voteup_count", "赞同数"],
    ["comment_count", "评论数"],
  ],
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
  instanceFilterRows: document.querySelector("#instanceFilterRows"),
  taskFilterRows: document.querySelector("#taskFilterRows"),
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
  const selectedId = els.taskInstanceSelect.value;
  els.taskInstanceSelect.innerHTML = state.instances
    .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} (${escapeHtml(item.platform)})</option>`)
    .join("");
  if (selectedId && state.instances.some((item) => item.id === selectedId)) {
    els.taskInstanceSelect.value = selectedId;
  }
  syncFilterRowsWithPlatform("task");
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

function renderFilterRows(scope) {
  const platform = currentPlatform(scope);
  const target = scope === "instance" ? els.instanceFilterRows : els.taskFilterRows;
  const rows = state.filterRows[scope];

  target.innerHTML = rows.length
    ? rows
        .map((row, index) => `
          <div class="filter-row" data-scope="${scope}" data-index="${index}">
            <label>
              指标
              <select data-field="metric">
                ${metricOptions(platform, row.metric)}
              </select>
            </label>
            <label>
              最小值
              <input data-field="min" inputmode="numeric" placeholder="不限，可填 1万" value="${escapeHtml(row.min)}" />
            </label>
            <label>
              最大值
              <input data-field="max" inputmode="numeric" placeholder="不限，可填 1万" value="${escapeHtml(row.max)}" />
            </label>
            <button class="secondary icon-button" type="button" data-action="remove-filter" data-scope="${scope}" data-index="${index}" aria-label="删除过滤条件">×</button>
          </div>
        `)
        .join("")
    : `<p class="empty-note">未设置过滤条件</p>`;
}

function metricOptions(platform, selectedMetric) {
  return (filterFields[platform] || filterFields.xhs)
    .map(([value, label]) => `<option value="${value}" ${value === selectedMetric ? "selected" : ""}>${label}</option>`)
    .join("");
}

function currentPlatform(scope) {
  if (scope === "instance") {
    return els.instanceForm.elements.platform.value || "xhs";
  }
  const instanceId = els.taskInstanceSelect.value;
  return state.instances.find((item) => item.id === instanceId)?.platform || "xhs";
}

function addFilterRow(scope) {
  const [metric] = (filterFields[currentPlatform(scope)] || filterFields.xhs)[0];
  state.filterRows[scope].push({ metric, min: "", max: "" });
  renderFilterRows(scope);
}

function removeFilterRow(scope, index) {
  state.filterRows[scope].splice(index, 1);
  renderFilterRows(scope);
}

function syncFilterRowsWithPlatform(scope) {
  const fields = filterFields[currentPlatform(scope)] || filterFields.xhs;
  const allowed = new Set(fields.map(([value]) => value));
  const fallback = fields[0][0];
  state.filterRows[scope] = state.filterRows[scope].map((row) => ({
    ...row,
    metric: allowed.has(row.metric) ? row.metric : fallback,
  }));
  renderFilterRows(scope);
}

function updateFilterValue(target) {
  const rowEl = target.closest(".filter-row");
  if (!rowEl) return;
  const row = state.filterRows[rowEl.dataset.scope]?.[Number(rowEl.dataset.index)];
  if (!row) return;
  row[target.dataset.field] = target.value;
}

function collectFilters(scope) {
  return state.filterRows[scope].reduce((filters, row) => {
    const min = String(row.min || "").trim();
    const max = String(row.max || "").trim();
    if (!row.metric || (!min && !max)) return filters;
    filters[row.metric] = {};
    if (min) filters[row.metric].min = min;
    if (max) filters[row.metric].max = max;
    return filters;
  }, {});
}

function setNumberParam(params, key, value) {
  const text = String(value || "").trim();
  if (text) params[key] = Number(text);
}

function setStringParam(params, key, value) {
  const text = String(value || "").trim();
  if (text) params[key] = text;
}

function setBoolSelectParam(params, key, value) {
  if (value === "true") params[key] = true;
  if (value === "false") params[key] = false;
}

function collectDefaultParams(data) {
  const params = {};
  setBoolSelectParam(params, "enable_comments", data.get("default_enable_comments"));
  setBoolSelectParam(params, "enable_sub_comments", data.get("default_enable_sub_comments"));
  setBoolSelectParam(params, "cdp_connect_existing", data.get("default_cdp_connect_existing"));
  setBoolSelectParam(params, "enable_ip_proxy", data.get("default_enable_ip_proxy"));
  setNumberParam(params, "start_page", data.get("default_start_page"));
  setNumberParam(params, "max_notes_count", data.get("default_max_notes_count"));
  setNumberParam(params, "max_comments_count", data.get("default_max_comments_count"));
  setNumberParam(params, "max_concurrency_num", data.get("default_max_concurrency_num"));
  setNumberParam(params, "ip_proxy_pool_count", data.get("default_ip_proxy_pool_count"));
  setStringParam(params, "cookies", data.get("default_cookies"));
  setStringParam(params, "ip_proxy_provider_name", data.get("default_ip_proxy_provider_name"));
  setStringParam(params, "static_proxy_url", data.get("default_static_proxy_url"));
  const filters = collectFilters("instance");
  if (Object.keys(filters).length) params.content_filters = filters;
  return params;
}

function collectTaskParams(data) {
  const params = {};
  setBoolSelectParam(params, "enable_comments", data.get("task_enable_comments"));
  setBoolSelectParam(params, "enable_sub_comments", data.get("task_enable_sub_comments"));
  setBoolSelectParam(params, "cdp_connect_existing", data.get("task_cdp_connect_existing"));
  setBoolSelectParam(params, "enable_ip_proxy", data.get("task_enable_ip_proxy"));
  setNumberParam(params, "start_page", data.get("task_start_page"));
  setNumberParam(params, "max_notes_count", data.get("task_max_notes_count"));
  setNumberParam(params, "max_comments_count", data.get("task_max_comments_count"));
  setNumberParam(params, "max_concurrency_num", data.get("task_max_concurrency_num"));
  setNumberParam(params, "ip_proxy_pool_count", data.get("task_ip_proxy_pool_count"));
  setStringParam(params, "cookies", data.get("task_cookies"));
  setStringParam(params, "ip_proxy_provider_name", data.get("task_ip_proxy_provider_name"));
  setStringParam(params, "static_proxy_url", data.get("task_static_proxy_url"));
  const filters = collectFilters("task");
  if (Object.keys(filters).length) params.content_filters = filters;
  return params;
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
    default_params: collectDefaultParams(data),
  };
  const port = String(data.get("cdp_debug_port") || "").trim();
  if (port) body.cdp_debug_port = Number(port);
  await api.post("/api/scheduler/instances", body);
  event.currentTarget.reset();
  state.filterRows.instance = [];
  renderFilterRows("instance");
  await refreshAll();
});

els.taskForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  await api.post("/api/scheduler/tasks", {
    instance_id: data.get("instance_id"),
    crawler_type: data.get("crawler_type"),
    target_text: data.get("target_text") || "",
    params: collectTaskParams(data),
  });
  event.currentTarget.reset();
  state.filterRows.task = [];
  renderFilterRows("task");
  await refreshAll();
});

els.instanceForm.elements.platform.addEventListener("change", () => syncFilterRowsWithPlatform("instance"));
els.taskInstanceSelect.addEventListener("change", () => syncFilterRowsWithPlatform("task"));

document.addEventListener("input", (event) => updateFilterValue(event.target));
document.addEventListener("change", (event) => updateFilterValue(event.target));

document.addEventListener("click", async (event) => {
  const target = event.target.closest("button[data-action]");
  if (!target) return;
  const action = target.dataset.action;
  const id = target.dataset.id;
  if (action === "add-filter") {
    addFilterRow(target.dataset.scope);
    return;
  }
  if (action === "remove-filter") {
    removeFilterRow(target.dataset.scope, Number(target.dataset.index));
    return;
  }
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

renderFilterRows("instance");
renderFilterRows("task");
refreshAll().catch((err) => {
  els.summary.textContent = `读取失败：${err.message}`;
});

setInterval(() => {
  refreshAll().catch(() => {});
}, 5000);
