// 转诊一件事 · 多视图单页应用。与网关同源，调 /api/* 真实接口。
const $ = (s) => document.querySelector(s);
const NODE_LABEL = { first_visit: "首诊评估", package: "资料打包", apply: "转诊申请", accept: "接收确认", downward_plan: "下转方案", continue: "接续确认", followup: "随访执行" };
const TYPE_LABEL = { up: "上转", down: "下转", flat: "平转", emergency: "急诊", mdt: "MDT" };
const PAYEE_LABEL = { individual: "个人", dept: "科室", org: "机构", platform: "平台" };
let currentRef = null, currentTab = "progress", activePane = null, renderGen = 0;
const INC = { drg: 4, ratio: 5, surplus: 2800000, surRatio: 25 };

function token() { return localStorage.getItem("hosp_token"); }
function toast(m, k = "") { const t = document.createElement("div"); t.className = "t " + k; t.textContent = m; $("#toast").appendChild(t); setTimeout(() => { t.style.opacity = "0"; t.style.transition = ".4s"; }, 2400); setTimeout(() => t.remove(), 2900); }

async function api(path, opts = {}) {
  const res = await fetch("/api" + path, { ...opts, headers: { "Content-Type": "application/json", ...(token() ? { Authorization: "Bearer " + token() } : {}), ...(opts.headers || {}) } });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) { if (res.status === 401) logout(); throw new Error(body.detail || body.message || "请求失败(" + res.status + ")"); }
  return body;
}

async function login() {
  $("#loginBtn").disabled = true;
  try {
    const r = await api("/platform-auth/login", { method: "POST", body: JSON.stringify({ username: $("#username").value, password: $("#password").value }) });
    localStorage.setItem("hosp_token", r.token); localStorage.setItem("hosp_name", r.name);
    localStorage.setItem("hosp_scopes", (r.scopes || []).join(","));
    localStorage.setItem("hosp_roles", (r.roles || []).join(","));
    localStorage.setItem("hosp_patient", r.patient_id || "");
    localStorage.setItem("hosp_refresh", r.refresh_token || "");
    route();
  } catch (e) { toast(e.message, "err"); } finally { $("#loginBtn").disabled = false; }
}
function route() { ((localStorage.getItem("hosp_roles") || "").split(",").includes("resident")) ? showPatientApp() : showApp(); }
async function logout() {
  const rt = localStorage.getItem("hosp_refresh");
  if (rt) { try { await fetch("/api/platform-auth/logout", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: rt }) }); } catch { /* 忽略 */ } }
  localStorage.clear(); $("#appView").classList.add("hidden"); $("#patientView").classList.add("hidden"); $("#loginView").classList.remove("hidden");
}
function dept() { return (localStorage.getItem("hosp_scopes") || "card").split(",")[0]; }

function showApp() {
  $("#loginView").classList.add("hidden"); $("#appView").classList.remove("hidden");
  $("#whoName").textContent = localStorage.getItem("hosp_name") || "";
  $("#whoMeta").textContent = "科室权限：" + (localStorage.getItem("hosp_scopes") || "—");
  loadReferrals(); loadAccount();
}
function switchView(v, btn) {
  document.querySelectorAll(".view").forEach((x) => x.classList.remove("show"));
  $("#view-" + v).classList.add("show");
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("on", b === btn));
  if (v === "mdt") loadMdt(); if (v === "admin") loadAdmin(); if (v === "credit") loadAccount();
  if (v === "teleconsult") loadConsults(); if (v === "homebed") loadBeds();
}

