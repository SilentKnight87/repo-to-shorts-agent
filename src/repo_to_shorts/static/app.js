/* repo-to-shorts — VHS Cassette frontend behavior
 *
 * Phase 5 of the redesign. Drives the form submit, the SP/LP/EP tape-mode
 * toggle, the audio toggle, the optional FALLBACKS button, the rotating
 * error headline, the timecode tick, and the progress poll that maps
 * backend stage statuses onto the new .channel-row[data-state] contract.
 *
 * Backend POST contract (preserved): target, audience, kimi_model,
 * creative_mode, preview, skip_audio, render_mp4, session_id. Hidden
 * inputs whose toggle resolves to "off" have their `name` attribute set
 * to "" so they are not posted (Python reads `"creative_mode" in form`,
 * so absence of the name is what matters).
 */
(() => {
  "use strict";

  const prefersReduced =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const ERROR_TITLES = [
    "TRACKING ERROR.",
    "TAPE ATE THE REEL.",
    "SIGNAL LOST.",
    "DROPOUT.",
    "BAD HEAD.",
  ];

  const STAGE_STATE_MAP = {
    pending: "stby",
    in_progress: "live",
    complete: "done",
    error: "error",
  };

  // RFC4122 v4 generator — same shape as the prior inline implementation.
  function uuid() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  function pickRandom(list) {
    return list[Math.floor(Math.random() * list.length)];
  }

  // ---------------------------------------------------------------------------
  // Error headline rotator
  // ---------------------------------------------------------------------------
  function rotateErrorHeadlines() {
    const rotators = document.querySelectorAll(
      ".glitch-headline[data-rotate-error]"
    );
    rotators.forEach((el) => {
      el.textContent = pickRandom(ERROR_TITLES);
    });
  }

  // ---------------------------------------------------------------------------
  // Tape-mode + audio toggles
  // ---------------------------------------------------------------------------
  //
  // The visual toggle is decoupled from the form fields. JS holds the
  // current selection and recomputes the three hidden-input states on
  // every change. Tape mode is the master:
  //   SP: skip_audio=on (forced),  preview=on,  creative_mode=on
  //   LP: skip_audio=audioToggle,  preview=on,  creative_mode=on
  //   EP: skip_audio=audioToggle,  preview=off, creative_mode=on
  // Audio toggle: DOLBY -> "off" (we want audio), OFF -> "on" (skip).
  const toggleState = {
    tape: "sp", // sp | lp | ep
    audio: "dolby", // dolby | off
  };

  function readInitialToggleState(root) {
    const tapeCluster = root.querySelector('.toggle-mode[data-toggle="tape-mode"]');
    if (tapeCluster) {
      const lit = tapeCluster.querySelector(".is-lit[data-tape-mode]");
      if (lit && lit.dataset.tapeMode) {
        toggleState.tape = lit.dataset.tapeMode.toLowerCase();
      }
    }
    const audioCluster = root.querySelector(
      '.toggle-mode[data-toggle="audio-mode"]'
    );
    if (audioCluster) {
      const lit = audioCluster.querySelector(".is-lit[data-audio-mode]");
      if (lit && lit.dataset.audioMode) {
        toggleState.audio = lit.dataset.audioMode.toLowerCase();
      }
    }
  }

  // Set a hidden input's `name` attribute to either the canonical name
  // (when "on") or "" (when "off"). An input with name="" is not
  // submitted — that's how we encode "absent" without removing the node.
  function setFlag(form, canonicalName, on) {
    const input = form.querySelector(`input[data-flag="${canonicalName}"]`);
    if (!input) return;
    input.name = on ? canonicalName : "";
    input.value = on ? "on" : "";
  }

  function applyToggleState(form) {
    if (!form) return;
    const tape = toggleState.tape;
    const audio = toggleState.audio;

    // creative_mode is always on for SP/LP/EP — they're all creative shorts.
    const creative = true;
    let preview;
    let skipAudio;
    let finalMode;

    if (tape === "sp") {
      preview = true;
      finalMode = false;
      skipAudio = true; // forced silent for fastest preview
    } else if (tape === "lp") {
      preview = true;
      finalMode = false;
      skipAudio = audio === "off";
    } else {
      // ep (full master)
      preview = false;
      finalMode = true;
      skipAudio = audio === "off";
    }

    setFlag(form, "creative_mode", creative);
    setFlag(form, "preview", preview);
    setFlag(form, "final", finalMode);
    setFlag(form, "skip_audio", skipAudio);
  }

  function wireToggleCluster(cluster, key, form) {
    const childAttr = key === "tape" ? "data-tape-mode" : "data-audio-mode";
    const datasetKey = key === "tape" ? "tapeMode" : "audioMode";

    cluster.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target.closest(`[${childAttr}]`) : null;
      if (!target || !cluster.contains(target)) return;

      const value = (target.dataset[datasetKey] || "").toLowerCase();
      if (!value) return;

      cluster.querySelectorAll(`[${childAttr}]`).forEach((sib) => {
        sib.classList.remove("is-lit");
        sib.setAttribute("aria-pressed", "false");
      });
      target.classList.add("is-lit");
      target.setAttribute("aria-pressed", "true");

      toggleState[key] = value;
      applyToggleState(form);
    });
  }

  function wireToggles(form) {
    if (!form) return;
    document
      .querySelectorAll('.toggle-mode[data-toggle="tape-mode"]')
      .forEach((cluster) => wireToggleCluster(cluster, "tape", form));
    document
      .querySelectorAll('.toggle-mode[data-toggle="audio-mode"]')
      .forEach((cluster) => wireToggleCluster(cluster, "audio", form));

    readInitialToggleState(document);
    applyToggleState(form);
  }

  // ---------------------------------------------------------------------------
  // Fallbacks button (toggles the render_mp4 hidden input)
  // ---------------------------------------------------------------------------
  function wireFallbacksButton(form) {
    if (!form) return;
    const btn = document.querySelector(
      '#btn-fallbacks, .btn-tape[data-action="fallbacks"]'
    );
    if (!btn) return;

    // Initial state: input may already be authored as on/off in markup.
    const input = form.querySelector('input[data-flag="render_mp4"]');
    const initial = !!(input && input.name === "render_mp4");
    btn.classList.toggle("is-active", initial);
    btn.setAttribute("aria-pressed", initial ? "true" : "false");

    btn.addEventListener("click", (event) => {
      event.preventDefault();
      const next = !btn.classList.contains("is-active");
      btn.classList.toggle("is-active", next);
      btn.setAttribute("aria-pressed", next ? "true" : "false");
      setFlag(form, "render_mp4", next);
    });
  }

  // ---------------------------------------------------------------------------
  // Timecode tick (mm:ss:ff @ 30fps; runs while broadcasting)
  // ---------------------------------------------------------------------------
  let tcStart = null;
  let tcRaf = null;

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function startTimecodeTick() {
    if (prefersReduced) return; // leave at the static 00:00:00:00
    const el = document.querySelector(".slate-tc");
    if (!el) return;

    tcStart = performance.now();
    const tick = (now) => {
      const elapsed = (now - tcStart) / 1000;
      const fps = 30;
      const totalFrames = Math.floor(elapsed * fps);
      const ff = totalFrames % fps;
      const secs = Math.floor(elapsed);
      const ss = secs % 60;
      const mm = Math.floor(secs / 60) % 60;
      const hh = Math.floor(secs / 3600);
      el.textContent = `${pad(hh)}:${pad(mm)}:${pad(ss)}:${pad(ff)}`;
      tcRaf = requestAnimationFrame(tick);
    };
    tcRaf = requestAnimationFrame(tick);
  }

  function stopTimecodeTick() {
    if (tcRaf != null) {
      cancelAnimationFrame(tcRaf);
      tcRaf = null;
    }
  }

  // ---------------------------------------------------------------------------
  // Progress poll
  // ---------------------------------------------------------------------------
  let pollInterval = null;

  async function pollProgress(sid) {
    try {
      const res = await fetch(`/progress?session=${encodeURIComponent(sid)}`);
      if (!res.ok) return;
      const data = await res.json();

      const stages = Array.isArray(data.stages) ? data.stages : [];
      const percent = Number.isFinite(data.percent) ? data.percent : 0;

      stages.forEach((s) => {
        if (!s || typeof s.name !== "string") return;
        const row = document.querySelector(
          `.deck-broadcasting .channel-row[data-stage="${s.name}"]`
        );
        if (!row) return;

        row.dataset.state = STAGE_STATE_MAP[s.status] || "stby";

        const status = row.querySelector(".ch-status");
        if (status) {
          if (s.status === "in_progress") {
            status.textContent = `LIVE · ${percent}%`;
          } else if (s.status === "complete") {
            status.textContent = "DONE";
          } else if (s.status === "error") {
            status.textContent = "ERR";
          } else {
            status.textContent = "STBY";
          }
        }

        const fill = row.querySelector(".ch-fill");
        if (fill) {
          if (s.status === "in_progress") {
            fill.style.width = `${percent}%`;
          } else if (s.status === "complete") {
            fill.style.width = "100%";
          } else if (s.status === "error") {
            // Leave whatever fill is currently shown; the row's data-state
            // signals the failure to the CSS layer.
          } else {
            fill.style.width = "0%";
          }
        }
      });

      if (data.error) {
        const slate = document.querySelector(".slate-state");
        if (slate) {
          slate.textContent = "● SIGNAL LOST";
          slate.classList.remove("is-rec", "is-pulsing");
          slate.classList.add("is-error");
        }
      }

      const finished = percent >= 100 || !!data.error;
      if (finished) {
        if (pollInterval != null) {
          clearInterval(pollInterval);
          pollInterval = null;
        }
        stopTimecodeTick();

        if (!prefersReduced) {
          document.body.classList.add("has-dropout");
          setTimeout(() => {
            document.body.classList.remove("has-dropout");
          }, 200);
        }
      }
    } catch (_e) {
      // Ignore transient polling errors — the next tick will retry.
    }
  }

  // ---------------------------------------------------------------------------
  // Submit handler
  // ---------------------------------------------------------------------------
  function fireGlitchOnce(headline) {
    if (!headline || prefersReduced) return;
    headline.setAttribute("data-glitch", "1");
    setTimeout(() => headline.removeAttribute("data-glitch"), 320);
  }

  function wireFormSubmit(form) {
    if (!form) return;

    form.addEventListener("submit", (event) => {
      if (form.dataset.submitting === "true") {
        event.preventDefault();
        return;
      }
      event.preventDefault();
      form.dataset.submitting = "true";
      form.classList.add("is-submitting");
      form.setAttribute("aria-busy", "true");

      // Recompute toggle-derived hidden inputs one last time before submit.
      applyToggleState(form);

      const sid = uuid();
      const sessionInput = document.getElementById("session-id");
      if (sessionInput) sessionInput.value = sid;

      // In-place takeover: hide the control deck, show the broadcasting deck.
      const ctrl = form.querySelector(".deck-control");
      const bcast = form.querySelector(".deck-broadcasting");
      if (ctrl) ctrl.hidden = true;
      if (bcast) bcast.hidden = false;

      // One-shot tracking-error glitch on the broadcasting headline.
      const headline = document.querySelector(
        ".deck-broadcasting .glitch-headline"
      );
      fireGlitchOnce(headline);

      // Slate flips to ON AIR (red, pulsing).
      const slateState = document.querySelector(".slate-state");
      if (slateState) {
        slateState.textContent = "● ON AIR";
        slateState.classList.remove("is-lock", "is-error", "is-idle");
        slateState.classList.add("is-rec", "is-pulsing");
      }

      // Begin polling and ticking.
      startTimecodeTick();
      pollProgress(sid);
      pollInterval = setInterval(() => pollProgress(sid), 1500);

      // Yield ~80ms so the UI can render the takeover before navigation.
      setTimeout(() => {
        HTMLFormElement.prototype.submit.call(form);
      }, 80);
    });
  }

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------
  function boot() {
    rotateErrorHeadlines();

    const form = document.getElementById("generate-form");
    wireToggles(form);
    wireFallbacksButton(form);
    wireFormSubmit(form);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
