$(document).ready(async function () {
  const DATA_URL = "data/tickertrends_daily_20251029_233830.json";

  // Set your preferred default category here (exact string match),
  // or pass via URL: ?category=Sports
  const DEFAULT_CATEGORY = null;

  const params = new URLSearchParams(window.location.search);
  const categoryFromUrl = params.get("category");

  try {
    const resp = await fetch(DATA_URL, { cache: "no-store" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const raw = await resp.json();

    // Collect unique categories and sort
    const categories = [...new Set(raw.map(r => r.category).filter(Boolean))].sort();

    // Populate the select WITHOUT "All"
    const $sel = $("#categoryFilter");
    categories.forEach(c => $sel.append(`<option value="${c}">${c}</option>`));

    // Prepare table rows (Category is hidden column 0)
    const rows = raw.map(r => {
      const growthNum = Number((r.value ?? "").toString().replace(/,/g, ""));
      const pctNum = Number((r.ticker_percent ?? "").toString().replace(/%/g, "")) || 0;
      return {
        category: r.category || "",
        keyword: r.name || "",
        growth_display: r.raw_growth || "",
        growth_sort: Number.isFinite(growthNum) ? growthNum : 0,
        ticker_symbol: r.ticker_symbol || "",
        ticker_pct_num: pctNum
      };
    });

    const table = $('#trendsTable').DataTable({
      data: rows,
      columns: [
        { data: 'category', title: "Category", visible: false }, // 0 (hidden)
        { data: 'keyword',  title: "Keyword" },                  // 1
        {
          data: 'growth_display', title: "Growth",               // 2
          render: (d, type, row) => {
            if (type === 'sort' || type === 'type') return row.growth_sort;
            const n = row.growth_sort || 0;
            const cls = n >= 50 ? 'bg-success' : n >= 20 ? 'bg-warning' : 'bg-secondary';
            return `<span class="badge ${cls}">${d ?? ''}</span>`;
          }
        },
        { data: 'ticker_symbol', title: "Ticker" },              // 3
        {
          data: 'ticker_pct_num', title: "Ticker %",
          render: (d, type) => (type === 'sort' || type === 'type') ? d : `${d}%`
        }                                                        // 4
      ],
      order: [[2, 'desc']],   // sort by Growth numeric
      pageLength: 25,
      responsive: { details: { type: 'inline' } },
      columnDefs: [
        { responsivePriority: 1, targets: 1 },
        { responsivePriority: 2, targets: 2 }
      ],
      dom:
        "<'row'<'col-md-6'B><'col-md-6'f>>" +
        "<'row'<'col-12'tr>>" +
        "<'row'<'col-md-5'i><'col-md-7'p>>",
      buttons: [{ extend: 'csvHtml5', title: 'tiktok_viral_keywords' }]
    });

    // Choose initial category (URL param > DEFAULT_CATEGORY > first in list)
    let initial = categoryFromUrl || DEFAULT_CATEGORY || categories[0] || "";
    if (initial && categories.includes(initial)) {
      $sel.val(initial);
      table.column(0).search(initial).draw();
    }

    // Enforce always-one-category filter (no "All")
    $sel.on('change', function () {
      const val = this.value; // always a real category
      table.column(0).search(val).draw();
    });

  } catch (e) {
    console.error("Error loading JSON:", e);
    $('body').append(`<p class="text-danger text-center mt-3">Failed to load data.</p>`);
  }
});
