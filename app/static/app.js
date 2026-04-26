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
let dragScrollFrame = null;
let dragScrollSpeed = 0;

function normalizeMediaUrl(path) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const storageMarker = "/storage/";
  const storageIndex = path.indexOf(storageMarker);
  if (storageIndex >= 0) return encodeURI(`/media/${path.slice(storageIndex + storageMarker.length)}`);
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

function setTextStatus(el, value) {
  el.textContent = value;
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

function formatTimestamp(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function fileStem(filename) {
  const value = String(filename || "").trim();
  return value.replace(/\.[^.]+$/, "") || "Uploaded Track";
}

const fallbackTrackArtUrl =
  "https://images.unsplash.com/photo-1516280440614-37939bbacd81?auto=format&fit=crop&w=900&q=80";

function trackCoverUrl(track) {
  return normalizeMediaUrl(track?.metadata_json?.image_url || track?.image_url) || fallbackTrackArtUrl;
}

function trackCoverLabel(track) {
  return track?.metadata_json?.image_url || track?.image_url ? "커버 있음" : "커버 없음";
}

function uploadResultLine(track, index) {
  return `${index + 1}. ${displayTitle(track.title)} | ${statusLabel(track.status)} | ${formatDuration(
    track.duration_seconds
  )} | ${trackCoverLabel(track)}`;
}

function setQuickUploadProgress(total, results, failures, activeFileName = "") {
  const lines = [];
  const finished = results.length + failures.length;
  if (activeFileName) {
    lines.push(`업로드 중 ${finished + 1}/${total}: ${activeFileName}`);
  } else {
    lines.push(`업로드 결과: 성공 ${results.length}/${total}${failures.length ? `, 실패 ${failures.length}` : ""}`);
  }

  if (results.length) {
    lines.push("");
    lines.push("성공");
    results.forEach((track, index) => lines.push(uploadResultLine(track, index)));
  }

  if (failures.length) {
    lines.push("");
    lines.push("실패");
    failures.forEach((failure, index) => lines.push(`${index + 1}. ${failure.name} | ${failure.message}`));
  }

  setTextStatus(quickUploadStatus, lines.join("\n"));
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
      await refreshBoard();
    } catch (error) {
      alert(error.message);
      button.disabled = false;
    }
  });
  return button;
}

async function reorderApprovedTrack(workspace, currentIndex, direction) {
  const targetIndex = currentIndex + direction;
  if (targetIndex < 0 || targetIndex >= workspace.tracks.length) return;

  const trackIds = workspace.tracks.map((track) => track.id);
  [trackIds[currentIndex], trackIds[targetIndex]] = [trackIds[targetIndex], trackIds[currentIndex]];
  await saveApprovedTrackOrder(workspace, trackIds);
}

async function saveApprovedTrackOrder(workspace, trackIds) {
  await api(`/api/playlists/${workspace.id}/tracks/reorder`, {
    method: "POST",
    body: JSON.stringify({
      track_ids: trackIds,
      actor: "web-ui",
    }),
  });
}

function dropPlacement(card, event) {
  const bounds = card.getBoundingClientRect();
  const midpoint = bounds.top + bounds.height / 2;
  return event.clientY < midpoint ? "before" : "after";
}

async function reorderApprovedTrackByDrop(workspace, draggedTrackId, targetTrackId, placement) {
  if (!draggedTrackId || !targetTrackId || draggedTrackId === targetTrackId) return;
  const trackIds = workspace.tracks.map((track) => track.id);
  const fromIndex = trackIds.indexOf(draggedTrackId);
  const targetIndex = trackIds.indexOf(targetTrackId);
  if (fromIndex < 0 || targetIndex < 0) return;

  const [dragged] = trackIds.splice(fromIndex, 1);
  const targetIndexAfterRemoval = trackIds.indexOf(targetTrackId);
  const insertIndex = placement === "after" ? targetIndexAfterRemoval + 1 : targetIndexAfterRemoval;
  trackIds.splice(insertIndex, 0, dragged);
  await saveApprovedTrackOrder(workspace, trackIds);
}

function setDropPlacement(card, placement) {
  card.classList.toggle("drop-before", placement === "before");
  card.classList.toggle("drop-after", placement === "after");
}

