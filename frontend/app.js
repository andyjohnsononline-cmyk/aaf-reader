(() => {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const loading = document.getElementById("loading");
  const loadingText = document.getElementById("loading-text");
  const loadingStage = document.getElementById("loading-stage");
  const errorBanner = document.getElementById("error");
  const results = document.getElementById("results");

  const MAX_FILE_SIZE = 200 * 1024 * 1024;
  const STAGE_LABELS = {
    loading: "Loading parser engine...",
    installing: "Installing packages...",
    parsing: "Parsing AAF file...",
  };

  let worker = null;
  let pendingResolve = null;
  let pendingReject = null;
  let requestId = 0;

  function getWorker() {
    if (worker) return worker;
    worker = new Worker("worker.js");
    worker.onmessage = handleWorkerMessage;
    worker.onerror = handleWorkerError;
    return worker;
  }

  function handleWorkerMessage(e) {
    const msg = e.data;

    if (msg.op === "progress") {
      const label = STAGE_LABELS[msg.stage] || msg.stage;
      loadingStage.textContent = label;
      return;
    }

    if (msg.ok) {
      if (pendingResolve) pendingResolve(msg.result);
    } else {
      if (pendingReject) pendingReject(new Error(msg.error));
    }
    pendingResolve = null;
    pendingReject = null;
  }

  function handleWorkerError(e) {
    if (pendingReject) {
      pendingReject(new Error("Parser crashed. Please refresh and try again."));
    }
    pendingResolve = null;
    pendingReject = null;
    worker = null;
  }

  function parseFile(buffer) {
    return new Promise((resolve, reject) => {
      pendingResolve = resolve;
      pendingReject = reject;
      const id = String(++requestId);
      getWorker().postMessage({ id, op: "parse", buffer }, [buffer]);
    });
  }

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });

  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (file) handleFile(file);
    fileInput.value = "";
  });

  async function handleFile(file) {
    if (!file.name.toLowerCase().endsWith(".aaf")) {
      showError("Please select an .aaf file.");
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      showError(
        `This file is ${(file.size / 1024 / 1024).toFixed(0)}MB, which exceeds the ~200MB browser limit. ` +
        `Try the Docker version for large files.`
      );
      return;
    }

    showLoading();

    try {
      const buffer = await file.arrayBuffer();
      const jsonStr = await parseFile(buffer);
      const data = JSON.parse(jsonStr);
      renderResults(data);
    } catch (err) {
      showError(err.message);
    }
  }

  function showLoading() {
    loading.classList.remove("hidden");
    loadingText.textContent = "Parsing AAF file...";
    loadingStage.textContent = "";
    errorBanner.classList.add("hidden");
    results.classList.add("hidden");
    dropzone.classList.add("hidden");
  }

  function showError(msg) {
    loading.classList.add("hidden");
    errorBanner.textContent = msg;
    errorBanner.classList.remove("hidden");
    results.classList.add("hidden");
    dropzone.classList.remove("hidden");
  }

  function renderResults(data) {
    loading.classList.add("hidden");
    errorBanner.classList.add("hidden");
    dropzone.classList.remove("hidden");
    results.classList.remove("hidden");

    renderOverview(data);
    renderMedia(data);
    renderCompositions(data);
    renderClips(data);
    renderClipMetadata(data);
    renderSources(data);
  }

  // --- Overview ---
  function renderOverview(data) {
    const el = document.getElementById("overview-content");
    const id = data.identification || {};
    const hdr = data.header || {};
    const f = data.file || {};

    const rows = [
      ["File", f.name],
      ["Size", f.size_human],
      ["Application", id.product],
      ["Company", id.company],
      ["Platform", id.platform],
      ["Created", id.date],
      ["AAF Version", hdr.aaf_version],
      ["Byte Order", hdr.byte_order],
    ];

    el.innerHTML = rows
      .filter(([, v]) => v != null)
      .map(([k, v]) => `<span class="label">${k}</span><span class="value">${esc(String(v))}</span>`)
      .join("");

    const mc = data.mob_counts || {};
    const countsHtml = `
      <div class="mob-counts">
        <div class="mob-count"><div class="count-num">${mc.total || 0}</div><div class="count-label">Total Mobs</div></div>
        <div class="mob-count"><div class="count-num">${mc.compositions || 0}</div><div class="count-label">Compositions</div></div>
        <div class="mob-count"><div class="count-num">${mc.master_mobs || 0}</div><div class="count-label">Master Clips</div></div>
        <div class="mob-count"><div class="count-num">${mc.source_mobs || 0}</div><div class="count-label">Source Mobs</div></div>
      </div>`;

    el.insertAdjacentHTML("afterend", countsHtml);

    const existing = el.parentElement.querySelector(".mob-counts:nth-of-type(n+2)");
    if (existing) existing.remove();
  }

  // --- Media Summary ---
  function renderMedia(data) {
    const el = document.getElementById("media-content");
    const ms = data.media_summary || {};
    let html = '<div class="media-badges">';

    for (const vf of ms.video_formats || []) {
      html += `
        <div class="media-badge">
          <h3>Video</h3>
          <div class="spec">
            <div class="spec-line"><span class="spec-label">Resolution</span><span>${vf.stored_width}x${vf.stored_height}</span></div>
            <div class="spec-line"><span class="spec-label">Frame Layout</span><span>${vf.frame_layout || "—"}</span></div>
            <div class="spec-line"><span class="spec-label">Bit Depth</span><span>${vf.component_width || "—"}-bit</span></div>
            <div class="spec-line"><span class="spec-label">Subsampling</span><span>${subsamplingStr(vf)}</span></div>
            <div class="spec-line"><span class="spec-label">Color</span><span>${cleanEnum(vf.coding_equations)}</span></div>
            <div class="spec-line"><span class="spec-label">Transfer</span><span>${cleanEnum(vf.transfer_characteristic)}</span></div>
            <div class="spec-line"><span class="spec-label">Frame Rate</span><span>${vf.sample_rate || "—"} fps</span></div>
          </div>
        </div>`;
    }

    for (const af of ms.audio_formats || []) {
      html += `
        <div class="media-badge">
          <h3>Audio</h3>
          <div class="spec">
            <div class="spec-line"><span class="spec-label">Format</span><span>${af.codec || "—"}</span></div>
            <div class="spec-line"><span class="spec-label">Sample Rate</span><span>${af.sample_rate ? (af.sample_rate / 1000).toFixed(1) + " kHz" : "—"}</span></div>
            <div class="spec-line"><span class="spec-label">Bit Depth</span><span>${af.quantization_bits || "—"}-bit</span></div>
            <div class="spec-line"><span class="spec-label">Channels</span><span>${af.channels || "—"}</span></div>
          </div>
        </div>`;
    }

    if (ms.tape_sources > 0) {
      html += `
        <div class="media-badge">
          <h3>Tape Sources</h3>
          <div class="spec">
            <div class="spec-line"><span class="spec-label">Count</span><span>${ms.tape_sources}</span></div>
          </div>
        </div>`;
    }

    html += "</div>";
    el.innerHTML = html;
  }

  // --- Compositions ---
  function renderCompositions(data) {
    const el = document.getElementById("compositions-content");
    const comps = data.compositions || [];

    if (comps.length === 0) {
      el.innerHTML = '<p class="text-muted">No compositions found.</p>';
      return;
    }

    const toplevel = new Set(data.toplevel_compositions || []);

    let html = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Duration</th>
            <th>Edit Rate</th>
            <th>Tracks</th>
            <th>Start TC</th>
          </tr>
        </thead>
        <tbody>`;

    for (const c of comps) {
      const isToplevel = toplevel.has(c.name);
      const startTc = c.timecodes && c.timecodes.length > 0 ? c.timecodes[0].start_tc : "—";
      html += `
          <tr>
            <td>${esc(c.name)}${isToplevel ? ' <span class="text-muted">(top-level)</span>' : ""}</td>
            <td>${c.total_duration_tc || "—"}</td>
            <td>${c.edit_rate} fps</td>
            <td>${c.track_count}</td>
            <td>${startTc}</td>
          </tr>`;
    }

    html += "</tbody></table>";

    const topComp = comps.find((c) => toplevel.has(c.name));
    if (topComp) {
      html += renderCompositionDetail(topComp);
    }

    el.innerHTML = html;

    el.querySelectorAll(".collapsible-header").forEach((header) => {
      header.addEventListener("click", () => {
        header.classList.toggle("open");
        header.nextElementSibling.classList.toggle("open");
      });
    });
  }

  function renderCompositionDetail(comp) {
    const seqSlots = (comp.slots || []).filter(
      (s) => s.segment_type === "Sequence" && s.component_count > 0
    );
    if (seqSlots.length === 0) return "";

    let html = "";
    for (const slot of seqSlots) {
      html += `
        <div style="margin-top: 1rem;">
          <div class="collapsible-header">
            <strong>Slot ${slot.slot_id}</strong>
            <span class="text-muted">&mdash; ${slot.component_count} components, ${slot.total_length_tc}</span>
          </div>
          <div class="collapsible-body">
            <table class="data-table">
              <thead>
                <tr><th>#</th><th>Type</th><th>Duration</th><th>Start</th></tr>
              </thead>
              <tbody>`;

      for (let i = 0; i < slot.components.length; i++) {
        const c = slot.components[i];
        html += `
                <tr>
                  <td>${i + 1}</td>
                  <td>${c.type}</td>
                  <td>${c.length_tc || "—"}</td>
                  <td>${c.start_frame != null ? c.start_frame : "—"}</td>
                </tr>`;
      }

      html += `
              </tbody>
            </table>
          </div>
        </div>`;
    }
    return html;
  }

  // --- Master Clips ---
  function renderClips(data) {
    const el = document.getElementById("clips-content");
    const clips = data.master_mobs || [];

    if (clips.length === 0) {
      el.innerHTML = '<p class="text-muted">No master clips found.</p>';
      return;
    }

    let html = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Slots</th>
          </tr>
        </thead>
        <tbody>`;

    for (const c of clips) {
      html += `
          <tr>
            <td>${esc(c.name)}</td>
            <td>${c.slot_count}</td>
          </tr>`;
    }

    html += "</tbody></table>";
    el.innerHTML = html;
  }

  // --- Clip Metadata ---
  const CATEGORY_LABELS = {
    editorial: "Editorial / Production",
    camera: "Camera / Image",
    lens: "Lens / Optics",
    color: "Color / Grade",
    other: "Other",
  };

  const CATEGORY_ORDER = ["editorial", "camera", "lens", "color", "other"];

  const EDITORIAL_HIGHLIGHT_KEYS = new Set([
    "Scene", "Slate", "Take", "Episode", "Soundroll", "Camroll",
    "Comments", "Camera TC", "Sound TC", "Filename",
  ]);

  function renderClipMetadata(data) {
    const el = document.getElementById("clip-metadata-content");
    const clips = (data.master_mobs || []).filter(
      (c) => c.metadata && Object.keys(c.metadata).length > 0
    );

    if (clips.length === 0) {
      el.innerHTML = '<p class="text-muted">No clip metadata found (no UserComments or Attributes in this AAF).</p>';
      document.getElementById("section-clip-metadata").classList.add("hidden");
      return;
    }
    document.getElementById("section-clip-metadata").classList.remove("hidden");

    let html = "";
    for (const clip of clips) {
      const meta = clip.metadata;
      const summary = buildClipSummary(meta);

      html += `<div class="clip-meta-block">`;
      html += `<div class="clip-meta-header"><span class="clip-name">${esc(clip.name)}</span><span class="clip-summary">${esc(summary)}</span></div>`;
      html += `<div class="clip-meta-body">`;

      for (const cat of CATEGORY_ORDER) {
        const entries = meta[cat];
        if (!entries || Object.keys(entries).length === 0) continue;

        html += `<div class="meta-category">`;
        html += `<div class="meta-category-label">${CATEGORY_LABELS[cat]}</div>`;
        html += `<div class="meta-entries">`;

        const keys = Object.keys(entries);
        if (cat === "editorial") {
          keys.sort((a, b) => {
            const aH = EDITORIAL_HIGHLIGHT_KEYS.has(a) ? 0 : 1;
            const bH = EDITORIAL_HIGHLIGHT_KEYS.has(b) ? 0 : 1;
            return aH - bH || a.localeCompare(b);
          });
        }

        for (const key of keys) {
          const val = entries[key];
          if (val === "" || val === "??" || val === "-1" || val === "??:??:??:??") continue;
          html += `<span class="mk">${esc(key)}</span><span class="mv">${esc(val)}</span>`;
        }

        html += `</div></div>`;
      }

      html += `</div></div>`;
    }

    el.innerHTML = html;

    el.querySelectorAll(".clip-meta-header").forEach((header) => {
      header.addEventListener("click", () => {
        header.classList.toggle("open");
        header.nextElementSibling.classList.toggle("open");
      });
    });
  }

  function buildClipSummary(meta) {
    const ed = meta.editorial || {};
    const parts = [];
    if (ed["Scene"]) parts.push(`S${ed["Scene"]}`);
    if (ed["Slate"]) parts.push(`SL${ed["Slate"]}`);
    if (ed["Take"]) parts.push(`T${ed["Take"]}`);
    if (ed["Soundroll"]) parts.push(ed["Soundroll"]);

    const cam = meta.camera || {};
    if (cam["cameraModel"] || cam["CameraType"]) {
      parts.push(cam["cameraModel"] || cam["CameraType"]);
    }

    return parts.join(" · ");
  }

  // --- Source References ---
  function renderSources(data) {
    const el = document.getElementById("sources-content");
    const sources = data.source_mobs || [];

    const withLocators = sources.filter((s) => s.locators && s.locators.length > 0);
    const withTape = sources.filter(
      (s) => s.descriptor && s.descriptor.type === "tape"
    );
    const mediaRefs = sources.filter(
      (s) => s.descriptor && (s.descriptor.type === "video" || s.descriptor.type === "audio")
    );

    let html = "";

    if (withLocators.length > 0) {
      html += `
        <div class="collapsible-header open"><strong>Network Locators</strong> <span class="text-muted">(${withLocators.length})</span></div>
        <div class="collapsible-body open">
          <table class="data-table">
            <thead><tr><th>Type</th><th>Path</th></tr></thead>
            <tbody>`;

      const seen = new Set();
      for (const s of withLocators) {
        for (const loc of s.locators) {
          if (seen.has(loc.path)) continue;
          seen.add(loc.path);
          html += `<tr><td>${s.descriptor ? s.descriptor.type : "—"}</td><td>${esc(loc.path)}</td></tr>`;
        }
      }

      html += "</tbody></table></div>";
    }

    if (withTape.length > 0) {
      html += `
        <div style="margin-top: 1rem;">
          <div class="collapsible-header"><strong>Tape Sources</strong> <span class="text-muted">(${withTape.length})</span></div>
          <div class="collapsible-body">
            <table class="data-table">
              <thead><tr><th>Name</th><th>Mob ID</th></tr></thead>
              <tbody>`;

      for (const s of withTape) {
        html += `<tr><td>${esc(s.name)}</td><td class="text-muted">${esc(s.mob_id)}</td></tr>`;
      }

      html += "</tbody></table></div></div>";
    }

    if (mediaRefs.length > 0) {
      html += `
        <div style="margin-top: 1rem;">
          <div class="collapsible-header"><strong>Media Source Mobs</strong> <span class="text-muted">(${mediaRefs.length})</span></div>
          <div class="collapsible-body">
            <table class="data-table">
              <thead><tr><th>Type</th><th>Details</th><th>Length</th></tr></thead>
              <tbody>`;

      for (const s of mediaRefs) {
        const d = s.descriptor;
        let details = "";
        if (d.type === "video") {
          details = `${d.stored_width}x${d.stored_height} ${d.component_width || "?"}bit`;
        } else if (d.type === "audio") {
          details = `${d.sample_rate ? (d.sample_rate / 1000).toFixed(1) + "kHz" : "?"} ${d.quantization_bits || "?"}bit ch${d.channels || "?"}`;
        }
        html += `<tr><td>${d.type}</td><td>${details}</td><td>${d.length || "—"}</td></tr>`;
      }

      html += "</tbody></table></div></div>";
    }

    if (!html) {
      html = '<p class="text-muted">No source references found.</p>';
    }

    el.innerHTML = html;

    el.querySelectorAll(".collapsible-header").forEach((header) => {
      header.addEventListener("click", () => {
        header.classList.toggle("open");
        header.nextElementSibling.classList.toggle("open");
      });
    });
  }

  // --- Helpers ---
  function esc(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function subsamplingStr(vf) {
    const h = vf.horizontal_subsampling;
    const v = vf.vertical_subsampling;
    if (h === 2 && v === 1) return "4:2:2";
    if (h === 2 && v === 2) return "4:2:0";
    if (h === 1 && v === 1) return "4:4:4";
    if (h === 4 && v === 1) return "4:1:1";
    if (h != null && v != null) return `${h}:${v}`;
    return "—";
  }

  function cleanEnum(val) {
    if (!val) return "—";
    return String(val)
      .replace(/^.*_/, "")
      .replace(/([a-z])([A-Z])/g, "$1 $2");
  }
})();
