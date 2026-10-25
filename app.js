// Talks to the Flask REST API (/api/tasks) using fetch().
let tasks = [];
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const NEXT = { todo: "doing", doing: "done", done: "todo" };
const LABEL = { todo: "Start", doing: "Complete", done: "Reopen" };
const COLOR = { High: "bad", Medium: "warn", Low: "ok" };

async function api(url, method = "GET", body) {
  const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function load() {
  tasks = await api("/api/tasks");
  render();
}

function render() {
  const p = $("#fPriority").value, q = $("#fSearch").value.toLowerCase();
  const today = new Date().toISOString().slice(0, 10);
  for (const s of ["todo", "doing", "done"]) $("#col-" + s).innerHTML = "";
  tasks.filter((t) => (!p || t.priority === p) && t.title.toLowerCase().includes(q)).forEach((t) => {
    const overdue = t.due_date && t.due_date < today && t.status !== "done";
    $("#col-" + t.status).insertAdjacentHTML("beforeend", `
      <div class="card" style="padding:10px">
        <b>${esc(t.title)}</b> <span class="badge ${COLOR[t.priority]}">${t.priority}</span>
        <div class="muted" style="font-size:.85rem">${esc(t.description)}</div>
        ${t.due_date ? `<div class="${overdue ? "badge bad" : "muted"}" style="font-size:.8rem">Due: ${esc(t.due_date)}${overdue ? " (overdue)" : ""}</div>` : ""}
        <div style="margin-top:6px">
          <button class="btn sm" onclick="move(${t.id},'${NEXT[t.status]}')">${LABEL[t.status]}</button>
          <button class="btn sm bad" onclick="del(${t.id})">Delete</button>
        </div>
      </div>`);
  });
  const n = (s) => tasks.filter((t) => t.status === s).length;
  $("#stats").innerHTML = `<div class="stat"><b>${tasks.length}</b><span>Total</span></div><div class="stat"><b>${n("doing")}</b><span>In progress</span></div><div class="stat"><b>${n("done")}</b><span>Done</span></div>`;
}

window.move = async (id, status) => { await api("/api/tasks/" + id, "PUT", { status }); load(); };
window.del = async (id) => { if (confirm("Delete this task?")) { await api("/api/tasks/" + id, "DELETE"); load(); } };

$("#taskForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  try { await api("/api/tasks", "POST", data); e.target.reset(); $("#msg").textContent = "Task added!"; load(); }
  catch (err) { $("#msg").textContent = err.message; }
});
$("#fPriority").addEventListener("change", render);
$("#fSearch").addEventListener("input", render);
load();