/* ---------- 在线复诊（scenario-006） ---------- */
const TRIAGE = { low: '<span class="tag ok">低危</span>', medium: '<span class="tag warn">中危</span>', high: '<span class="tag" style="background:#fef2f2;color:#dc2626">高危</span>' };
let curConsult = null;
async function loadConsults() {
  const tb = $("#consultRows");
  try {
    const rows = await api("/scenario-006/consults");
    if (!rows.length) { tb.innerHTML = '<tr><td colspan="6" class="empty">暂无候诊</td></tr>'; return; }
    tb.innerHTML = rows.map((c) => {
      const k = c.consult_no.replace(/[^a-zA-Z0-9]/g, "");
      return `<tr><td>${c.consult_no}</td><td class="cp-${k}">${c.patient_id}</td><td>${c.chief_complaint || ""}</td><td>${TRIAGE[c.ai_triage] || c.ai_triage || ""}</td>
        <td>${{ waiting: "候诊", in_progress: "接诊中", finished: "已完成" }[c.status] || c.status}</td>
        <td>${c.status === "waiting" ? `<button class="primary sm" onclick="acceptConsult('${c.consult_no}')">接诊</button>` : c.status === "in_progress" ? `<button class="ghost sm" onclick="openConsult('${c.consult_no}','${c.patient_id}')">继续</button>` : ""}</td></tr>`;
    }).join("");
    rows.forEach((c) => { const k = c.consult_no.replace(/[^a-zA-Z0-9]/g, ""); resolvePatient(c.patient_id).then((p) => { if (p) { const e = $(".cp-" + k); if (e) e.textContent = p.name || c.patient_id; } }); });
  } catch (e) { tb.innerHTML = `<tr><td colspan="6" class="empty">${e.message}</td></tr>`; }
}
async function acceptConsult(no) {
  try { const c = await api(`/scenario-006/consults/${no}/accept`, { method: "POST" }); toast("已接诊 " + no, "ok"); loadConsults(); openConsult(no, c.patient_id); } catch (e) { toast(e.message, "err"); }
}
async function openConsult(no, pid) {
  curConsult = no; $("#consultRef").textContent = no;
  const p = await resolvePatient(pid);
  $("#consultPanel").innerHTML = `
    <div class="inf-row"><span class="l">患者</span><span class="v">${p ? p.name : pid}</span></div>
    <div class="sub-h" style="margin-top:10px">开具电子处方（AI审方）</div>
    <input id="rxDrug" placeholder="药品（如 氨氯地平 5mg）" style="width:100%;padding:8px;border:1px solid var(--line);border-radius:8px;margin-bottom:6px" />
    <input id="rxUsage" placeholder="用法（如 qd 口服）" style="width:100%;padding:8px;border:1px solid var(--line);border-radius:8px;margin-bottom:8px" />
    <div class="btn-row"><button class="ghost sm" onclick="prescribeConsult()">AI审方并开方</button><button class="primary sm" onclick="finishConsult()">结束接诊（计酬）</button></div>
    <div id="rxResult"></div>`;
}
async function prescribeConsult() {
  try {
    const r = await api(`/scenario-006/consults/${curConsult}/prescribe`, { method: "POST", body: JSON.stringify({ drug_name: $("#rxDrug").value, usage: $("#rxUsage").value }) });
    const ok = r.ai_review === "passed";
    $("#rxResult").innerHTML = `<div class="adv ${ok ? "" : "p2"}">${ok ? "✅ AI审方通过" : "⚠️ " + (r.review_note || "审方预警")}：${r.drug_name} ${r.usage || ""}</div>` + ($("#rxResult").innerHTML || "");
    toast(ok ? "AI审方通过" : "AI审方预警", ok ? "ok" : "err");
  } catch (e) { toast(e.message, "err"); }
}
async function finishConsult() {
  try { const r = await api(`/scenario-006/consults/${curConsult}/finish`, { method: "POST" }); toast(`接诊结束，计酬 个人¥${r.splits.find((s) => s.payee_type === "individual").amount}`, "ok"); $("#consultPanel").innerHTML = '<div class="empty">已结束接诊</div>'; loadConsults(); loadAccount(); } catch (e) { toast(e.message, "err"); }
}

