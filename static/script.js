let chart;
const $ = (id) => document.getElementById(id);
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function scoreClass(level) { return level === "HIGH" ? "risk-high" : level === "MEDIUM" ? "risk-medium" : "risk-low"; }
async function api(url, options={}) {
  const response = await fetch(url, options);
  const type = response.headers.get("content-type") || "";
  const data = type.includes("application/json") ? await response.json() : await response.blob();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}
  
async function refreshAll() {
  const button = document.querySelector(".top-actions button");
  const originalText = button ? button.textContent : "";

  if (button) {
    button.disabled = true;
    button.textContent = "Refreshing...";
  }

  try {
    // Fetch dashboard data from Flask
    const [health, rows] = await Promise.all([
      api("/api/health"),
      api("/api/transactions")
    ]);

    if (!Array.isArray(rows)) {
      throw new Error("Transaction API did not return a list.");
    }

    // Update summary cards
    $("stat-total").textContent = rows.length;

    $("stat-high").textContent = rows.filter(
      row => row.risk_level === "HIGH"
    ).length;

    $("stat-pending").textContent = rows.filter(
      row => !row.review_status ||
             row.review_status === "PENDING"
    ).length;

    $("stat-model").textContent =
      health.model_loaded ? "Ready" : "Not trained";

    $("model-foot").textContent =
      health.model_loaded
        ? "Model loaded"
        : "Run python model/train.py";

    $("stat-model").className =
      "stat-number status-text " +
      (health.model_loaded ? "risk-low" : "risk-medium");

    // Update the transaction table
    renderRows(rows);

    // Chart.js should not prevent the rest of the dashboard refreshing
    try {
      if (typeof Chart !== "undefined") {
        renderChart(rows);
      } else {
        console.warn("Chart.js is unavailable; dashboard data refreshed.");
      }
    } catch (chartError) {
      console.error("Chart refresh failed:", chartError);
    }

    console.log("PayGuard AI dashboard refreshed successfully.");

  } catch (error) {
    console.error("Dashboard refresh failed:", error);

    $("model-foot").textContent = error.message;
    $("stat-model").textContent = "Error";

  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = originalText;
    }
  }
}


