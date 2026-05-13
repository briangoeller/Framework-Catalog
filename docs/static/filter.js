// Framework Catalog — index filter
// Pure DOM, no framework. Reads data-* attributes on .entry-card elements.

(function () {
  const els = {
    search: document.getElementById("search"),
    discipline: document.getElementById("filter-discipline"),
    type: document.getElementById("filter-type"),
    band: document.getElementById("filter-band"),
    origConf: document.getElementById("filter-orig-conf"),
    yearConf: document.getElementById("filter-year-conf"),
    srcConf: document.getElementById("filter-src-conf"),
    verifyRadios: document.querySelectorAll('input[name="verify"]'),
    count: document.getElementById("result-count"),
  };
  // If we're not on the index page (no filters), do nothing.
  if (!els.search) return;

  const cards = Array.from(document.querySelectorAll(".entry-card"));

  // Confidence ordering for "at least" comparisons
  const confRank = { high: 3, medium: 2, low: 1, "": 0 };

  function confMatches(filterValue, cardValue) {
    if (!filterValue) return true;
    return (confRank[cardValue] || 0) >= (confRank[filterValue] || 0);
  }

  function getVerify() {
    for (const r of els.verifyRadios) {
      if (r.checked) return r.value;
    }
    return "";
  }

  function apply() {
    const q = els.search.value.trim().toLowerCase();
    const d = els.discipline.value;
    const t = els.type.value;
    const b = els.band.value;
    const oc = els.origConf.value;
    const yc = els.yearConf.value;
    const sc = els.srcConf.value;
    const v = getVerify();

    let visible = 0;
    for (const card of cards) {
      const matches =
        (!q || card.dataset.search.includes(q)) &&
        (!d || card.dataset.discipline === d) &&
        (!t || card.dataset.type === t) &&
        (!b || card.dataset.band === b) &&
        confMatches(oc, card.dataset.origConf) &&
        confMatches(yc, card.dataset.yearConf) &&
        confMatches(sc, card.dataset.srcConf) &&
        (!v || card.dataset.needsVerify === v);

      if (matches) {
        card.classList.remove("hidden");
        visible++;
      } else {
        card.classList.add("hidden");
      }
    }
    if (els.count) els.count.textContent = visible;
  }

  // Wire up listeners
  ["search", "discipline", "type", "band", "origConf", "yearConf", "srcConf"].forEach(
    (k) => {
      if (els[k]) els[k].addEventListener("input", apply);
      if (els[k]) els[k].addEventListener("change", apply);
    }
  );
  els.verifyRadios.forEach((r) => r.addEventListener("change", apply));

  // Initial pass
  apply();
})();
