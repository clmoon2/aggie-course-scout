/* Conservative Porter stemmer. Mirrors src/text.py exactly. */
(function (global) {
  const VOWELS = new Set(["a", "e", "i", "o", "u"]);

  function cons(w, i) {
    const ch = w[i];
    if (VOWELS.has(ch)) return false;
    if (ch === "y") return i === 0 || !cons(w, i - 1);
    return true;
  }
  function measure(stem) {
    let m = 0, prevV = false;
    for (let i = 0; i < stem.length; i++) {
      const c = cons(stem, i);
      if (c && prevV) m++;
      prevV = !c;
    }
    return m;
  }
  function hasVowel(stem) {
    for (let i = 0; i < stem.length; i++) if (!cons(stem, i)) return true;
    return false;
  }
  function cvc(w) {
    if (w.length < 3) return false;
    return !cons(w, w.length - 1) && cons(w, w.length - 2) &&
      !cons(w, w.length - 3) && !"wxy".includes(w[w.length - 1]);
  }
  const STEP2 = [["ational","ate"],["tional","tion"],["enci","ence"],["anci","ance"],
    ["izer","ize"],["bli","ble"],["alli","al"],["entli","ent"],["eli","e"],
    ["ousli","ous"],["ization","ize"],["ation","ate"],["ator","ate"],["alism","al"],
    ["iveness","ive"],["fulness","ful"],["ousness","ous"],["aliti","al"],
    ["iviti","ive"],["biliti","ble"],["logi","log"]];
  const STEP3 = [["icate","ic"],["ative",""],["alize","al"],["iciti","ic"],
    ["ical","ic"],["ful",""],["ness",""]];
  const STEP4 = ["al","ance","ence","er","ic","able","ible","ant","ement","ment",
    "ent","ion","ou","ism","ate","iti","ous","ive","ize"];

  function stem(word) {
    if (word.length <= 3 || !/^[a-z]+$/.test(word)) return word;
    let w = word;
    if (w.endsWith("sses")) w = w.slice(0, -2);
    else if (w.endsWith("ies")) w = w.slice(0, -2);
    else if (w.endsWith("ss")) { /* keep */ }
    else if (w.endsWith("s") && w.length > 3) w = w.slice(0, -1);
    if (w.endsWith("eed")) { if (measure(w.slice(0, -3)) > 0) w = w.slice(0, -1); }
    else if (w.endsWith("ed") && hasVowel(w.slice(0, -2))) {
      w = w.slice(0, -2);
      if (w.endsWith("at") || w.endsWith("bl") || w.endsWith("iz")) w += "e";
      else if (w.length > 1 && w[w.length-1] === w[w.length-2] && !"lsz".includes(w[w.length-1])) w = w.slice(0, -1);
      else if (measure(w) === 1 && cvc(w)) w += "e";
    } else if (w.endsWith("ing") && hasVowel(w.slice(0, -3))) {
      w = w.slice(0, -3);
      if (w.endsWith("at") || w.endsWith("bl") || w.endsWith("iz")) w += "e";
      else if (w.length > 1 && w[w.length-1] === w[w.length-2] && !"lsz".includes(w[w.length-1])) w = w.slice(0, -1);
      else if (measure(w) === 1 && cvc(w)) w += "e";
    }
    if (w.endsWith("y") && hasVowel(w.slice(0, -1))) w = w.slice(0, -1) + "i";
    if (w.length > 4) {
      for (const [suf, rep] of STEP2) {
        if (w.endsWith(suf) && measure(w.slice(0, -suf.length)) > 0) { w = w.slice(0, -suf.length) + rep; break; }
      }
    }
    if (w.length > 4) {
      for (const [suf, rep] of STEP3) {
        if (w.endsWith(suf) && measure(w.slice(0, -suf.length)) > 0) { w = w.slice(0, -suf.length) + rep; break; }
      }
    }
    if (w.length > 5) {
      for (const suf of STEP4) {
        if (w.endsWith(suf)) {
          const base = w.slice(0, -suf.length);
          if (measure(base) > 1 && (suf !== "ion" || base.endsWith("s") || base.endsWith("t"))) w = base;
          break;
        }
      }
    }
    if (w.endsWith("e")) {
      const base = w.slice(0, -1), m = measure(base);
      if (m > 1 || (m === 1 && !cvc(base))) w = base;
    }
    if (w.endsWith("ll") && measure(w) > 1) w = w.slice(0, -1);
    return w;
  }

  const STOPWORDS = new Set(`a about above after again against all also am an and any are as at be because been
before being below between both but by can could did do does doing down during each few for from further had has have having he her here hers herself him himself his how
i if in into is it its itself just me more most my myself no nor not now of off on once only or other our ours ourselves out over own same she should so some such than that the
their theirs them themselves then there these they this those through to too under until up very was we were what when where which while who whom why will with would you your
yours yourself yourselves`.split(/\s+/));

  function tokenize(text) {
    return (text.toLowerCase().match(/[a-z0-9]+/g) || []);
  }
  function normalizeTokens(text) {
    const out = [];
    for (const token of tokenize(text)) {
      if (STOPWORDS.has(token)) continue;
      const s = stem(token);
      if (s && !STOPWORDS.has(s)) out.push(s);
    }
    return out;
  }
  global.ACSStem = { stem, tokenize, normalizeTokens, STOPWORDS };
})(window);