/* ---------- 家庭病床（scenario-002） ---------- */
let curBed = null;
async function loadHbDash() {
  try {
    const [d, q] = await Promise.all([api("/scenario-002/dashboard"), api("/scenario-002/quality")]);
    const items = [["在床", d.admitted], ["准入审核", d.reviewing], ["预警患者", d.alert_patients], ["待办任务", d.pending_tasks], ["任务完成率", (q.completion_rate * 100).toFixed(0) + "%"]];
    $("#hbKpi").innerHTML = items.map(([l, n]) => `<div class="kpi"><div class="kl">${l}</div><div class="kn">${n}</div></div>`).join("");
  } catch (e) { /* 静默 */ }
}
async function loadBeds() {
  loadHbDash();
  const tb = $("#bedRows");
  try {
    const rows = await api("/scenario-002/beds");
    if (!rows.length) { tb.innerHTML = '<tr><td colspan="5" class="empty">暂无病床</td></tr>'; return; }
    tb.innerHTML = rows.map((b) => {
      const k = b.bed_no.replace(/[^a-zA-Z0-9]/g, "");
      return `<tr><td>${b.bed_no}</td><td class="bp-${k}">${b.patient_id}</td><td>${b.care_level || ""}</td>
        <td>${{ reviewing: "准入审核", admitted: "在床", discharged: "已出院", rejected: "已驳回" }[b.status] || b.status}</td>
        <td><button class="ghost sm" onclick="openBed('${b.bed_no}','${b.patient_id}','${b.status}')">监测</button></td></tr>`;
    }).join("");
    rows.forEach((b) => { const k = b.bed_no.replace(/[^a-zA-Z0-9]/g, ""); resolvePatient(b.patient_id).then((p) => { if (p) { const e = $(".bp-" + k); if (e) e.textContent = p.name || b.patient_id; } }); });
  } catch (e) { tb.innerHTML = `<tr><td colspan="5" class="empty">${e.message}</td></tr>`; }
}
async function openBed(no, pid, status) {
  curBed = no; $("#bedRef").textContent = no;
  const pane = $("#bedPanel"); pane.innerHTML = '<p class="empty">加载中…</p>';
  try {
    const [mon, tasks, msgs] = await Promise.all([api(`/scenario-002/beds/${no}/monitor`), api(`/scenario-002/beds/${no}/tasks`), api(`/scenario-002/beds/${no}/messages`)]);
    const vitals = mon.latest.map((v) => `<div class="inf-row"><span class="l">${({ bp: "血压", glucose: "血糖", spo2: "血氧", hr: "心率", temp: "体温", weight: "体重" }[v.metric]) || v.metric}</span><span class="v ${v.abnormal_flag ? "risk-red" : ""}">${v.value_text}${v.unit || ""} ${v.abnormal_flag ? "⚠" : ""}</span></div>`).join("") || '<p class="note">暂无体征</p>';
    const taskRows = tasks.map((t) => `<div class="inf-row"><span class="l">${t.type}·${t.content || ""}</span><span class="v">${t.status === "done" ? '<span class="tag ok">✓完成</span>' : `<button class="ghost sm" onclick="doneBedTask('${t.id}')">完成</button>`}</span></div>`).join("") || '<p class="note">暂无任务</p>';
    const thread = msgs.map((m) => `<div style="margin:4px 0;text-align:${m.sender_role === "patient" ? "left" : "right"}"><span style="display:inline-block;padding:6px 10px;border-radius:10px;font-size:12.5px;background:${m.sender_role === "patient" ? "#f1f5f9" : "#e8f0fe"};max-width:82%">${m.sender_role === "patient" ? "👤" : "🩺"} ${m.content}</span></div>`).join("") || '<p class="note">暂无消息</p>';
    pane.innerHTML = `
      ${mon.alert_count > 0 ? `<div class="adv p1">⚠️ 该患者当前有 <b>${mon.alert_count}</b> 项体征异常预警</div>` : '<div class="adv">✅ 体征平稳</div>'}
      <div class="sub-h" style="margin-top:10px">实时体征（platform_iot）</div>${vitals}
      <div class="sub-h" style="margin-top:12px">护理任务</div>${taskRows}
      <div class="btn-row" style="margin-top:6px"><input id="newTask" placeholder="新任务（如 换药）" style="flex:1;padding:7px;border:1px solid var(--line);border-radius:8px" /><button class="ghost sm" onclick="addBedTask()">加任务</button></div>
      <div class="sub-h" style="margin-top:12px">远程问诊</div><div style="max-height:150px;overflow-y:auto;border:1px solid var(--line);border-radius:8px;padding:8px">${thread}</div>
      <div class="btn-row" style="margin-top:6px"><input id="bedMsg" placeholder="回复患者…" style="flex:1;padding:7px;border:1px solid var(--line);border-radius:8px" /><button class="ghost sm" onclick="sendBedMessage()">发送</button></div>
      ${status === "admitted" ? `<button class="primary sm" style="margin-top:10px" onclick="dischargeBed()">办理出院（结算）</button>` : ""}`;
  } catch (e) { pane.innerHTML = `<p class="empty">${e.message}</p>`; }
}
async function sendBedMessage() {
  const v = ($("#bedMsg").value || "").trim(); if (!v) return;
  try { await api(`/scenario-002/beds/${curBed}/messages`, { method: "POST", body: JSON.stringify({ content: v }) }); openBed(curBed, "", "admitted"); } catch (e) { toast(e.message, "err"); }
}
async function addBedTask() {
  try { await api(`/scenario-002/beds/${curBed}/tasks`, { method: "POST", body: JSON.stringify({ type: $("#newTask").value || "护理", content: "" }) }); toast("已添加任务", "ok"); openBed(curBed, "", "admitted"); } catch (e) { toast(e.message, "err"); }
}
async function doneBedTask(id) {
  try { await api(`/scenario-002/tasks/${id}/done`, { method: "POST" }); toast("任务已完成", "ok"); openBed(curBed, "", "admitted"); } catch (e) { toast(e.message, "err"); }
}
async function dischargeBed() {
  try { const r = await api(`/scenario-002/beds/${curBed}/discharge`, { method: "POST" }); toast(`已出院，结算 ${r.days}天 ¥${r.gross_amount}（个人¥${r.splits.find((s) => s.payee_type === "individual").amount}）`, "ok"); loadBeds(); $("#bedPanel").innerHTML = '<div class="empty">已出院</div>'; loadAccount(); } catch (e) { toast(e.message, "err"); }
}

/* ---------- 患者主数据解析 ---------- */
const ptCache = {};
async function resolvePatient(id) { if (ptCache[id]) return ptCache[id]; try { const p = await api("/platform-patient/patients/" + encodeURIComponent(id)); ptCache[id] = p; return p; } catch { return null; } }

