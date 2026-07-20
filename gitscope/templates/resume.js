(() => {
  const storageKey = "gitscope-theme";
  let storedTheme = null;
  try {
    storedTheme = window.localStorage.getItem(storageKey);
  } catch (_error) {
    storedTheme = null;
  }
  const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
  const initialTheme = storedTheme === "dark" || storedTheme === "light"
    ? storedTheme
    : systemTheme;
  document.documentElement.dataset.theme = initialTheme;

  function applyTheme(theme, persist) {
    document.documentElement.dataset.theme = theme;
    const toggle = document.getElementById("resume-theme-toggle");
    toggle?.setAttribute("aria-checked", String(theme === "dark"));
    if (persist) {
      try {
        window.localStorage.setItem(storageKey, theme);
      } catch (_error) {
        // Theme switching remains available when storage is blocked.
      }
    }
  }

  window.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("resume-theme-toggle");
    applyTheme(initialTheme, false);
    toggle?.addEventListener("click", () => {
      const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      applyTheme(nextTheme, true);
    });
    document.getElementById("resume-print")?.addEventListener("click", () => window.print());
  });
})();
