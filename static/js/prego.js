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

/* Impostazioni: fonte delle letture nella scheda Giorno.
   La preferenza (lc-letture = "biennale" | "ufficio") è già applicata
   su <html data-letture> prima del rendering; qui il ripiego quando la
   fonte scelta manca in questa giornata, e il salvataggio dalla pagina
   Impostazioni. */
document.addEventListener("DOMContentLoaded", function () {
    var LETTURE_KEY = "lc-letture";
    var html = document.documentElement;
    var pane = document.getElementById("doc-giorno");
    if (pane) {
        var wanted = html.getAttribute("data-letture") || "biennale";
        var has = function (fonte) {
            return !!pane.querySelector('[data-fonte="' + fonte + '"]');
        };
        if (!has(wanted)) {
            var other = wanted === "ufficio" ? "biennale" : "ufficio";
            if (has(other)) { html.setAttribute("data-letture", other); }
        }
    }
    document.querySelectorAll('input[name="letture"]').forEach(function (radio) {
        radio.checked = radio.value === (localStorage.getItem(LETTURE_KEY) || "biennale");
        radio.addEventListener("change", function () {
            localStorage.setItem(LETTURE_KEY, radio.value);
            html.setAttribute("data-letture", radio.value);
            if (window.notifier) {
                notifier.success(radio.value === "ufficio"
                    ? "Nella scheda Giorno vedrai l'Ufficio delle Letture."
                    : "Nella scheda Giorno vedrai Biennale e Proprio.");
            }
        });
    });
});

/* Silenzio per la preghiera (scheda Giorno): 5/10/15 minuti di conto
   alla rovescia; al termine un sibilo generato con Web Audio (nessun
   file audio: funziona anche offline nell'app) e, se possibile, una
   vibrazione. Il contesto audio viene creato al tocco del pulsante,
   come richiedono i browser, e riusato alla fine. Se il browser lo
   permette, lo schermo resta acceso per la durata (Wake Lock). */
document.addEventListener("DOMContentLoaded", function () {
    var panel = document.getElementById("silenzioPanel");
    if (!panel) { return; }
    var scelta = panel.querySelector(".silenzio-scelta");
    var corso = panel.querySelector(".silenzio-corso");
    var tempo = panel.querySelector(".silenzio-tempo");
    var barra = panel.querySelector(".silenzio-progress .progress-bar");
    var stop = panel.querySelector(".silenzio-stop");
    var audio = null, timer = null, fine = 0, durata = 0, wakeLock = null;

    function due(n) { return (n < 10 ? "0" : "") + n; }

    function sibilo() {
        if (!audio) { return; }
        var ora = audio.currentTime;
        /* due fischi ascendenti, come un richiamo sommesso */
        [0, 1.4].forEach(function (ritardo) {
            var osc = audio.createOscillator();
            var gain = audio.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(880, ora + ritardo);
            osc.frequency.exponentialRampToValueAtTime(1760, ora + ritardo + 1.0);
            gain.gain.setValueAtTime(0.0001, ora + ritardo);
            gain.gain.exponentialRampToValueAtTime(0.35, ora + ritardo + 0.15);
            gain.gain.exponentialRampToValueAtTime(0.0001, ora + ritardo + 1.2);
            osc.connect(gain).connect(audio.destination);
            osc.start(ora + ritardo);
            osc.stop(ora + ritardo + 1.25);
        });
        if (navigator.vibrate) { navigator.vibrate([400, 200, 400]); }
    }

    function aggiorna() {
        var resto = Math.max(0, Math.round((fine - Date.now()) / 1000));
        tempo.textContent = due(Math.floor(resto / 60)) + ":" + due(resto % 60);
        if (barra) { barra.style.width = (100 * (1 - resto / durata)) + "%"; }
        if (resto <= 0) { termina(true); }
    }

    function rilasciaSchermo() {
        if (wakeLock) { wakeLock.release().catch(function () {}); wakeLock = null; }
    }

    function termina(suona) {
        clearInterval(timer); timer = null;
        rilasciaSchermo();
        if (suona) {
            sibilo();
            if (window.notifier) { notifier.info("Il tempo di silenzio è terminato."); }
        }
        corso.hidden = true;
        scelta.hidden = false;
    }

    function avvia(minuti) {
        try {
            var Ctx = window.AudioContext || window.webkitAudioContext;
            if (Ctx) {
                audio = audio || new Ctx();
                if (audio.state === "suspended") { audio.resume(); }
            }
        } catch (e) { audio = null; }
        if (navigator.wakeLock && navigator.wakeLock.request) {
            navigator.wakeLock.request("screen")
                .then(function (lock) { wakeLock = lock; })
                .catch(function () {});
        }
        durata = minuti * 60;
        fine = Date.now() + durata * 1000;
        scelta.hidden = true;
        corso.hidden = false;
        aggiorna();
        timer = setInterval(aggiorna, 500);
    }

    panel.querySelectorAll(".silenzio-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            avvia(parseInt(btn.dataset.minuti, 10) || 5);
        });
    });
    stop.addEventListener("click", function () { termina(false); });
    document.addEventListener("visibilitychange", function () {
        if (timer && !document.hidden) { aggiorna(); }
    });
});

/* Impostazioni > Chi sei: nome ed email dell'utente, salvati nell'app
   Android (ponte window.PregoApp) e inviati con il ping di avvio. Fuori
   dall'app (browser) la sezione resta nascosta. */
document.addEventListener("DOMContentLoaded", function () {
    var card = document.getElementById("utenteCard");
    var app = window.PregoApp;
    if (!card || !app || !app.getUtente || !app.setUtente) { return; }
    var nome = document.getElementById("utenteNome");
    var email = document.getElementById("utenteEmail");
    try {
        var dati = JSON.parse(app.getUtente());
        nome.value = dati.nome || "";
        email.value = dati.email || "";
        document.getElementById("utenteTelefono").textContent = dati.nome_telefono || "—";
    } catch (e) { /* app vecchia o dati illeggibili */ }
    card.hidden = false;
    document.getElementById("utenteSalva").addEventListener("click", function () {
        var mail = email.value.trim();
        if (mail && !/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(mail)) {
            if (window.notifier) { notifier.alert("L'indirizzo email non sembra valido."); }
            email.focus();
            return;
        }
        app.setUtente(nome.value.trim(), mail);
        if (window.notifier) { notifier.success("Salvato."); }
    });
});

/* salti alle sezioni della scheda Giorno (pagina giorno) */
document.addEventListener("DOMContentLoaded", function () {
    var TARGETS = {
        salmi: ["antifone_e_salmi"],
        letture: ["ufficio_letture", "lettura_breve"],
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