/* ---------- 医生工作台 ---------- */
async function loadReferrals() {
  const tb = $("#refRows");
  try {
    const rows = await api("/scenario-019/referrals");
    if (!rows.length) { tb.innerHTML = '<tr><td colspan="7" class="empty">暂无单子，先在上方「发起转诊」</td></tr>'; return; }
    tb.innerHTML = rows.map((r) => {
      const k = r.ref_no.replace(/[^a-zA-Z0-9]/g, "");
      return `<tr>
        <td>${r.ref_no}</td>
        <td class="pt-${k}">${r.patient_id}</td>
        <td>${TYPE_LABEL[r.type] || r.type}</td>
        <td class="risk-${r.risk_level}">${r.risk_level}</td>
        <td class="ins-${k}">—</td>
        <td><span class="badge b-${r.status}">${statusLabel(r.status)}</span></td>
        <td>
          ${r.status === "applying" ? `<button class="primary sm" onclick="receive('${r.ref_no}')">接收</button> <button class="ghost sm" onclick="reject('${r.ref_no}')">退回</button>` : ""}
          <button class="ghost sm" onclick="openDetail('${r.ref_no}')">详情</button>
        </td></tr>`;
    }).join("");
    for (const r of rows) {
      const k = r.ref_no.replace(/[^a-zA-Z0-9]/g, "");
      resolvePatient(r.patient_id).then((p) => {
        if (!p) return;
        const c = $(".pt-" + k); if (c) c.textContent = (p.name || r.patient_id) + (p.gender === "M" ? " ♂" : p.gender === "F" ? " ♀" : "");
        const ic = $(".ins-" + k); if (ic && p.insurance_type) ic.innerHTML = `${p.insurance_type}<br><span class="tag ${p.filed ? "ok" : "warn"}">${p.filed ? "已备案" : "未备案"}</span>`;
      });
    }
  } catch (e) { tb.innerHTML = `<tr><td colspan="7" class="empty">${e.message}</td></tr>`; }
}
function statusLabel(s) { return { applying: "待接收", received: "已接收", rejected: "已退回", down: "下转中" }[s] || s; }

async function loadRecommend() {
  const box = $("#recommendBox");
  box.innerHTML = '<p class="note">推荐中…</p>';
  try {
    const recs = await api(`/scenario-019/recommend?dept=${dept()}&type=${$("#newType").value}`);
    box.innerHTML = recs.map((r, i) => `<div class="reco ${i === 0 ? "first" : ""}">
      <div><b>${r.org_name}</b>${i === 0 ? ' <span class="tag info">推荐首选</span>' : ""}<div class="m">${r.tier} · ${r.reasons.join(" · ")} · 余号 ${r.available_slots}</div></div>
      <div class="score"><b>${r.score}</b><span>匹配分</span></div></div>`).join("");
  } catch (e) { box.innerHTML = `<p class="note">${e.message}</p>`; }
}

async function createReferral() {
  $("#createBtn").disabled = true;
  try {
    const r = await api("/scenario-019/referrals", { method: "POST", body: JSON.stringify({ patient_id: $("#newPatient").value, type: $("#newType").value, risk_level: $("#newRisk").value }) });
    toast("已发起转诊单 " + r.ref_no, "ok"); loadReferrals();
  } catch (e) { toast(e.message, "err"); } finally { $("#createBtn").disabled = false; }
}
async function receive(ref) {
  try { const r = await api(`/scenario-019/referrals/${ref}/receive`, { method: "POST" }); toast(`已接收 ${ref}，分账 ` + r.splits.map((x) => `${PAYEE_LABEL[x.payee_type]}¥${x.amount}`).join("/"), "ok"); loadReferrals(); loadAccount(); } catch (e) { toast(e.message, "err"); }
}
async function reject(ref) {
  try { await api(`/scenario-019/referrals/${ref}/reject`, { method: "POST", body: JSON.stringify({ reason: "资料不完整，退回补充" }) }); toast("已退回 " + ref, "ok"); loadReferrals(); } catch (e) { toast(e.message, "err"); }
}

/* ---------- 转诊单详情（七大子页） ---------- */
function openDetail(ref) { currentRef = ref; $("#detailRef").textContent = ref; $("#detailEmpty").classList.add("hidden"); $("#detailBody").classList.remove("hidden"); detailTab("progress", document.querySelector("#detailSeg button")); }
function detailTab(tab, btn) {
  currentTab = tab;
  document.querySelectorAll("#detailSeg button").forEach((b) => b.classList.remove("on"));
  if (btn) btn.classList.add("on"); else { const idx = ["progress", "insurance", "materials", "consent", "checks", "nodes", "downward"].indexOf(tab); document.querySelectorAll("#detailSeg button")[idx]?.classList.add("on"); }
  renderGen++;
  activePane = $("#detailPane"); activePane.innerHTML = '<p class="empty">加载中…</p>';
  ({ progress: renderProgress, insurance: renderInsurance, materials: renderMaterials, consent: renderConsent, checks: renderChecks, nodes: renderNodes, downward: renderDownward }[tab])(activePane);
}

async function renderProgress(pane) {
  const myGen = renderGen;
  try {
    const [d, nodes, track] = await Promise.all([api(`/scenario-019/referrals/${currentRef}/detail`), api(`/scenario-019/referrals/${currentRef}/nodes`), api(`/scenario-019/referrals/${currentRef}/track`)]);
    if (myGen !== renderGen) return;
    const steps = nodes.map((n) => `<div class="st ${n.done ? "done" : ""}"><div class="dot">${n.done ? "✓" : ""}</div>${NODE_LABEL[n.node]}</div>`).join("");
    const tl = track.map((t) => `<div class="ev"><b>${t.title}</b><span>${t.detail || ""}</span></div>`).join("") || '<p class="note">暂无进度事件</p>';
    pane.innerHTML = `<div class="stepper">${steps}</div>
      <div class="two-grid">
        <div><div class="sub-h">转出信息</div>
          <div class="inf-row"><span class="l">转出机构</span><span class="v">${d.source_org_name || d.source_org || "—"}</span></div>
          <div class="inf-row"><span class="l">经治医生</span><span class="v">${d.source_doctor_name || d.source_doctor || "—"}</span></div>
          <div class="inf-row"><span class="l">风险等级</span><span class="v risk-${d.risk_level}">${d.risk_level}</span></div></div>
        <div><div class="sub-h">接收信息</div>
          <div class="inf-row"><span class="l">接收机构</span><span class="v">${d.target_org_name || d.target_org || "—"}</span></div>
          <div class="inf-row"><span class="l">接诊医生</span><span class="v">${d.target_doctor_name || d.target_doctor || "—"}</span></div>
          <div class="inf-row"><span class="l">状态</span><span class="v">${statusLabel(d.status)}</span></div></div>
      </div>
      <div class="sub-h" style="margin-top:14px">进度时间轴</div><div class="tl">${tl}</div>`;
  } catch (e) { pane.innerHTML = `<p class="empty">${e.message}</p>`; }
}

