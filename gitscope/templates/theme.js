(() => {
  const storageKey = "gitscope-theme";
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  let storedTheme = null;

  try {
    storedTheme = window.localStorage.getItem(storageKey);
  } catch (_error) {
    storedTheme = null;
  }

  const initialTheme = storedTheme === "light" || storedTheme === "dark"
    ? storedTheme
    : systemDark ? "dark" : "light";
  document.documentElement.dataset.theme = initialTheme;

  const chartPalette = {
    light: { ink: "#172033", grid: "rgba(127, 127, 127, 0.22)" },
    dark: { ink: "#dfe8f4", grid: "rgba(169, 181, 199, 0.22)" },
  };

  function updateCharts(theme) {
    if (!window.Plotly) return;
    const palette = chartPalette[theme];
    document.querySelectorAll(".plotly-graph-div").forEach((chart) => {
      const update = {
        "font.color": palette.ink,
        "title.font.color": palette.ink,
        "legend.font.color": palette.ink,
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
      };
      const layout = chart._fullLayout || {};
      Object.keys(layout)
        .filter((key) => /^xaxis\d*$|^yaxis\d*$/.test(key))
        .forEach((axis) => {
          update[`${axis}.color`] = palette.ink;
          update[`${axis}.gridcolor`] = palette.grid;
          update[`${axis}.zerolinecolor`] = palette.grid;
          update[`${axis}.title.font.color`] = palette.ink;
          update[`${axis}.tickfont.color`] = palette.ink;
        });
      (layout.annotations || []).forEach((_annotation, index) => {
        update[`annotations[${index}].font.color`] = palette.ink;
      });
      window.Plotly.relayout(chart, update);
    });
  }

  function applyTheme(theme, persist) {
    document.documentElement.dataset.theme = theme;
    const toggle = document.getElementById("theme-toggle");
    if (toggle) toggle.setAttribute("aria-checked", String(theme === "dark"));
    updateCharts(theme);
    if (persist) {
      try {
        window.localStorage.setItem(storageKey, theme);
      } catch (_error) {
        // The dashboard still works when browser storage is unavailable.
      }
    }
  }

  window.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("theme-toggle");
    applyTheme(initialTheme, false);
    toggle?.addEventListener("click", () => {
      const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      applyTheme(nextTheme, true);
    });
  });
  window.addEventListener("beforeprint", () => updateCharts("light"));
  window.addEventListener("afterprint", () => {
    updateCharts(document.documentElement.dataset.theme || "light");
  });
})();
