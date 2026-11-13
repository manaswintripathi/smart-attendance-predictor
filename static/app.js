// Smart Attendance Predictor — Built by Manaswin Tripathi (@manaswintripathi)
const subjectsEl = document.getElementById("subjects");
const emptyState = document.getElementById("empty-state");
const formError = document.getElementById("form-error");

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function adviceText(s) {
  if (s.total === 0) return "No classes recorded yet.";
  if (s.is_safe) {
    return s.can_skip === 0
      ? "You are just above target — attending the next class keeps you safe."
      : `You can skip ${s.can_skip} more class${s.can_skip === 1 ? "" : "es"} and still stay at or above ${s.target}%.`;
  }
  return `Attend the next ${s.needed_to_reach_target} class${s.needed_to_reach_target === 1 ? "" : "es"} in a row to reach ${s.target}%.`;
}

async function loadAll() {
  const [subjects, overall] = await Promise.all([
    api("/api/subjects"),
    api("/api/overall"),
  ]);
  renderOverall(overall);
  renderSubjects(subjects);
}

function renderOverall(o) {
  document.getElementById("overall-pct").textContent = o.percentage.toFixed(2);
  document.getElementById("overall-count").textContent = `${o.attended} / ${o.total}`;
  const bar = document.getElementById("overall-bar");
  bar.style.width = `${Math.min(100, o.percentage)}%`;
  bar.className = `progress-fill ${o.is_safe ? "safe" : "risk"}`;
  const status = document.getElementById("overall-status");
  status.textContent = o.total === 0
    ? "No data yet"
    : o.is_safe ? `✅ Safe — at or above ${o.target}%` : `⚠️ Below ${o.target}% — action needed`;
  status.className = `status-line ${o.is_safe ? "safe" : "risk"}`;
  const advice = document.getElementById("overall-advice");
  advice.textContent = adviceText(o);
  advice.className = `advice ${o.is_safe ? "safe" : ""}`;
}

function renderSubjects(subjects) {
  emptyState.hidden = subjects.length !== 0;
  subjectsEl.innerHTML = subjects.map((s) => `
    <article class="subject-card">
      <h3>${escapeHtml(s.name)}</h3>
      <span class="badge ${s.is_safe ? "safe" : "risk"}">${s.is_safe ? "Safe" : "Below target"}</span>
      <div class="pct">${s.percentage.toFixed(2)}%</div>
      <p>${s.attended} / ${s.total} attended</p>
      <div class="progress"><div class="progress-fill ${s.is_safe ? "safe" : "risk"}" style="width:${Math.min(100, s.percentage)}%"></div></div>
      <p>${escapeHtml(adviceText(s))}</p>
      <div class="card-actions">
        <button class="btn small" data-action="attend" data-id="${s.id}">✓ Attended</button>
        <button class="btn small ghost" data-action="miss" data-id="${s.id}">✗ Missed</button>
        <button class="btn small danger" data-action="delete" data-id="${s.id}">Delete</button>
      </div>
    </article>`).join("");
}

subjectsEl.addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-action]");
  if (!btn) return;
  const id = btn.dataset.id;
  try {
    if (btn.dataset.action === "delete") {
      if (!confirm("Delete this subject?")) return;
      await api(`/api/subjects/${id}`, { method: "DELETE" });
    } else {
      await api(`/api/subjects/${id}/${btn.dataset.action}`, { method: "POST" });
    }
    await loadAll();
  } catch (err) { alert(err.message); }
});

document.getElementById("add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  formError.textContent = "";
  const name = document.getElementById("new-name").value.trim();
  const attended = Number(document.getElementById("new-attended").value);
  const total = Number(document.getElementById("new-total").value);
  try {
    await api("/api/subjects", {
      method: "POST",
      body: JSON.stringify({ name, attended, total }),
    });
    e.target.reset();
    document.getElementById("new-attended").value = 0;
    document.getElementById("new-total").value = 0;
    await loadAll();
  } catch (err) { formError.textContent = err.message; }
});

document.getElementById("predict-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const attended = document.getElementById("pred-attended").value;
  const total = document.getElementById("pred-total").value;
  const target = document.getElementById("pred-target").value;
  const out = document.getElementById("predict-result");
  try {
    const r = await api(`/api/predict?attended=${attended}&total=${total}&target=${target}`);
    out.textContent = `${r.percentage.toFixed(2)}% (${r.attended}/${r.total}) — ${adviceText(r)}`;
  } catch (err) { out.textContent = err.message; }
});

document.getElementById("seed-btn").addEventListener("click", async () => {
  await api("/api/seed", { method: "POST" });
  await loadAll();
});

document.getElementById("clear-btn").addEventListener("click", async () => {
  if (!confirm("Clear all subjects?")) return;
  await api("/api/clear", { method: "POST" });
  await loadAll();
});

loadAll().catch((err) => {
  document.getElementById("overall-status").textContent = `Could not load data: ${err.message}`;
});