async function renderInsurance(pane) {
  const myGen = renderGen;
  try {
    const i = await api(`/scenario-019/referrals/${currentRef}/insurance`);
    if (myGen !== renderGen) return;
    pane.innerHTML = `<div class="ins-calc">
        <div class="ir"><span>预计总费用</span><span>¥ ${i.total}</span></div>
        <div class="ir"><span>医保起付线</span><span>¥ ${i.deductible}</span></div>
        <div class="ir"><span>报销比例</span><span>${(i.reimburse_ratio * 100).toFixed(0)}%</span></div>
        <div class="ir"><span>医保报销</span><span style="color:#1565d8">¥ ${i.reimbursed}</span></div>
        <div class="ir"><span>个人自付</span><span>¥ ${i.self_pay}</span></div></div>
      <div class="inf-row"><span class="l">参保类型</span><span class="v">${i.insurance_type || "—"}</span></div>
      <div class="inf-row"><span class="l">转诊备案</span><span class="v">${i.filed ? '<span class="tag ok">已备案</span>' : '<span class="tag warn">未备案</span>'}</span></div>
      <div class="inf-row"><span class="l">年度累计报销</span><span class="v">¥${i.annual_reimbursed ?? "—"} / ¥${i.cap_line ?? "—"} 封顶</span></div>
      ${i.saved_vs_unfiled > 0 ? `<div class="adv">✅ 已备案享高档报销，相比未备案预计节省 <b>¥${i.saved_vs_unfiled}</b>。</div>` : ""}`;
  } catch (e) { pane.innerHTML = `<p class="empty">${e.message}</p>`; }
}

async function renderMaterials(pane) {
  const myGen = renderGen;
  try {
    const m = await api(`/scenario-019/referrals/${currentRef}/materials`);
    if (myGen !== renderGen) return;
    pane.innerHTML = `<table class="tbl"><thead><tr><th>资料</th><th>互认</th><th>有效期</th><th>范围</th></tr></thead><tbody>${m.map((x) => `<tr><td>${x.doc_type}${x.conclusion ? `<br><span style="font-size:11px;color:#94a3b8">${x.conclusion}</span>` : ""}</td><td>${x.mutual_recognition ? '<span class="tag info">可互认</span>' : '<span class="tag">已包含</span>'}</td><td>${x.valid_days ? x.valid_days + "天" : "—"}</td><td>${x.recognize_scope || "—"}</td></tr>`).join("")}</tbody></table>
      <div class="adv">🔄 识别 ${m.filter((x) => x.mutual_recognition).length} 项可互认结果，接收医院优先采用，减少重复检查。</div>`;
  } catch (e) { pane.innerHTML = `<p class="empty">${e.message}</p>`; }
}

async function renderConsent(pane) {
  const myGen = renderGen;
  try {
    const c = await api(`/scenario-019/referrals/${currentRef}/consents`);
    if (myGen !== renderGen) return;
    pane.innerHTML = c.map((x) => `<div class="inf-row"><span class="l">${x.doc_name}</span><span class="v">${x.signed ? '<span class="tag ok">✓ 已签署</span>' : `<button class="ghost sm" onclick="signConsent('${x.doc_name}')">电子签署</button>`}</span></div>`).join("") + '<p class="note">全程留痕可追溯。</p>';
  } catch (e) { pane.innerHTML = `<p class="empty">${e.message}</p>`; }
}
async function signConsent(doc) { try { await api(`/scenario-019/referrals/${currentRef}/consents/${encodeURIComponent(doc)}/sign`, { method: "POST" }); toast("已签署：" + doc, "ok"); renderConsent(activePane); } catch (e) { toast(e.message, "err"); } }

