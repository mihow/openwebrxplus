/**
 * Scanner UI views — Activity Feed, Listening, Log, Settings.
 */

// --- Utility ---

function formatFreq(hz) {
    return (hz / 1e6).toFixed(hz % 1e6 === 0 ? 1 : 3);
}

function formatTime(isoStr) {
    if (!isoStr) return "";
    var d = new Date(isoStr);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function strengthBars(snrDb, maxSnr) {
    maxSnr = maxSnr || 30;
    var level = Math.min(5, Math.max(0, Math.round((snrDb / maxSnr) * 5)));
    var html = "";
    for (var i = 0; i < 5; i++) {
        html += '<div class="bar' + (i < level ? " active" : "") + '"></div>';
    }
    return html;
}

function el(tag, className, content) {
    var e = document.createElement(tag);
    if (className) e.className = className;
    if (content !== undefined) {
        if (typeof content === "string") e.innerHTML = content;
        else e.appendChild(content);
    }
    return e;
}

// --- Activity Feed View ---

var ActivityFeedView = {
    init: function() {
        this.activeList = document.getElementById("active-list");
        this.recentList = document.getElementById("recent-list");
        this.bookmarksList = document.getElementById("bookmarks-list");
        this.mostActiveList = document.getElementById("most-active-list");
        this.statusDot = document.querySelector("#activity-feed .status-dot");
        this.statusText = document.querySelector("#activity-feed .status-text");
    },

    updateState: function(state) {
        if (!state) return;

        // Update status indicator
        this.statusDot.className = "status-dot";
        if (state.state === "scanning") {
            this.statusDot.classList.add("scanning");
            this.statusText.textContent = "Scanning " + formatFreq(state.freq_start || 25e6) + "–" + formatFreq(state.freq_stop || 1700e6) + " MHz";
        } else if (state.state === "listening") {
            this.statusDot.classList.add("listening");
            this.statusText.textContent = "Listening " + formatFreq(state.current_freq || 0) + " MHz";
        } else if (state.state === "paused") {
            this.statusDot.classList.add("paused");
            this.statusText.textContent = "Paused";
        } else {
            this.statusText.textContent = "Idle";
        }

        if (state.progress !== undefined) {
            this.statusText.textContent += " (" + Math.round(state.progress * 100) + "%)";
        }
    },

    updateActive: function(signals) {
        this.activeList.innerHTML = "";
        if (!signals || signals.length === 0) return;
        signals.forEach(function(sig) {
            var row = _makeSignalRow(sig, true);
            this.activeList.appendChild(row);
        }.bind(this));
    },

    updateRecent: function(detections) {
        this.recentList.innerHTML = "";
        if (!detections || detections.length === 0) return;
        detections.forEach(function(det) {
            var row = _makeSignalRow(det, false);
            this.recentList.appendChild(row);
        }.bind(this));
    },

    updateBookmarks: function(bookmarks) {
        this.bookmarksList.innerHTML = "";
        if (!bookmarks || bookmarks.length === 0) return;
        bookmarks.forEach(function(bm) {
            var row = el("div", "signal-row");
            row.dataset.freq = bm.frequency_hz;
            row.innerHTML =
                '<span class="signal-freq">' + formatFreq(bm.frequency_hz) + "</span>" +
                '<span class="signal-label">' + (bm.label || "") + "</span>" +
                (bm.active ? '<span class="signal-activity"></span>' : "");
            row.addEventListener("click", function() {
                ScannerApp.tuneTo(bm.frequency_hz, bm.mode);
            });
            this.bookmarksList.appendChild(row);
        }.bind(this));
    },

    updateMostActive: function(data) {
        this.mostActiveList.innerHTML = "";
        if (!data || data.length === 0) return;
        data.forEach(function(item) {
            var row = el("div", "signal-row");
            row.dataset.freq = item.frequency_hz;
            row.innerHTML =
                '<span class="signal-freq">' + formatFreq(item.frequency_hz) + "</span>" +
                '<span class="signal-mode">' + (item.mode || "").toUpperCase() + "</span>" +
                '<span class="signal-count">' + item.count + " det.</span>";
            row.addEventListener("click", function() {
                ScannerApp.tuneTo(item.frequency_hz, item.mode);
            });
            this.mostActiveList.appendChild(row);
        }.bind(this));
    },
};

function _makeSignalRow(sig, showStrength) {
    var row = el("div", "signal-row");
    row.dataset.freq = sig.frequency_hz;
    var html =
        '<span class="signal-freq">' + formatFreq(sig.frequency_hz) + "</span>" +
        '<span class="signal-mode">' + (sig.mode || "").toUpperCase() + "</span>";
    if (sig.bookmark_label) {
        html += '<span class="signal-label">' + sig.bookmark_label + "</span>";
    }
    if (showStrength && sig.snr_db !== undefined) {
        html += '<span class="signal-strength">' + strengthBars(sig.snr_db) + "</span>";
    }
    if (sig.timestamp) {
        html += '<span class="signal-time">' + formatTime(sig.timestamp) + "</span>";
    }
    row.innerHTML = html;
    row.addEventListener("click", function() {
        ScannerApp.tuneTo(sig.frequency_hz, sig.mode);
    });
    return row;
}

// --- Listening View ---

var ListeningView = {
    currentFreq: 0,
    currentMode: "",
    held: false,

    init: function() {
        this.freqDisplay = document.getElementById("listen-freq");
        this.modeDisplay = document.getElementById("listen-mode");
        this.labelDisplay = document.getElementById("listen-label");
        this.meterFill = document.querySelector("#listening-view .meter-fill");
        this.freqLabel = document.getElementById("tune-freq-label");
        this.bwLabel = document.getElementById("tune-bw-label");
        this.statusDot = document.querySelector("#listening-view .status-dot");
        this.statusText = document.getElementById("listen-status-text");
        this.holdBtn = document.getElementById("btn-hold");

        // Tune buttons
        document.querySelectorAll(".tune-btn").forEach(function(btn) {
            btn.addEventListener("click", function() {
                var action = btn.dataset.action;
                if (!action) return;
                switch (action) {
                    case "freq-down-coarse": ScannerApp.nudgeFreq(-5000); break;
                    case "freq-down":        ScannerApp.nudgeFreq(-1000); break;
                    case "freq-up":          ScannerApp.nudgeFreq(1000); break;
                    case "freq-up-coarse":   ScannerApp.nudgeFreq(5000); break;
                    case "bw-down":          ScannerApp.nudgeBw(-2500); break;
                    case "bw-up":            ScannerApp.nudgeBw(2500); break;
                }
            });
        });

        document.getElementById("btn-skip").addEventListener("click", function() {
            ScannerApp.sendCommand("skip");
        });

        this.holdBtn.addEventListener("click", function() {
            ListeningView.held = !ListeningView.held;
            ListeningView.holdBtn.classList.toggle("held", ListeningView.held);
            ListeningView.holdBtn.textContent = ListeningView.held ? "Release" : "Hold";
            ScannerApp.sendCommand(ListeningView.held ? "hold" : "resume");
        });

        document.getElementById("btn-save").addEventListener("click", function() {
            var label = prompt("Bookmark label:");
            if (label) {
                ScannerApp.saveBookmark(ListeningView.currentFreq, label, ListeningView.currentMode);
            }
        });
    },

    show: function(freqHz, mode, label) {
        this.currentFreq = freqHz;
        this.currentMode = mode || "";
        this.held = false;
        this.holdBtn.classList.remove("held");
        this.holdBtn.textContent = "Hold";

        this.freqDisplay.textContent = formatFreq(freqHz);
        this.modeDisplay.textContent = (mode || "").toUpperCase();
        this.labelDisplay.textContent = label || "";
        this.freqLabel.textContent = formatFreq(freqHz) + " MHz";
        this.bwLabel.textContent = "BW";
        this.meterFill.style.width = "0%";

        this.statusDot.className = "status-dot listening";
        this.statusText.textContent = "Listening";

        ScannerApp.showScreen("listening-view");
    },

    updateSignal: function(power, snr) {
        var pct = Math.min(100, Math.max(0, (snr / 30) * 100));
        this.meterFill.style.width = pct + "%";
    },

    updateFreq: function(freqHz) {
        this.currentFreq = freqHz;
        this.freqDisplay.textContent = formatFreq(freqHz);
        this.freqLabel.textContent = formatFreq(freqHz) + " MHz";
    },
};

// --- Log View ---

var LogView = {
    init: function() {
        this.list = document.getElementById("log-list");
        document.getElementById("log-filter-mode").addEventListener("change", function() {
            LogView.refresh();
        });
        document.getElementById("log-filter-class").addEventListener("change", function() {
            LogView.refresh();
        });
    },

    refresh: function() {
        var mode = document.getElementById("log-filter-mode").value;
        var cls = document.getElementById("log-filter-class").value;
        var params = new URLSearchParams();
        if (mode) params.set("mode", mode);
        if (cls) params.set("classification", cls);

        fetch("/api/scanner/detections?" + params.toString())
            .then(function(r) { return r.json(); })
            .then(function(data) {
                LogView.render(data.detections || []);
            })
            .catch(function(err) {
                console.error("Failed to load log:", err);
            });
    },

    render: function(detections) {
        this.list.innerHTML = "";
        detections.forEach(function(det) {
            var entry = el("div", "log-entry");
            entry.innerHTML =
                '<span class="log-time">' + formatTime(det.timestamp) + "</span>" +
                '<span class="log-freq">' + formatFreq(det.frequency_hz) + "</span>" +
                '<span class="log-mode">' + (det.mode || "").toUpperCase() + "</span>" +
                (det.duration_sec ? '<span class="log-duration">' + det.duration_sec.toFixed(1) + "s</span>" : "") +
                (det.recording_path ? '<button class="log-play" data-path="' + det.recording_path + '">&#9654;</button>' : "");
            this.list.appendChild(entry);
        }.bind(this));
    },
};

// --- Settings View ---

var SettingsView = {
    init: function() {
        // Load current settings from API
    },

    loadSettings: function() {
        fetch("/api/scanner")
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var s = data.config || {};
                if (s.freq_start) document.getElementById("set-freq-start").value = s.freq_start / 1e6;
                if (s.freq_stop) document.getElementById("set-freq-stop").value = s.freq_stop / 1e6;
                if (s.dwell_time) document.getElementById("set-dwell").value = s.dwell_time;
                if (s.hang_time) document.getElementById("set-hang").value = s.hang_time;
            })
            .catch(function() {});
    },
};
