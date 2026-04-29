const initialReleaseId = new URLSearchParams(window.location.search).get("release") || "";

const state = {
  tracks: [],
  workspaces: [],
  selectedWorkspaceId: initialReleaseId,
  drawerOpen: false,
  releaseFocus: Boolean(initialReleaseId),
  autoRefreshDeferred: false,
  autoRefreshInFlight: false,
};

const appHeader = document.querySelector(".app-header");
const quickUploadPanel = document.querySelector(".quick-upload-panel");
const boardShell = document.querySelector(".board-shell");
const workspaceGrid = document.querySelector("#workspace-grid");
const workspaceSection = document.querySelector(".workspace-section");
const archivedWorkspaceSection = document.querySelector("#archived-workspace-section");
const archivedWorkspaceGrid = document.querySelector("#archived-workspace-grid");
const detailPanel = document.querySelector("#workspace-detail-panel");
const detailTitle = document.querySelector("#detail-title");
const detailMeta = document.querySelector("#detail-meta");
const detailActions = document.querySelector("#detail-actions");
const detailPipeline = document.querySelector("#detail-pipeline");
const detailLinks = document.querySelector("#detail-links");
const detailColumns = document.querySelector("#detail-columns");
const approvedColumn = document.querySelector("#approved-column");
const queueColumn = document.querySelector("#queue-column");
const queueGrid = document.querySelector("#queue-grid");
const approvedGrid = document.querySelector("#approved-grid");
const queueTitle = document.querySelector("#queue-title");
const approvedTitle = document.querySelector("#approved-title");
const toolbarSummaryText = document.querySelector("#toolbar-summary-text");
const menuToggleButton = document.querySelector("#menu-toggle-button");
const utilityDrawer = document.querySelector("#utility-drawer");
const refreshButton = document.querySelector("#refresh-button");
const quickUploadInput = document.querySelector("#quick-upload-input");
const quickUploadCoverInput = document.querySelector("#quick-upload-cover-input");
const quickUploadPickButton = document.querySelector("#quick-upload-pick-button");
const quickUploadCoverPickButton = document.querySelector("#quick-upload-cover-pick-button");
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
const QUICK_UPLOAD_NEW_SINGLE_VALUE = "__new_single_release__";
const AUTO_REFRESH_INTERVAL_MS = 15000;

let quickUploadFiles = [];
let quickUploadCoverFiles = [];
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

