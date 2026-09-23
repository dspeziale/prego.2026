/* Prego - script dell'applicazione (estratto da base.html) */
(function () {
    "use strict";

    var PREGO_DATA = JSON.parse(
        document.getElementById("prego-data").textContent
    );

/* Awesome Notifications: toast e conferme */
            window.notifier = new AWN({
                position: "top-right",
                durations: { global: 3500 },
                labels: {
                    info: "Info", success: "Fatto", warning: "Attenzione",
                    alert: "Errore", confirm: "Conferma", confirmOk: "Sì",
                    confirmCancel: "Annulla"
                }
            });

            /* messaggi flash del server come toast */
    PREGO_DATA.flash.forEach(function (pair) {
        var kind = pair[0] === "success" ? "success" : "alert";
        notifier[kind](pair[1]);
    });

        /* form con conferma AWN (sostituisce confirm() nativo) */
        document.querySelectorAll("form.js-confirm").forEach(function (form) {
            form.addEventListener("submit", function (event) {
                if (form.dataset.confirmed) { return; }
                event.preventDefault();
                notifier.confirm(
                    form.dataset.message || "Confermare l'operazione?",
                    function () {
                        form.dataset.confirmed = "1";
                        form.submit();
                    }
                );
            });
        });
        var THEME_KEY = "lc-theme";
        var FONT_KEY = "lc-font-size";
        var FONT_MIN = 12, FONT_MAX = 32, FONT_STEP = 1, FONT_DEFAULT = 16;

        var header = document.querySelector(".main-header");
        var sidebar = document.querySelector(".main-sidebar");
        var toggleIcon = document.querySelector("#themeToggle i");

        function applyTheme(theme) {
            var dark = theme === "dark";
            document.body.classList.toggle("dark-mode", dark);
            if (header) {
                header.classList.toggle("navbar-dark", dark);
                header.classList.toggle("navbar-white", !dark);
                header.classList.toggle("navbar-light", !dark);
            }
            if (sidebar) {
                sidebar.classList.toggle("sidebar-dark-primary", dark);
                sidebar.classList.toggle("sidebar-light-primary", !dark);
            }
            if (toggleIcon) {
                toggleIcon.classList.toggle("fa-sun", dark);
                toggleIcon.classList.toggle("fa-moon", !dark);
            }
        }

        function applyFont(px) {
            document.documentElement.style.fontSize = px + "px";
            document.body.style.fontSize = px + "px";
        }

        var theme = localStorage.getItem(THEME_KEY) || "light";
        var font = parseInt(localStorage.getItem(FONT_KEY), 10) || FONT_DEFAULT;
        applyTheme(theme);
        applyFont(font);

        document.getElementById("themeToggle").addEventListener("click", function (e) {
            e.preventDefault();
            theme = theme === "dark" ? "light" : "dark";
            localStorage.setItem(THEME_KEY, theme);
            applyTheme(theme);
        });

        function changeFont(delta) {
            font = Math.min(FONT_MAX, Math.max(FONT_MIN, font + delta));
            localStorage.setItem(FONT_KEY, String(font));
            applyFont(font);
        }
        document.getElementById("fontPlus").addEventListener("click", function () {
            changeFont(FONT_STEP);
        });
        document.getElementById("fontMinus").addEventListener("click", function () {
            changeFont(-FONT_STEP);
        });

        /* selettore data: clic sulla data -> picker -> vai al giorno */
        var dateInput = document.getElementById("dateJumpInput");
        var availableDays = new Set(PREGO_DATA.availableDays);
        document.querySelectorAll(".js-date-jump").forEach(function (el) {
            el.addEventListener("click", function (e) {
                e.preventDefault();
                try { dateInput.showPicker(); }
                catch (err) { dateInput.focus(); dateInput.click(); }
            });
        });
        dateInput.addEventListener("change", function () {
            var value = dateInput.value;
            if (!value) { return; }
            if (availableDays.has(value)) {
                window.location.href = "/giorno/" + value;
            } else {
                alert("Nessuna liturgia raccolta per " + value);
            }
        });

        /* aggancia badge e toolbar sotto la navbar (mobile) */
        var dayBadges = document.querySelector(".day-badges");
        var tabsHeader = document.querySelector(
            ".card-primary.card-outline-tabs > .card-header"
        );
        var jumpFabs = document.querySelector(".jump-fabs");
        function alignSticky() {
            if (!header || window.innerWidth >= 768) {
                if (jumpFabs) { jumpFabs.style.top = ""; }
                return;
            }
            var offset = header.offsetHeight;
            if (dayBadges) {
                dayBadges.style.top = offset + "px";
                offset += dayBadges.offsetHeight;
            }
            if (tabsHeader) {
                tabsHeader.style.top = offset + "px";
                offset += tabsHeader.offsetHeight;
            }
            if (jumpFabs) { jumpFabs.style.top = (offset + 40) + "px"; }
        }
        alignSticky();
        window.addEventListener("resize", alignSticky);
        window.addEventListener("load", alignSticky);
        /* i webfont cambiano le altezze dopo il primo layout
           (soprattutto nell'app, dove arrivano dagli asset locali):
           ricalcola gli agganci quando sono pronti */
        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(alignSticky);
        }

        /* segni salmodici † e * in rosso rubricale */
        document.querySelectorAll(".liturgical-text").forEach(function (el) {
            el.innerHTML = el.innerHTML.replace(
                /([†*])/g, '<span class="rubric-mark">$1</span>'
            );
        });
})();

/* salti alle sezioni della scheda Giorno (pagina giorno) */
document.addEventListener("DOMContentLoaded", function () {
    var TARGETS = {
        salmi: ["antifone_e_salmi"],
        letture: ["biennale", "proprio", "ufficio_letture", "lettura_breve"],
        biennale: ["biennale"],
        proprio: ["proprio"],
        vangelo: ["vangelo_messa"]
    };
    function stickyOffset() {
        var offset = 10;
        if (window.innerWidth < 768) {
            [document.querySelector(".main-header"),
             document.querySelector(".day-badges"),
             document.querySelector(
                 ".card-primary.card-outline-tabs > .card-header")
            ].forEach(function (el) {
                if (el) { offset += el.offsetHeight; }
            });
        }
        return offset;
    }
    document.querySelectorAll(".jump-fabs [data-jump]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var link = document.querySelector('a[href="#doc-giorno"]');
            if (link && !link.classList.contains("active")) { link.click(); }
            setTimeout(function () {
                var pane = document.getElementById("doc-giorno");
                if (!pane) { return; }
                var target = null;
                (TARGETS[btn.dataset.jump] || []).some(function (key) {
                    target = pane.querySelector('[data-key="' + key + '"]');
                    return !!target;
                });
                if (!target) { return; }
                var y = target.getBoundingClientRect().top
                        + window.scrollY - stickyOffset();
                window.scrollTo({ top: y, behavior: "smooth" });
            }, 80);
        });
    });
});

