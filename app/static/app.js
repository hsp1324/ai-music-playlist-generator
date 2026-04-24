const state = {
  tracks: [],
  workspaces: [],
  selectedWorkspaceId: "",
  drawerOpen: false,
};

const workspaceGrid = document.querySelector("#workspace-grid");
const detailPanel = document.querySelector("#workspace-detail-panel");
const detailTitle = document.querySelector("#detail-title");
const detailMeta = document.querySelector("#detail-meta");
const detailActions = document.querySelector("#detail-actions");
const detailLinks = document.querySelector("#detail-links");
const queueGrid = document.querySelector("#queue-grid");
const approvedGrid = document.querySelector("#approved-grid");
const queueTitle = document.querySelector("#queue-title");
const approvedTitle = document.querySelector("#approved-title");
const toolbarSummaryText = document.querySelector("#toolbar-summary-text");
const menuToggleButton = document.querySelector("#menu-toggle-button");
const utilityDrawer = document.querySelector("#utility-drawer");
const refreshButton = document.querySelector("#refresh-button");
const quickUploadInput = document.querySelector("#quick-upload-input");
const quickUploadPickButton = document.querySelector("#quick-upload-pick-button");
const quickUploadSubmitButton = document.querySelector("#quick-upload-submit-button");
const quickUploadWorkspaceSelect = document.querySelector("#quick-upload-workspace-select");
const quickUploadFileList = document.querySelector("#quick-upload-file-list");
const quickUploadStatus = document.querySelector("#quick-upload-status");
const uploadDropzone = document.querySelector("#upload-dropzone");
const trackForm = document.querySelector("#track-form");
const trackWorkspaceSelect = document.querySelector("#track-workspace-select");
const workspaceForm = document.querySelector("#workspace-form");
const trackStatus = document.querySelector("#track-status");
const workspaceStatus = document.querySelector("#workspace-status");
const sessionTitle = document.querySelector("#session-title");
const sessionMessage = document.querySelector("#session-message");
const sessionOpenButton = document.querySelector("#session-open-button");
const sessionAlertButton = document.querySelector("#session-alert-button");
const youtubeTitle = document.querySelector("#youtube-title");
const youtubeMessage = document.querySelector("#youtube-message");
const youtubeConnectButton = document.querySelector("#youtube-connect-button");
const workspaceTileTemplate = document.querySelector("#workspace-tile-template");
const queueTemplate = document.querySelector("#queue-card-template");
const approvedCardTemplate = document.querySelector("#approved-card-template");

let quickUploadFiles = [];

function normalizeMediaUrl(path) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (path.startsWith("storage/")) return encodeURI(`/media/${path.slice("storage/".length)}`);
  return encodeURI(path);
}

function formatDuration(seconds) {
  if (!seconds) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

function setStatus(el, payload) {
  el.textContent = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
}

function displayTitle(value, fallback = "Untitled") {
  if (!value) return fallback;
  const cleaned = String(value).replace(/\s+[a-f0-9]{24,}$/i, "").trim();
  return cleaned || fallback;
}

function shortText(value, maxLength = 120) {
  if (!value) return "";
  const normalized = String(value).replace(/\s+/g, " ").trim();
  if (normalized.length <= maxLength) return normalized;
  return `${normalized.slice(0, maxLength - 1).trimEnd()}…`;
}

function statusLabel(value) {
  return String(value || "").replaceAll("_", " ");
}

function fileStem(filename) {
  const value = String(filename || "").trim();
  return value.replace(/\.[^.]+$/, "") || "Uploaded Track";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!response.ok) {
    throw new Error(typeof data === "string" ? data : JSON.stringify(data, null, 2));
  }
  return data;
}

function buildLink(label, href) {
  const anchor = document.createElement("a");
  anchor.className = "pill-link";
  anchor.href = href;
  anchor.target = "_blank";
  anchor.rel = "noreferrer";
  anchor.textContent = label;
  return anchor;
}

function actionButton(label, className, handler) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await handler();
      await refresh();
    } catch (error) {
      alert(error.message);
      button.disabled = false;
    }
  });
  return button;
}

function activeWorkspace() {
  return state.workspaces.find((workspace) => workspace.id === state.selectedWorkspaceId) || null;
}

function visibleWorkspaces() {
  return state.workspaces.filter((workspace) => !workspace.hidden);
}

function ensureSelectedWorkspace() {
  const visible = visibleWorkspaces();
  if (visible.some((workspace) => workspace.id === state.selectedWorkspaceId)) return;
  state.selectedWorkspaceId = visible[0]?.id || "";
}