// 健康档案（跨院汇聚，来自 platform-archive）
async function renderArchive(pane) {
  const myGen = renderGen;
  const pid = localStorage.getItem("hosp_patient");
  try {
    const [sum, dx, reps, rxs] = await Promise.all([
      api(`/platform-archive/patients/${pid}/summary`),
      api(`/platform-archive/patients/${pid}/diagnoses`),
      api(`/platform-archive/patients/${pid}/reports`),
      api(`/platform-archive/patients/${pid}/prescriptions`),
    ]);
    if (myGen !== renderGen) return;
    pane.innerHTML = `
      <div class="acct-nums"><div><b>${sum.orgs}</b><span>贯通机构</span></div><div><b>${sum.encounters}</b><span>就诊</span></div><div><b>${sum.reports}</b><span>报告</span></div></div>
      <div class="sub-h">诊断</div>${dx.map((d) => `<div class="inf-row"><span class="l">${d.name}</span><span class="v">${d.is_chronic ? '<span class="tag warn">慢病</span> ' : ""}${d.icd_code || ""}</span></div>`).join("")}
      <div class="sub-h" style="margin-top:10px">检验 / 影像报告</div>${reps.map((r) => `<div class="inf-row"><span class="l">${r.item_name}<br><span style="font-size:11px;color:#94a3b8">${r.conclusion || ""} · ${r.org_name || ""}</span></span><span class="v">${r.category}</span></div>`).join("")}
      <div class="sub-h" style="margin-top:10px">处方</div>${rxs.flatMap((rx) => rx.items).map((i) => `<div class="inf-row"><span class="l">${i.drug_name}</span><span class="v">${i.usage || ""} ${i.course || ""}</span></div>`).join("") || '<p class="note">无</p>'}`;
  } catch (e) { if (myGen === renderGen) pane.innerHTML = `<p class="empty">${e.message}</p>`; }
}

async function renderChecks(pane) {
  const myGen = renderGen;
  try {
    const c = await api(`/scenario-019/referrals/${currentRef}/checks`);
    if (myGen !== renderGen) return;
    const ok = c.filter((x) => x.passed).length;
    pane.innerHTML = `<p class="note">规范转诊五要素：达标 ${ok}/${c.length}（达标进入 DRG 质量点数调节）</p>` + c.map((x) => `<div class="inf-row"><span class="l">${x.item}</span><span class="v">${x.passed ? '<span class="tag ok">✓</span>' : '<span class="tag warn">缺</span>'}</span></div>`).join("");
  } catch (e) { pane.innerHTML = `<p class="empty">${e.message}</p>`; }
}

async function renderNodes(pane) {
  const myGen = renderGen;
  try {
    const nodes = await api(`/scenario-019/referrals/${currentRef}/nodes`);
    if (myGen !== renderGen) return;
    pane.innerHTML = nodes.map((n) => `<div class="node ${n.done ? "done" : ""}"><span class="ndot">${n.done ? "✓" : ""}</span><span class="n-name">${NODE_LABEL[n.node]}</span><span class="n-pts">+${n.points}分</span>${n.done ? "" : `<button class="ghost sm" onclick="completeNode('${n.node}')">完成</button>`}</div>`).join("");
  } catch (e) { pane.innerHTML = `<p class="empty">${e.message}</p>`; }
}
async function completeNode(node) { try { const r = await api(`/scenario-019/referrals/${currentRef}/nodes/${node}/complete`, { method: "POST" }); toast(`${NODE_LABEL[node]} +${r.points}分（账户 ${r.account_points} 分）`, "ok"); renderNodes(activePane); loadAccount(); } catch (e) { toast(e.message, "err"); } }

async function renderDownward(pane) {
  const myGen = renderGen;
  try {
    const d = await api(`/scenario-019/referrals/${currentRef}/downward`);
    if (myGen !== renderGen) return;
    if (d) {
      pane.innerHTML = `<div class="adv">${d.summary || ""}</div><table class="tbl"><thead><tr><th>药品</th><th>用法</th><th>疗程</th></tr></thead><tbody>${d.drugs.map((x) => `<tr><td>${x.drug}</td><td>${x.usage || ""}</td><td>${x.course || ""}</td></tr>`).join("")}</tbody></table>${d.review_plan ? `<p class="note">复查节点：${d.review_plan}</p>` : ""}`;
    } else {
      pane.innerHTML = `<p class="note">尚无下转方案，可下发：</p>
        <textarea id="dwSummary" placeholder="病情小结（如：PCI术后病情稳定，符合下转标准）"></textarea>
        <input id="dwReview" placeholder="复查节点（如：1个月血常规/肝肾/心电图）" style="width:100%;margin-top:8px;padding:8px;border:1px solid var(--line);border-radius:8px" />
        <button class="primary sm" style="margin-top:10px" onclick="createDownward()">下发下转康复方案</button>`;
    }
  } catch (e) { pane.innerHTML = `<p class="empty">${e.message}</p>`; }
}
async function createDownward() {
  try {
    await api(`/scenario-019/referrals/${currentRef}/downward`, { method: "POST", body: JSON.stringify({ summary: $("#dwSummary").value || "病情稳定，符合下转标准", review_plan: $("#dwReview").value, drugs: [{ drug: "阿司匹林肠溶片 100mg", usage: "qd 口服", course: "长期" }, { drug: "阿托伐他汀 20mg", usage: "qn 口服", course: "长期" }] }) });
    toast("下转方案已下发", "ok"); renderDownward(activePane); loadReferrals();
  } catch (e) { toast(e.message, "err"); }
}

