/* UI controller. No framework, no build step. */
(function () {
  "use strict";
  const $ = (sel) => document.querySelector(sel);
  const form = $("#search-form"), input = $("#q"), list = $("#result-list"),
    summary = $("#summary"), empty = $("#empty"), status = $("#status"),
    loading = $("#loading"), facets = $("#facets"), facetPanel = $("#facet-panel"),
    suggestion = $("#suggestion"), more = $("#more"), detail = $("#detail"),
    detailBody = $("#detail-body"), detailClose = $("#detail-close");
  let index = null, current = null, shown = 20, timer = null, searchSeq = 0;
  const PAGE = 20;

  const FIELD_LABEL = { t: "title", d: "department", x: "description", p: "prereq", phrase: "phrase" };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function marked(s) {
    return esc(s).replace(/&lt;mark&gt;/g, "<mark>").replace(/&lt;\/mark&gt;/g, "</mark>");
  }

  function setStatus(text) {
    const old = status.querySelector(".status-text");
    if (old) old.remove();
    if (text) {
      const p = document.createElement("p");
      p.className = "status-text";
      p.textContent = text;
      status.appendChild(p);
    }
  }

  function queryParams(overrides) {
    const p = new URLSearchParams();
    const q = overrides && "q" in overrides ? overrides.q : input.value.trim();
    if (q) p.set("q", q);
    if (overrides && overrides.dept) p.set("dept", overrides.dept);
    if (overrides && overrides.level) p.set("level", overrides.level);
    if (overrides && overrides.credits) p.set("credits", overrides.credits);
    return p;
  }

  function loadFromUrl() {
    const p = new URLSearchParams(location.search);
    const q = p.get("q") || "";
    if (q) {
      input.value = q;
      runSearch(q);
    }
  }

  function runSearch(q, append) {
    if (!index || !q) {
      current = null;
      renderEmpty();
      setStatus("");
      return;
    }
    const seq = ++searchSeq;
    loading.hidden = false;
    empty.hidden = true;
    more.hidden = true;
    if (!append) {
      list.innerHTML = "";
      shown = PAGE;
    }
    setStatus("Searching " + index.n.toLocaleString() + " course records...");
    const t0 = performance.now();
    let res;
    try {
      res = ACSSearch.search(index, q, 200, { explain: true });
    } catch (err) {
      loading.hidden = true;
      setStatus("Search failed: " + err.message);
      return;
    }
    if (seq !== searchSeq) return;
    const elapsed = performance.now() - t0;
    current = res;
    window.__lastLatency = elapsed;
    loading.hidden = true;
    suggestion.innerHTML = "";
    if (res.suggestion) {
      const div = document.createElement("p");
      div.className = "suggest";
      div.innerHTML = "Showing results for <strong>" + esc(res.suggestion) + "</strong> too.";
      const btn = document.createElement("button");
      btn.type = "button"; btn.className = "linkish"; btn.textContent = " use only the correction";
      btn.addEventListener("click", () => {
        let fixed = q;
        for (const [bad, good] of Object.entries(res.correctionMap)) {
          fixed = fixed.replace(new RegExp("\\b" + bad.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b", "gi"), good);
        }
        input.value = fixed; runSearch(fixed);
      });
      div.appendChild(btn);
      suggestion.appendChild(div);
    }
    summary.innerHTML = "<strong>" + res.total.toLocaleString() + "</strong> courses match. Ranked by BM25F in " + elapsed.toFixed(0) + " ms.";
    renderFacets(res.facets);
    facetPanel.hidden = false;
    list.innerHTML = "";
    renderPage(0);
    if (res.total === 0) {
      empty.hidden = false;
      more.hidden = true;
    } else if (res.total > PAGE) {
      more.hidden = false;
    }
    setStatus("");
    const p = new URLSearchParams();
    p.set("q", q);
    history.replaceState(null, "", "?" + p.toString());
  }

  function renderPage(start) {
    if (!current) return;
    const slice = current.results.slice(start, start + PAGE);
    for (const r of slice) list.appendChild(card(r));
    shown = Math.min(current.results.length, start + PAGE);
    if (shown >= current.results.length) more.hidden = true;
    else {
      more.hidden = false;
      more.textContent = "Show " + Math.min(PAGE, current.results.length - shown) + " more";
    }
  }

  function card(r) {
    const li = document.createElement("li");
    li.className = "card";
    const h2 = document.createElement("h2");
    const open = document.createElement("button");
    open.type = "button";
    open.textContent = r.code + " · " + r.title;
    open.addEventListener("click", () => showDetail(r));
    h2.appendChild(open);
    li.appendChild(h2);
    const meta = document.createElement("p");
    meta.className = "meta";
    meta.innerHTML = "<span>" + esc(r.department) + "</span>" +
      "<span class='pill'>" + esc(r.credits || "?") + " credits</span>" +
      "<span>" + esc(r.level) + "</span><span>" + esc(r.college) + "</span>";
    li.appendChild(meta);
    const snip = document.createElement("p");
    snip.innerHTML = marked(r.snippet || "No description text.");
    li.appendChild(snip);
    const foot = document.createElement("div");
    foot.className = "card-foot";
    const score = document.createElement("span");
    score.className = "score";
    score.textContent = "score " + r.score.toFixed(2);
    const whyBtn = document.createElement("button");
    whyBtn.type = "button"; whyBtn.className = "why-toggle"; whyBtn.textContent = "Why this rank?";
    whyBtn.setAttribute("aria-expanded", "false");
    const why = document.createElement("div");
    why.className = "why"; why.hidden = true;
    whyBtn.addEventListener("click", () => {
      why.hidden = !why.hidden;
      whyBtn.setAttribute("aria-expanded", String(!why.hidden));
      if (!why.hidden && !why.childElementCount) why.innerHTML = whyTable(r.why);
    });
    foot.appendChild(score); foot.appendChild(whyBtn); li.appendChild(foot); li.appendChild(why);
    return li;
  }

  function whyTable(why) {
    const entries = Object.entries(why || {});
    if (!entries.length) return "<p>No positive term matched. Ranking came from filters or a phrase.</p>";
    let html = "<table><thead><tr><th>Query piece</th><th>Field</th><th>TF</th><th>Weighted TF</th><th>Term score</th></tr></thead><tbody>";
    for (const [term, data] of entries) {
      const fields = data.fields || {};
      let first = true;
      for (const [f, v] of Object.entries(fields)) {
        const w = f === "phrase" ? 1 : Number(v.weight || 0);
        html += "<tr><td>" + esc(term) + "</td><td>" + esc(FIELD_LABEL[f] || f) + "</td><td>" +
          (f === "phrase" ? "yes" : esc(v.tf)) + "</td><td>" + (f === "phrase" ? "-" : (Number(v.tf) * w).toFixed(1)) +
          "</td><td class='num'>" + (first ? Number(data.contribution || 0).toFixed(2) : "") + "</td></tr>";
        first = false;
      }
    }
    html += "</tbody></table><p>Term score is the saturated BM25F score after the field TFs are weighted and summed. Field weights: title 3, department 2, description 1, prerequisite 0.5.</p>";
    return html;
  }

  function renderFacets(f) {
    facets.innerHTML = "";
    const groups = [["dept", "Department"], ["level", "Level"], ["credits", "Credits"], ["college", "College"]];
    for (const [key, label] of groups) {
      const entries = Object.entries(f[key] || {});
      if (!entries.length) continue;
      const wrap = document.createElement("div"); wrap.className = "facet-group";
      const h3 = document.createElement("h3"); h3.textContent = label; wrap.appendChild(h3);
      for (const [val, count] of entries) {
        const b = document.createElement("button");
        b.type = "button"; b.className = "facet";
        const shown = key === "dept" ? (index.docs.find(d => d[3] === val) || [])[4] || val : val;
        b.innerHTML = "<span>" + esc(shown) + "</span><span class='count'>" + count + "</span>";
        b.setAttribute("aria-label", "Filter " + label + " by " + shown + ", " + count + " results");
        b.addEventListener("click", () => toggleFacet(key, val));
        wrap.appendChild(b);
      }
      facets.appendChild(wrap);
    }
  }

  function toggleFacet(key, val) {
    if (val === "?") return;
    let q = input.value;
    let token;
    let re;
    if (key === "credits" && val.includes("to")) {
      const [lo, hi] = val.split("to");
      token = "credits:>=" + lo + " credits:<=" + hi;
      re = /(^|\s)credits:>=\d+ credits:<=\d+(?=\s|$)/i;
      if (re.test(q)) {
        q = q.replace(re, " ").trim();
      } else {
        q = (q + " " + token).trim();
      }
    } else {
      token = key + ":" + val;
      re = new RegExp("(^|\\s)" + key + ":" + val.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "(?=\\s|$)", "i");
      if (re.test(q)) q = q.replace(re, " ").trim();
      else q = (q + " " + token).trim();
    }
    input.value = q;
    runSearch(q);
  }

  function showDetail(r) {
    detail.hidden = false;
    document.body.style.overflow = "hidden";
    const why = whyTable(r.why);
    detailBody.innerHTML =
      "<p class='eyebrow'>" + esc(r.code) + " · " + esc(r.credits || "?") + " credits · " + esc(r.level) + "</p>" +
      "<h2>" + esc(r.title) + "</h2>" +
      "<p class='meta'>" + esc(r.department) + ", " + esc(r.college) + "</p>" +
      "<p class='desc'>" + esc(r.snippet ? r.snippet.replace(/<\/?mark>/g, "") : "") + "</p>" +
      "<h3>Full catalog description</h3><p class='desc'>" + esc(index.text[findDoc(r)][0]) + "</p>" +
      "<h3>Prerequisites</h3><p>" + esc(index.text[findDoc(r)][1] || "None listed") + "</p>" +
      "<h3>Why this ranked here</h3><div class='why'>" + why + "</div>" +
      "<p><a href='" + esc(r.url) + "' target='_blank' rel='noopener'>Open the department page in the catalog</a></p>";
    detailClose.focus();
  }

  function findDoc(r) {
    return index.docs.findIndex(d => d[0] === r.id);
  }

  function closeDetail() {
    detail.hidden = true;
    document.body.style.overflow = "";
  }

  function renderEmpty() {
    list.innerHTML = ""; summary.textContent = ""; empty.hidden = false;
    facetPanel.hidden = true; more.hidden = true; suggestion.innerHTML = "";
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (q) runSearch(q);
  });
  input.addEventListener("input", () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (!q) { renderEmpty(); history.replaceState(null, "", location.pathname); return; }
    timer = setTimeout(() => runSearch(q), 220);
  });
  more.addEventListener("click", () => renderPage(shown));
  detailClose.addEventListener("click", closeDetail);
  $("#clear-facets").addEventListener("click", () => {
    const q = input.value.replace(/\b(?:dept|level|credits):\S+/gi, "").replace(/\s+/g, " ").trim();
    input.value = q; runSearch(q);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !detail.hidden) closeDetail();
    if (e.key === "/" && document.activeElement !== input) { e.preventDefault(); input.focus(); }
  });

  async function boot() {
    setStatus("Loading the search index (about 2 MB compressed)...");
    loading.hidden = false;
    try {
      index = await ACSSearch.loadIndex("data/index.json.gz");
      loading.hidden = true;
      setStatus("Ready. " + index.n.toLocaleString() + " courses indexed.");
      input.value = new URLSearchParams(location.search).get("q") || "";
      if (input.value.trim()) runSearch(input.value.trim());
      else renderEmpty();
      window.__ready = true;
      window.__readyMs = performance.now();
    } catch (err) {
      loading.hidden = true;
      setStatus("Could not load the index: " + err.message + ". Serve the folder over HTTP, not file://.");
    }
  }
  boot();
})();