function formatLongDuration(seconds) {
  if (!Number.isFinite(Number(seconds))) return "";
  const total = Math.max(Math.round(Number(seconds)), 0);
  const hours = Math.floor(total / 3600);
  const mins = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hours) return `${hours}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

function setStatus(el, payload) {
  el.textContent = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
}

function setTextStatus(el, value) {
  el.textContent = value;
}

function isAudioPlaybackActive() {
  return [...document.querySelectorAll("audio")].some((audio) => !audio.paused && !audio.ended);
}

async function autoRefresh() {
  if (document.hidden || isAudioPlaybackActive()) {
    state.autoRefreshDeferred = true;
    return;
  }
  if (state.autoRefreshInFlight) return;

  state.autoRefreshInFlight = true;
  try {
    await refresh();
    state.autoRefreshDeferred = false;
  } finally {
    state.autoRefreshInFlight = false;
  }
}

function resumeDeferredAutoRefresh() {
  if (!state.autoRefreshDeferred) return;
  window.setTimeout(() => {
    if (!document.hidden && !isAudioPlaybackActive()) {
      autoRefresh().catch(() => {});
    }
  }, 750);
}

function pauseOtherAudioPlayers(activeAudio) {
  document.querySelectorAll("audio").forEach((audio) => {
    if (audio !== activeAudio && !audio.paused) {
      audio.pause();
    }
  });
}

function playNextAwaitingTrack(currentAudio) {
  if (!currentAudio?.dataset.autoplayQueue) return;
  const queueAudios = [...queueGrid.querySelectorAll("audio.track-audio")]
    .filter((audio) => audio.dataset.autoplayQueue === currentAudio.dataset.autoplayQueue && audio.src);
  const currentIndex = queueAudios.indexOf(currentAudio);
  if (currentIndex < 0 || currentIndex >= queueAudios.length - 1) return;

  const nextAudio = queueAudios[currentIndex + 1];
  window.setTimeout(() => {
    pauseOtherAudioPlayers(nextAudio);
    nextAudio.play().catch(() => {});
  }, 250);
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

function isSingleRelease(workspace) {
  return workspace?.workspace_mode === "single_track_video";
}

function releaseModeLabel(workspace) {
  return isSingleRelease(workspace) ? "Single Release" : "Playlist Release";
}

function releaseOptionLabel(workspace) {
  return `${displayTitle(workspace.title)} · ${isSingleRelease(workspace) ? "Single" : "Playlist"}`;
}

function updateReleaseUrl(releaseId, replace = false) {
  const url = new URL(window.location.href);
  if (releaseId) {
    url.searchParams.set("release", releaseId);
  } else {
    url.searchParams.delete("release");
  }
  const method = replace ? "replaceState" : "pushState";
  window.history[method]({ releaseId: releaseId || "" }, "", `${url.pathname}${url.search}${url.hash}`);
}

function renderLayoutMode() {
  document.body.classList.toggle("release-focus-mode", state.releaseFocus);
  if (appHeader) appHeader.hidden = state.releaseFocus;
  if (quickUploadPanel) quickUploadPanel.hidden = state.releaseFocus;
  if (workspaceSection) workspaceSection.hidden = state.releaseFocus;
  if (utilityDrawer) utilityDrawer.hidden = state.releaseFocus || !state.drawerOpen;
  if (boardShell) boardShell.classList.toggle("focus-board", state.releaseFocus);
}

function openWorkspaceFocus(workspaceId, replace = false) {
  state.selectedWorkspaceId = workspaceId;
  state.releaseFocus = true;
  updateReleaseUrl(workspaceId, replace);
  renderLayoutMode();
  renderWorkspaceTiles();
  renderWorkspaceDetail();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function closeWorkspaceFocus(replace = false) {
  state.releaseFocus = false;
  updateReleaseUrl("", replace);
  renderLayoutMode();
  renderWorkspaceTiles();
  renderWorkspaceDetail();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function isReleaseReviewStage(workspace) {
  const releaseReviewStates = new Set([
    "metadata_review",
    "publish_ready",
    "publish_queued",
    "ready_for_youtube",
    "ready_for_youtube_auth",
    "youtube_upload_failed",
    "uploaded",
  ]);
  return Boolean(
    workspace?.output_video_path
    || workspace?.youtube_title
    || workspace?.metadata_approved
    || workspace?.publish_approved
    || workspace?.youtube_video_id
    || releaseReviewStates.has(workspace?.workflow_state)
  );
}

function releasePipeline(workspace) {
  const workflowState = workspace.workflow_state || "collecting";
  const hasApprovedAudio = workspace.tracks.length > 0;
  const hasRenderedAudio = Boolean(workspace.output_audio_path);
  const hasCover = Boolean(workspace.cover_image_path);
  const coverApproved = Boolean(workspace.cover_approved);
  const hasVideo = Boolean(workspace.output_video_path);
  const metadataDrafted = Boolean(workspace.youtube_title);
  const metadataApproved = Boolean(workspace.metadata_approved);
  const uploaded = workflowState === "uploaded" || Boolean(workspace.youtube_video_id);
  const publishQueued = workflowState === "publish_queued";
  const readyForYouTube = ["ready_for_youtube", "ready_for_youtube_auth"].includes(workflowState);
  const metadataReady = uploaded || metadataApproved || readyForYouTube || workflowState === "youtube_upload_failed";

  const stages = [
    {
      key: "audio",
      label: "Audio",
      status: "current",
      detail: isSingleRelease(workspace) ? "한 곡을 approve하고 오디오를 확정하세요." : "곡을 approve하고 최종 순서를 확정하세요.",
    },
    {
      key: "cover",
      label: "Cover",
      status: "waiting",
      detail: "오디오 확정 후 16:9 cover를 준비합니다.",
    },
    {
      key: "video",
      label: "Video",
      status: "waiting",
      detail: "cover와 audio를 합쳐 YouTube용 영상을 만듭니다.",
    },
    {
      key: "metadata",
      label: "Metadata",
      status: "waiting",
      detail: "YouTube 제목, 설명, 태그를 확인합니다.",
    },
    {
      key: "publish",
      label: "Publish",
      status: "waiting",
      detail: "최종 승인 후 YouTube 업로드를 진행합니다.",
    },
  ];

  if (uploaded) {
    return stages.map((stage) => ({
      ...stage,
      status: "done",
      detail: stage.key === "publish" ? "Uploaded to YouTube." : stage.detail,
    }));
  }

  if (workflowState === "render_failed") {
    stages[0].status = "failed";
    stages[0].detail = workspace.note || "Audio render failed.";
  } else if (hasRenderedAudio) {
    stages[0].status = "done";
    stages[0].detail = isSingleRelease(workspace) ? "Single audio is ready." : "Playlist audio is rendered.";
  } else if (["render_queued", "rendering"].includes(workflowState) || workspace.status === "building") {
    stages[0].status = "current";
    stages[0].detail = "Audio render is running.";
  } else if (hasApprovedAudio) {
    stages[0].status = "current";
    stages[0].detail = isSingleRelease(workspace)
      ? "Use the approved source audio to continue."
      : "Approved tracks are ready to render.";
  }

  if (hasCover && coverApproved) {
    stages[1].status = "done";
    stages[1].detail = "Cover image is approved.";
  } else if (hasCover) {
    stages[1].status = "current";
    stages[1].detail = "Review and approve the generated cover.";
  } else if (hasRenderedAudio || publishQueued) {
    stages[1].status = "current";
    stages[1].detail = publishQueued ? "Cover and video build is queued." : "Cover image is the next review step.";
  }

  if (workflowState === "video_build_failed") {
    stages[2].status = "failed";
    stages[2].detail = workspace.note || "Video build failed.";
  } else if (hasVideo) {
    stages[2].status = "done";
    stages[2].detail = "Release video is ready.";
  } else if (coverApproved || ["video_queued", "video_rendering"].includes(workflowState)) {
    stages[2].status = "current";
    stages[2].detail = ["video_queued", "video_rendering"].includes(workflowState)
      ? "Video render is running."
      : "Render the YouTube video next.";
  }

  if (metadataReady) {
    stages[3].status = "done";
    stages[3].detail = metadataApproved ? "YouTube metadata is approved." : "YouTube metadata draft is ready.";
  } else if (metadataDrafted) {
    stages[3].status = "current";
    stages[3].detail = "Review and approve the YouTube metadata draft.";
  } else if (hasVideo) {
    stages[3].status = "current";
    stages[3].detail = "Generate title, description, and tags.";
  }

  if (uploaded) {
    stages[4].status = "done";
    stages[4].detail = "Uploaded to YouTube.";
  } else if (workflowState === "youtube_upload_failed") {
    stages[4].status = "failed";
    stages[4].detail = workspace.note || "YouTube upload failed.";
  } else if (publishQueued) {
    stages[4].status = "current";
    stages[4].detail = "Final publish job is queued.";
  } else if (readyForYouTube || metadataApproved) {
    stages[4].status = "current";
    stages[4].detail = workflowState === "ready_for_youtube_auth"
      ? "Connect YouTube, then publish."
      : "Ready for final publish check.";
  }

  let activeSeen = false;
  return stages.map((stage) => {
    if (stage.status === "failed" || stage.status === "current") {
      activeSeen = true;
      return stage;
    }
    if (!activeSeen && stage.status === "waiting") {
      activeSeen = true;
      return { ...stage, status: "current" };
    }
    return stage;
  });
}

function currentPipelineStage(workspace) {
  const stages = releasePipeline(workspace);
  return stages.find((stage) => ["failed", "current"].includes(stage.status)) || stages[stages.length - 1];
}

function renderPipeline(container, workspace, options = {}) {
  if (!container) return;
  container.innerHTML = "";
  const stages = releasePipeline(workspace);
  const rail = document.createElement("div");
  rail.className = options.compact ? "pipeline-rail compact-pipeline" : "pipeline-rail";

  stages.forEach((stage) => {
    const item = document.createElement("div");
    item.className = `pipeline-step ${stage.status}`;

    const marker = document.createElement("span");
    marker.className = "pipeline-marker";
    marker.textContent = stage.status === "done" ? "✓" : stage.status === "failed" ? "!" : "•";

    const label = document.createElement("span");
    label.className = "pipeline-label";
    label.textContent = stage.label;

    item.title = stage.detail;
    item.appendChild(marker);
    item.appendChild(label);
    rail.appendChild(item);
  });

  container.appendChild(rail);
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

function metadataTagsText(workspace) {
  return (workspace.youtube_tags || []).join(", ");
}

function parseMetadataTags(value) {
  return String(value || "")
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean)
    .slice(0, 15);
}

function metadataDraftValues() {
  const title = detailPanel.querySelector('[data-metadata-field="title"]')?.value?.trim();
  const description = detailPanel.querySelector('[data-metadata-field="description"]')?.value?.trim();
  const tags = parseMetadataTags(detailPanel.querySelector('[data-metadata-field="tags"]')?.value);
  return { title, description, tags };
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

async function uploadCoverFile(workspace, file) {
  const form = new FormData();
  form.append("actor", "web-ui");
  form.append("cover_file", file, file.name);
  const response = await fetch(`/api/playlists/${workspace.id}/cover/upload`, {
    method: "POST",
    body: form,
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

function pickCoverFile(workspace) {
  return new Promise((resolve, reject) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/png,image/jpeg,image/webp";
    input.addEventListener("change", async () => {
      const file = input.files?.[0];
      if (!file) {
        resolve(null);
        return;
      }
      try {
        const result = await uploadCoverFile(workspace, file);
        resolve(result);
      } catch (error) {
        reject(error);
      }
    }, { once: true });
    input.click();
  });
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
  if (job.status === "running") {
    const progress = job.progress || {};
    const message = progress.message || "";
    const percent = Number(progress.percent);
    const processed = Number(progress.processed_seconds);
    const total = Number(progress.total_seconds);
    const eta = Number(progress.eta_seconds);
    const parts = [];
    if (message) parts.push(message);
    if (!message && Number.isFinite(percent)) parts.push(`${job.type === "build_video" ? "Video" : "Audio"} rendering ${percent.toFixed(1)}%.`);
    if (Number.isFinite(processed) && Number.isFinite(total) && total > 0) {
      parts.push(`${formatLongDuration(processed)} / ${formatLongDuration(total)}`);
    }
    if (Number.isFinite(eta)) parts.push(`ETA ${formatLongDuration(eta)}`);
    if (parts.length) return parts.join(" · ");
    return `Rendering started ${formatTimestamp(job.started_at) || "just now"}.`;
  }
  if (job.status === "succeeded" && !workspace.output_audio_path) {
    return "Previous render is stale. Render again after the current audio selection is ready.";
  }
  if (job.status === "succeeded") {
    const kind = job.type === "build_video" ? "Video" : "Audio";
    return `${kind} render complete at ${formatTimestamp(job.finished_at) || "recently"}.`;
  }
  if (job.status === "failed") return `Render failed: ${job.error_text || "unknown error"}`;
  return `Render job: ${status}`;
}

function appendRenderStatus(workspace) {
  const card = document.createElement("div");
  const job = workspace.render_job;
  const status = job?.status || (workspace.output_audio_path ? "succeeded" : "idle");
  card.className = `render-status render-${status}`;
  const progressRatio = Number(job?.progress?.progress_ratio);
  if (Number.isFinite(progressRatio)) {
    card.style.setProperty("--render-progress", `${Math.max(0, Math.min(progressRatio, 1)) * 100}%`);
  } else if (status === "running") {
    card.style.setProperty("--render-progress", "42%");
  } else if (status === "succeeded") {
    card.style.setProperty("--render-progress", "100%");
  }

  const title = document.createElement("strong");
  title.textContent = job?.type === "build_video"
    ? status === "succeeded" ? "Video Rendered" : "Rendering Video"
    : workspace.output_audio_path
      ? "Rendered Audio Ready"
      : workspace.workflow_state === "render_required"
        ? "Re-render Required"
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
  title.textContent = isSingleRelease(workspace) ? "Source Audio" : "Rendered Mix";

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
  actions.appendChild(buildLink(isSingleRelease(workspace) ? "Open Audio" : "Open File", audioUrl));
  body.appendChild(copy);
  body.appendChild(actions);
  player.appendChild(art);
  player.appendChild(body);
  detailLinks.appendChild(player);
}

function appendCoverPreview(workspace) {
  const coverUrl = normalizeMediaUrl(workspace.cover_image_path);
  if (!coverUrl) return;

  const card = document.createElement("div");
  card.className = `asset-preview cover-preview ${workspace.cover_approved ? "approved" : "review"}`;

  const image = document.createElement("img");
  image.src = coverUrl;
  image.alt = `${displayTitle(workspace.title)} cover`;

  const body = document.createElement("div");
  body.className = "asset-preview-body";

  const title = document.createElement("strong");
  title.textContent = workspace.cover_approved ? "Cover Approved" : "Cover Review";

  const copy = document.createElement("span");
  copy.textContent = "16:9 cover image for the YouTube release.";

  const actions = document.createElement("div");
  actions.className = "asset-preview-actions";
  actions.appendChild(buildLink("Open Cover", coverUrl));

  body.appendChild(title);
  body.appendChild(copy);
  body.appendChild(actions);
  card.appendChild(image);
  card.appendChild(body);
  detailLinks.appendChild(card);
}

function appendVideoPreview(workspace) {
  const videoUrl = normalizeMediaUrl(workspace.output_video_path);
  if (!videoUrl) return;

  const card = document.createElement("div");
  card.className = "asset-preview video-preview approved";

  const body = document.createElement("div");
  body.className = "asset-preview-body";

  const title = document.createElement("strong");
  title.textContent = "Rendered Video";

  const copy = document.createElement("span");
  copy.textContent = "Audio and approved cover are combined for YouTube.";

  const video = document.createElement("video");
  video.controls = true;
  video.preload = "none";
  video.src = videoUrl;

  const actions = document.createElement("div");
  actions.className = "asset-preview-actions";
  actions.appendChild(buildLink("Open Video", videoUrl));

  body.appendChild(title);
  body.appendChild(copy);
  body.appendChild(video);
  body.appendChild(actions);
  card.appendChild(body);
  detailLinks.appendChild(card);
}

function appendMetadataDraft(workspace) {
  if (!workspace.youtube_title && !workspace.youtube_description) return;

  const card = document.createElement("div");
  card.className = `metadata-preview metadata-review-panel ${workspace.metadata_approved ? "approved" : "review"}`;

  const header = document.createElement("div");
  header.className = "metadata-review-header";

  const titleBlock = document.createElement("div");

  const kicker = document.createElement("span");
  kicker.className = "metadata-kicker";
  kicker.textContent = workspace.metadata_approved ? "Metadata Approved" : "Metadata Review";

  const heading = document.createElement("h3");
  heading.textContent = workspace.youtube_title || "Untitled YouTube Draft";

  const summary = document.createElement("p");
  summary.textContent = workspace.metadata_approved
    ? "Approved YouTube copy. Final publish can use this title, description, and tags."
    : "YouTube에 올라갈 제목, 설명, 태그입니다. 여기서 확인하고 필요하면 바로 수정한 뒤 승인하세요.";

  titleBlock.appendChild(kicker);
  titleBlock.appendChild(heading);
  titleBlock.appendChild(summary);

  const source = document.createElement("div");
  source.className = "metadata-source";
  const sourceCount = `${workspace.tracks.length} track${workspace.tracks.length === 1 ? "" : "s"}`;
  source.innerHTML = `<span>${releaseModeLabel(workspace)}</span><strong>${formatDuration(workspace.actual_duration_seconds)}</strong><span>${sourceCount}</span>`;

  header.appendChild(titleBlock);
  header.appendChild(source);

  const fields = document.createElement("div");
  fields.className = "metadata-fields";

  const titleField = document.createElement("label");
  titleField.className = "metadata-field title-field";
  const titleLabel = document.createElement("span");
  titleLabel.textContent = "YouTube Title";
  const titleInput = document.createElement("input");
  titleInput.type = "text";
  titleInput.maxLength = 100;
  titleInput.value = workspace.youtube_title || "";
  titleInput.readOnly = Boolean(workspace.metadata_approved);
  titleInput.dataset.metadataField = "title";
  titleField.appendChild(titleLabel);
  titleField.appendChild(titleInput);

  const descriptionField = document.createElement("label");
  descriptionField.className = "metadata-field description-field";
  const descriptionLabel = document.createElement("span");
  descriptionLabel.textContent = "YouTube Description";
  const descriptionInput = document.createElement("textarea");
  descriptionInput.rows = 10;
  descriptionInput.value = workspace.youtube_description || "";
  descriptionInput.readOnly = Boolean(workspace.metadata_approved);
  descriptionInput.dataset.metadataField = "description";
  descriptionField.appendChild(descriptionLabel);
  descriptionField.appendChild(descriptionInput);

  const tagsField = document.createElement("label");
  tagsField.className = "metadata-field tags-field";
  const tagsLabel = document.createElement("span");
  tagsLabel.textContent = "Tags";
  const tagsInput = document.createElement("input");
  tagsInput.type = "text";
  tagsInput.value = metadataTagsText(workspace);
  tagsInput.readOnly = Boolean(workspace.metadata_approved);
  tagsInput.dataset.metadataField = "tags";
  tagsField.appendChild(tagsLabel);
  tagsField.appendChild(tagsInput);

  fields.appendChild(titleField);
  fields.appendChild(descriptionField);
  fields.appendChild(tagsField);

  const tags = document.createElement("div");
  tags.className = "metadata-tags";
  (workspace.youtube_tags || []).forEach((tag) => {
    const chip = document.createElement("span");
    chip.textContent = tag;
    tags.appendChild(chip);
  });

  card.appendChild(header);
  card.appendChild(fields);
  card.appendChild(tags);
  detailLinks.appendChild(card);
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

function archivedWorkspaces() {
  return state.workspaces.filter((workspace) => workspace.hidden);
}

function ensureSelectedWorkspace() {
  const visible = visibleWorkspaces();
  if (visible.some((workspace) => workspace.id === state.selectedWorkspaceId)) return;
  if (state.releaseFocus) {
    state.releaseFocus = false;
    updateReleaseUrl("", true);
  }
  state.selectedWorkspaceId = visible[0]?.id || "";
}

function workspaceOptions(selectedId = "") {
  const defaultOption = `<option value="">Choose workspace</option>`;
  const options = visibleWorkspaces()
    .map((workspace) => {
      const selected = workspace.id === selectedId ? "selected" : "";
      return `<option value="${workspace.id}" ${selected}>${releaseOptionLabel(workspace)}</option>`;
    })
    .join("");
  return `${defaultOption}${options}`;
}

function quickUploadWorkspaceOptions(selectedId = "") {
  const createSingleSelected = selectedId === QUICK_UPLOAD_NEW_SINGLE_VALUE ? "selected" : "";
  const createSingleOption = `<option value="${QUICK_UPLOAD_NEW_SINGLE_VALUE}" ${createSingleSelected}>+ New Single Release from selected candidate(s)</option>`;
  const options = visibleWorkspaces()
    .map((workspace) => {
      const selected = workspace.id === selectedId ? "selected" : "";
      return `<option value="${workspace.id}" ${selected}>${releaseOptionLabel(workspace)}</option>`;
    })
    .join("");
  return `<option value="">Choose release</option>${createSingleOption}${options}`;
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
  const archived = archivedWorkspaces().length;
  const ready = visible.filter((workspace) => workspace.publish_ready && !workspace.publish_approved).length;
  const singles = visible.filter((workspace) => isSingleRelease(workspace)).length;
  const playlists = visible.length - singles;
  toolbarSummaryText.textContent = `Review ${pending} · Singles ${singles} · Playlists ${playlists} · Ready ${ready} · Archive ${archived}`;
}

function renderTrackWorkspaceOptions() {
  if (!trackWorkspaceSelect) return;
  const visible = visibleWorkspaces();
  const options = visible
    .map((workspace) => `<option value="${workspace.id}">${releaseOptionLabel(workspace)}</option>`)
    .join("");
  trackWorkspaceSelect.innerHTML = `<option value="">Unassigned Queue</option>${options}`;
  if (quickUploadWorkspaceSelect) {
    const currentQuickUploadWorkspace = quickUploadWorkspaceSelect.value;
    quickUploadWorkspaceSelect.innerHTML = quickUploadWorkspaceOptions(currentQuickUploadWorkspace);
    if (
      currentQuickUploadWorkspace === QUICK_UPLOAD_NEW_SINGLE_VALUE
      || visible.some((workspace) => workspace.id === currentQuickUploadWorkspace)
    ) {
      quickUploadWorkspaceSelect.value = currentQuickUploadWorkspace;
    }
  }
}

function renderQuickUploadFiles() {
  if (!quickUploadFileList) return;
  if (!quickUploadFiles.length && !quickUploadCoverFiles.length) {
    quickUploadFileList.textContent = "No files selected.";
    return;
  }
  const lines = [];
  if (quickUploadFiles.length) {
    lines.push("Audio:");
    quickUploadFiles.forEach((file, index) => {
      const cover = matchingQuickUploadCover(file, index);
      lines.push(`${index + 1}. ${file.name}${cover ? ` + cover ${cover.name}` : ""}`);
    });
  }
  if (quickUploadCoverFiles.length) {
    lines.push("Covers:");
    quickUploadCoverFiles.forEach((file, index) => lines.push(`${index + 1}. ${file.name}`));
  }
  quickUploadFileList.textContent = lines.join("\n");
}

function setQuickUploadFiles(files) {
  quickUploadFiles = [...files];
  renderQuickUploadFiles();
  if (quickUploadFiles.length) {
    const hint = quickUploadFiles.length === 1
      ? "기존 release를 선택하거나 '+ New Single Release from this file'을 선택하세요."
      : quickUploadFiles.length === 2
        ? "Suno 후보 2곡은 새 Single Release 후보로 함께 올릴 수 있습니다."
        : "3개 이상 파일은 Playlist Release를 선택하세요.";
    setTextStatus(quickUploadStatus, `${quickUploadFiles.length}개 파일 준비됨. ${hint}`);
  }
}

function setQuickUploadCoverFiles(files) {
  quickUploadCoverFiles = [...files];
  renderQuickUploadFiles();
  if (quickUploadCoverFiles.length) {
    setTextStatus(
      quickUploadStatus,
      `${quickUploadCoverFiles.length}개 cover 준비됨. 파일명이 audio와 같으면 자동 매칭하고, 아니면 같은 순서로 매칭합니다.`
    );
  }
}

function normalizedFileStem(file) {
  return fileStem(file?.name || "").toLowerCase();
}

function matchingQuickUploadCover(audioFile, index) {
  if (!quickUploadCoverFiles.length) return null;
  const audioStem = normalizedFileStem(audioFile);
  const sameStem = quickUploadCoverFiles.find((file) => normalizedFileStem(file) === audioStem);
  if (sameStem) return sameStem;
  if (quickUploadCoverFiles.length === quickUploadFiles.length) return quickUploadCoverFiles[index] || null;
  if (quickUploadFiles.length === 1 && quickUploadCoverFiles.length === 1) return quickUploadCoverFiles[0];
  return null;
}

async function createSingleReleaseFromFiles(files) {
  const title = fileStem(files[0].name);
  return api("/api/playlists/workspaces", {
    method: "POST",
    body: JSON.stringify({
      title,
      target_duration_seconds: 1,
      workspace_mode: "single_track_video",
      auto_publish_when_ready: false,
      description: files.length === 1
        ? `Single release created from ${files[0].name}.`
        : `Single release created from ${files.length} Suno candidates: ${files.map((file) => file.name).join(", ")}.`,
      cover_prompt: "",
      dreamina_prompt: "",
    }),
  });
}

async function submitQuickUpload() {
  if (!quickUploadFiles.length) {
    setStatus(quickUploadStatus, "파일을 먼저 선택하세요.");
    return;
  }
  if (!quickUploadWorkspaceSelect?.value) {
    setStatus(quickUploadStatus, "release를 먼저 선택하세요.");
    return;
  }
  const createNewSingle = quickUploadWorkspaceSelect.value === QUICK_UPLOAD_NEW_SINGLE_VALUE;
  if (createNewSingle && quickUploadFiles.length > 2) {
    setStatus(quickUploadStatus, "New Single Release는 Suno 후보 기준 최대 2곡까지 올릴 수 있습니다.");
    return;
  }
  const selectedWorkspace = state.workspaces.find((workspace) => workspace.id === quickUploadWorkspaceSelect.value);
  if (isSingleRelease(selectedWorkspace) && quickUploadFiles.length + pendingTracks(selectedWorkspace.id).length > 2) {
    setStatus(quickUploadStatus, "Single release 후보는 최대 2곡입니다. 기존 후보를 먼저 선택하거나 reject하세요.");
    return;
  }

  quickUploadSubmitButton.disabled = true;
  const results = [];
  const failures = [];
  let workspaceId = quickUploadWorkspaceSelect.value;
  const failedFiles = [];
  try {
    if (createNewSingle) {
      setTextStatus(quickUploadStatus, `Single release 생성 중: ${fileStem(quickUploadFiles[0].name)}`);
      const workspace = await createSingleReleaseFromFiles(quickUploadFiles);
      workspaceId = workspace.id;
      state.selectedWorkspaceId = workspaceId;
      await refreshBoard();
    } else {
      state.selectedWorkspaceId = workspaceId;
    }
    for (const [index, file] of quickUploadFiles.entries()) {
      setQuickUploadProgress(quickUploadFiles.length, results, failures, file.name);
      try {
        const form = new FormData();
        form.append("title", fileStem(file.name));
        form.append("prompt", "manual quick upload");
        form.append("duration_seconds", "0");
        form.append("pending_workspace_id", workspaceId);
        form.append("audio_file", file, file.name);
        const coverFile = matchingQuickUploadCover(file, index);
        if (coverFile) {
          form.append("cover_file", coverFile, coverFile.name);
        }
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
      quickUploadCoverFiles = [];
      renderQuickUploadFiles();
      setTextStatus(
        quickUploadStatus,
        `${quickUploadStatus.textContent}\n\nrelease queue에 반영됐습니다. Slack 알림은 백그라운드에서 전송됩니다.`
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
    if (quickUploadCoverInput && !failures.length) {
      quickUploadCoverInput.value = "";
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
  if (scrollIntoView && state.releaseFocus && detailPanel && !detailPanel.hidden) {
    detailPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function renderWorkspaceTiles() {
  workspaceGrid.innerHTML = "";

  const visible = visibleWorkspaces();
  renderArchivedWorkspaceTiles();

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
    const pipeline = fragment.querySelector(".workspace-pipeline");
    const next = fragment.querySelector(".workspace-next");
    const approvedStat = fragment.querySelector(".approved-stat");
    const pendingStat = fragment.querySelector(".pending-stat");
    const hint = fragment.querySelector(".workspace-hint");
    const moreButton = fragment.querySelector(".more-button");
    const pendingCount = pendingTracks(workspace.id).length;
    const currentStage = currentPipelineStage(workspace);

    if (workspace.id === state.selectedWorkspaceId) {
      tile.classList.add("active");
    }

    mode.textContent = releaseModeLabel(workspace);
    name.textContent = displayTitle(workspace.title, "Untitled Release");
    stateEl.textContent = currentStage?.label || statusLabel(workspace.workflow_state);
    stateEl.classList.add(currentStage?.status || "current");
    copy.textContent = shortText(workspace.description || "Ready to collect approved tracks.", 120);
    approvedStat.textContent = isSingleRelease(workspace)
      ? `${workspace.tracks.length ? "1" : "0"} selected`
      : `${workspace.tracks.length} approved`;
    pendingStat.textContent = `${pendingCount} in review`;
    renderPipeline(pipeline, workspace, { compact: true });
    next.textContent = currentStage?.detail || "Next action is ready.";

    hint.textContent = workspace.workspace_mode === "single_track_video"
      ? "One approved track"
      : `${formatDuration(workspace.actual_duration_seconds)} / ${formatDuration(workspace.target_duration_seconds)}`;

    moreButton.textContent = "Open";
    moreButton.addEventListener("click", (event) => {
      event.stopPropagation();
      openWorkspaceFocus(workspace.id);
    });

    tile.addEventListener("click", () => openWorkspaceFocus(workspace.id));
    workspaceGrid.appendChild(fragment);
  });
}

function renderArchivedWorkspaceTiles() {
  if (!archivedWorkspaceSection || !archivedWorkspaceGrid) return;
  const archived = archivedWorkspaces();
  archivedWorkspaceSection.hidden = !archived.length;
  archivedWorkspaceGrid.innerHTML = "";
  archived.forEach((workspace) => {
    const fragment = workspaceTileTemplate.content.cloneNode(true);
    const tile = fragment.querySelector(".workspace-tile");
    const mode = fragment.querySelector(".workspace-mode");
    const name = fragment.querySelector(".workspace-name");
    const stateEl = fragment.querySelector(".workspace-state");
    const copy = fragment.querySelector(".workspace-copy");
    const pipeline = fragment.querySelector(".workspace-pipeline");
    const next = fragment.querySelector(".workspace-next");
    const approvedStat = fragment.querySelector(".approved-stat");
    const pendingStat = fragment.querySelector(".pending-stat");
    const hint = fragment.querySelector(".workspace-hint");
    const moreButton = fragment.querySelector(".more-button");
    const rejectedCount = state.tracks.filter(
      (track) => track.status === "rejected" && track.metadata_json?.pending_workspace_id === workspace.id
    ).length;

    tile.classList.add("archived-tile");
    mode.textContent = `${releaseModeLabel(workspace)} · Archived`;
    name.textContent = displayTitle(workspace.title, "Archived Release");
    stateEl.textContent = "Archived";
    stateEl.classList.add("waiting");
    copy.textContent = shortText(workspace.note || workspace.description || "All candidates were rejected.", 140);
    pipeline.remove();
    next.textContent = "Restore하면 rejected 후보가 다시 review queue로 돌아옵니다.";
    approvedStat.textContent = `${workspace.tracks.length} selected`;
    pendingStat.textContent = `${rejectedCount} rejected`;
    hint.textContent = "Archived";
    moreButton.textContent = "Restore";
    moreButton.addEventListener("click", async (event) => {
      event.stopPropagation();
      await api(`/api/playlists/${workspace.id}/archive`, {
        method: "POST",
        body: JSON.stringify({
          actor: "web-ui",
          archived: false,
          revive_rejected: true,
        }),
      });
      state.selectedWorkspaceId = workspace.id;
      await refresh();
    });
    archivedWorkspaceGrid.appendChild(fragment);
  });
}

function renderWorkspaceDetail() {
  const workspace = activeWorkspace();
  const tracksForReview = workspace ? pendingTracks(workspace.id) : [];

  if (!workspace || !state.releaseFocus) {
    detailPanel.hidden = true;
    if (detailColumns) detailColumns.hidden = true;
    return;
  }

  detailPanel.hidden = false;
  detailTitle.textContent = displayTitle(workspace.title, "Release");
  const renderState = workspace.output_audio_path
    ? isSingleRelease(workspace) ? "audio ready" : "rendered"
    : workspace.status === "building"
      ? "rendering"
      : isSingleRelease(workspace) ? "source not ready" : "not rendered";
  const currentStage = currentPipelineStage(workspace);
  const pendingCount = tracksForReview.length;
  detailMeta.textContent = `${releaseModeLabel(workspace)} · ${currentStage?.label || statusLabel(workspace.workflow_state)} · ${workspace.tracks.length} approved · ${pendingCount} in review · ${renderState}`;
  queueTitle.textContent = isSingleRelease(workspace)
    ? `${displayTitle(workspace.title)} candidates`
    : `${displayTitle(workspace.title)} review queue`;
  approvedTitle.textContent = isSingleRelease(workspace)
    ? "Selected Track"
    : `${displayTitle(workspace.title)} final order`;

  detailPipeline.innerHTML = "";
  detailLinks.innerHTML = "";
  detailActions.innerHTML = "";
  queueGrid.innerHTML = "";
  approvedGrid.innerHTML = "";

  const backButton = document.createElement("button");
  backButton.type = "button";
  backButton.className = "toolbar-button";
  backButton.textContent = "All Releases";
  backButton.addEventListener("click", () => closeWorkspaceFocus());
  detailActions.appendChild(backButton);

  renderPipeline(detailPipeline, workspace);
  appendRenderStatus(workspace);
  appendRenderedAudioPlayer(workspace);
  appendCoverPreview(workspace);
  appendVideoPreview(workspace);
  appendMetadataDraft(workspace);

  const videoBusy = ["video_queued", "video_rendering"].includes(workspace.workflow_state);
  if (workspace.tracks.length) {
    if (workspace.status === "building" && !videoBusy) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "action-button secondary-button";
      button.textContent = "Rendering Audio...";
      button.disabled = true;
      detailActions.appendChild(button);
    } else if (!videoBusy && (!isSingleRelease(workspace) || !workspace.output_audio_path)) {
      detailActions.appendChild(
        actionButton(
          isSingleRelease(workspace)
            ? "Use Approved Audio"
            : workspace.output_audio_path
            ? "Re-render Audio"
            : "Render Playlist Audio",
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

  const coverChangeBlocked = ["video_queued", "video_rendering", "youtube_uploading"].includes(workspace.workflow_state);
  const canManageCover = workspace.output_audio_path && !workspace.youtube_video_id && !coverChangeBlocked;
  if (canManageCover) {
    if (workspace.cover_image_path && !workspace.cover_approved) {
      detailActions.appendChild(
        actionButton("Approve Cover, then Render Video", "action-button primary-button", async () => {
          await api(`/api/playlists/${workspace.id}/cover/approve`, {
            method: "POST",
            body: JSON.stringify({
              actor: "web-ui",
              approved: true,
              note: "Approved from workspace detail.",
            }),
          });
        })
      );
    }

    detailActions.appendChild(
      actionButton(
        "Upload Cover",
        workspace.cover_image_path ? "action-button secondary-button" : "action-button primary-button",
        async () => {
          await pickCoverFile(workspace);
        }
      )
    );

    detailActions.appendChild(
      actionButton(
        workspace.cover_image_path ? "Generate New Draft Cover" : "Generate Draft Cover",
        "action-button secondary-button",
        async () => {
          await api(`/api/playlists/${workspace.id}/cover/generate`, {
            method: "POST",
            body: JSON.stringify({
              actor: "web-ui",
              regenerate: Boolean(workspace.cover_image_path),
            }),
          });
        }
      )
    );
  }

  if (workspace.cover_approved && !workspace.output_video_path) {
    if (["video_queued", "video_rendering"].includes(workspace.workflow_state) || workspace.status === "building") {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "action-button secondary-button";
      button.textContent = "Rendering Video...";
      button.disabled = true;
      detailActions.appendChild(button);
    } else {
      detailActions.appendChild(
        actionButton("Render Video", "action-button primary-button", async () => {
          await api(`/api/playlists/${workspace.id}/video/render`, {
            method: "POST",
            body: JSON.stringify({
              actor: "web-ui",
            }),
          });
        })
      );
    }
  }

  if (workspace.output_video_path && !workspace.youtube_title) {
    detailActions.appendChild(
      actionButton("Generate Metadata", "action-button secondary-button", async () => {
        await api(`/api/playlists/${workspace.id}/metadata/generate`, {
          method: "POST",
          body: JSON.stringify({
            actor: "web-ui",
          }),
        });
      })
    );
  } else if (workspace.youtube_title && !workspace.metadata_approved) {
    detailActions.appendChild(
      actionButton("Approve Metadata", "action-button primary-button", async () => {
        const metadata = metadataDraftValues();
        await api(`/api/playlists/${workspace.id}/metadata/approve`, {
          method: "POST",
          body: JSON.stringify({
            actor: "web-ui",
            title: metadata.title,
            description: metadata.description,
            tags: metadata.tags,
            note: "Approved from workspace detail.",
          }),
        });
      })
    );
    detailActions.appendChild(
      actionButton("Regenerate Metadata", "action-button secondary-button", async () => {
        await api(`/api/playlists/${workspace.id}/metadata/generate`, {
          method: "POST",
          body: JSON.stringify({
            actor: "web-ui",
          }),
        });
      })
    );
  }

  if (workspace.metadata_approved && !workspace.youtube_video_id) {
    detailActions.appendChild(
      actionButton(workspace.publish_approved ? "Retry Publish" : "Approve Publish", "action-button primary-button", async () => {
        let forceUnderTarget = false;
        const underTarget = !isSingleRelease(workspace)
          && workspace.target_duration_seconds > 0
          && workspace.actual_duration_seconds < workspace.target_duration_seconds;
        if (underTarget) {
          const proceed = window.confirm(
            `이 playlist는 아직 목표 길이보다 짧습니다.\n\n현재: ${formatDuration(workspace.actual_duration_seconds)}\n목표: ${formatDuration(workspace.target_duration_seconds)}\n\n그래도 YouTube publish를 진행할까요?`
          );
          if (!proceed) return;
          forceUnderTarget = true;
        }
        await api(`/api/playlists/${workspace.id}/approve-publish`, {
          method: "POST",
          body: JSON.stringify({
            actor: "web-ui",
            note: "Approved from workspace detail.",
            force_under_target: forceUnderTarget,
          }),
        });
      })
    );
  }

  if (workspace.publish_approved && !workspace.youtube_video_id) {
    const manualBox = document.createElement("div");
    manualBox.className = "manual-upload-box";
    const label = document.createElement("span");
    label.textContent = "Manual fallback only";
    const hint = document.createElement("small");
    hint.textContent = "자동 YouTube 업로드가 안 될 때만, 이미 직접 올린 영상의 video ID를 입력하세요.";
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
    manualBox.appendChild(label);
    manualBox.appendChild(hint);
    manualBox.appendChild(input);
    manualBox.appendChild(button);
    detailActions.appendChild(manualBox);
  }

  const showTrackReviewColumns = !isReleaseReviewStage(workspace);
  if (detailColumns) {
    detailColumns.hidden = !showTrackReviewColumns;
  }
  if (approvedColumn) {
    approvedColumn.hidden = !showTrackReviewColumns;
  }
  if (queueColumn) {
    queueColumn.hidden = !showTrackReviewColumns;
  }
  if (!showTrackReviewColumns) {
    return;
  }

  if (!tracksForReview.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = isSingleRelease(workspace)
      ? "single candidate가 없습니다. 이 release에 곡 하나를 업로드하세요."
      : "review를 기다리는 곡이 없습니다.";
    queueGrid.appendChild(empty);
  } else {
    tracksForReview.forEach((track, index) => {
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
        audio.dataset.autoplayQueue = workspace.id;
        audio.dataset.queueIndex = String(index);
        audio.addEventListener("ended", () => playNextAwaitingTrack(audio));
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
    empty.textContent = isSingleRelease(workspace)
      ? "아직 선택된 single track이 없습니다. queue에서 한 곡을 approve하세요."
      : "아직 승인된 곡이 없습니다.";
    approvedGrid.appendChild(empty);
    return;
  }

  workspace.tracks.forEach((track, index) => {
    const fragment = approvedCardTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".approved-card");
    const order = fragment.querySelector(".approved-index");
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
    if (order) order.textContent = String(index + 1).padStart(2, "0");
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
        ? `Press Connect once and finish OAuth. Redirect URI: ${youtubeStatus.redirect_uri || "not set"}`
        : "Set AIMP_YOUTUBE_CLIENT_SECRETS_PATH in .env first.";
}

function applyBoardData(tracks, workspaces) {
  state.tracks = tracks;
  state.workspaces = workspaces;
  ensureSelectedWorkspace();
  renderLayoutMode();
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
    state.selectedWorkspaceId = result.id;
    await refresh();
  } catch (error) {
    setStatus(workspaceStatus, error.message);
  }
});

menuToggleButton.addEventListener("click", () => toggleDrawer());
refreshButton.addEventListener("click", () => refresh().catch((error) => alert(error.message)));
window.addEventListener("popstate", () => {
  const releaseId = new URLSearchParams(window.location.search).get("release") || "";
  state.selectedWorkspaceId = releaseId || state.selectedWorkspaceId;
  state.releaseFocus = Boolean(releaseId);
  renderLayoutMode();
  renderWorkspaceTiles();
  renderWorkspaceDetail();
});
quickUploadPickButton?.addEventListener("click", () => quickUploadInput?.click());
quickUploadCoverPickButton?.addEventListener("click", () => quickUploadCoverInput?.click());
quickUploadInput?.addEventListener("change", (event) => {
  setQuickUploadFiles(event.target.files || []);
});
quickUploadCoverInput?.addEventListener("change", (event) => {
  setQuickUploadCoverFiles(event.target.files || []);
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
    const files = [...event.dataTransfer.files];
    setQuickUploadFiles(files.filter((file) => file.type.startsWith("audio/")));
    setQuickUploadCoverFiles(files.filter((file) => file.type.startsWith("image/")));
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

youtubeConnectButton.addEventListener("click", () => {
  window.location.href = "/api/youtube/connect";
});

refresh()
  .then(() => {
    if (new URLSearchParams(window.location.search).get("youtube") === "connected") {
      setStatus(workspaceStatus, "YouTube connected. You can approve publish again.");
      window.history.replaceState({}, "", window.location.pathname);
    }
  })
  .catch((error) => {
    setStatus(trackStatus, error.message);
  });

document.addEventListener("pause", resumeDeferredAutoRefresh, true);
document.addEventListener("ended", resumeDeferredAutoRefresh, true);
document.addEventListener("play", (event) => {
  if (event.target instanceof HTMLAudioElement) {
    pauseOtherAudioPlayers(event.target);
  }
}, true);
document.addEventListener("visibilitychange", resumeDeferredAutoRefresh);

window.setInterval(() => {
  autoRefresh().catch(() => {});
}, AUTO_REFRESH_INTERVAL_MS);