/* ---------- 信用账户 ---------- */
async function loadAccount() {
  try {
    const a = await api("/scenario-019/credit/account");
    $("#acctPoints").textContent = a.points; $("#acctBalance").textContent = "¥" + a.balance;
    $("#ledgerRows").innerHTML = a.ledger.length ? a.ledger.map((l) => `<tr><td>${NODE_LABEL[l.node] || l.node}</td><td>${l.points}</td><td>¥${l.earned}</td></tr>`).join("") : '<tr><td colspan="3" class="empty">暂无流水</td></tr>';
    renderIncentive();
  } catch (e) { /* 静默 */ }
}

/* ---------- 三源融合测算（客户端实时折算，积分取真实账户） ---------- */
function renderIncentive() {
  const P = parseInt(($("#acctPoints").textContent || "0").replace(/\D/g, "")) || 0;
  const drg = P * (INC.drg / 100) * 50;
  const unit = Math.min(Math.max(1.0 + INC.ratio * 0.3, 1.5), 3.5);
  const perf = P * unit;
  const annual = INC.surplus * (INC.surRatio / 100) * (P / 100000);
  const monthly = drg + perf + annual / 12;
  const fy = (n) => "¥" + Math.round(n).toLocaleString();
  const set = (id, v) => { const e = $("#" + id); if (e) e.textContent = v; };
  set("vDrg", INC.drg); set("vRatio", INC.ratio); set("vSur", INC.surRatio);
  set("incMonthly", Math.round(monthly).toLocaleString()); set("incUnit", unit.toFixed(2));
  const sr = $("#srcRow");
  if (sr) sr.innerHTML = `
    <div class="src"><b>DRG 质量点数</b><span class="amt">${fy(drg)}</span></div>
    <div class="src"><b>绩效工资专项</b><span class="amt">${fy(perf)}</span></div>
    <div class="src"><b>年度结余奖励</b><span class="amt">${fy(annual)}</span></div>`;
}

/* ---------- 患者端（移动视图） ---------- */
function showPatientApp() {
  $("#loginView").classList.add("hidden"); $("#appView").classList.add("hidden"); $("#patientView").classList.remove("hidden");
  $("#pWhoName").textContent = localStorage.getItem("hosp_name") || "";
  $("#pHello").textContent = "您好，" + (localStorage.getItem("hosp_name") || "") + " 👋";
  loadMyReferrals();
}
async function loadMyReferrals() {
  try {
    const refs = await api("/scenario-019/my/referrals");
    if (!refs.length) { $("#pRefSel").innerHTML = ""; $("#pPane").innerHTML = '<p class="empty">您当前没有转诊单</p>'; return; }
    currentRef = refs[0].ref_no;
    $("#pRefSel").innerHTML = refs.map((r, i) => `<button class="${i === 0 ? "on" : ""}" onclick="pickRef('${r.ref_no}',this)">${r.ref_no} · ${statusLabel(r.status)}</button>`).join("");
    pTab("progress", document.querySelector("#pSeg button"));
  } catch (e) { $("#pPane").innerHTML = `<p class="empty">${e.message}</p>`; }
}
function pickRef(ref, btn) { currentRef = ref; document.querySelectorAll("#pRefSel button").forEach((b) => b.classList.toggle("on", b === btn)); pTab("progress", document.querySelector("#pSeg button")); }
function pTab(tab, btn) {
  document.querySelectorAll("#pSeg button").forEach((b) => b.classList.remove("on"));
  if (btn) btn.classList.add("on");
  renderGen++;
  activePane = $("#pPane"); activePane.innerHTML = '<p class="empty">加载中…</p>';
  ({ progress: renderProgress, insurance: renderInsurance, materials: renderMaterials, consent: renderConsent, archive: renderArchive }[tab])(activePane);
}

/* ---------- MDT ---------- */
async function loadMdt() {
  try {
    const list = await api("/scenario-019/mdt");
    $("#mdtList").innerHTML = list.length ? list.map((s) => `<div class="mdt-item" onclick='openMdt("${s.id}")'><b>${s.topic}</b><span>${s.case_summary || ""}</span><span>专家 ${s.experts.length} 人 · ${s.status === "done" ? "已完成" : "待会诊"}</span></div>`).join("") : '<div class="empty">暂无会诊</div>';
  } catch (e) { $("#mdtList").innerHTML = `<div class="empty">${e.message}</div>`; }
}
async function openMdt(id) {
  try {
    const s = await api("/scenario-019/mdt/" + id);
    $("#mdtTopic").textContent = s.topic;
    const experts = s.experts.map((e) => `<div class="expert"><span class="ava">${e.name[0]}</span><div style="flex:1"><b>${e.name}</b> <span style="color:#64748b">${e.dept || ""} ${e.org || ""}</span></div><span class="tag ${e.confirmed ? "ok" : "warn"}">${e.role}${e.confirmed ? "·已确认" : "·待确认"}</span></div>`).join("");
    const opinions = s.opinions.map((o) => `<div class="adv">✍️ ${o.name || ""}：${o.opinion}</div>`).join("");
    $("#mdtDetail").innerHTML = `<div class="adv">${s.case_summary || ""}</div><div class="sub-h" style="margin-top:10px">参会专家</div>${experts}<div class="sub-h" style="margin-top:12px">会诊意见</div>${opinions || '<p class="note">暂无意见</p>'}<textarea id="opinionTxt" placeholder="输入会诊意见…">考虑LAD中段临界病变，建议完善FFR评估；同期优化降糖。同意上转行冠脉造影。</textarea><button class="primary sm" style="margin-top:8px" onclick='submitOpinion("${id}")'>✍️ 签名并提交意见</button>`;
  } catch (e) { $("#mdtDetail").innerHTML = `<div class="empty">${e.message}</div>`; }
}
async function submitOpinion(id) { try { await api(`/scenario-019/mdt/${id}/opinion`, { method: "POST", body: JSON.stringify({ opinion: $("#opinionTxt").value }) }); toast("会诊意见已提交并留痕", "ok"); openMdt(id); loadMdt(); } catch (e) { toast(e.message, "err"); } }

