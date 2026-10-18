"use strict";
(() => {
  const byId = (id) => document.getElementById(id);
  const categories = ["CONFIRMED_LOSS", "SUSPECTED_CONVERSION", "EQUIVALENT", "UNKNOWN"];
  const labels = {CONFIRMED_LOSS: "Confirmed loss", SUSPECTED_CONVERSION: "Suspected conversion", EQUIVALENT: "Equivalent", UNKNOWN: "Unknown"};
  const files = {before: null, after: null};
  let config = null;
  let result = null;
  let busy = false;
  const status = (message, type = "") => { byId("status").textContent = message; byId("status").className = "status " + type; };
  const node = (tag, text, className) => { const element = document.createElement(tag); if (text !== undefined) element.textContent = text; if (className) element.className = className; return element; };
  const invalidate = () => { result = null; byId("results").hidden = true; };
  function selectFile(side, file) {
    if (busy) return;
    invalidate();
    files[side] = file || null;
    byId(side + "-name").textContent = file ? file.name : (side === "before" ? "Drop your original file here" : "Drop your converted file here");
    byId(side + "-hint").textContent = file ? (file.size / 1024).toLocaleString(undefined, {maximumFractionDigits: 1}) + " KiB · choose another file" : "or choose a file";
    byId(side + "-zone").classList.toggle("selected", Boolean(file));
    if (file && file.size > (config ? config.max_file_bytes : 5 * 1024 * 1024)) status("File exceeds 5 MiB. Choose a smaller file.", "error");
    else status(files.before && files.after ? "Files ready. Set your rules, then compare." : "Choose a before and after file to begin.");
  }
  for (const side of ["before", "after"]) {
    const input = byId(side + "-file");
    const zone = byId(side + "-zone");
    input.addEventListener("change", () => selectFile(side, input.files[0]));
    zone.addEventListener("dragover", (event) => { event.preventDefault(); if (!busy) zone.classList.add("dragover"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
    zone.addEventListener("drop", (event) => { event.preventDefault(); zone.classList.remove("dragover"); if (event.dataTransfer.files.length !== 1) { status("Drop one file into each area.", "error"); return; } selectFile(side, event.dataTransfer.files[0]); });
  }
  // Prevent accidental browser navigation when files are dropped outside the targets.
  document.addEventListener("dragover", (event) => event.preventDefault());
  document.addEventListener("drop", (event) => event.preventDefault());
  function parsePolicy() {
    const value = JSON.parse(byId("policy").value);
    if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Policy JSON must be an object.");
    return value;
  }
  byId("policy").addEventListener("input", () => {
    invalidate();
    try { const policy = parsePolicy(); byId("keys").value = Array.isArray(policy.keys) ? policy.keys.join(", ") : ""; byId("ignore-order").checked = policy.ignore_order === true; } catch (_) { /* Editing can temporarily produce incomplete JSON. */ }
  });
  function syncControls() {
    invalidate();
    try {
      const policy = parsePolicy();
      policy.keys = byId("keys").value.trim() ? byId("keys").value.split(",").map((key) => key.trim()) : [];
      policy.ignore_order = byId("ignore-order").checked;
      byId("policy").value = JSON.stringify(policy, null, 2);
    } catch (_) { status("Fix the policy JSON before changing the main controls.", "error"); }
  }
  byId("keys").addEventListener("input", syncControls);
  byId("ignore-order").addEventListener("change", syncControls);
  async function readFile(file) {
    const bytes = new Uint8Array(await file.arrayBuffer());
    let binary = "";
    for (let offset = 0; offset < bytes.length; offset += 16384) binary += String.fromCharCode(...bytes.subarray(offset, offset + 16384));
    return {name: file.name, data: btoa(binary)};
  }
  function renderFindings() {
    if (!result) return;
    const filter = byId("filter").value;
    const all = result.report.findings || [];
    const selected = all.filter((finding) => filter === "ALL" || finding.verdict === filter);
    const container = byId("findings");
    container.replaceChildren();
    byId("finding-count").textContent = selected.length + " of " + all.length;
    if (!selected.length) container.append(node("div", all.length ? "No findings in this category." : "No findings under the recorded comparison rules. Review the assumptions above.", "empty"));
    for (const finding of selected) {
      const card = node("article", undefined, "finding");
      const top = node("div", undefined, "finding-top");
      const category = categories.includes(finding.verdict) ? finding.verdict : "UNKNOWN";
      top.append(node("span", labels[category], "finding-category " + category), node("h3", finding.code || "Finding"));
      card.append(top, node("p", finding.message || ""));
      card.append(node("div", "Table: " + (finding.table == null ? "—" : finding.table), "finding-location"));
      const evidence = node("div", undefined, "evidence-grid");
      for (const side of ["before", "after"]) {
        const section = node("section");
        section.append(node("h4", side.toUpperCase()), node("pre", finding[side] == null ? "Not present / no aligned cell" : JSON.stringify(finding[side], null, 2)));
        evidence.append(section);
      }
      const details = node("details");
      details.append(node("summary", "Complete finding evidence"), node("pre", JSON.stringify(finding, null, 2)));
      card.append(evidence, details);
      container.append(card);
    }
  }
  function renderResult(value) {
    result = value;
    const report = value.report;
    const category = categories.includes(report.verdict) ? report.verdict : "UNKNOWN";
    byId("overall-verdict").textContent = labels[category];
    byId("overall-verdict").className = "verdict " + category;
    byId("verdict-note").textContent = category === "EQUIVALENT" ? "Equivalent under the recorded policy and alignment assumptions." : category === "UNKNOWN" ? "Unresolved evidence remains. Review unknown findings before drawing a conclusion." : "Observed differences violate the chosen rules. Review each finding and its original evidence.";
    if (report.truncated) byId("verdict-note").textContent += " The report is truncated; it cannot establish equivalence.";
    byId("stats").replaceChildren();
    for (const name of categories) {
      const stat = node("div", undefined, "stat");
      stat.append(node("strong", String((report.summary || {})[name] || 0)), node("span", labels[name]));
      byId("stats").append(stat);
    }
    const metadata = {};
    for (const [key, item] of Object.entries(report)) if (key !== "findings") metadata[key] = item;
    byId("metadata").textContent = JSON.stringify(metadata, null, 2);
    byId("filter").value = "ALL";
    renderFindings();
    byId("results").hidden = false;
  }
  byId("filter").addEventListener("change", renderFindings);
  for (const format of ["json", "html", "csv"]) {
    byId("download-" + format).addEventListener("click", () => {
      if (!result) return;
      const content = format === "json" ? JSON.stringify(result.report, null, 2) + "\n" : result[format];
      const types = {json: "application/json;charset=utf-8", html: "text/html;charset=utf-8", csv: "text/csv;charset=utf-8"};
      const url = URL.createObjectURL(new Blob([content], {type: types[format]}));
      const link = node("a"); link.href = url; link.download = "importproof-report." + format; document.body.append(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  }
  byId("compare-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    try {
      if (!config) throw new Error("The local server is unavailable. Reload this page after starting ImportProof.");
      if (!files.before || !files.after) throw new Error("Choose both a before and an after file.");
      if (files.before.size > config.max_file_bytes || files.after.size > config.max_file_bytes) throw new Error("Each file must be 5 MiB or smaller.");
      const options = parsePolicy();
      invalidate(); busy = true;
      for (const field of byId("compare-form").elements) field.disabled = true;
      byId("compare-button").textContent = "Comparing…";
      status("Comparing locally and collecting original evidence…", "busy");
      const [before, after] = await Promise.all([readFile(files.before), readFile(files.after)]);
      const response = await fetch("/api/compare", {method: "POST", headers: {"Content-Type": "application/json", "X-ImportProof-Token": config.token}, body: JSON.stringify({before, after, options}), signal: AbortSignal.timeout(45000)});
      const value = await response.json();
      if (!response.ok) throw new Error(value.error || "Comparison failed.");
      renderResult(value);
      status("Comparison complete. Review the evidence below and download your report.");
      byId("results").scrollIntoView({behavior: "smooth", block: "start"});
    } catch (error) { status(error.name === "TimeoutError" ? "The local request timed out. Reduce input size and try again." : error.message, "error"); }
    finally { busy = false; for (const field of byId("compare-form").elements) field.disabled = false; byId("compare-button").textContent = "Compare files →"; }
  });
  fetch("/api/config", {cache: "no-store"}).then(async (response) => { if (!response.ok) throw new Error("Local server refused the session."); config = await response.json(); status("Choose a before and after file to begin."); }).catch((error) => status(error.message, "error"));
})();