function clearDropPlacement(card) {
  card.classList.remove("drop-before", "drop-after");
}

function renderJobStatusText(workspace) {
  const job = workspace.render_job;
  if (!job) {
    return workspace.output_audio_path
      ? "Render complete. No recent job metadata."
      : "No render has been queued yet.";
  }

  const status = statusLabel(job.status);
  if (job.status === "queued") return `Render queued at ${formatTimestamp(job.created_at) || "now"}.`;
  if (job.status === "running") return `Rendering started ${formatTimestamp(job.started_at) || "just now"}.`;
  if (job.status === "succeeded") return `Render complete at ${formatTimestamp(job.finished_at) || "recently"}.`;
  if (job.status === "failed") return `Render failed: ${job.error_text || "unknown error"}`;
  return `Render job: ${status}`;
}

function appendRenderStatus(workspace) {
  const card = document.createElement("div");
  const job = workspace.render_job;
  const status = job?.status || (workspace.output_audio_path ? "succeeded" : "idle");
  card.className = `render-status render-${status}`;

  const title = document.createElement("strong");
  title.textContent = workspace.output_audio_path
    ? "Rendered Audio Ready"
    : workspace.status === "building"
      ? "Rendering Audio"
      : "Audio Render";

  const message = document.createElement("span");
  message.textContent = renderJobStatusText(workspace);

  card.appendChild(title);
  card.appendChild(message);
  detailLinks.appendChild(card);
}

function appendRenderedAudioPlayer(workspace) {
  const audioUrl = normalizeMediaUrl(workspace.output_audio_path);
  if (!audioUrl) return;

  const player = document.createElement("div");
  player.className = "render-player";

  const art = document.createElement("img");
  art.className = "render-player-art";
  art.src = normalizeMediaUrl(workspace.cover_image_path) || fallbackTrackArtUrl;
  art.alt = `${displayTitle(workspace.title)} cover`;

  const body = document.createElement("div");
  body.className = "render-player-body";

  const copy = document.createElement("div");
  copy.className = "render-player-copy";

  const title = document.createElement("strong");
  title.textContent = "Rendered Mix";

  const meta = document.createElement("span");
  const trackCount = `${workspace.tracks.length} track${workspace.tracks.length === 1 ? "" : "s"}`;
  meta.textContent = `${formatDuration(workspace.actual_duration_seconds)} · ${trackCount}`;

  const actions = document.createElement("div");
  actions.className = "render-player-actions";

  const audio = document.createElement("audio");
  audio.controls = true;
  audio.preload = "none";
  audio.src = audioUrl;

  copy.appendChild(title);
  copy.appendChild(meta);
  actions.appendChild(audio);
  actions.appendChild(buildLink("Open File", audioUrl));
  body.appendChild(copy);
  body.appendChild(actions);
  player.appendChild(art);
  player.appendChild(body);
  detailLinks.appendChild(player);
}

function stopDragAutoScroll() {
  dragScrollSpeed = 0;
  if (dragScrollFrame) {
    window.cancelAnimationFrame(dragScrollFrame);
    dragScrollFrame = null;
  }
}

function runDragAutoScroll() {
  if (dragScrollSpeed) {
    window.scrollBy({ top: dragScrollSpeed, behavior: "auto" });
    dragScrollFrame = window.requestAnimationFrame(runDragAutoScroll);
  } else {
    dragScrollFrame = null;
  }
}

function updateDragAutoScroll(event) {
  const edgeSize = Math.min(140, window.innerHeight * 0.2);
  const maxSpeed = 22;
  let nextSpeed = 0;

  if (event.clientY < edgeSize) {
    nextSpeed = -Math.ceil(((edgeSize - event.clientY) / edgeSize) * maxSpeed);
  } else if (window.innerHeight - event.clientY < edgeSize) {
    nextSpeed = Math.ceil(((edgeSize - (window.innerHeight - event.clientY)) / edgeSize) * maxSpeed);
  }

  dragScrollSpeed = nextSpeed;
  if (dragScrollSpeed && !dragScrollFrame) {
    dragScrollFrame = window.requestAnimationFrame(runDragAutoScroll);
  } else if (!dragScrollSpeed) {
    stopDragAutoScroll();
  }
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
  toolbarSummaryText.textContent = `Review ${pending} · Workspaces ${visible.length} · Ready ${ready}`;
}

