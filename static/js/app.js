async function loadTranslations(language) {
    try {
        const response = await fetch(`/static/translations/${language}.json`);
        if (!response.ok) {
            throw new Error(`Could not load ${language}.json`);
        }
        return await response.json();
    } catch (error) {
        console.error("Translation load error:", error);
        return {};
    }
}

function applyTranslations(translations) {
    document.querySelectorAll("[data-i18n]").forEach((element) => {
        const key = element.getAttribute("data-i18n");
        if (translations[key]) {
            element.textContent = translations[key];
        }
    });

    document.querySelectorAll("option[data-i18n]").forEach((option) => {
        const key = option.getAttribute("data-i18n");
        if (translations[key]) {
            option.textContent = translations[key];
        }
    });

    document.querySelectorAll("[data-dynamic-i18n]").forEach((element) => {
        const key = element.getAttribute("data-dynamic-i18n");
        if (translations[key]) {
            element.textContent = translations[key];
        }
    });
}

function syncHiddenLanguageField(language) {
    const hiddenInput = document.getElementById("language_selected");
    if (hiddenInput) {
        hiddenInput.value = language;
    }
}

async function setLanguage(language) {
    localStorage.setItem("tb_language", language);

    const translations = await loadTranslations(language);
    applyTranslations(translations);

    const languageSelect = document.getElementById("language");
    if (languageSelect) {
        languageSelect.value = language;
    }

    syncHiddenLanguageField(language);
}

function setupSidebar() {
    const toggle = document.getElementById("menuToggle");
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("mobileOverlay");

    if (!toggle || !sidebar || !overlay) return;

    toggle.addEventListener("click", () => {
        sidebar.classList.toggle("mobile-open");
        overlay.classList.toggle("show");
    });

    overlay.addEventListener("click", () => {
        sidebar.classList.remove("mobile-open");
        overlay.classList.remove("show");
    });

    document.querySelectorAll(".sidebar-link").forEach((link) => {
        link.addEventListener("click", () => {
            sidebar.classList.remove("mobile-open");
            overlay.classList.remove("show");
        });
    });
}

document.addEventListener("DOMContentLoaded", async () => {
    const savedLanguage = localStorage.getItem("tb_language") || "en";
    await setLanguage(savedLanguage);

    const languageSelect = document.getElementById("language");
    if (languageSelect) {
        languageSelect.addEventListener("change", async (event) => {
            await setLanguage(event.target.value);
        });
    }

    setupSidebar();
});