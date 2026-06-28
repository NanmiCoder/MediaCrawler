const api = {
  async get(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(await errorText(res));
    return res.json();
  },
  async post(path, body = {}) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await errorText(res));
    return res.json();
  },
  async patch(path, body) {
    const res = await fetch(path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await errorText(res));
    return res.json();
  },
  async delete(path) {
    const res = await fetch(path, { method: "DELETE" });
    if (!res.ok) throw new Error(await errorText(res));
    return res.json();
  },
};

let state = {
  jobs: [],
  selectedJobId: "",
  editingJobId: "",
  filterRows: {
    job: [],
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
  jobForm: document.querySelector("#jobForm"),
  jobsBody: document.querySelector("#jobsBody"),
  jobHint: document.querySelector("#jobHint"),
  formTitle: document.querySelector("#formTitle"),
  jobSubmitBtn: document.querySelector("#jobSubmitBtn"),
  cancelEditBtn: document.querySelector("#cancelEditBtn"),
  logsBox: document.querySelector("#logsBox"),
  artifactsList: document.querySelector("#artifactsList"),
  jobFilterRows: document.querySelector("#jobFilterRows"),
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
  const [status, jobs] = await Promise.all([
    api.get("/api/scheduler/status"),
    api.get("/api/scheduler/jobs"),
  ]);
  state.jobs = jobs;
  renderStatus(status);
  renderJobs();
  if (state.selectedJobId) await loadJobDetail(state.selectedJobId);
}

function renderStatus(status) {
  els.summary.textContent = `作业 ${status.instances_total} 个，运行中 ${status.running_instances} 个`;
}

function renderJobs() {
  els.jobHint.textContent = `${state.jobs.length} 个作业`;
  els.jobsBody.innerHTML = state.jobs
    .map((job) => {
      const canRun = !["running", "stopping"].includes(job.status);
      const target = job.target_text || "-";
      const taskId = job.current_task_id || job.last_task_id || "-";
      return `
        <tr>
          <td><strong>${escapeHtml(job.name)}</strong><br><small>${escapeHtml(job.id)}</small></td>
          <td>${escapeHtml(job.platform)}</td>
          <td>${escapeHtml(job.crawler_type)}</td>
          <td>${statusPill(job.status)}</td>
          <td>${escapeHtml(target)}</td>
          <td>${escapeHtml(taskId === "-" ? "-" : taskId.slice(0, 8))}</td>
          <td>
            <div class="actions">
              <button class="secondary" data-action="view-job" data-id="${escapeHtml(job.id)}">查看</button>
              <button class="secondary" data-action="edit-job" data-id="${escapeHtml(job.id)}" ${canRun ? "" : "disabled"}>编辑</button>
              <button class="secondary" data-action="login-job" data-id="${escapeHtml(job.id)}" ${canRun ? "" : "disabled"}>登录</button>
              <button data-action="run-job" data-id="${escapeHtml(job.id)}" ${canRun ? "" : "disabled"}>运行</button>
              <button class="danger" data-action="stop-job" data-id="${escapeHtml(job.id)}" ${canRun ? "disabled" : ""}>停止</button>
              <button class="danger" data-action="delete-job" data-id="${escapeHtml(job.id)}" ${canRun ? "" : "disabled"}>删除</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

function renderFilterRows(scope) {
  const platform = currentPlatform();
  const rows = state.filterRows[scope];
  els.jobFilterRows.innerHTML = rows.length
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

function currentPlatform() {
  return els.jobForm.elements.platform.value || "xhs";
}

function addFilterRow(scope) {
  const [metric] = (filterFields[currentPlatform()] || filterFields.xhs)[0];
  state.filterRows[scope].push({ metric, min: "", max: "" });
  renderFilterRows(scope);
}

function removeFilterRow(scope, index) {
  state.filterRows[scope].splice(index, 1);
  renderFilterRows(scope);
}

function syncFilterRowsWithPlatform() {
  const fields = filterFields[currentPlatform()] || filterFields.xhs;
  const allowed = new Set(fields.map(([value]) => value));
  const fallback = fields[0][0];
  state.filterRows.job = state.filterRows.job.map((row) => ({
    ...row,
    metric: allowed.has(row.metric) ? row.metric : fallback,
  }));
  renderFilterRows("job");
}

function updateFilterValue(target) {
  const rowEl = target.closest(".filter-row");
  if (!rowEl) return;
  const row = state.filterRows[rowEl.dataset.scope]?.[Number(rowEl.dataset.index)];
  if (!row) return;
  row[target.dataset.field] = target.value;
}

function collectFilters() {
  return state.filterRows.job.reduce((filters, row) => {
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

function collectJobParams(data) {
  const params = {};
  setBoolSelectParam(params, "enable_comments", data.get("enable_comments"));
  setBoolSelectParam(params, "enable_sub_comments", data.get("enable_sub_comments"));
  setBoolSelectParam(params, "cdp_connect_existing", data.get("cdp_connect_existing"));
  setBoolSelectParam(params, "enable_ip_proxy", data.get("enable_ip_proxy"));
  setNumberParam(params, "start_page", data.get("start_page"));
  setNumberParam(params, "max_notes_count", data.get("max_notes_count"));
  setNumberParam(params, "max_comments_count", data.get("max_comments_count"));
  setNumberParam(params, "max_concurrency_num", data.get("max_concurrency_num"));
  setNumberParam(params, "ip_proxy_pool_count", data.get("ip_proxy_pool_count"));
  setStringParam(params, "cookies", data.get("cookies"));
  setStringParam(params, "ip_proxy_provider_name", data.get("ip_proxy_provider_name"));
  setStringParam(params, "static_proxy_url", data.get("static_proxy_url"));
  const filters = collectFilters();
  if (Object.keys(filters).length) params.content_filters = filters;
  return params;
}

function collectJobBody(data) {
  const body = {
    name: data.get("name"),
    platform: data.get("platform"),
    login_type: data.get("login_type"),
    save_option: data.get("save_option"),
    crawler_type: data.get("crawler_type"),
    target_text: data.get("target_text") || "",
    headless: data.get("headless") === "on",
    browser_profile_dir: data.get("browser_profile_dir") || "",
    params: collectJobParams(data),
  };
  const port = String(data.get("cdp_debug_port") || "").trim();
  if (port) body.cdp_debug_port = Number(port);
  return body;
}

function setSelect(name, value) {
  els.jobForm.elements[name].value = value == null ? "" : String(value);
}

function setParamFields(params) {
  const form = els.jobForm.elements;
  form.start_page.value = params.start_page || "";
  form.max_notes_count.value = params.max_notes_count || "";
  form.max_comments_count.value = params.max_comments_count || "";
  form.max_concurrency_num.value = params.max_concurrency_num || "";
  form.ip_proxy_pool_count.value = params.ip_proxy_pool_count || "";
  form.cookies.value = params.cookies || "";
  form.static_proxy_url.value = params.static_proxy_url || "";
  setSelect("enable_comments", params.enable_comments === true ? "true" : params.enable_comments === false ? "false" : "");
  setSelect("enable_sub_comments", params.enable_sub_comments === true ? "true" : params.enable_sub_comments === false ? "false" : "");
  setSelect("cdp_connect_existing", params.cdp_connect_existing === true ? "true" : params.cdp_connect_existing === false ? "false" : "");
  setSelect("enable_ip_proxy", params.enable_ip_proxy === true ? "true" : params.enable_ip_proxy === false ? "false" : "");
  setSelect("ip_proxy_provider_name", params.ip_proxy_provider_name || "");
  state.filterRows.job = Object.entries(params.content_filters || {}).map(([metric, range]) => ({
    metric,
    min: range?.min ?? "",
    max: range?.max ?? "",
  }));
  syncFilterRowsWithPlatform();
}

function editJob(job) {
  const form = els.jobForm.elements;
  state.editingJobId = job.id;
  els.formTitle.textContent = "编辑作业";
  els.jobSubmitBtn.textContent = "保存作业";
  els.cancelEditBtn.hidden = false;
  form.name.value = job.name;
  form.platform.value = job.platform;
  form.login_type.value = job.login_type;
  form.save_option.value = job.save_option;
  form.crawler_type.value = job.crawler_type;
  form.target_text.value = job.target_text || "";
  form.cdp_debug_port.value = job.cdp_debug_port || "";
  form.browser_profile_dir.value = job.browser_profile_dir || "";
  form.headless.checked = Boolean(job.headless);
  setParamFields(job.params || {});
  els.jobForm.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetForm() {
  state.editingJobId = "";
  els.formTitle.textContent = "新建作业";
  els.jobSubmitBtn.textContent = "创建作业";
  els.cancelEditBtn.hidden = true;
  els.jobForm.reset();
  state.filterRows.job = [];
  renderFilterRows("job");
}

async function loadJobDetail(jobId) {
  const [logs, artifacts] = await Promise.all([
    api.get(`/api/scheduler/jobs/${jobId}/logs?limit=300`),
    api.get(`/api/scheduler/jobs/${jobId}/artifacts`),
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

els.cancelEditBtn.addEventListener("click", resetForm);

els.jobForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const body = collectJobBody(data);
  if (state.editingJobId) {
    await api.patch(`/api/scheduler/jobs/${state.editingJobId}`, body);
  } else {
    await api.post("/api/scheduler/jobs", body);
  }
  resetForm();
  await refreshAll();
});

els.jobForm.elements.platform.addEventListener("change", syncFilterRowsWithPlatform);

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
    if (action === "view-job") {
      state.selectedJobId = id;
      await loadJobDetail(id);
    }
    if (action === "edit-job") {
      const job = state.jobs.find((item) => item.id === id) || await api.get(`/api/scheduler/jobs/${id}`);
      editJob(job);
    }
    if (action === "login-job") {
      await api.post(`/api/scheduler/jobs/${id}/login`);
      state.selectedJobId = id;
      await refreshAll();
    }
    if (action === "run-job") {
      await api.post(`/api/scheduler/jobs/${id}/run`);
      state.selectedJobId = id;
      await refreshAll();
    }
    if (action === "stop-job") {
      await api.post(`/api/scheduler/jobs/${id}/stop`);
      state.selectedJobId = id;
      await refreshAll();
    }
    if (action === "delete-job") {
      await api.delete(`/api/scheduler/jobs/${id}`);
      if (state.selectedJobId === id) state.selectedJobId = "";
      if (state.editingJobId === id) resetForm();
      await refreshAll();
    }
  } catch (err) {
    alert(err.message);
  }
});

renderFilterRows("job");
refreshAll().catch((err) => {
  els.summary.textContent = `读取失败：${err.message}`;
});

setInterval(() => {
  refreshAll().catch(() => {});
}, 5000);