function workspaceOptions(selectedId = "") {
  const defaultOption = `<option value="">Choose workspace</option>`;
  const options = visibleWorkspaces()
    .map((workspace) => {
      const selected = workspace.id === selectedId ? "selected" : "";
      return `<option value="${workspace.id}" ${selected}>${displayTitle(workspace.title)}</option>`;
    })
    .join("");
  return `${defaultOption}${options}`;
}

function pendingTracks(workspaceId = "") {
  return state.tracks.filter((track) => {
    if (!["pending_review", "held"].includes(track.status)) return false;
    if (!workspaceId) return true;
    return track.metadata_json?.pending_workspace_id === workspaceId;
  });
}

function toggleDrawer(forceOpen) {
  state.drawerOpen = typeof forceOpen === "boolean" ? forceOpen : !state.drawerOpen;
  utilityDrawer.hidden = !state.drawerOpen;
  menuToggleButton.setAttribute("aria-expanded", String(state.drawerOpen));
}

function updateToolbarSummary() {
  const pending = pendingTracks().length;
  const visible = visibleWorkspaces();
  const ready = visible.filter((workspace) => workspace.publish_ready && !workspace.publish_approved).length;
  toolbarSummaryText.textContent = `Queue ${pending} · Workspaces ${visible.length} · Ready ${ready}`;
}

function renderTrackWorkspaceOptions() {
  if (!trackWorkspaceSelect) return;
  const options = visibleWorkspaces()
    .map((workspace) => `<option value="${workspace.id}">${displayTitle(workspace.title)}</option>`)
    .join("");
  trackWorkspaceSelect.innerHTML = `<option value="">Unassigned Queue</option>${options}`;
  if (quickUploadWorkspaceSelect) {
    quickUploadWorkspaceSelect.innerHTML = `<option value="">Choose workspace</option>${options}`;
  }
}

function renderQuickUploadFiles() {
  if (!quickUploadFileList) return;
  if (!quickUploadFiles.length) {
    quickUploadFileList.textContent = "No files selected.";
    return;
  }
  quickUploadFileList.textContent = quickUploadFiles.map((file) => file.name).join("\n");
}

function setQuickUploadFiles(files) {
  quickUploadFiles = [...files];
  renderQuickUploadFiles();
}

async function submitQuickUpload() {
  if (!quickUploadFiles.length) {
    setStatus(quickUploadStatus, "파일을 먼저 선택하세요.");
    return;
  }
  if (!quickUploadWorkspaceSelect?.value) {
    setStatus(quickUploadStatus, "workspace를 먼저 선택하세요.");
    return;
  }

  quickUploadSubmitButton.disabled = true;
  const results = [];
  try {
    for (const file of quickUploadFiles) {
      const form = new FormData();
      form.append("title", fileStem(file.name));
      form.append("prompt", "manual quick upload");
      form.append("duration_seconds", "0");
      form.append("pending_workspace_id", quickUploadWorkspaceSelect.value);
      form.append("audio_file", file, file.name);
      const response = await fetch("/api/tracks/manual-upload", {
        method: "POST",
        body: form,
      });
      const text = await response.text();
      let result;
      try {
        result = text ? JSON.parse(text) : null;
      } catch {
        result = text;
      }
      if (!response.ok) {
        throw new Error(typeof result === "string" ? result : JSON.stringify(result, null, 2));
      }
      results.push({ title: result.title, status: result.status });
    }
    setStatus(quickUploadStatus, results);
    setQuickUploadFiles([]);
    if (quickUploadInput) {
      quickUploadInput.value = "";
    }
    await refresh();
  } catch (error) {
    setStatus(quickUploadStatus, error.message);
  } finally {
    quickUploadSubmitButton.disabled = false;
  }
}

