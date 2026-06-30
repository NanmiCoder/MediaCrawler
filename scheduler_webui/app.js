const WORKS_PAGE_SIZE = 8;

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
  formDirty: false,
  works: [],
  worksPage: 1,
  filterRows: {
    job: [],
  },
};

const filterFields = {
  xhs: [
    ["publish_time", "发布时间", "date"],
    ["liked_count", "点赞数", "number"],
    ["collected_count", "收藏数", "number"],
    ["comment_count", "评论数", "number"],
    ["share_count", "转发数", "number"],
  ],
  dy: [
    ["publish_time", "发布时间", "date"],
    ["liked_count", "点赞数", "number"],
    ["collected_count", "收藏数", "number"],
    ["comment_count", "评论数", "number"],
    ["share_count", "转发数", "number"],
  ],
  ks: [
    ["publish_time", "发布时间", "date"],
    ["liked_count", "点赞数", "number"],
    ["view_count", "播放数", "number"],
  ],
  bili: [
    ["publish_time", "发布时间", "date"],
    ["liked_count", "点赞数", "number"],
    ["disliked_count", "点踩数", "number"],
    ["play_count", "播放数", "number"],
    ["favorite_count", "收藏数", "number"],
    ["share_count", "分享数", "number"],
    ["coin_count", "投币数", "number"],
    ["danmaku_count", "弹幕数", "number"],
    ["comment_count", "评论数", "number"],
  ],
  wb: [
    ["publish_time", "发布时间", "date"],
    ["liked_count", "点赞数", "number"],
    ["comment_count", "评论数", "number"],
    ["share_count", "转发数", "number"],
  ],
  tieba: [
    ["publish_time", "发布时间", "date"],
    ["reply_count", "回复数", "number"],
    ["reply_page_count", "回复页数", "number"],
  ],
  zhihu: [
    ["publish_time", "发布时间", "date"],
    ["voteup_count", "赞同数", "number"],
    ["comment_count", "评论数", "number"],
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
  worksList: document.querySelector("#worksList"),
  worksHint: document.querySelector("#worksHint"),
  worksPager: document.querySelector("#worksPager"),
  wordCloud: document.querySelector("#wordCloud"),
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

function safeHttpUrl(value) {
  try {
    const url = new URL(String(value || ""));
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
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
  if (state.selectedJobId && !state.jobs.some((job) => job.id === state.selectedJobId)) {
    resetForm();
  }
  syncSelectedJobForm();
  if (state.selectedJobId) {
    await loadJobDetail(state.selectedJobId);
  } else {
    clearJobDetail();
  }
}

function renderStatus(status) {
  els.summary.textContent = `作业 ${status.instances_total} 个，运行中 ${status.running_instances} 个`;
}

function renderJobs() {
  els.jobHint.textContent = `${state.jobs.length} 个作业`;
  els.jobsBody.innerHTML = state.jobs.length
    ? state.jobs
    .map((job) => {
      const canRun = !["running", "stopping"].includes(job.status);
      const target = job.target_text || "-";
      const taskId = job.current_task_id || job.last_task_id || "-";
      const selected = job.id === state.selectedJobId ? " selected" : "";
      return `
        <article class="job-item${selected}" data-job-id="${escapeHtml(job.id)}" role="button" tabindex="0" aria-pressed="${selected ? "true" : "false"}">
          <div class="job-main">
            <div class="job-name">
              <strong>${escapeHtml(job.name)}</strong>
              <small>${escapeHtml(job.id)}</small>
            </div>
            ${statusPill(job.status)}
          </div>
          <div class="job-meta">
            <span>${escapeHtml(job.platform)}</span>
            <span>${escapeHtml(job.crawler_type)}</span>
            <span>运行 ${escapeHtml(taskId === "-" ? "-" : taskId.slice(0, 8))}</span>
          </div>
          <div class="job-target">${escapeHtml(target)}</div>
          <div class="actions">
            <button class="secondary" data-action="login-job" data-id="${escapeHtml(job.id)}" ${canRun ? "" : "disabled"}>登录</button>
            <button data-action="run-job" data-id="${escapeHtml(job.id)}" ${canRun ? "" : "disabled"}>运行</button>
            <button class="danger" data-action="stop-job" data-id="${escapeHtml(job.id)}" ${canRun ? "disabled" : ""}>停止</button>
            <button class="danger" data-action="delete-job" data-id="${escapeHtml(job.id)}" ${canRun ? "" : "disabled"}>删除</button>
          </div>
        </article>
      `;
    })
    .join("")
    : `<p class="empty-note">暂无作业。</p>`;
}

function renderFilterRows(scope) {
  const platform = currentPlatform();
  const rows = state.filterRows[scope];
  els.jobFilterRows.innerHTML = rows.length
    ? rows
        .map((row, index) => renderFilterRow(scope, platform, row, index))
        .join("")
    : `<p class="empty-note">未设置过滤条件</p>`;
}

function renderFilterRow(scope, platform, row, index) {
  const type = filterFieldType(platform, row.metric);
  const isDate = type === "date";
  const minControl = isDate
    ? `
      <label>
        不早于
        <input data-field="min" type="date" value="${escapeHtml(dateInputValue(row.min))}" />
      </label>
    `
    : `
      <label>
        最小值
        <input data-field="min" inputmode="numeric" placeholder="不限，可填 1万" value="${escapeHtml(row.min)}" />
      </label>
      <label>
        最大值
        <input data-field="max" inputmode="numeric" placeholder="不限，可填 1万" value="${escapeHtml(row.max)}" />
      </label>
    `;
  return `
    <div class="filter-row ${isDate ? "time-filter-row" : ""}" data-scope="${scope}" data-index="${index}">
      <label>
        指标
        <select data-field="metric">
          ${metricOptions(platform, row.metric)}
        </select>
      </label>
      ${minControl}
      <button class="secondary icon-button" type="button" data-action="remove-filter" data-scope="${scope}" data-index="${index}" aria-label="删除过滤条件">×</button>
    </div>
  `;
}

function metricOptions(platform, selectedMetric) {
  return (filterFields[platform] || filterFields.xhs)
    .map(([value, label]) => `<option value="${value}" ${value === selectedMetric ? "selected" : ""}>${label}</option>`)
    .join("");
}

function filterFieldType(platform, metric) {
  const fields = filterFields[platform] || filterFields.xhs;
  const field = fields.find(([value]) => value === metric) || fields[0];
  return field[2] || "number";
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
  if (target.dataset.field === "metric" && row.metric !== target.value) {
    row.metric = target.value;
    row.min = "";
    row.max = "";
    renderFilterRows(rowEl.dataset.scope);
    return;
  }
  row[target.dataset.field] = target.value;
}

function collectFilters() {
  return state.filterRows.job.reduce((filters, row) => {
    const type = filterFieldType(currentPlatform(), row.metric);
    const min = String(row.min || "").trim();
    const max = type === "date" ? "" : String(row.max || "").trim();
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

function dateInputValue(value) {
  const text = String(value ?? "").trim();
  if (!text) return "";
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) return text.slice(0, 10);

  const timestamp = Number(text);
  if (!Number.isFinite(timestamp)) return "";
  const date = new Date((timestamp > 10_000_000_000 ? timestamp : timestamp * 1000));
  if (Number.isNaN(date.getTime())) return "";
  const year = String(date.getFullYear());
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
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

function fillJobForm(job) {
  const form = els.jobForm.elements;
  state.editingJobId = job.id;
  els.formTitle.textContent = "作业配置";
  els.jobSubmitBtn.textContent = "保存更改";
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
  state.formDirty = false;
}

function resetForm() {
  state.selectedJobId = "";
  state.editingJobId = "";
  state.formDirty = false;
  els.formTitle.textContent = "新建作业";
  els.jobSubmitBtn.textContent = "创建作业";
  els.cancelEditBtn.hidden = true;
  els.jobForm.reset();
  state.filterRows.job = [];
  renderFilterRows("job");
  clearJobDetail();
  renderJobs();
}

function syncSelectedJobForm() {
  if (!state.selectedJobId || state.formDirty) return;
  const job = state.jobs.find((item) => item.id === state.selectedJobId);
  if (job) fillJobForm(job);
}

async function selectJob(jobId) {
  const job = state.jobs.find((item) => item.id === jobId) || await api.get(`/api/scheduler/jobs/${jobId}`);
  state.selectedJobId = job.id;
  state.worksPage = 1;
  fillJobForm(job);
  renderJobs();
  await loadJobDetail(job.id);
}

function clearJobDetail() {
  state.works = [];
  state.worksPage = 1;
  els.logsBox.textContent = "选择一个作业查看日志。";
  els.artifactsList.innerHTML = "<li>选择一个作业查看产物。</li>";
  els.worksHint.textContent = "";
  els.worksList.innerHTML = "<li>选择一个作业查看作品。</li>";
  els.worksPager.innerHTML = "";
  els.wordCloud.innerHTML = `<p class="empty-note">选择一个作业查看评论词云。</p>`;
}

async function withButtonFeedback(button, pendingText, doneText, action) {
  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = pendingText;
  try {
    await action();
    button.textContent = doneText;
    setTimeout(() => {
      button.textContent = originalText;
      button.disabled = false;
    }, 1500);
  } catch (err) {
    button.textContent = originalText;
    button.disabled = false;
    throw err;
  }
}

async function loadJobDetail(jobId) {
  const [logs, artifacts, summary] = await Promise.all([
    api.get(`/api/scheduler/jobs/${jobId}/logs?limit=300`),
    api.get(`/api/scheduler/jobs/${jobId}/artifacts`),
    api.get(`/api/scheduler/jobs/${jobId}/artifact-summary?work_limit=100&word_limit=60`),
  ]);
  els.logsBox.textContent = logs.length
    ? logs.map((log) => `[${log.timestamp}] [${log.level}] ${log.message}`).join("\n")
    : "暂无日志。";
  els.artifactsList.innerHTML = artifacts.length
    ? artifacts
        .map((item) => {
          const sizeKb = (item.size / 1024).toFixed(1);
          const count = item.record_count == null ? "" : `，${item.record_count} 条`;
          return `
            <li class="artifact-item">
              <div class="artifact-info">
                <strong>${escapeHtml(item.type)}</strong> ${escapeHtml(sizeKb)} KB${count}
                <br>${escapeHtml(item.path)}
              </div>
              <div class="actions">
                <button class="secondary" data-action="open-artifact" data-id="${escapeHtml(item.id)}">打开文件</button>
                <button class="danger" data-action="delete-artifact" data-id="${escapeHtml(item.id)}">删除文件</button>
              </div>
            </li>
          `;
        })
        .join("")
    : "<li>暂无产物。</li>";
  state.works = summary.works || [];
  renderWorks();
  renderWordCloud(summary.word_cloud || []);
}

function renderWorks() {
  const works = state.works || [];
  const totalPages = Math.max(1, Math.ceil(works.length / WORKS_PAGE_SIZE));
  state.worksPage = Math.min(Math.max(state.worksPage, 1), totalPages);
  const start = (state.worksPage - 1) * WORKS_PAGE_SIZE;
  const currentWorks = works.slice(start, start + WORKS_PAGE_SIZE);

  els.worksHint.textContent = works.length ? `${works.length} 个作品，第 ${state.worksPage}/${totalPages} 页` : "";
  els.worksList.innerHTML = currentWorks.length
    ? currentWorks.map((item) => {
      const url = safeHttpUrl(item.url);
      const title = escapeHtml(item.title || item.id || "未命名作品");
      const metrics = Object.entries(item.metrics || {})
        .filter(([, value]) => value !== "" && value != null)
        .map(([key, value]) => `${escapeHtml(key)} ${escapeHtml(value)}`)
        .join(" · ");
      const openLink = url
        ? `<a class="secondary link-button" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">打开作品</a>`
        : "";
      return `
        <li class="work-item">
          <strong class="work-title">${title}</strong>
          <div class="work-meta">
            ${escapeHtml(item.author || "未知作者")}
            ${item.publish_time ? ` · ${escapeHtml(item.publish_time)}` : ""}
            ${item.source_keyword ? ` · ${escapeHtml(item.source_keyword)}` : ""}
          </div>
          ${metrics ? `<div class="work-meta">${metrics}</div>` : ""}
          ${openLink ? `<div class="actions">${openLink}</div>` : ""}
        </li>
      `;
    }).join("")
    : "<li>暂无符合条件的作品。</li>";
  els.worksPager.innerHTML = works.length
    ? `
      <button class="secondary" data-action="works-prev" ${state.worksPage <= 1 ? "disabled" : ""}>上一页</button>
      <span>第 ${state.worksPage} / ${totalPages} 页</span>
      <button class="secondary" data-action="works-next" ${state.worksPage >= totalPages ? "disabled" : ""}>下一页</button>
    `
    : "";
}

function renderWordCloud(words) {
  if (!words.length) {
    els.wordCloud.innerHTML = `<p class="empty-note">暂无评论词云。</p>`;
    return;
  }
  const maxWeight = Math.max(...words.map((item) => item.weight || 1));
  els.wordCloud.innerHTML = words.map((item) => {
    const ratio = Math.max(0.7, (item.weight || 1) / maxWeight);
    const size = Math.round(13 + ratio * 20);
    return `<span class="word-token" style="font-size:${size}px" title="${escapeHtml(item.weight)} 次">${escapeHtml(item.text)}</span>`;
  }).join("");
}

els.refreshBtn.addEventListener("click", () => {
  refreshAll().catch((err) => alert(err.message));
});

els.cancelEditBtn.addEventListener("click", resetForm);

els.jobsBody.addEventListener("click", async (event) => {
  if (event.target.closest("button[data-action]")) return;
  const item = event.target.closest("[data-job-id]");
  if (item) await selectJob(item.dataset.jobId).catch((err) => alert(err.message));
});

els.jobForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const body = collectJobBody(data);
  let job;
  if (state.editingJobId) {
    job = await api.patch(`/api/scheduler/jobs/${state.editingJobId}`, body);
  } else {
    job = await api.post("/api/scheduler/jobs", body);
  }
  state.selectedJobId = job.id;
  state.editingJobId = job.id;
  state.formDirty = false;
  await refreshAll();
});

els.jobForm.elements.platform.addEventListener("change", syncFilterRowsWithPlatform);

document.addEventListener("input", (event) => {
  updateFilterValue(event.target);
  if (event.target.closest("#jobForm")) state.formDirty = true;
});
document.addEventListener("change", (event) => {
  updateFilterValue(event.target);
  if (event.target.closest("#jobForm")) state.formDirty = true;
});

document.addEventListener("click", async (event) => {
  const target = event.target.closest("button[data-action]");
  if (!target) return;
  const action = target.dataset.action;
  const id = target.dataset.id;
  try {
    if (action === "works-prev") {
      state.worksPage -= 1;
      renderWorks();
      return;
    }
    if (action === "works-next") {
      state.worksPage += 1;
      renderWorks();
      return;
    }
    if (action === "add-filter") {
      addFilterRow(target.dataset.scope);
      state.formDirty = true;
      return;
    }
    if (action === "remove-filter") {
      removeFilterRow(target.dataset.scope, Number(target.dataset.index));
      state.formDirty = true;
      return;
    }
    if (action === "login-job") {
      await api.post(`/api/scheduler/jobs/${id}/login`);
      state.selectedJobId = id;
      state.formDirty = false;
      await refreshAll();
    }
    if (action === "run-job") {
      await api.post(`/api/scheduler/jobs/${id}/run`);
      state.selectedJobId = id;
      state.formDirty = false;
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
    if (action === "open-artifact") {
      if (!state.selectedJobId) return;
      await withButtonFeedback(target, "打开中...", "已打开", () =>
        api.post(`/api/scheduler/jobs/${state.selectedJobId}/artifacts/${id}/open`)
      );
    }
    if (action === "delete-artifact") {
      if (!state.selectedJobId || !confirm("确定删除这个产物文件？")) return;
      await api.delete(`/api/scheduler/jobs/${state.selectedJobId}/artifacts/${id}`);
      await loadJobDetail(state.selectedJobId);
    }
  } catch (err) {
    alert(err.message);
  }
});

document.addEventListener("keydown", async (event) => {
  if (!["Enter", " "].includes(event.key)) return;
  if (event.target.closest("button")) return;
  const item = event.target.closest("[data-job-id]");
  if (!item) return;
  event.preventDefault();
  await selectJob(item.dataset.jobId).catch((err) => alert(err.message));
});

renderFilterRows("job");
refreshAll().catch((err) => {
  els.summary.textContent = `读取失败：${err.message}`;
});

setInterval(() => {
  refreshAll().catch(() => {});
}, 5000);
