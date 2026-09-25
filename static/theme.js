const toggleBtn = document.getElementById("theme-toggle");

const THEMES = {
  dark: {
    className: "dark-mode",
    icon: "🌙"
  },
  light: {
    className: "light-mode",
    icon: "🌞"
  }
};

function applyTheme(mode) {
  const isLight = mode === "light";

  document.body.classList.toggle("light-mode", isLight);
  document.body.classList.toggle("dark-mode", !isLight);

  // Smooth transition for theme switch
  document.body.classList.add("theme-transition");
  setTimeout(() => {
    document.body.classList.remove("theme-transition");
  }, 300);

  localStorage.setItem("theme", mode);

  if (toggleBtn) {
    toggleBtn.textContent = THEMES[mode].icon;
  }

  // Optional: update meta theme-color for mobile browsers
  const metaTheme = document.querySelector("meta[name='theme-color']");
  if (metaTheme) {
    metaTheme.setAttribute(
      "content",
      isLight ? "#ff6a00" : "#0f0f0f"
    );
  }
}

function initTheme() {
  const savedTheme = localStorage.getItem("theme") || "dark";
  applyTheme(savedTheme);
}

if (toggleBtn) {
  toggleBtn.addEventListener("click", () => {
    const isLight = document.body.classList.contains("light-mode");
    applyTheme(isLight ? "dark" : "light");
  });
}

// Init on load
initTheme();