function renderTrackWorkspaceOptions() {
  if (!trackWorkspaceSelect) return;
  const visible = visibleWorkspaces();
  const options = visible
    .map((workspace) => `<option value="${workspace.id}">${displayTitle(workspace.title)}</option>`)
    .join("");
  trackWorkspaceSelect.innerHTML = `<option value="">Unassigned Queue</option>${options}`;
  if (quickUploadWorkspaceSelect) {
    const currentQuickUploadWorkspace = quickUploadWorkspaceSelect.value;
    quickUploadWorkspaceSelect.innerHTML = `<option value="">Choose workspace</option>${options}`;
    if (visible.some((workspace) => workspace.id === currentQuickUploadWorkspace)) {
      quickUploadWorkspaceSelect.value = currentQuickUploadWorkspace;
    }
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
  if (quickUploadFiles.length) {
    setTextStatus(quickUploadStatus, `${quickUploadFiles.length}개 파일 준비됨. workspace를 선택하고 Upload Audio를 누르세요.`);
  }
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
  const failures = [];
  const workspaceId = quickUploadWorkspaceSelect.value;
  const failedFiles = [];
  state.selectedWorkspaceId = workspaceId;
  try {
    for (const [index, file] of quickUploadFiles.entries()) {
      setQuickUploadProgress(quickUploadFiles.length, results, failures, file.name);
      try {
        const form = new FormData();
        form.append("title", fileStem(file.name));
        form.append("prompt", "manual quick upload");
        form.append("duration_seconds", "0");
        form.append("pending_workspace_id", workspaceId);
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
        results.push(result);
        setQuickUploadProgress(quickUploadFiles.length, results, failures);
        refreshBoard().catch(() => {});
      } catch (error) {
        failures.push({ name: file.name, message: error.message });
        failedFiles.push(file);
        setQuickUploadProgress(quickUploadFiles.length, results, failures);
      }
    }
    await refreshBoard();
    setQuickUploadProgress(quickUploadFiles.length, results, failures);
    if (!failures.length) {
      quickUploadFiles = [];
      renderQuickUploadFiles();
      setTextStatus(
        quickUploadStatus,
        `${quickUploadStatus.textContent}\n\nworkspace queue에 반영됐습니다. Slack 알림은 백그라운드에서 전송됩니다.`
      );
    } else {
      quickUploadFiles = failedFiles;
      renderQuickUploadFiles();
      setTextStatus(
        quickUploadStatus,
        `${quickUploadStatus.textContent}\n\n실패한 파일만 목록에 남겼습니다. 다시 Upload Audio를 누르면 재시도합니다.`
      );
    }
    if (quickUploadInput && !failures.length) {
      quickUploadInput.value = "";
    }
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
  const renderState = workspace.output_audio_path
    ? "rendered"
    : workspace.status === "building"
      ? "rendering"
      : "not rendered";
  detailMeta.textContent = `${workspace.workspace_mode === "single_track_video" ? "Single Track Video" : "Playlist Mix"} · ${statusLabel(workspace.workflow_state)} · ${workspace.tracks.length} approved · ${renderState}`;
  queueTitle.textContent = `${displayTitle(workspace.title)} review queue`;
  approvedTitle.textContent = `${displayTitle(workspace.title)} approved tracks`;

  detailLinks.innerHTML = "";
  detailActions.innerHTML = "";
  queueGrid.innerHTML = "";
  approvedGrid.innerHTML = "";

  appendRenderStatus(workspace);
  appendRenderedAudioPlayer(workspace);
  if (workspace.output_video_path) {
    detailLinks.appendChild(buildLink("Rendered Video", normalizeMediaUrl(workspace.output_video_path)));
  }

  if (workspace.tracks.length) {
    if (workspace.status === "building") {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "action-button secondary-button";
      button.textContent = "Rendering Audio...";
      button.disabled = true;
      detailActions.appendChild(button);
    } else {
      detailActions.appendChild(
        actionButton(
          workspace.output_audio_path ? "Re-render Audio" : "Render Audio",
          "action-button secondary-button",
          async () => {
            await api(`/api/playlists/${workspace.id}/render-audio`, {
              method: "POST",
              body: JSON.stringify({
                actor: "web-ui",
              }),
            });
          }
        )
      );
    }
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

      const imageUrl = trackCoverUrl(track);
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
      if (track.metadata_json?.image_url) links.appendChild(buildLink("Cover", imageUrl));

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

  workspace.tracks.forEach((track, index) => {
    const fragment = approvedCardTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".approved-card");
    const image = fragment.querySelector(".approved-art");
    const title = fragment.querySelector(".approved-title");
    const meta = fragment.querySelector(".approved-meta");
    const duration = fragment.querySelector(".approved-duration");
    const audio = fragment.querySelector(".approved-audio");
    const links = fragment.querySelector(".approved-links");
    const actions = fragment.querySelector(".approved-actions");
    const audioUrl = normalizeMediaUrl(track.audio_path) || track.preview_url || "";
    const imageUrl = trackCoverUrl(track);

    card.dataset.trackId = track.id;
    if (workspace.tracks.length > 1) {
      card.draggable = true;
      card.addEventListener("dragstart", (event) => {
        card.classList.add("dragging");
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", track.id);
      });
      card.addEventListener("dragend", () => {
        card.classList.remove("dragging");
        clearDropPlacement(card);
        stopDragAutoScroll();
      });
      card.addEventListener("dragover", (event) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        updateDragAutoScroll(event);
        setDropPlacement(card, dropPlacement(card, event));
      });
      card.addEventListener("dragleave", () => {
        clearDropPlacement(card);
      });
      card.addEventListener("drop", (event) => {
        event.preventDefault();
        stopDragAutoScroll();
        const placement = dropPlacement(card, event);
        clearDropPlacement(card);
        const draggedTrackId = event.dataTransfer.getData("text/plain");
        reorderApprovedTrackByDrop(workspace, draggedTrackId, track.id, placement)
          .then(() => refreshBoard())
          .catch((error) => alert(error.message));
      });
    }

    image.src = imageUrl;
    image.alt = displayTitle(track.title, "Track");
    title.textContent = displayTitle(track.title, "Untitled Track");
    meta.textContent = shortText(track.tags || "approved track", 80);
    duration.textContent = formatDuration(track.duration_seconds);

    if (audioUrl) {
      audio.src = audioUrl;
    } else {
      audio.remove();
    }
    if (track.preview_url) links.appendChild(buildLink("Preview", track.preview_url));
    if (track.image_url) links.appendChild(buildLink("Cover", imageUrl));
    if (workspace.tracks.length > 1) {
      const upButton = actionButton("Up", "pill-action reorder", async () => {
        await reorderApprovedTrack(workspace, index, -1);
      });
      upButton.disabled = index === 0;
      actions.appendChild(upButton);

      const downButton = actionButton("Down", "pill-action reorder", async () => {
        await reorderApprovedTrack(workspace, index, 1);
      });
      downButton.disabled = index === workspace.tracks.length - 1;
      actions.appendChild(downButton);
    }
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

function applyBoardData(tracks, workspaces) {
  state.tracks = tracks;
  state.workspaces = workspaces;
  ensureSelectedWorkspace();
  updateToolbarSummary();
  renderTrackWorkspaceOptions();
  renderWorkspaceTiles();
  renderWorkspaceDetail();
}

async function refreshBoard() {
  const [tracks, workspaces] = await Promise.all([
    api("/api/tracks"),
    api("/api/playlists/workspaces"),
  ]);
  applyBoardData(tracks, workspaces);
}

async function refresh() {
  const [tracks, workspaces, sessionStatus, youtubeStatus] = await Promise.all([
    api("/api/tracks"),
    api("/api/playlists/workspaces"),
    api("/api/suno/session-status"),
    api("/api/youtube/status"),
  ]);
  applyBoardData(tracks, workspaces);
  renderSessionStatus(sessionStatus);
  renderYouTubeStatus(youtubeStatus);
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
    setTextStatus(
      trackStatus,
      `추가 완료: ${displayTitle(result.title)}\n상태: ${statusLabel(result.status)}\n길이: ${formatDuration(
        result.duration_seconds
      )}\n${trackCoverLabel(result)}`
    );
    if (result.metadata_json?.pending_workspace_id) {
      state.selectedWorkspaceId = result.metadata_json.pending_workspace_id;
    }
    trackForm.reset();
    await refreshBoard();
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
