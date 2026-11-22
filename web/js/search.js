/* Browser query layer. Mirrors src/query.py: BM25F, phrases, filters, synonyms,
   edit-distance suggestions, facets, snippets, and term contribution details. */
(function (global) {
  const S = global.ACSStem;
  const SYNONYMS = {
    ml: [["machine","learning"]], ai: [["artificial","intelligence"]],
    db: [["database"],["databases"]], dbs: [["database"]],
    os: [["operating","system"],["operating","systems"]],
    sec: [["security"]], security: [["cybersecurity"],["cyber","security"]],
    stats: [["statistics"],["statistical"]], stat: [["statistics"]],
    hci: [["human","computer","interaction"]], net: [["network"],["networking"]],
    networks: [["networking"]], nlp: [["natural","language","processing"]],
    cv: [["computer","vision"]], se: [["software","engineering"]],
    oop: [["object","oriented","programming"]], ds: [["data","structures"]],
    algos: [["algorithms"]], math: [["mathematics"]], bio: [["biology"]],
    chem: [["chemistry"]], econ: [["economics"]], psych: [["psychology"]],
    swe: [["software","engineering"]]
  };
  const FILTER_RE = /^(-?)(dept|level|credits|college):(.+)$/i;
  const CREDIT_RE = /^(>=|<=|>|<)?(\d+)$/;

  function loadIndex(url) {
    return fetch(url).then(r => {
      if (!r.ok) throw new Error("Index request failed: HTTP " + r.status);
      return r.blob();
    }).then(async blob => {
      if (blob.stream && typeof DecompressionStream !== "undefined") {
        const ds = new DecompressionStream("gzip");
        const stream = blob.stream().pipeThrough(ds);
        return new Response(stream).json();
      }
      // Fallback for browsers without DecompressionStream.
      const buf = await blob.arrayBuffer();
      const bytes = new Uint8Array(buf);
      if (bytes[0] === 0x1f && bytes[1] === 0x8b) throw new Error("This browser cannot gunzip the index.");
      return JSON.parse(new TextDecoder().decode(bytes));
    }).then(idx => {
      const vocab = new Set();
      for (const [desc, prereq, title] of idx.text) {
        for (const t of S.tokenize(title + " " + desc + " " + prereq)) {
          if (!S.STOPWORDS.has(t) && t.length > 2) vocab.add(t);
        }
      }
      for (const t of Object.keys(idx.terms)) vocab.add(t);
      idx._vocab = [...vocab].sort();
      return idx;
    });
  }

  function editDistance(a, b, cap) {
    if (Math.abs(a.length - b.length) > cap) return cap + 1;
    let prev2 = null;
    let prev = Array.from({length: b.length + 1}, (_, i) => i);
    for (let i = 1; i <= a.length; i++) {
      const cur = [i]; let rowMin = i;
      for (let j = 1; j <= b.length; j++) {
        const cost = a[i-1] === b[j-1] ? 0 : 1;
        let val = Math.min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + cost);
        if (i > 1 && j > 1 && a[i-1] === b[j-2] && a[i-2] === b[j-1]) val = Math.min(val, prev2[j-2] + 1);
        cur[j] = val;
        rowMin = Math.min(rowMin, val);
      }
      if (rowMin > cap) return cap + 1;
      prev2 = prev; prev = cur;
    }
    return prev[b.length];
  }
  function suggest(term, vocab, limit = 3) {
    const cap = term.length <= 7 ? 1 : 2;
    const scored = [];
    for (const word of vocab) {
      if (Math.abs(word.length - term.length) > cap) continue;
      const d = editDistance(term, word, cap);
      if (d <= cap && word !== term) {
        const penalty = word[0] === term[0] ? 0 : 0.4;
        scored.push([d + penalty, -word.length, word]);
      }
    }
    scored.sort((a,b) => a[0]-b[0] || a[1]-b[1]);
    return scored.slice(0, limit).map(x => x[2]);
  }

  function parseQuery(raw, index) {
    const q = {raw, terms: [], phrases: [], negTerms: [], negPhrases: [],
      depts: [], negDepts: [], colleges: [], negColleges: [], levels: [], negLevels: [],
      credits: null, creditBucket: null, synonyms: {}, corrections: {}, unknown: []};
    const pieces = raw.match(/-?"[^"]+"|\S+/g) || [];
    for (const piece of pieces) {
      const neg = piece.startsWith("-");
      const body = neg ? piece.slice(1) : piece;
      if (body.startsWith('"') && body.endsWith('"') && body.length >= 2) {
        const toks = S.normalizeTokens(body.slice(1, -1));
        if (toks.length) (neg ? q.negPhrases : q.phrases).push(toks);
        continue;
      }
      const fm = body.match(FILTER_RE);
      if (fm) {
        const val = fm[3].trim().toLowerCase();
        if (fm[2].toLowerCase() === "dept") (neg ? q.negDepts : q.depts).push(val.toUpperCase());
        else if (fm[2].toLowerCase() === "college") (neg ? q.negColleges : q.colleges).push(val.toLowerCase());
        else if (fm[2].toLowerCase() === "level") {
          if (["undergraduate","undergrad","ug"].includes(val)) (neg ? q.negLevels : q.levels).push("undergraduate");
          if (["graduate","grad"].includes(val)) (neg ? q.negLevels : q.levels).push("graduate");
        } else {
          if (CREDIT_BUCKETS.includes(val)) q.creditBucket = val;
          else {
            const cm = val.match(CREDIT_RE);
            if (cm) q.credits = [cm[1] || "=", parseInt(cm[2], 10)];
          }
        }
        continue;
      }
      const toks = S.normalizeTokens(body);
      if (!toks.length) continue;
      if (neg) q.negTerms.push(...toks); else q.terms.push(...toks);
    }
    q.unknown = q.terms.filter(t => !index.terms[t]);
    const pairs = [];
    for (const rawTok of S.tokenize(raw)) {
      if (S.STOPWORDS.has(rawTok) || rawTok.length <= 1) continue;
      pairs.push([S.stem(rawTok), rawTok]);
    }
    for (const term of q.unknown) {
      if (term.length < 4) continue;
      const rawTerm = (pairs.find(p => p[0] === term) || [term, term])[1];
      const s = suggest(rawTerm, index._vocab);
      if (s.length) q.corrections[term] = s[0];
    }
    for (const term of q.terms.slice()) {
      for (const phrase of (SYNONYMS[term] || [])) {
        (q.synonyms[term] = q.synonyms[term] || []).push(phrase);
      }
    }
    return q;
  }

  const CREDIT_BUCKETS = ["0", "1-2", "3", "4", "5+"];
  function creditBounds(credits) {
    const nums = (String(credits || "").match(/\d+(?:\.\d+)?/g) || []).map(Number).sort((a,b) => a-b);
    return nums.length ? [nums[0], nums[nums.length - 1]] : [0, 0];
  }
  function creditBucket(credits) {
    const [lo, hi] = creditBounds(credits);
    if (lo <= 0 && hi >= 0) return "0";
    if (lo <= 2 && hi >= 1) return "1-2";
    if (lo <= 3 && hi >= 3) return "3";
    if (lo <= 4 && hi >= 4) return "4";
    if (hi >= 5) return "5+";
    return "?";
  }
  function docMatchesFilters(doc, q) {
    const dept = doc[3], level = doc[6], credits = String(doc[7] || "", 10);
    const college = doc[9] || "";
    const [lo, hi] = doc.length > 11 ? [doc[10], doc[11]] : creditBounds(credits);
    if (q.depts.length && !q.depts.includes(dept)) return false;
    if (q.negDepts.length && q.negDepts.includes(dept)) return false;
    if (q.colleges.length && !q.colleges.includes(college)) return false;
    if (q.negColleges.length && q.negColleges.includes(college)) return false;
    if (q.levels.length && !q.levels.includes(level)) return false;
    if (q.negLevels.length && q.negLevels.includes(level)) return false;
    if (q.creditBucket && creditBucket(credits) !== q.creditBucket) return false;
    if (q.credits) {
      const [op, val] = q.credits;
      if (op === ">=" && hi < val) return false;
      if (op === "<=" && lo > val) return false;
      if (op === ">" && hi <= val) return false;
      if (op === "<" && lo >= val) return false;
      if (op === "=" && !(lo <= val && val <= hi)) return false;
    }
    return true;
  }

  const phraseCache = new Map();
  function phraseDocs(index, phrase) {
    const key = phrase.join(" ");
    if (phraseCache.has(key)) return phraseCache.get(key);
    const hits = new Set();
    for (let did = 0; did < index.n; did++) {
      const fields = index.text[did];
      let found = false;
      for (const fieldText of fields) {
        const toks = S.normalizeTokens(fieldText);
        outer: for (let i = 0; i <= toks.length - phrase.length; i++) {
          for (let j = 0; j < phrase.length; j++) if (toks[i+j] !== phrase[j]) continue outer;
          found = true; break;
        }
        if (found) break;
      }
      if (found) hits.add(did);
    }
    phraseCache.set(key, hits);
    return hits;
  }

  function snippet(desc, terms, width = 26) {
    const words = desc.split(/\s+/);
    if (!words.length) return "";
    let best = 0, bestHits = -1;
    for (let i = 0; i < words.length; i += 5) {
      let hits = 0;
      for (const w of words.slice(i, i + width)) {
        if (S.normalizeTokens(w).some(t => terms.has(t))) hits++;
      }
      if (hits > bestHits) { bestHits = hits; best = i; }
    }
    const start = Math.max(0, best - 3), end = Math.min(words.length, start + width);
    let out = words.slice(start, end).join(" ");
    if (start > 0) out = "..." + out;
    if (end < words.length) out += "...";
    for (const term of [...terms].sort((a,b) => b.length - a.length)) {
      out = out.replace(new RegExp("\\b(" + term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\w*)", "gi"), "<mark>$1</mark>");
    }
    return out;
  }

  function search(index, raw, limit = 10, opts = {}) {
    const q = parseQuery(raw, index);
    const weights = opts.weights || index.weights;
    const n = index.n;
    const scores = new Map(), why = new Map(), matched = new Map();
    const synonymPhrases = [];
    for (const vals of Object.values(q.synonyms)) for (const ph of vals) if (ph.length > 1) synonymPhrases.push(ph);

    function addTerm(term, qweight, label) {
      if (!(term in index.terms)) {
        const toks = S.normalizeTokens(term);
        if (!toks.length) return;
        term = toks[0];
      }
      const post = index.terms[term];
      if (!post) return;
      const dfset = new Set();
      for (const short of Object.keys(weights)) for (const [did] of (post[short] || [])) dfset.add(did);
      const df = Math.max(dfset.size, 1);
      const idf = Math.log(1 + (n - df + 0.5) / (df + 0.5));
      const contribs = new Map();
      for (const short of Object.keys(weights)) {
        const w = weights[short];
        if (!w) continue;
        const avg = index.avglen[short] || 1;
        for (const [did, tf] of (post[short] || [])) {
          const dl = index.doclen[short][did];
          const norm = tf / (1 - index.b + index.b * dl / avg);
          const c = contribs.get(did) || {norm: 0, fields: {}};
          c.norm += w * norm;
          c.fields[short] = {tf, weight: w};
          contribs.set(did, c);
        }
      }
      for (const [did, c] of contribs) {
        const inc = qweight * idf * c.norm * (index.k1 + 1) / (index.k1 + c.norm);
        scores.set(did, (scores.get(did) || 0) + inc);
        if (!matched.has(did)) matched.set(did, new Set());
        matched.get(did).add(term);
        if (opts.explain !== false) {
          if (!why.has(did)) why.set(did, {});
          const e = why.get(did)[label] || (why.get(did)[label] = {});
          e.idf = Math.round(idf * 1000) / 1000;
          e.fields = c.fields;
          e.contribution = Math.round(((e.contribution || 0) + inc) * 100) / 100;
        }
      }
    }

    if (!q.terms.length && !q.phrases.length) {
      for (let did = 0; did < n; did++) scores.set(did, 1);
    }
    for (const term of q.terms) {
      addTerm(term, term.length <= 3 ? 0.5 : 1, term);
      if (q.corrections[term]) addTerm(q.corrections[term], 0.55, "~" + q.corrections[term]);
      for (const phrase of (q.synonyms[term] || [])) {
        if (phrase.length === 1) addTerm(phrase[0], 0.55, term + "~" + phrase[0]);
        else for (const t of S.normalizeTokens(phrase.join(" "))) addTerm(t, 0.5, term + "~" + phrase.join(" "));
      }
    }
    for (const phrase of q.phrases.concat(synonymPhrases)) {
      const ph = phrase.filter(Boolean);
      if (ph.length < 2) continue;
      const hits = phraseDocs(index, ph);
      if (!hits.size) continue;
      const idf = Math.log(1 + (n - hits.size + 0.5) / (hits.size + 0.5));
      for (const did of hits) {
        let inc = 2.5 + idf;
        const titleToks = S.normalizeTokens(index.text[did][2]);
        let inTitle = false;
        outer: for (let i = 0; i <= titleToks.length - ph.length; i++) {
          for (let j = 0; j < ph.length; j++) if (titleToks[i+j] !== ph[j]) continue outer;
          inTitle = true; break;
        }
        if (inTitle) inc += 2;
        scores.set(did, (scores.get(did) || 0) + inc);
        if (!matched.has(did)) matched.set(did, new Set());
        for (const t of ph) matched.get(did).add(t);
        if (opts.explain !== false) {
          if (!why.has(did)) why.set(did, {});
          const key = '"' + ph.join(" ") + '"';
          why.get(did)[key] = {idf: Math.round(idf * 1000) / 1000,
            fields: {phrase: {tf: 1, weight: 2.5}}, title_bonus: inTitle,
            contribution: Math.round(inc * 100) / 100};
        }
      }
    }

    const banned = new Set();
    for (const term of q.negTerms) {
      const post = index.terms[term];
      if (post) for (const [did] of (post.x || [])) banned.add(did);
    }
    for (const phrase of q.negPhrases) for (const did of phraseDocs(index, phrase)) banned.add(did);

    const ranked = [];
    for (const [did, score] of scores) {
      if (banned.has(did)) continue;
      const doc = index.docs[did];
      if (!docMatchesFilters(doc, q)) continue;
      ranked.push([score, did]);
    }
    ranked.sort((a,b) => b[0] - a[0] || a[1] - b[1]);
    const facets = {dept: {}, level: {}, college: {}, credits: {}};
    for (const [, did] of ranked) {
      const d = index.docs[did];
      for (const [key, val] of [["dept", d[3]], ["level", d[6]], ["college", d[9] || "other"], ["credits", creditBucket(d[7])]]) {
        facets[key][val] = (facets[key][val] || 0) + 1;
      }
    }
    for (const key of Object.keys(facets)) {
      facets[key] = Object.fromEntries(Object.entries(facets[key]).sort((a,b) => b[1]-a[1]).slice(0, 12));
    }
    const results = ranked.slice(0, limit).map(([score, did]) => {
      const d = index.docs[did];
      return {id: d[0], code: d[1], title: index.text[did][2], dept: d[3],
        department: d[4], college: d[5], collegeSlug: d[9], level: d[6], credits: d[7], url: d[8],
        score: Math.round(score * 1000) / 1000,
        snippet: snippet(index.text[did][0], matched.get(did) || new Set()),
        why: (why.get(did) || {})};
    });
    return {query: raw, total: ranked.length, suggestion: Object.values(q.corrections)[0] || null,
      correctionMap: q.corrections, synonyms: Object.fromEntries(Object.entries(q.synonyms).map(([k,v]) => [k, v.map(x => x.join(" "))])),
      results, facets, parsed: q};
  }

  global.ACSSearch = { loadIndex, search, parseQuery, suggest };
})(window);
