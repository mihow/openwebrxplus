/**
 * Scanner app — main entry point.
 * Manages WebSocket connection, view routing, and scanner commands.
 */

var ScannerApp = (function() {
    var ws = null;
    var reconnectTimer = null;
    var currentScreen = "activity-feed";
    var pollTimer = null;

    function init() {
        // Init views
        ActivityFeedView.init();
        ListeningView.init();
        LogView.init();
        SettingsView.init();

        // Tap overlay — init audio on first tap
        var overlay = document.getElementById("tap-overlay");
        overlay.addEventListener("click", function() {
            overlay.classList.add("hidden");
            _startPolling();
            _connectWs();
            ScannerAudio.init().then(function() {
                ScannerAudio.resume();
            }).catch(function(e) {
                console.log("[Scanner] Audio init failed (ok, will retry):", e);
            });
        });

        // Navigation
        document.getElementById("btn-scan").addEventListener("click", function() {
            _toggleScan();
        });
        document.getElementById("btn-log").addEventListener("click", function() {
            LogView.refresh();
            showScreen("log-view");
        });
        document.getElementById("btn-settings").addEventListener("click", function() {
            SettingsView.loadSettings();
            showScreen("settings-view");
        });

        // Back buttons
        document.getElementById("btn-back").addEventListener("click", function() {
            showScreen("activity-feed");
        });
        document.getElementById("btn-log-back").addEventListener("click", function() {
            showScreen("activity-feed");
        });
        document.getElementById("btn-settings-back").addEventListener("click", function() {
            showScreen("activity-feed");
        });

        // Refresh button
        document.querySelector(".refresh-btn").addEventListener("click", function() {
            _pollState();
        });
    }

    function showScreen(screenId) {
        document.querySelectorAll(".screen").forEach(function(s) {
            s.classList.remove("active");
        });
        var target = document.getElementById(screenId);
        if (target) {
            target.classList.add("active");
            currentScreen = screenId;
        }
    }

    function _connectWs() {
        if (ws && ws.readyState <= 1) return;

        var proto = location.protocol === "https:" ? "wss:" : "ws:";
        var url = proto + "//" + location.host + "/ws/";
        ws = new WebSocket(url);
        ws.binaryType = "arraybuffer";

        ws.onopen = function() {
            console.log("[Scanner] WebSocket connected");
            // Request scanner state
            ws.send(JSON.stringify({ type: "scanner_subscribe" }));
        };

        ws.onmessage = function(evt) {
            if (typeof evt.data === "string") {
                _handleJsonMessage(JSON.parse(evt.data));
            } else {
                _handleBinaryMessage(new Uint8Array(evt.data));
            }
        };

        ws.onclose = function() {
            console.log("[Scanner] WebSocket closed, reconnecting...");
            reconnectTimer = setTimeout(_connectWs, 3000);
        };

        ws.onerror = function() {
            ws.close();
        };
    }

    function _handleJsonMessage(msg) {
        switch (msg.type) {
            case "scanner_state":
                ActivityFeedView.updateState(msg);
                if ((msg.state || msg.status) === "listening" && currentScreen === "activity-feed") {
                    // Auto-switch to listening view when scanner locks on
                    ListeningView.show(msg.current_freq, msg.current_mode, msg.current_label);
                }
                if ((msg.state || msg.status) === "scanning" && currentScreen === "listening-view" && !ListeningView.held) {
                    // Return to feed when scanner resumes scanning
                    showScreen("activity-feed");
                }
                break;

            case "scanner_signal":
                // Real-time signal strength update while listening
                if (currentScreen === "listening-view") {
                    ListeningView.updateSignal(msg.power, msg.snr);
                }
                break;

            case "scanner_detection":
                // New detection logged — update feed
                _pollState();
                break;
        }
    }

    function _handleBinaryMessage(data) {
        if (data.length < 2) return;
        var msgType = data[0];
        if (msgType === 0x02) {
            // Audio data
            ScannerAudio.processAudioData(data);
        }
    }

    function _startPolling() {
        _pollState();
        pollTimer = setInterval(_pollState, 2000);
    }

    function _pollState() {
        // Fetch each endpoint independently — one failure shouldn't block others
        fetch("/api/scanner").then(function(r) { return r.json(); })
            .then(function(state) {
                ActivityFeedView.updateState(state);
                // active_signals from scanner state = current FFT window's detections
                if (state.active_signals && state.active_signals.length > 0) {
                    ActivityFeedView.updateActive(state.active_signals);
                }
            }).catch(function() {});

        fetch("/api/scanner/detections?limit=10").then(function(r) { return r.json(); })
            .then(function(data) {
                ActivityFeedView.updateRecent(data.detections || []);
            }).catch(function() {});

        fetch("/api/scanner/active").then(function(r) { return r.json(); })
            .then(function(data) {
                ActivityFeedView.updateMostActive(data.signals || []);
            }).catch(function() {});

        fetch("/api/scanner/bookmarks").then(function(r) { return r.json(); })
            .then(function(data) {
                ActivityFeedView.updateBookmarks(data.bookmarks || []);
            }).catch(function() {});
    }

    function _toggleScan() {
        fetch("/api/scanner")
            .then(function(r) { return r.json(); })
            .then(function(state) {
                var s = state.state || state.status;
            if (s === "scanning" || s === "listening") {
                    sendCommand("stop");
                } else {
                    sendCommand("start");
                }
            });
    }

    function sendCommand(cmd, params) {
        var body = { command: cmd };
        if (params) body.params = params;

        fetch("/api/scanner/command", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        })
        .then(function() {
            _pollState();
        })
        .catch(function(err) {
            console.error("[Scanner] Command failed:", err);
        });
    }

    function tuneTo(freqHz, mode) {
        sendCommand("tune", { frequency: freqHz, mode: mode });
        ListeningView.show(freqHz, mode);
    }

    function nudgeFreq(offsetHz) {
        var newFreq = ListeningView.currentFreq + offsetHz;
        sendCommand("tune", { frequency: newFreq });
        ListeningView.updateFreq(newFreq);
    }

    function nudgeBw(offsetHz) {
        sendCommand("nudge_bw", { offset: offsetHz });
    }

    function saveBookmark(freqHz, label, mode) {
        fetch("/api/scanner/bookmarks", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ frequency_hz: freqHz, label: label, mode: mode }),
        })
        .then(function() {
            _pollState();
        });
    }

    // Public API
    return {
        init: init,
        showScreen: showScreen,
        sendCommand: sendCommand,
        tuneTo: tuneTo,
        nudgeFreq: nudgeFreq,
        nudgeBw: nudgeBw,
        saveBookmark: saveBookmark,
    };
})();

// Boot on DOM ready
document.addEventListener("DOMContentLoaded", ScannerApp.init);