/* ---------- 管理驾驶舱 ---------- */
async function loadAdmin() {
  try {
    const [d, s, rules, alerts] = await Promise.all([api("/scenario-019/admin/dashboard"), api("/scenario-019/admin/settlements"), api("/scenario-019/admin/rules"), api("/scenario-019/admin/alerts")]);
    const k = d.kpi;
    $("#kpiRow").innerHTML = [["转诊总量", k.total], ["上转", k.up], ["下转", k.down], ["接收率", (k.received_rate * 100).toFixed(0) + "%"], ["检查互认率", (k.mutual_recognition_rate * 100).toFixed(0) + "%"]].map(([l, n]) => `<div class="kpi"><div class="kl">${l}</div><div class="kn">${n}</div></div>`).join("");
    const tot = Math.max(k.total, 1);
    $("#typeDist").innerHTML = Object.entries(d.type_distribution).map(([t, n]) => `<div class="bar-item"><div class="bar-top"><span>${TYPE_LABEL[t] || t}</span><span>${n} · ${((n / tot) * 100).toFixed(0)}%</span></div><div class="bar-track"><div class="bar-fill" style="width:${(n / tot) * 100}%"></div></div></div>`).join("");
    $("#orgRank").innerHTML = `<table class="tbl"><thead><tr><th>机构</th><th>接收量</th></tr></thead><tbody>${d.org_ranking.map((o) => `<tr><td>${o.org_name || o.org_id}</td><td>${o.inbound}</td></tr>`).join("")}</tbody></table>`;
    $("#alertList").innerHTML = alerts.map((a) => `<div class="alert-row"><span class="lv ${a.level}">${a.level.toUpperCase()}</span><div class="a-body"><b>${a.title}</b><span>${a.detail || ""}</span></div>${a.status === "handled" ? '<span class="tag ok">已处置</span>' : `<button class="ghost sm" onclick='handleAlert("${a.id}")'>处置</button>`}</div>`).join("") || '<div class="empty">无预警</div>';
    $("#settleBox").innerHTML = `<table class="tbl"><thead><tr><th>协同服务</th><th>数量</th><th>单价</th><th>小计</th></tr></thead><tbody>${s.measures.map((m) => `<tr><td>${m.name}</td><td>${m.qty}</td><td>¥${m.unit}</td><td>¥${m.subtotal}</td></tr>`).join("")}</tbody></table><div class="sub-h" style="margin-top:12px">机构分账明细</div><table class="tbl"><thead><tr><th>机构</th><th>服务金额</th><th>质量奖励</th><th>实际分配</th></tr></thead><tbody>${s.org_settlements.map((o) => `<tr><td>${o.org_id}</td><td>¥${o.service_amount}</td><td style="color:#15803d">+¥${o.quality_bonus}</td><td><b>¥${o.actual_alloc}</b></td></tr>`).join("")}</tbody></table>`;
    $("#rulesBox").innerHTML = `<div class="sub-h">病情分层</div>${rules.risk_layers.map((r) => `<div class="adv">${r.level}：${r.desc}</div>`).join("")}<div class="sub-h" style="margin-top:10px">时限规则</div><table class="tbl"><thead><tr><th>场景</th><th>时限</th><th>预警阈值</th></tr></thead><tbody>${rules.time_limits.map((t) => `<tr><td>${t.scene}</td><td>${t.limit}</td><td>${t.warn}</td></tr>`).join("")}</tbody></table><div class="sub-h" style="margin-top:10px">检查互认目录</div><table class="tbl"><thead><tr><th>类型</th><th>项目</th><th>有效期</th><th>范围</th></tr></thead><tbody>${rules.mutual_recognition.map((m) => `<tr><td>${m.category}</td><td>${m.item_name}</td><td>${m.valid_days}天</td><td>${m.recognize_scope}</td></tr>`).join("")}</tbody></table>`;
  } catch (e) { $("#kpiRow").innerHTML = `<div class="empty">${e.message}</div>`; }
}
async function handleAlert(id) { try { await api(`/scenario-019/admin/alerts/${id}/handle`, { method: "POST" }); toast("预警已处置，全程留痕", "ok"); loadAdmin(); } catch (e) { toast(e.message, "err"); } }

/* ---------- 启动 ---------- */
$("#loginBtn").addEventListener("click", login);
["username", "password"].forEach((id) => $("#" + id).addEventListener("keydown", (e) => { if (e.key === "Enter") login(); }));
if (token()) route();