function selectWorkspace(workspaceId, scrollIntoView = true) {
  state.selectedWorkspaceId = workspaceId;
  renderWorkspaceTiles();
  renderWorkspaceDetail();
  if (scrollIntoView && detailPanel && !detailPanel.hidden) {
    detailPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function renderWorkspaceTiles() {
  workspaceGrid.innerHTML = "";

  const visible = visibleWorkspaces();

  if (!visible.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "먼저 workspace를 하나 만들어 주세요.";
    workspaceGrid.appendChild(empty);
    return;
  }

  visible.forEach((workspace) => {
    const fragment = workspaceTileTemplate.content.cloneNode(true);
    const tile = fragment.querySelector(".workspace-tile");
    const mode = fragment.querySelector(".workspace-mode");
    const name = fragment.querySelector(".workspace-name");
    const stateEl = fragment.querySelector(".workspace-state");
    const copy = fragment.querySelector(".workspace-copy");
    const approvedStat = fragment.querySelector(".approved-stat");
    const pendingStat = fragment.querySelector(".pending-stat");
    const hint = fragment.querySelector(".workspace-hint");
    const moreButton = fragment.querySelector(".more-button");

    if (workspace.id === state.selectedWorkspaceId) {
      tile.classList.add("active");
    }

    mode.textContent = workspace.workspace_mode === "single_track_video" ? "Single Track" : "Playlist";
    name.textContent = displayTitle(workspace.title, "Untitled Workspace");
    stateEl.textContent = statusLabel(workspace.workflow_state);
    copy.textContent = shortText(workspace.description || "Ready to collect approved tracks.", 120);
    approvedStat.textContent = `${workspace.tracks.length} approved`;
    pendingStat.textContent = `${pendingTracks(workspace.id).length} in review`;

    hint.textContent = workspace.workspace_mode === "single_track_video"
      ? "Single release lane"
      : `${formatDuration(workspace.actual_duration_seconds)} / ${formatDuration(workspace.target_duration_seconds)}`;

    moreButton.addEventListener("click", (event) => {
      event.stopPropagation();
      selectWorkspace(workspace.id);
    });

    tile.addEventListener("click", () => selectWorkspace(workspace.id, false));
    workspaceGrid.appendChild(fragment);
  });
}

function renderWorkspaceDetail() {
  const workspace = activeWorkspace();
  const tracksForReview = workspace ? pendingTracks(workspace.id) : [];

  if (!workspace) {
    detailPanel.hidden = true;
    return;
  }

  detailPanel.hidden = false;
  detailTitle.textContent = displayTitle(workspace.title, "Workspace");
  detailMeta.textContent = `${workspace.workspace_mode === "single_track_video" ? "Single Track Video" : "Playlist Mix"} · ${statusLabel(workspace.workflow_state)} · ${workspace.tracks.length} approved`;
  queueTitle.textContent = `${displayTitle(workspace.title)} review queue`;
  approvedTitle.textContent = `${displayTitle(workspace.title)} approved tracks`;

  detailLinks.innerHTML = "";
  detailActions.innerHTML = "";
  queueGrid.innerHTML = "";
  approvedGrid.innerHTML = "";

  if (workspace.output_audio_path) {
    detailLinks.appendChild(buildLink("Rendered Audio", normalizeMediaUrl(workspace.output_audio_path)));
  }
  if (workspace.output_video_path) {
    detailLinks.appendChild(buildLink("Rendered Video", normalizeMediaUrl(workspace.output_video_path)));
  }
  if (workspace.cover_image_path) {
    detailLinks.appendChild(buildLink("Cover", normalizeMediaUrl(workspace.cover_image_path)));
  }

  if (workspace.publish_ready && !workspace.publish_approved) {
    detailActions.appendChild(
      actionButton("Approve Publish", "action-button primary-button", async () => {
        await api(`/api/playlists/${workspace.id}/approve-publish`, {
          method: "POST",
          body: JSON.stringify({
            actor: "web-ui",
            note: "Approved from workspace detail.",
          }),
        });
      })
    );
  } else if (workspace.publish_approved && !workspace.youtube_video_id) {
    const input = document.createElement("input");
    input.type = "text";
    input.className = "inline-input";
    input.placeholder = "YouTube video id";
    const button = actionButton("Mark Uploaded", "action-button secondary-button", async () => {
      await api(`/api/playlists/${workspace.id}/mark-uploaded`, {
        method: "POST",
        body: JSON.stringify({
          actor: "web-ui",
          youtube_video_id: input.value || null,
          note: "Marked uploaded from workspace detail.",
        }),
      });
    });
    detailActions.appendChild(input);
    detailActions.appendChild(button);
  }

  if (!tracksForReview.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "review를 기다리는 곡이 없습니다.";
    queueGrid.appendChild(empty);
  } else {
    tracksForReview.forEach((track) => {
      const fragment = queueTemplate.content.cloneNode(true);
      const card = fragment.querySelector(".queue-card");
      const image = fragment.querySelector(".track-art");
      const duration = fragment.querySelector(".track-duration");
      const title = fragment.querySelector(".track-title");
      const subtitle = fragment.querySelector(".track-subtitle");
      const status = fragment.querySelector(".track-status");
      const audio = fragment.querySelector(".track-audio");
      const prompt = fragment.querySelector(".track-prompt");
      const links = fragment.querySelector(".track-links");
      const actions = fragment.querySelector(".track-actions");
      const select = fragment.querySelector(".workspace-select");

      const imageUrl =
        track.metadata_json?.image_url ||
        "https://images.unsplash.com/photo-1516280440614-37939bbacd81?auto=format&fit=crop&w=900&q=80";
      const audioUrl = normalizeMediaUrl(track.audio_path) || track.preview_url || "";

      image.src = imageUrl;
      image.alt = displayTitle(track.title, "Track");
      duration.textContent = formatDuration(track.duration_seconds);
      title.textContent = displayTitle(track.title, "Untitled Track");
      subtitle.textContent = shortText(track.metadata_json?.tags || track.source_track_id || "manual candidate", 64);
      status.textContent = statusLabel(track.status);
      status.classList.add(track.status);
      prompt.textContent = shortText(track.prompt || "Prompt not provided.", 160);

      if (audioUrl) {
        audio.src = audioUrl;
      } else {
        audio.remove();
      }

      if (track.preview_url) links.appendChild(buildLink("Preview", track.preview_url));
      if (track.metadata_json?.source_audio_url) links.appendChild(buildLink("Source", track.metadata_json.source_audio_url));
      if (imageUrl) links.appendChild(buildLink("Cover", imageUrl));

      select.innerHTML = workspaceOptions(workspace.id);
      select.value = workspace.id;

      actions.appendChild(
        actionButton("Approve", "pill-action approve", async () => {
          if (!select.value) {
            throw new Error("Approve before choosing a workspace.");
          }
          await api(`/api/tracks/${track.id}/decisions`, {
            method: "POST",
            body: JSON.stringify({
              decision: "approve",
              source: "human",
              actor: "web-ui",
              rationale: "Approved from workspace detail.",
              playlist_id: select.value,
            }),
          });
        })
      );
      actions.appendChild(
        actionButton("Hold", "pill-action hold", async () => {
          await api(`/api/tracks/${track.id}/decisions`, {
            method: "POST",
            body: JSON.stringify({
              decision: "hold",
              source: "human",
              actor: "web-ui",
              rationale: "Held from workspace detail.",
            }),
          });
        })
      );
      actions.appendChild(
        actionButton("Reject", "pill-action reject", async () => {
          await api(`/api/tracks/${track.id}/decisions`, {
            method: "POST",
            body: JSON.stringify({
              decision: "reject",
              source: "human",
              actor: "web-ui",
              rationale: "Rejected from workspace detail.",
            }),
          });
        })
      );

      card.dataset.trackId = track.id;
      queueGrid.appendChild(fragment);
    });
  }

  if (!workspace.tracks.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "아직 승인된 곡이 없습니다.";
    approvedGrid.appendChild(empty);
    return;
  }

  workspace.tracks.forEach((track) => {
    const fragment = approvedCardTemplate.content.cloneNode(true);
    const title = fragment.querySelector(".approved-title");
    const meta = fragment.querySelector(".approved-meta");
    const duration = fragment.querySelector(".approved-duration");
    const audio = fragment.querySelector(".approved-audio");
    const links = fragment.querySelector(".approved-links");
    const actions = fragment.querySelector(".approved-actions");
    const audioUrl = normalizeMediaUrl(track.audio_path) || track.preview_url || "";

    title.textContent = displayTitle(track.title, "Untitled Track");
    meta.textContent = shortText(track.tags || "approved track", 80);
    duration.textContent = formatDuration(track.duration_seconds);

    if (audioUrl) {
      audio.src = audioUrl;
    } else {
      audio.remove();
    }
    if (track.preview_url) links.appendChild(buildLink("Preview", track.preview_url));
    actions.appendChild(
      actionButton("Hold", "pill-action hold", async () => {
        await api(`/api/tracks/${track.id}/return-to-review`, {
          method: "POST",
          body: JSON.stringify({
            playlist_id: workspace.id,
            actor: "web-ui",
            rationale: "Returned from approved tracks to awaiting approval.",
          }),
        });
      })
    );

    approvedGrid.appendChild(fragment);
  });
}

function renderSessionStatus(sessionStatus) {
  sessionTitle.textContent = `State: ${sessionStatus.state}`;
  sessionMessage.textContent = `${sessionStatus.message} Last sync: ${sessionStatus.last_synced_at || "never"}`;
}

function renderYouTubeStatus(youtubeStatus) {
  youtubeTitle.textContent = youtubeStatus.ready
    ? "YouTube connected"
    : youtubeStatus.configured
      ? "YouTube not authenticated"
      : "YouTube client secrets missing";
  youtubeMessage.textContent = youtubeStatus.ready
    ? `Token path: ${youtubeStatus.token_path}`
    : youtubeStatus.error
      ? youtubeStatus.error
      : youtubeStatus.configured
        ? "Press Connect once and finish the OAuth flow in your browser."
        : "Set AIMP_YOUTUBE_CLIENT_SECRETS_PATH in .env first.";
}

async function refresh() {
  const [tracks, workspaces, sessionStatus, youtubeStatus] = await Promise.all([
    api("/api/tracks"),
    api("/api/playlists/workspaces"),
    api("/api/suno/session-status"),
    api("/api/youtube/status"),
  ]);
  state.tracks = tracks;
  state.workspaces = workspaces;
  ensureSelectedWorkspace();
  updateToolbarSummary();
  renderTrackWorkspaceOptions();
  renderSessionStatus(sessionStatus);
  renderYouTubeStatus(youtubeStatus);
  renderWorkspaceTiles();
  renderWorkspaceDetail();
}

trackForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(trackForm);
  try {
    const response = await fetch("/api/tracks/manual-upload", {
      method: "POST",
      body: form,
    });
    const text = await response.text();
    let result;
    try {
      result = text ? JSON.parse(text) : null;
    } catch {
      result = text;
    }
    if (!response.ok) {
      throw new Error(typeof result === "string" ? result : JSON.stringify(result, null, 2));
    }
    setStatus(trackStatus, result);
    trackForm.reset();
    await refresh();
  } catch (error) {
    setStatus(trackStatus, error.message);
  }
});

workspaceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(workspaceForm);
  try {
    const result = await api("/api/playlists/workspaces", {
      method: "POST",
      body: JSON.stringify({
        title: form.get("title"),
        target_duration_seconds: Number(form.get("target_duration_seconds")),
        workspace_mode: form.get("workspace_mode"),
        auto_publish_when_ready: form.get("auto_publish_when_ready") === "true",
        description: form.get("description"),
        cover_prompt: form.get("cover_prompt"),
        dreamina_prompt: form.get("dreamina_prompt"),
      }),
    });
    setStatus(workspaceStatus, result);
    await refresh();
  } catch (error) {
    setStatus(workspaceStatus, error.message);
  }
});

menuToggleButton.addEventListener("click", () => toggleDrawer());
refreshButton.addEventListener("click", () => refresh().catch((error) => alert(error.message)));
quickUploadPickButton?.addEventListener("click", () => quickUploadInput?.click());
quickUploadInput?.addEventListener("change", (event) => {
  setQuickUploadFiles(event.target.files || []);
});
quickUploadSubmitButton?.addEventListener("click", () => {
  submitQuickUpload().catch((error) => setStatus(quickUploadStatus, error.message));
});

uploadDropzone?.addEventListener("dragover", (event) => {
  event.preventDefault();
  uploadDropzone.classList.add("dragover");
});

uploadDropzone?.addEventListener("dragleave", () => {
  uploadDropzone.classList.remove("dragover");
});

uploadDropzone?.addEventListener("drop", (event) => {
  event.preventDefault();
  uploadDropzone.classList.remove("dragover");
  if (event.dataTransfer?.files?.length) {
    setQuickUploadFiles(event.dataTransfer.files);
  }
});

sessionOpenButton.addEventListener("click", async () => {
  try {
    const result = await api("/api/suno/session/open-login", { method: "POST" });
    setStatus(trackStatus, result);
    await refresh();
  } catch (error) {
    alert(error.message);
  }
});

sessionAlertButton.addEventListener("click", async () => {
  try {
    const result = await api("/api/suno/session/notify-expired", { method: "POST" });
    setStatus(trackStatus, result);
    await refresh();
  } catch (error) {
    alert(error.message);
  }
});

youtubeConnectButton.addEventListener("click", async () => {
  try {
    const result = await api("/api/youtube/connect", { method: "POST" });
    setStatus(workspaceStatus, result);
    await refresh();
  } catch (error) {
    alert(error.message);
  }
});

refresh().catch((error) => {
  setStatus(trackStatus, error.message);
});

window.setInterval(() => {
  refresh().catch(() => {});
}, 15000);