function renderRows(rows) {
  const body = $("transaction-rows");
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="7" class="muted">No assessments yet. Analyze a transaction to begin.</td></tr>';
    return;
  }
  body.innerHTML = rows.map(r => `<tr>
    <td>#${r.id}</td><td>${esc(new Date(r.created_at).toLocaleString())}</td>
    <td>${r.amount == null ? "—" : "$" + Number(r.amount).toFixed(2)}</td>
    <td>${(Number(r.risk_score)*100).toFixed(1)}%</td>
    <td><span class="badge ${esc(r.risk_level)}">${esc(r.risk_level)}</span></td>
    <td>${esc(r.review_status || "PENDING")}</td>
    <td><button class="text-button" onclick="showDetail(${r.id})">Inspect →</button></td></tr>`).join("");
}
function renderChart(rows) {
  const counts = {LOW:0,MEDIUM:0,HIGH:0};
  rows.forEach(r => counts[r.risk_level] = (counts[r.risk_level] || 0) + 1);
  const ctx = $("risk-chart");
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type:"doughnut",
    data:{labels:["Low risk","Medium risk","High risk"],datasets:[{data:[counts.LOW,counts.MEDIUM,counts.HIGH],backgroundColor:["#42e0c0","#ffca70","#ff6e80"],borderColor:"#101a2d",borderWidth:4}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:"bottom",labels:{color:"#aab9cf",padding:18,usePointStyle:true,pointStyle:"circle"}}},cutout:"68%"}
  });
}
$("score-form").addEventListener("submit", async e => {
  e.preventDefault();
  const form = new FormData(e.target);
  const payload = {Amount:Number(form.get("Amount")),Time:Number(form.get("Time"))};
  const box = $("score-result");
  box.className = "result-box";
  box.textContent = "Analyzing…";
  try {
    const result = await api("/api/score",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    box.innerHTML = `<div class="${scoreClass(result.risk_level)}"><b>${esc(result.risk_level)} RISK</b> · ${(result.risk_score*100).toFixed(1)}% estimated risk</div>
      <p><b>Recommended action:</b> ${esc(result.recommended_action)}</p><p><b>Assessment ID:</b> #${result.transaction_id}</p>
      <p><b>Explanation:</b></p><ul class="reason-list">${result.reasons.map(r=>`<li>${esc(r)}</li>`).join("")}</ul>
      <p class="small muted">A model estimate is not proof of fraud.</p>`;
    await refreshAll();
  } catch(err) { box.innerHTML = `<span class="error">${esc(err.message)}</span>`; }
});
$("csv-form").addEventListener("submit", async e => {
  e.preventDefault();
  const form = new FormData(e.target);
  $("csv-message").textContent = "Scoring transactions…";
  try {
    const response = await fetch("/api/score-batch",{method:"POST",body:form});
    if (!response.ok) {
      const data = await response.json(); throw new Error(data.error || "Upload failed");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href=url; a.download="payguard_scored_transactions.csv"; a.click(); URL.revokeObjectURL(url);
    $("csv-message").textContent = "Scored CSV downloaded.";
    await refreshAll();
  } catch(err) { $("csv-message").textContent = err.message; }
});
async function showDetail(id) {
  try {
    const item = await api(`/api/transactions/${id}`);
    $("detail-content").innerHTML = `<div class="eyebrow">TRANSACTION #${item.id}</div><h2>Risk assessment</h2>
      <p class="${scoreClass(item.risk_level)}"><b>${esc(item.risk_level)} · ${(item.risk_score*100).toFixed(1)}%</b></p>
      <p class="muted small">Created ${esc(new Date(item.created_at).toLocaleString())}</p>
      <h3>Model explanation</h3><ul class="reason-list">${item.reasons.map(r=>`<li>${esc(r)}</li>`).join("")}</ul>
      <h3>Input features</h3><pre>${esc(JSON.stringify(item.input,null,2))}</pre>
      <h3>Human review</h3><p class="muted small">Record a reviewer outcome for this demo assessment.</p>
      <form class="review-form" onsubmit="submitReview(event,${item.id})">
        <select name="decision"><option value="needs_more_info">Needs more information</option><option value="legitimate">Legitimate</option><option value="confirmed_fraud">Confirmed fraud</option></select>
        <textarea name="reason" placeholder="Review notes (optional)"></textarea><button class="button button-primary">Save review</button>
      </form>
      <h3>Review history</h3><ul class="reason-list">${(item.review_events||[]).map(e=>`<li>${esc(e.decision)} — ${esc(e.reason||"No note")}</li>`).join("") || "<li>No review events yet.</li>"}</ul>`;
    $("detail-modal").classList.remove("hidden");
  } catch(e) { alert(e.message); }
}
async function submitReview(event,id) {
  event.preventDefault();
  const form = new FormData(event.target);
  try {
    await api(`/api/transactions/${id}/review`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({decision:form.get("decision"),reason:form.get("reason")})});
    closeModal(); await refreshAll();
  } catch(e) { alert(e.message); }
}
function closeModal() { $("detail-modal").classList.add("hidden"); }
$("detail-modal").addEventListener("click",e=>{if(e.target.id==="detail-modal")closeModal();});
async function paypalSetup() {
  try {
    const config = await api("/api/paypal/config");
    if (config.enabled) $("paypal-status").textContent = "Client ID configured. Create a Sandbox order to test the API.";
    else $("paypal-status").textContent = "Not configured. Add Sandbox credentials to .env and restart Flask.";
  } catch(e) { $("paypal-status").textContent = e.message; }
}
$("create-order").addEventListener("click", async () => {
  const box = $("paypal-result"); box.textContent = "Creating Sandbox order…";
  try {
    const order = await api("/api/paypal/orders",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({})});
    box.innerHTML = `<p><b>Order created:</b> ${esc(order.id)}</p><p><b>Status:</b> ${esc(order.status)}</p><p><b>Amount:</b> $${esc(order.amount)} ${esc(order.currency)}</p><p class="small muted">Use the PayPal approval link from the Orders API response if you want to add the full checkout approval UI. This starter creates the server-side order.</p>`;
  } catch(e) { box.innerHTML = `<span class="error">${esc(e.message)}</span>`; }
});
refreshAll();
paypalSetup();
