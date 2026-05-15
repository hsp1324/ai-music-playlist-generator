const initialReleaseId = new URLSearchParams(window.location.search).get("release") || "";

const state = {
  tracks: [],
  workspaces: [],
  selectedWorkspaceId: initialReleaseId,
  drawerOpen: false,
  releaseFocus: Boolean(initialReleaseId),
  autoRefreshDeferred: false,
  autoRefreshInFlight: false,
  youtubeStatus: null,
  channelSummaries: [],
  workspacesLoading: false,
  editingMetadataReleaseId: "",
  metadataExpandedByRelease: {},
  metadataLanguageByRelease: {},
  orderEditingByRelease: {},
  workspaceTab: "active",
  channelFilter: "__all_channels__",
  releaseSortKey: "published",
  releaseSortDirection: "desc",
};

const appHeader = document.querySelector(".app-header");
const quickUploadPanel = document.querySelector(".quick-upload-panel");
const boardShell = document.querySelector(".board-shell");
const channelOverviewSection = document.querySelector(".channel-overview-section");
const channelSummaryGrid = document.querySelector("#channel-summary-grid");
const workspaceGrid = document.querySelector("#workspace-grid");
const workspaceSection = document.querySelector(".workspace-section");
const archivedWorkspaceSection = document.querySelector("#archived-workspace-section");
const archivedWorkspaceGrid = document.querySelector("#archived-workspace-grid");
const workspaceTabButtons = [...document.querySelectorAll("[data-workspace-tab]")];
const workspaceSortButtons = [...document.querySelectorAll("[data-release-sort]")];
const archiveCountBadge = document.querySelector("#archive-count-badge");
const channelFilterSelect = document.querySelector("#channel-filter-select");
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
const youtubeChannelControls = document.querySelector("#youtube-channel-controls");
const youtubeChannelSelect = document.querySelector("#youtube-channel-select");
const youtubeImportButton = document.querySelector("#youtube-import-button");
const workspaceTileTemplate = document.querySelector("#workspace-tile-template");
const queueTemplate = document.querySelector("#queue-card-template");
const approvedCardTemplate = document.querySelector("#approved-card-template");
const textModal = document.querySelector("#text-modal");
const textModalTitle = document.querySelector("#text-modal-title");
const textModalBody = document.querySelector("#text-modal-body");
const textModalCloseButton = document.querySelector("#text-modal-close-button");
const CHANNEL_FILTER_ALL = "__all_channels__";
const QUICK_UPLOAD_NEW_SINGLE_VALUE = "__new_single_release__";
const AUTO_REFRESH_INTERVAL_MS = 15000;
const RELEASE_SORT_OPTIONS = [
  { key: "published", label: "Published" },
  { key: "updated", label: "Updated" },
  { key: "created", label: "Created" },
];
const LEGACY_YOUTUBE_CHANNEL_TITLES = {
  "ai썰전": "Club Bloom",
  "ai sseoljeon": "Club Bloom",
};
const METADATA_LANGUAGES = [
  { code: "ko", label: "Korean", shortLabel: "KO" },
  { code: "ja", label: "Japanese", shortLabel: "JA" },
  { code: "en", label: "English", shortLabel: "EN" },
  { code: "es", label: "Spanish", shortLabel: "ES" },
  { code: "vi", label: "Vietnamese", shortLabel: "VI" },
  { code: "th", label: "Thai", shortLabel: "TH" },
  { code: "hi", label: "Hindi", shortLabel: "HI" },
  { code: "fil", label: "Filipino", shortLabel: "FIL" },
  { code: "id", label: "Indonesian", shortLabel: "ID" },
  { code: "pt-BR", label: "Portuguese (Brazil)", shortLabel: "PT" },
  { code: "pt-PT", label: "Portuguese (Portugal)", shortLabel: "PT-PT" },
  { code: "fr", label: "French", shortLabel: "FR" },
  { code: "de", label: "German", shortLabel: "DE" },
  { code: "ar", label: "Arabic", shortLabel: "AR" },
  { code: "zh-CN", label: "Chinese Simplified", shortLabel: "ZH" },
  { code: "zh-TW", label: "Chinese Traditional", shortLabel: "TW" },
];

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

function youtubeWatchUrl(videoId) {
  if (!videoId) return "";
  return `https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}`;
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

function isOrderEditingActive() {
  return Boolean(state.releaseFocus && state.selectedWorkspaceId && state.orderEditingByRelease[state.selectedWorkspaceId]);
}

function isTextModalOpen() {
  return Boolean(textModal && !textModal.hidden);
}

function shouldDeferAutoRefresh() {
  return document.hidden
    || state.releaseFocus
    || isAudioPlaybackActive()
    || Boolean(state.editingMetadataReleaseId)
    || isOrderEditingActive()
    || isTextModalOpen();
}

async function autoRefresh() {
  if (shouldDeferAutoRefresh()) {
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
    if (!shouldDeferAutoRefresh()) {
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

function playNextQueuedTrack(currentAudio, root, selector) {
  if (!currentAudio?.dataset.autoplayQueue) return;
  const queueAudios = [...root.querySelectorAll(selector)]
    .filter((audio) => audio.dataset.autoplayQueue === currentAudio.dataset.autoplayQueue && audio.src);
  const currentIndex = queueAudios.indexOf(currentAudio);
  if (currentIndex < 0 || currentIndex >= queueAudios.length - 1) return;

  const nextAudio = queueAudios[currentIndex + 1];
  window.setTimeout(() => {
    pauseOtherAudioPlayers(nextAudio);
    nextAudio.play().catch(() => {});
  }, 250);
}

function playNextAwaitingTrack(currentAudio) {
  playNextQueuedTrack(currentAudio, queueGrid, "audio.track-audio");
}

function playNextApprovedTrack(currentAudio) {
  playNextQueuedTrack(currentAudio, approvedGrid, "audio.approved-audio");
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

function isFailedWorkspace(workspace) {
  return [
    "render_failed",
    "video_build_failed",
    "youtube_upload_failed",
    "publish_failed",
  ].includes(workspace?.workflow_state);
}

function formatArchiveDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatPublishedDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${month}/${day} ${hours}:${minutes}`;
}

function isSingleRelease(workspace) {
  return workspace?.workspace_mode === "single_track_video";
}

function isOrderEditingUnlocked(workspace) {
  return Boolean(workspace?.id && state.orderEditingByRelease[workspace.id]);
}

function trackUserRating(track) {
  return String(track?.user_rating || track?.metadata_json?.user_rating || "");
}

function releaseModeLabel(workspace) {
  if (workspace?.workspace_mode === "youtube_import") return "YouTube Import";
  return isSingleRelease(workspace) ? "Single Release" : "Playlist Release";
}

function releaseTrackCount(workspace) {
  return Number(workspace?.track_count ?? workspace?.tracks?.length ?? 0);
}

function releaseOptionLabel(workspace) {
  return `${displayTitle(workspace.title)} · ${isSingleRelease(workspace) ? "Single" : "Playlist"}`;
}

function releasePublishedChannelLabel(workspace) {
  if (!workspace?.youtube_video_id && workspace?.workflow_state !== "uploaded") return "";
  return canonicalYouTubeChannelTitle(workspace.youtube_channel_title) || workspace.youtube_channel_id || "YouTube";
}

function releasePublishedAtLabel(workspace) {
  if (!workspace?.youtube_video_id && workspace?.workflow_state !== "uploaded") return "";
  return formatPublishedDate(workspace.youtube_scheduled_publish_at || workspace.youtube_published_at);
}

function dateSortTimestamp(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

function releaseDisplaySortTimestamp(workspace) {
  return dateSortTimestamp(
    workspace?.youtube_scheduled_publish_at || workspace?.youtube_published_at || workspace?.created_at || 0
  );
}

function workspaceSortTimestamp(workspace, sortKey) {
  if (sortKey === "updated") return dateSortTimestamp(workspace?.updated_at || workspace?.created_at || 0);
  if (sortKey === "created") return dateSortTimestamp(workspace?.created_at || 0);
  return releaseDisplaySortTimestamp(workspace);
}

function releaseIsScheduled(workspace) {
  return Boolean(workspace?.youtube_scheduled_publish_at);
}

function releaseChannelKey(workspace) {
  const channelId = String(workspace?.youtube_channel_id || "").trim();
  if (channelId) return `id:${channelId}`;
  const channelTitle = canonicalYouTubeChannelTitle(workspace?.youtube_channel_title);
  if (channelTitle) return `title:${channelTitle}`;
  return "unknown";
}

function releaseChannelDisplayLabel(workspace) {
  return canonicalYouTubeChannelTitle(workspace?.youtube_channel_title) || workspace?.youtube_channel_id || "Unknown Channel";
}

function canonicalYouTubeChannelTitle(title) {
  const clean = String(title || "").trim();
  if (!clean) return "";
  return LEGACY_YOUTUBE_CHANNEL_TITLES[clean.toLowerCase()] || clean;
}

function connectedYouTubeChannel(channelId, channelTitle = "") {
  const channels = state.youtubeStatus?.channels || [];
  const normalizedTitle = canonicalYouTubeChannelTitle(channelTitle).toLowerCase();
  if (channelId) {
    const match = channels.find((channel) => channel.id === channelId);
    if (match) return match;
  }
  if (normalizedTitle) {
    return channels.find((channel) => String(channel.title || "").trim().toLowerCase() === normalizedTitle) || null;
  }
  return null;
}

function channelInitials(label) {
  const clean = String(label || "YT").replace(/[@#]/g, "").trim();
  if (!clean) return "YT";
  if (clean.toLowerCase() === "all channels") return "ALL";
  const parts = clean.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0] || ""}${parts[1][0] || ""}`.toUpperCase();
  }
  return clean.slice(0, 2).toUpperCase();
}

function channelAvatar(channel, className = "channel-avatar") {
  const label = channel?.title || channel?.label || channel?.id || channel?.key || "YouTube";
  const thumbnailUrl = channel?.thumbnail_url || channel?.thumbnailUrl || "";
  const avatar = document.createElement("span");
  avatar.className = className;
  if (thumbnailUrl) {
    const img = document.createElement("img");
    img.src = thumbnailUrl;
    img.alt = "";
    img.loading = "lazy";
    img.referrerPolicy = "no-referrer";
    avatar.appendChild(img);
  } else {
    avatar.textContent = channelInitials(label);
  }
  return avatar;
}

function channelPickerLabel(item) {
  const base = item?.title || item?.label || item?.id || item?.key || "Channel";
  return item?.count ? `${base} (${item.count})` : base;
}

function channelPickerValue(item) {
  return item?.id || item?.key || "";
}

function enhanceChannelSelect(select, items) {
  if (!select) return;
  const list = (items || []).filter(Boolean);
  select.classList.toggle("native-channel-select", Boolean(list.length));
  select.parentElement?.querySelector(`[data-channel-picker-for="${select.id}"]`)?.remove();
  if (!list.length) return;

  const picker = document.createElement("div");
  picker.className = "channel-avatar-select";
  picker.dataset.channelPickerFor = select.id;

  const button = document.createElement("button");
  button.type = "button";
  button.className = "channel-avatar-select-button";
  button.setAttribute("aria-haspopup", "listbox");
  button.setAttribute("aria-expanded", "false");

  const menu = document.createElement("div");
  menu.className = "channel-avatar-select-menu";
  menu.setAttribute("role", "listbox");
  menu.hidden = true;

  const renderButton = () => {
    const selectedValue = select.value || channelPickerValue(list[0]);
    const selected = list.find((item) => channelPickerValue(item) === selectedValue) || list[0];
    button.innerHTML = "";
    button.appendChild(channelAvatar(selected));
    const text = document.createElement("span");
    text.className = "channel-avatar-select-text";
    text.textContent = channelPickerLabel(selected);
    button.appendChild(text);
  };

  list.forEach((item) => {
    const value = channelPickerValue(item);
    const optionButton = document.createElement("button");
    optionButton.type = "button";
    optionButton.className = "channel-avatar-select-option";
    optionButton.setAttribute("role", "option");
    optionButton.dataset.value = value;
    optionButton.appendChild(channelAvatar(item));
    const text = document.createElement("span");
    text.textContent = channelPickerLabel(item);
    optionButton.appendChild(text);
    optionButton.addEventListener("click", () => {
      select.value = value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      picker.classList.remove("open");
      menu.hidden = true;
      button.setAttribute("aria-expanded", "false");
      renderButton();
    });
    menu.appendChild(optionButton);
  });

  button.addEventListener("click", (event) => {
    event.stopPropagation();
    const open = picker.classList.toggle("open");
    menu.hidden = !open;
    button.setAttribute("aria-expanded", String(open));
  });

  renderButton();
  picker.append(button, menu);
  select.insertAdjacentElement("afterend", picker);
}

function releaseArtworkUrl(workspace) {
  const trackImage = workspace?.tracks?.find((track) => track.metadata_json?.image_url)?.metadata_json?.image_url;
  return normalizeMediaUrl(workspace?.cover_image_path || workspace?.youtube_thumbnail_path || trackImage || "");
}

function renderWorkspaceArtwork(fragment, workspace) {
  const img = fragment.querySelector(".workspace-cover");
  const placeholder = fragment.querySelector(".workspace-cover-placeholder");
  const url = releaseArtworkUrl(workspace);
  if (!img || !placeholder) return;
  if (!url) {
    img.hidden = true;
    placeholder.hidden = false;
    return;
  }
  img.src = url;
  img.hidden = false;
  placeholder.hidden = true;
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
  if (channelOverviewSection) channelOverviewSection.hidden = state.releaseFocus;
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
  ensureWorkspaceDetailLoaded(workspaceId)
    .then((workspace) => {
      if (!workspace || state.selectedWorkspaceId !== workspaceId) return;
      renderWorkspaceTiles();
      renderWorkspaceDetail();
    })
    .catch((error) => {
      if (detailMeta && state.selectedWorkspaceId === workspaceId) {
        detailMeta.textContent = `Release detail load failed: ${error.message}`;
      }
    });
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
  const hasApprovedAudio = releaseTrackCount(workspace) > 0;
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
      detail: stage.key === "publish"
        ? releaseIsScheduled(workspace)
          ? "Scheduled on YouTube for public release."
          : "Uploaded to YouTube."
        : stage.detail,
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
  const compactLabels = {
    audio: "Audio",
    cover: "Cover",
    video: "Video",
    metadata: "Meta",
    publish: "Post",
  };

  stages.forEach((stage) => {
    const item = document.createElement("div");
    item.className = `pipeline-step ${stage.status}`;

    const marker = document.createElement("span");
    marker.className = "pipeline-marker";
    marker.textContent = stage.status === "done" ? "✓" : stage.status === "failed" ? "!" : "•";

    const label = document.createElement("span");
    label.className = "pipeline-label";
    label.textContent = options.compact ? compactLabels[stage.key] || stage.label : stage.label;

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

function metadataDefaultLanguage(workspace) {
  const language = workspace?.youtube_default_language || "ko";
  return METADATA_LANGUAGES.some((item) => item.code === language) ? language : "ko";
}

function metadataLocalizations(workspace) {
  const localizations = { ...(workspace?.youtube_localizations || {}) };
  const defaultLanguage = metadataDefaultLanguage(workspace);
  if (!localizations[defaultLanguage]) {
    localizations[defaultLanguage] = {
      title: workspace?.youtube_title || "",
      description: workspace?.youtube_description || "",
    };
  }
  return localizations;
}

function activeMetadataLanguage(workspace) {
  const selected = state.metadataLanguageByRelease[workspace.id];
  if (METADATA_LANGUAGES.some((item) => item.code === selected)) return selected;
  return metadataDefaultLanguage(workspace);
}

function metadataDraftValues() {
  const defaultLanguage = detailPanel.querySelector("[data-metadata-default-language]")?.dataset.metadataDefaultLanguage || "ko";
  const localizations = {};
  METADATA_LANGUAGES.forEach((language) => {
    const title = detailPanel
      .querySelector(`[data-metadata-field="localized-title"][data-metadata-lang="${language.code}"]`)
      ?.value?.trim();
    const description = detailPanel
      .querySelector(`[data-metadata-field="localized-description"][data-metadata-lang="${language.code}"]`)
      ?.value?.trim();
    if (title || description) {
      localizations[language.code] = { title: title || "", description: description || "" };
    }
  });
  const defaultCopy = localizations[defaultLanguage] || {};
  const title = defaultCopy.title || "";
  const description = defaultCopy.description || "";
  const tags = parseMetadataTags(detailPanel.querySelector('[data-metadata-field="tags"]')?.value);
  return { title, description, tags, localizations, default_language: defaultLanguage };
}

async function saveMetadataChanges(workspace) {
  const metadata = metadataDraftValues();
  if (!metadata.title || !metadata.description) {
    alert("기본 언어(KO) YouTube title과 description은 비워둘 수 없습니다.");
    return;
  }
  const partialLanguage = METADATA_LANGUAGES.find((language) => {
    const copy = metadata.localizations[language.code];
    return copy && ((copy.title && !copy.description) || (!copy.title && copy.description));
  });
  if (partialLanguage) {
    alert(`${partialLanguage.label} 탭은 title과 description을 둘 다 입력하거나 둘 다 비워야 합니다.`);
    return;
  }
  const endpoint = workspace.youtube_video_id
    ? `/api/playlists/${workspace.id}/youtube/metadata`
    : `/api/playlists/${workspace.id}/metadata/approve`;
  await api(endpoint, {
    method: "POST",
    body: JSON.stringify({
      actor: "web-ui",
      title: metadata.title,
      description: metadata.description,
      tags: metadata.tags,
      localizations: metadata.localizations,
      default_language: metadata.default_language,
      note: workspace.metadata_approved
        ? workspace.youtube_video_id
          ? "Edited metadata and pushed to YouTube from workspace detail."
          : "Edited approved metadata from workspace detail."
        : "Approved from workspace detail.",
    }),
  });
  state.editingMetadataReleaseId = "";
  await refreshBoard();
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

async function activateYouTubeChannelForUpload(channelId) {
  const youtubeStatus = state.youtubeStatus || {};
  const channels = youtubeStatus.channels || [];
  if (!channels.length) {
    throw new Error("저장된 YouTube 채널이 없습니다. 먼저 YouTube 카드에서 Connect를 눌러 업로드할 채널을 연결하세요.");
  }
  const resolvedChannelId = channelId || youtubeStatus.selected_channel_id || channels[0].id;
  if (!channels.some((channel) => channel.id === resolvedChannelId)) {
    throw new Error("선택한 YouTube 채널을 찾을 수 없습니다. 다시 Connect해서 채널을 연결하세요.");
  }

  if (resolvedChannelId !== youtubeStatus.selected_channel_id) {
    const result = await api("/api/youtube/channels/select", {
      method: "POST",
      body: JSON.stringify({
        channel_id: resolvedChannelId,
      }),
    });
    renderYouTubeStatus(result);
  }
  return resolvedChannelId;
}

function buildYouTubeChannelPicker() {
  const channels = state.youtubeStatus?.channels || [];
  if (!channels.length) return null;

  const label = document.createElement("label");
  label.className = "publish-channel-picker";
  const caption = document.createElement("span");
  caption.textContent = "Publish Channel";
  const select = document.createElement("select");
  select.dataset.role = "publish-channel-select";
  channels.forEach((channel) => {
    const option = document.createElement("option");
    option.value = channel.id;
    option.textContent = channel.title || channel.id;
    select.appendChild(option);
  });
  select.value = state.youtubeStatus?.selected_channel_id || channels[0].id;
  label.appendChild(caption);
  label.appendChild(select);
  enhanceChannelSelect(select, channels);
  return { element: label, select };
}

async function uploadWorkspaceAssetFile(workspace, { endpoint, fieldName, file, extraFields = {} }) {
  const form = new FormData();
  form.append("actor", "web-ui");
  Object.entries(extraFields).forEach(([key, value]) => {
    form.append(key, value);
  });
  form.append(fieldName, file, file.name);
  const response = await fetch(`/api/playlists/${workspace.id}/${endpoint}`, {
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

async function uploadCoverFile(workspace, file) {
  return uploadWorkspaceAssetFile(workspace, {
    endpoint: "cover/upload",
    fieldName: "cover_file",
    file,
  });
}

async function uploadThumbnailFile(workspace, file) {
  return uploadWorkspaceAssetFile(workspace, {
    endpoint: "thumbnail/upload",
    fieldName: "thumbnail_file",
    file,
  });
}

async function uploadLoopVideoFile(workspace, file) {
  return uploadWorkspaceAssetFile(workspace, {
    endpoint: "loop-video/upload",
    fieldName: "loop_video_file",
    file,
    extraFields: {
      smooth_loop: "true",
    },
  });
}

function pickWorkspaceAssetFile(workspace, { accept, upload }) {
  return new Promise((resolve, reject) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = accept;
    input.addEventListener("change", async () => {
      const file = input.files?.[0];
      if (!file) {
        resolve(null);
        return;
      }
      try {
        const result = await upload(workspace, file);
        resolve(result);
      } catch (error) {
        reject(error);
      }
    }, { once: true });
    input.click();
  });
}

function pickCoverFile(workspace) {
  return pickWorkspaceAssetFile(workspace, {
    accept: "image/png,image/jpeg,image/webp",
    upload: uploadCoverFile,
  });
}

function pickThumbnailFile(workspace) {
  return pickWorkspaceAssetFile(workspace, {
    accept: "image/png,image/jpeg,image/webp",
    upload: uploadThumbnailFile,
  });
}

function pickLoopVideoFile(workspace) {
  return pickWorkspaceAssetFile(workspace, {
    accept: "video/mp4,video/quicktime,video/webm",
    upload: uploadLoopVideoFile,
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

function localActionButton(label, className, handler) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.addEventListener("click", handler);
  return button;
}

function chooseVisualizerStyle(workspace) {
  const styles = {
    bars: "20-bar spectrum, current default",
    multiwave: "layered audio waveform",
    thinwave: "clean thin waveform",
    dots: "audio-reactive dot wave",
    "mirror-bars": "center mirrored bars",
    radial: "large circular spectrum",
    pulse: "pulse line visualizer",
    none: "fast render, no spectrum overlay",
  };
  const current = workspace.video_spectrum_overlay_style || "bars";
  const message = [
    "Visualizer preset:",
    ...Object.entries(styles).map(([key, label]) => `${key} - ${label}`),
    "",
    "Enter preset name.",
  ].join("\n");
  const raw = window.prompt(message, current);
  if (raw === null) return null;
  const normalized = raw.trim().toLowerCase().replace(/_/g, "-");
  const aliases = {
    bar: "bars",
    spectrum: "bars",
    wave: "multiwave",
    waveform: "multiwave",
    waves: "multiwave",
    "thin-wave": "thinwave",
    "clean-wave": "thinwave",
    dot: "dots",
    particle: "dots",
    particles: "dots",
    mirror: "mirror-bars",
    mirrorbars: "mirror-bars",
    circle: "radial",
    ring: "radial",
    "radial-bars": "radial",
    "pulse-line": "pulse",
    pulses: "pulse",
    off: "none",
    disabled: "none",
    disable: "none",
    "no-spectrum": "none",
    fast: "none",
  };
  const style = aliases[normalized] || normalized || "bars";
  if (!Object.prototype.hasOwnProperty.call(styles, style)) {
    window.alert("Unknown visualizer preset. Use bars, multiwave, thinwave, dots, mirror-bars, radial, pulse, or none.");
    return null;
  }
  return style;
}

function openTextModal(title, text) {
  if (!textModal || !textModalTitle || !textModalBody) {
    alert(text || "");
    return;
  }
  textModalTitle.textContent = title;
  textModalBody.textContent = text || "";
  textModal.hidden = false;
  document.body.classList.add("modal-open");
  textModalCloseButton?.focus();
}

function closeTextModal() {
  if (!textModal) return;
  textModal.hidden = true;
  document.body.classList.remove("modal-open");
}

function createDetailActionGroups() {
  const element = document.createElement("div");
  element.className = "detail-action-groups";
  const groups = {};
  [
    ["release", "Release"],
    ["audio", "Audio"],
    ["visuals", "Visuals"],
    ["metadata", "Metadata"],
    ["publish", "Publish"],
  ].forEach(([key, label]) => {
    const group = document.createElement("section");
    group.className = "detail-action-group";
    group.dataset.empty = "true";

    const title = document.createElement("div");
    title.className = "detail-action-group-title";
    title.textContent = label;

    const buttons = document.createElement("div");
    buttons.className = "detail-action-group-buttons";

    group.appendChild(title);
    group.appendChild(buttons);
    element.appendChild(group);
    groups[key] = group;
  });
  return { element, groups };
}

function appendDetailAction(group, action) {
  if (!group || !action) return;
  group.dataset.empty = "false";
  group.querySelector(".detail-action-group-buttons")?.appendChild(action);
}

async function reorderApprovedTrack(workspace, currentIndex, direction) {
  const targetIndex = currentIndex + direction;
  if (targetIndex < 0 || targetIndex >= workspace.tracks.length) return;

  const trackIds = workspace.tracks.map((track) => track.id);
  [trackIds[currentIndex], trackIds[targetIndex]] = [trackIds[targetIndex], trackIds[currentIndex]];
  await saveApprovedTrackOrder(workspace, trackIds);
}

async function saveApprovedTrackOrder(workspace, trackIds) {
  const updatedWorkspace = await api(`/api/playlists/${workspace.id}/tracks/reorder`, {
    method: "POST",
    body: JSON.stringify({
      track_ids: trackIds,
      actor: "web-ui",
    }),
  });
  replaceWorkspace(updatedWorkspace, { compact: false });
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

function mergeTrackUpdate(updatedTrack) {
  const nextRating = trackUserRating(updatedTrack);
  state.tracks = state.tracks.map((track) => (
    track.id === updatedTrack.id ? { ...track, ...updatedTrack, user_rating: nextRating } : track
  ));
  state.workspaces.forEach((workspace) => {
    if (!workspace.tracks) return;
    workspace.tracks = workspace.tracks.map((track) => {
      if (track.id !== updatedTrack.id) return track;
      return {
        ...track,
        user_rating: nextRating,
        metadata_json: {
          ...(track.metadata_json || {}),
          ...(updatedTrack.metadata_json || {}),
        },
      };
    });
  });
}

async function setTrackUserRating(track, nextRating) {
  const currentRating = trackUserRating(track);
  const rating = currentRating === nextRating ? "none" : nextRating;
  const updatedTrack = await api(`/api/tracks/${track.id}/rating`, {
    method: "POST",
    body: JSON.stringify({
      rating,
      actor: "web-ui",
    }),
  });
  mergeTrackUpdate(updatedTrack);
  renderWorkspaceTiles();
  renderWorkspaceDetail();
}

function appendTrackRatingButtons(actions, track) {
  const currentRating = trackUserRating(track);
  [
    ["like", "👍", "Like this track"],
    ["dislike", "👎", "Dislike this track"],
  ].forEach(([rating, label, title]) => {
    const button = localActionButton(
      label,
      `pill-action rating ${rating}${currentRating === rating ? " active" : ""}`,
      async () => {
        button.disabled = true;
        try {
          await setTrackUserRating(track, rating);
        } catch (error) {
          alert(error.message);
          button.disabled = false;
        }
      }
    );
    button.title = currentRating === rating ? "Click again to clear" : title;
    button.setAttribute("aria-label", title);
    actions.appendChild(button);
  });
}

function setDropPlacement(card, placement) {
  card.classList.toggle("drop-before", placement === "before");
  card.classList.toggle("drop-after", placement === "after");
}

function clearDropPlacement(card) {
  card.classList.remove("drop-before", "drop-after");
}

function renderWorkerLabel(job) {
  const worker = job?.external_render_worker || {};
  return worker.nickname || worker.hostname || worker.worker_id || "";
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
    const workerLabel = job.type === "build_video" ? renderWorkerLabel(job) : "";
    if (message) parts.push(message);
    if (workerLabel) parts.push(`Worker: ${workerLabel}`);
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

const DETAIL_GROUP_CONFIG = {
  production: {
    title: "Production",
    copy: "Render status and final audio mix.",
  },
  visuals: {
    title: "Visual Assets",
    copy: "Cover, thumbnail, loop video, and rendered video files.",
  },
  distribution: {
    title: "Distribution",
    copy: "Published YouTube output and external links.",
  },
};

function appendDetailGroupItem(groupKey, element) {
  const config = DETAIL_GROUP_CONFIG[groupKey] || { title: groupKey, copy: "" };
  let section = detailLinks.querySelector(`[data-detail-group="${groupKey}"]`);
  if (!section) {
    section = document.createElement("section");
    section.className = `detail-group detail-group-${groupKey}`;
    section.dataset.detailGroup = groupKey;

    const header = document.createElement("div");
    header.className = "detail-group-head";

    const title = document.createElement("strong");
    title.textContent = config.title;
    header.appendChild(title);

    if (config.copy) {
      const copy = document.createElement("span");
      copy.textContent = config.copy;
      header.appendChild(copy);
    }

    const body = document.createElement("div");
    body.className = "detail-group-body";
    section.appendChild(header);
    section.appendChild(body);
    detailLinks.appendChild(section);
  }

  section.querySelector(".detail-group-body")?.appendChild(element);
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

  const worker = job?.external_render_worker || null;
  if (worker?.worker_id) {
    const workerRow = document.createElement("div");
    workerRow.className = "render-worker-row";

    const workerCopy = document.createElement("span");
    const label = renderWorkerLabel(job) || "Unnamed worker";
    workerCopy.textContent = `${label} · ${worker.worker_id}`;
    workerRow.appendChild(workerCopy);

    const nicknameButton = document.createElement("button");
    nicknameButton.type = "button";
    nicknameButton.className = "render-worker-nickname";
    nicknameButton.textContent = worker.nickname ? "Rename" : "Set Nickname";
    nicknameButton.addEventListener("click", async () => {
      const nickname = window.prompt("렌더 worker 닉네임을 입력하세요. 빈 값이면 닉네임을 지웁니다.", worker.nickname || worker.hostname || "");
      if (nickname === null) return;
      nicknameButton.disabled = true;
      try {
        await api(`/api/playlists/render-workers/${encodeURIComponent(worker.worker_id)}/nickname`, {
          method: "POST",
          body: JSON.stringify({ nickname, actor: "web-ui" }),
        });
        await refreshBoard();
      } catch (error) {
        alert(error.message);
        nicknameButton.disabled = false;
      }
    });
    workerRow.appendChild(nicknameButton);
    card.appendChild(workerRow);
  }
  appendDetailGroupItem("production", card);
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
  const trackCount = releaseTrackCount(workspace);
  meta.textContent = `${formatDuration(workspace.actual_duration_seconds)} · ${trackCount} track${trackCount === 1 ? "" : "s"}`;

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
  appendDetailGroupItem("production", player);
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
  appendDetailGroupItem("visuals", card);
}

function appendThumbnailPreview(workspace) {
  const thumbnailUrl = normalizeMediaUrl(workspace.youtube_thumbnail_path);
  if (!thumbnailUrl) return;

  const card = document.createElement("div");
  card.className = "asset-preview thumbnail-preview approved";

  const image = document.createElement("img");
  image.src = thumbnailUrl;
  image.alt = `${displayTitle(workspace.title)} YouTube thumbnail`;

  const body = document.createElement("div");
  body.className = "asset-preview-body";

  const title = document.createElement("strong");
  title.textContent = "YouTube Thumbnail";

  const copy = document.createElement("span");
  copy.textContent = "Click thumbnail with readable text. This is uploaded to YouTube, not used inside the rendered video.";

  const actions = document.createElement("div");
  actions.className = "asset-preview-actions";
  actions.appendChild(buildLink("Open Thumbnail", thumbnailUrl));

  body.appendChild(title);
  body.appendChild(copy);
  body.appendChild(actions);
  card.appendChild(image);
  card.appendChild(body);
  appendDetailGroupItem("visuals", card);
}

function appendLoopVideoPreview(workspace) {
  const loopVideoUrl = normalizeMediaUrl(workspace.loop_video_path);
  if (!loopVideoUrl) return;

  const card = document.createElement("div");
  card.className = "asset-preview loop-video-preview approved";

  const body = document.createElement("div");
  body.className = "asset-preview-body";

  const title = document.createElement("strong");
  title.textContent = "8s Loop Video";

  const copy = document.createElement("span");
  copy.textContent = workspace.loop_video_smooth
    ? "Moving visual for the rendered video. The short clip is reused across the full release."
    : "Moving visual for the rendered video. Direct clip reuse is enabled.";

  const video = document.createElement("video");
  video.controls = true;
  video.muted = true;
  video.loop = true;
  video.preload = "metadata";
  video.src = loopVideoUrl;

  const actions = document.createElement("div");
  actions.className = "asset-preview-actions";
  actions.appendChild(buildLink("Open Loop Video", loopVideoUrl));

  body.appendChild(title);
  body.appendChild(copy);
  body.appendChild(video);
  body.appendChild(actions);
  card.appendChild(body);
  appendDetailGroupItem("visuals", card);
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
  copy.textContent = workspace.loop_video_path
    ? "Audio and the uploaded loop video are combined for YouTube."
    : "Audio and the approved cover are combined for YouTube.";

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
  appendDetailGroupItem("visuals", card);
}

function appendYouTubePreview(workspace) {
  const youtubeUrl = youtubeWatchUrl(workspace.youtube_video_id);
  if (!youtubeUrl) return;

  const thumbnailUrl = normalizeMediaUrl(workspace.youtube_thumbnail_path);
  const card = document.createElement("div");
  card.className = "asset-preview youtube-link-preview approved";

  if (thumbnailUrl) {
    const image = document.createElement("img");
    image.src = thumbnailUrl;
    image.alt = `${displayTitle(workspace.title)} YouTube thumbnail`;
    card.appendChild(image);
  }

  const body = document.createElement("div");
  body.className = "asset-preview-body";

  const title = document.createElement("strong");
  title.textContent = releaseIsScheduled(workspace) ? "YouTube Scheduled Upload" : "YouTube Upload";

  const copy = document.createElement("span");
  const scheduledLabel = releasePublishedAtLabel(workspace);
  copy.textContent = releaseIsScheduled(workspace)
    ? `Uploaded to YouTube as a scheduled public release${scheduledLabel ? ` for ${scheduledLabel}` : ""}.`
    : workspace.output_video_path
    ? "Uploaded to YouTube. The local rendered MP4 is still available until cleanup runs."
    : "Uploaded to YouTube. The long local MP4 has been removed from this server; use the YouTube link to watch it.";

  const idLine = document.createElement("small");
  idLine.textContent = `Video ID: ${workspace.youtube_video_id}`;

  const actions = document.createElement("div");
  actions.className = "asset-preview-actions";
  actions.appendChild(buildLink("Watch on YouTube", youtubeUrl));

  body.appendChild(title);
  body.appendChild(copy);
  body.appendChild(idLine);
  body.appendChild(actions);
  card.appendChild(body);
  appendDetailGroupItem("distribution", card);
}

function appendMetadataDraft(workspace) {
  if (!workspace.youtube_title && !workspace.youtube_description) return;

  const metadataEditing = state.editingMetadataReleaseId === workspace.id;
  const card = document.createElement("details");
  card.className = `metadata-preview metadata-review-panel ${workspace.metadata_approved ? "approved" : "review"}${
    metadataEditing ? " editing" : ""
  }`;
  card.open = Boolean(metadataEditing || state.metadataExpandedByRelease[workspace.id]);
  card.addEventListener("toggle", () => {
    state.metadataExpandedByRelease[workspace.id] = card.open;
  });

  const summaryRow = document.createElement("summary");
  summaryRow.className = "metadata-summary";
  const header = document.createElement("div");
  header.className = "metadata-review-header";

  const titleBlock = document.createElement("div");

  const kicker = document.createElement("span");
  kicker.className = "metadata-kicker";
  kicker.textContent = metadataEditing
    ? "Metadata Editing"
    : workspace.metadata_approved
    ? "Metadata Approved"
    : "Metadata Review";

  const heading = document.createElement("h3");
  heading.textContent = workspace.youtube_title || "Untitled YouTube Draft";

  const summary = document.createElement("p");
  summary.textContent = metadataEditing
    ? "승인된 YouTube 제목, 설명, 태그를 수정 중입니다. KO/JA/EN 탭을 확인한 뒤 저장하세요."
    : workspace.metadata_approved
    ? "Approved YouTube copy. Final publish can use these default and localized titles/descriptions."
    : "YouTube에 올라갈 제목, 설명, 태그입니다. KO/JA/EN 탭에서 확인하고 필요하면 수정한 뒤 승인하세요.";

  titleBlock.appendChild(kicker);
  titleBlock.appendChild(heading);
  titleBlock.appendChild(summary);
  if (workspace.metadata_provider || workspace.metadata_generation_error) {
    const provider = document.createElement("p");
    provider.className = workspace.metadata_generation_error ? "metadata-provider warning" : "metadata-provider";
    provider.textContent = workspace.metadata_generation_error
      ? `Generated by ${workspace.metadata_provider || "template"} fallback: ${workspace.metadata_generation_error}`
      : `Generated by ${workspace.metadata_provider}`;
    titleBlock.appendChild(provider);
  }

  const source = document.createElement("div");
  source.className = "metadata-source";
  const trackCount = releaseTrackCount(workspace);
  const sourceCount = `${trackCount} track${trackCount === 1 ? "" : "s"}`;
  source.innerHTML = `<span>${releaseModeLabel(workspace)}</span><strong>${formatDuration(workspace.actual_duration_seconds)}</strong><span>${sourceCount}</span>`;

  header.appendChild(titleBlock);
  header.appendChild(source);

  summaryRow.appendChild(header);

  const body = document.createElement("div");
  body.className = "metadata-review-body";

  const fields = document.createElement("div");
  fields.className = "metadata-fields";
  fields.dataset.metadataDefaultLanguage = metadataDefaultLanguage(workspace);

  const localizations = metadataLocalizations(workspace);
  const selectedLanguage = activeMetadataLanguage(workspace);

  const languageTabs = document.createElement("div");
  languageTabs.className = "metadata-language-tabs";
  METADATA_LANGUAGES.forEach((language) => {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = `metadata-language-tab${language.code === selectedLanguage ? " active" : ""}`;
    tab.textContent = language.shortLabel;
    tab.title = language.label;
    tab.addEventListener("click", () => {
      state.metadataLanguageByRelease[workspace.id] = language.code;
      languageTabs.querySelectorAll(".metadata-language-tab").forEach((item) => {
        item.classList.toggle("active", item === tab);
      });
      languagePanels.querySelectorAll(".metadata-language-panel").forEach((panel) => {
        panel.hidden = panel.dataset.metadataLang !== language.code;
      });
    });
    languageTabs.appendChild(tab);
  });

  const languagePanels = document.createElement("div");
  languagePanels.className = "metadata-language-panels";
  METADATA_LANGUAGES.forEach((language) => {
    const copy = localizations[language.code] || {};
    const panel = document.createElement("div");
    panel.className = "metadata-language-panel";
    panel.dataset.metadataLang = language.code;
    panel.hidden = language.code !== selectedLanguage;

    const titleField = document.createElement("label");
    titleField.className = "metadata-field title-field";
    const titleLabel = document.createElement("span");
    titleLabel.textContent = `${language.label} Title`;
    const titleInput = document.createElement("input");
    titleInput.type = "text";
    titleInput.maxLength = 100;
    titleInput.value = copy.title || "";
    titleInput.readOnly = Boolean(workspace.metadata_approved && !metadataEditing);
    titleInput.dataset.metadataField = "localized-title";
    titleInput.dataset.metadataLang = language.code;
    titleField.appendChild(titleLabel);
    titleField.appendChild(titleInput);

    const descriptionField = document.createElement("label");
    descriptionField.className = "metadata-field description-field";
    const descriptionLabel = document.createElement("span");
    descriptionLabel.textContent = `${language.label} Description`;
    const descriptionInput = document.createElement("textarea");
    descriptionInput.rows = 10;
    descriptionInput.value = copy.description || "";
    descriptionInput.readOnly = Boolean(workspace.metadata_approved && !metadataEditing);
    descriptionInput.dataset.metadataField = "localized-description";
    descriptionInput.dataset.metadataLang = language.code;
    descriptionField.appendChild(descriptionLabel);
    descriptionField.appendChild(descriptionInput);

    panel.appendChild(titleField);
    panel.appendChild(descriptionField);
    languagePanels.appendChild(panel);
  });

  const tagsField = document.createElement("label");
  tagsField.className = "metadata-field tags-field";
  const tagsLabel = document.createElement("span");
  tagsLabel.textContent = "Tags";
  const tagsInput = document.createElement("input");
  tagsInput.type = "text";
  tagsInput.value = metadataTagsText(workspace);
  tagsInput.readOnly = Boolean(workspace.metadata_approved && !metadataEditing);
  tagsInput.dataset.metadataField = "tags";
  tagsField.appendChild(tagsLabel);
  tagsField.appendChild(tagsInput);

  fields.appendChild(languageTabs);
  fields.appendChild(languagePanels);
  fields.appendChild(tagsField);

  const inlineActions = document.createElement("div");
  inlineActions.className = "metadata-inline-actions";
  if (workspace.metadata_approved) {
    if (metadataEditing) {
      inlineActions.appendChild(
        actionButton("Save Metadata Changes", "action-button primary-button", async () => {
          await saveMetadataChanges(workspace);
        })
      );
      inlineActions.appendChild(
        localActionButton("Cancel Metadata Edit", "action-button secondary-button", () => {
          state.editingMetadataReleaseId = "";
          renderWorkspaceDetail();
        })
      );
    } else {
      inlineActions.appendChild(
        localActionButton("Edit Metadata", "action-button primary-button", () => {
          state.editingMetadataReleaseId = workspace.id;
          state.metadataExpandedByRelease[workspace.id] = true;
          renderWorkspaceDetail();
          window.setTimeout(() => {
            const language = activeMetadataLanguage(workspace);
            detailPanel
              .querySelector(`[data-metadata-field="localized-description"][data-metadata-lang="${language}"]`)
              ?.focus();
          }, 0);
        })
      );
    }
  }

  const tags = document.createElement("div");
  tags.className = "metadata-tags";
  (workspace.youtube_tags || []).forEach((tag) => {
    const chip = document.createElement("span");
    chip.textContent = tag;
    tags.appendChild(chip);
  });

  card.appendChild(summaryRow);
  body.appendChild(fields);
  if (inlineActions.children.length) {
    body.appendChild(inlineActions);
  }
  body.appendChild(tags);
  card.appendChild(body);
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

function markCompactWorkspaces(workspaces) {
  return workspaces.map((workspace) => ({ ...workspace, __compact: true }));
}

function replaceWorkspace(workspace, { compact = false } = {}) {
  const nextWorkspace = { ...workspace, __compact: compact };
  const index = state.workspaces.findIndex((item) => item.id === workspace.id);
  if (index >= 0) {
    state.workspaces.splice(index, 1, nextWorkspace);
  } else {
    state.workspaces.unshift(nextWorkspace);
  }
  return nextWorkspace;
}

async function fetchReviewTracks() {
  const [pending, held] = await Promise.all([
    api("/api/tracks?status_filter=pending_review"),
    api("/api/tracks?status_filter=held"),
  ]);
  return [...pending, ...held];
}

async function fetchWorkspaceList() {
  return markCompactWorkspaces(await api("/api/playlists/workspaces?compact=true"));
}

async function fetchWorkspaceSummary() {
  const summary = await api("/api/playlists/workspaces/summary");
  return summary?.channels || [];
}

async function ensureWorkspaceDetailLoaded(workspaceId) {
  const workspace = state.workspaces.find((item) => item.id === workspaceId);
  if (!workspace || !workspace.__compact) return workspace || null;
  const fullWorkspace = await api(`/api/playlists/workspaces/${encodeURIComponent(workspaceId)}`);
  return replaceWorkspace(fullWorkspace, { compact: false });
}

function activeWorkspaces() {
  return state.workspaces.filter((workspace) => !workspace.hidden);
}

function activeReleaseSortOption() {
  return RELEASE_SORT_OPTIONS.find((option) => option.key === state.releaseSortKey) || RELEASE_SORT_OPTIONS[0];
}

function sortedReleaseWorkspaces(workspaces) {
  const sortOption = activeReleaseSortOption();
  if (sortOption.key === "published" && state.releaseSortDirection === "desc") {
    return workspaces;
  }

  const direction = state.releaseSortDirection === "asc" ? 1 : -1;
  return [...workspaces].sort((left, right) => {
    const leftTime = workspaceSortTimestamp(left, sortOption.key);
    const rightTime = workspaceSortTimestamp(right, sortOption.key);
    if (leftTime !== rightTime) return (leftTime - rightTime) * direction;
    return 0;
  });
}

function channelFilterOptions() {
  return channelUploadSummaries().map((channel) => ({
    key: channel.key,
    label: channel.label,
    count: channel.count,
    thumbnailUrl: channel.thumbnailUrl,
  }));
}

function channelUploadSummaries() {
  if (!state.workspaces.length && state.channelSummaries.length) {
    return channelUploadSummariesFromServer();
  }

  const channels = new Map();
  (state.youtubeStatus?.channels || []).forEach((channel) => {
    const key = channel?.id ? `id:${channel.id}` : `title:${canonicalYouTubeChannelTitle(channel?.title)}`;
    if (!key || key === "title:") return;
    channels.set(key, {
      key,
      label: canonicalYouTubeChannelTitle(channel?.title) || channel?.id || "Unknown Channel",
      thumbnailUrl: channel?.thumbnail_url || "",
      count: 0,
      playlistCount: 0,
      singleCount: 0,
      totalDuration: 0,
      latestTitle: "",
      latestAt: 0,
      latestAtLabel: "",
    });
  });

  activeWorkspaces().forEach((workspace) => {
    if (!releasePublishedChannelLabel(workspace)) return;
    const key = releaseChannelKey(workspace);
    const connectedChannel = connectedYouTubeChannel(workspace.youtube_channel_id, workspace.youtube_channel_title);
    const releaseSortTime = releaseDisplaySortTimestamp(workspace);
    const existing = channels.get(key) || {
      key,
      label: releaseChannelDisplayLabel(workspace),
      thumbnailUrl: connectedChannel?.thumbnail_url || "",
      count: 0,
      playlistCount: 0,
      singleCount: 0,
      totalDuration: 0,
      latestTitle: "",
      latestAt: 0,
      latestAtLabel: "",
    };
    if (!existing.thumbnailUrl && connectedChannel?.thumbnail_url) {
      existing.thumbnailUrl = connectedChannel.thumbnail_url;
    }
    existing.count += 1;
    existing.totalDuration += Number(workspace.rendered_duration_seconds || workspace.actual_duration_seconds || 0);
    if (isSingleRelease(workspace)) {
      existing.singleCount += 1;
    } else {
      existing.playlistCount += 1;
    }
    if (releaseSortTime >= existing.latestAt) {
      existing.latestAt = releaseSortTime;
      existing.latestAtLabel = formatArchiveDate(
        workspace.youtube_scheduled_publish_at || workspace.youtube_published_at || workspace.created_at
      );
      existing.latestTitle = displayTitle(workspace.youtube_title || workspace.title, "Untitled Release");
    }
    channels.set(key, existing);
  });

  return [...channels.values()].sort((left, right) => {
    if (right.count !== left.count) return right.count - left.count;
    return left.label.localeCompare(right.label);
  });
}

function channelUploadSummariesFromServer() {
  const channels = new Map();
  (state.youtubeStatus?.channels || []).forEach((channel) => {
    const key = channel?.id ? `id:${channel.id}` : `title:${canonicalYouTubeChannelTitle(channel?.title)}`;
    if (!key || key === "title:") return;
    channels.set(key, {
      key,
      label: canonicalYouTubeChannelTitle(channel?.title) || channel?.id || "Unknown Channel",
      thumbnailUrl: channel?.thumbnail_url || "",
      count: 0,
      playlistCount: 0,
      singleCount: 0,
      totalDuration: 0,
      latestTitle: "",
      latestAt: 0,
      latestAtLabel: "",
    });
  });

  state.channelSummaries.forEach((summary) => {
    const key = summary.key || "";
    if (!key) return;
    const channelId = key.startsWith("id:") ? key.slice(3) : "";
    const connectedChannel = connectedYouTubeChannel(channelId, summary.label);
    const latestAt = new Date(summary.latestAt || 0);
    channels.set(key, {
      key,
      label: canonicalYouTubeChannelTitle(summary.label) || connectedChannel?.title || channelId || "Unknown Channel",
      thumbnailUrl: connectedChannel?.thumbnail_url || "",
      count: Number(summary.count || 0),
      playlistCount: Number(summary.playlistCount || 0),
      singleCount: Number(summary.singleCount || 0),
      totalDuration: Number(summary.totalDuration || 0),
      latestTitle: summary.latestTitle || "",
      latestAt: Number.isNaN(latestAt.getTime()) ? 0 : latestAt.getTime(),
      latestAtLabel: summary.latestAt ? formatArchiveDate(summary.latestAt) : "",
    });
  });

  return [...channels.values()].sort((left, right) => {
    if (right.count !== left.count) return right.count - left.count;
    return left.label.localeCompare(right.label);
  });
}

function activeWorkspaceCount() {
  if (state.workspaces.length) return activeWorkspaces().length;
  return channelUploadSummaries().reduce((sum, channel) => sum + Number(channel.count || 0), 0);
}

function ensureChannelFilter() {
  const options = channelFilterOptions();
  if (state.channelFilter !== CHANNEL_FILTER_ALL && !options.some((option) => option.key === state.channelFilter)) {
    state.channelFilter = CHANNEL_FILTER_ALL;
  }
  return options;
}

function workspaceMatchesChannelFilter(workspace) {
  if (state.channelFilter === CHANNEL_FILTER_ALL) return true;
  return releaseChannelKey(workspace) === state.channelFilter && Boolean(releasePublishedChannelLabel(workspace));
}

function visibleWorkspaces() {
  return sortedReleaseWorkspaces(activeWorkspaces().filter((workspace) => workspaceMatchesChannelFilter(workspace)));
}

function archivedWorkspaces() {
  return sortedReleaseWorkspaces(state.workspaces.filter((workspace) => workspace.hidden));
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
  const options = activeWorkspaces()
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
  const options = activeWorkspaces()
    .map((workspace) => {
      const selected = workspace.id === selectedId ? "selected" : "";
      return `<option value="${workspace.id}" ${selected}>${releaseOptionLabel(workspace)}</option>`;
    })
    .join("");
  return `<option value="">Choose release</option>${createSingleOption}${options}`;
}

function renderWorkspaceTabs() {
  const archivedCount = archivedWorkspaces().length;
  if (archiveCountBadge) archiveCountBadge.textContent = String(archivedCount);
  renderChannelFilter();
  renderWorkspaceSortControls();
  workspaceTabButtons.forEach((button) => {
    const selected = button.dataset.workspaceTab === state.workspaceTab;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-selected", String(selected));
  });
  workspaceGrid.hidden = state.workspaceTab !== "active";
  if (archivedWorkspaceSection) {
    archivedWorkspaceSection.hidden = state.workspaceTab !== "archive";
  }
}

function renderWorkspaceSortControls() {
  workspaceSortButtons.forEach((button) => {
    const sortKey = button.dataset.releaseSort || "published";
    const active = sortKey === activeReleaseSortOption().key;
    const direction = button.querySelector(".sort-direction");
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
    button.dataset.sortDirection = active ? state.releaseSortDirection : "";
    if (direction) {
      direction.textContent = active ? (state.releaseSortDirection === "desc" ? "↓" : "↑") : "";
    }
    const label = RELEASE_SORT_OPTIONS.find((option) => option.key === sortKey)?.label || "Published";
    const directionLabel = state.releaseSortDirection === "desc" ? "newest first" : "oldest first";
    button.title = active ? `${label}: ${directionLabel}` : `Sort by ${label}`;
  });
}

function renderChannelFilter() {
  if (!channelFilterSelect) return;
  const options = ensureChannelFilter();

  channelFilterSelect.innerHTML = "";
  const allOption = document.createElement("option");
  allOption.value = CHANNEL_FILTER_ALL;
  allOption.textContent = `All Channels (${activeWorkspaceCount()})`;
  channelFilterSelect.appendChild(allOption);

  options.forEach((channel) => {
    const option = document.createElement("option");
    option.value = channel.key;
    option.textContent = `${channel.label} (${channel.count})`;
    channelFilterSelect.appendChild(option);
  });

  channelFilterSelect.value = state.channelFilter;
  channelFilterSelect.disabled = !options.length;
  channelFilterSelect.closest(".channel-filter")?.classList.toggle("disabled", !options.length);
  enhanceChannelSelect(channelFilterSelect, [
    {
      key: CHANNEL_FILTER_ALL,
      label: "All Channels",
      count: activeWorkspaceCount(),
    },
    ...options,
  ]);
}

function setChannelFilter(channelKey, scrollToList = false) {
  state.channelFilter = channelKey || CHANNEL_FILTER_ALL;
  state.workspaceTab = "active";
  state.selectedWorkspaceId = "";
  renderWorkspaceTiles();
  renderWorkspaceDetail();
  updateToolbarSummary();
  if (scrollToList) {
    workspaceSection?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function setReleaseSort(sortKey) {
  const nextKey = RELEASE_SORT_OPTIONS.some((option) => option.key === sortKey) ? sortKey : "published";
  if (state.releaseSortKey === nextKey) {
    state.releaseSortDirection = state.releaseSortDirection === "desc" ? "asc" : "desc";
  } else {
    state.releaseSortKey = nextKey;
    state.releaseSortDirection = "desc";
  }
  renderWorkspaceTiles();
  renderWorkspaceDetail();
}

function renderChannelSummary() {
  if (!channelSummaryGrid) return;
  const channels = channelUploadSummaries();
  channelSummaryGrid.innerHTML = "";

  if (!channels.length) {
    const empty = document.createElement("div");
    empty.className = "channel-summary-empty";
    empty.textContent = "아직 앱에 기록된 YouTube 업로드가 없습니다.";
    channelSummaryGrid.appendChild(empty);
    return;
  }

  const total = channels.reduce(
    (summary, channel) => ({
      count: summary.count + channel.count,
      playlistCount: summary.playlistCount + channel.playlistCount,
      singleCount: summary.singleCount + channel.singleCount,
      totalDuration: summary.totalDuration + channel.totalDuration,
    }),
    { count: 0, playlistCount: 0, singleCount: 0, totalDuration: 0 }
  );
  channelSummaryGrid.appendChild(
    channelSummaryCard({
      key: CHANNEL_FILTER_ALL,
      label: "All Channels",
      count: total.count,
      playlistCount: total.playlistCount,
      singleCount: total.singleCount,
      totalDuration: total.totalDuration,
      latestTitle: "전체 release 보기",
      latestAtLabel: "",
    })
  );

  channels.forEach((channel) => {
    channelSummaryGrid.appendChild(channelSummaryCard(channel));
  });
}

function channelSummaryCard(channel) {
  const card = document.createElement("button");
  card.className = "channel-summary-card";
  card.type = "button";
  card.classList.toggle("active", state.channelFilter === channel.key);
  card.addEventListener("click", () => setChannelFilter(channel.key, true));

  const label = document.createElement("span");
  label.className = "channel-summary-label";
  label.textContent = channel.label;

  const count = document.createElement("strong");
  count.className = "channel-summary-count";
  count.textContent = String(channel.count);

  const caption = document.createElement("span");
  caption.className = "channel-summary-caption";
  caption.textContent = "uploaded releases";

  const meta = document.createElement("span");
  meta.className = "channel-summary-meta";
  const totalDuration = channel.totalDuration >= 3600 ? formatLongDuration(channel.totalDuration) : formatDuration(channel.totalDuration);
  meta.textContent = `Playlist ${channel.playlistCount} · Single ${channel.singleCount} · ${totalDuration}`;

  const latest = document.createElement("span");
  latest.className = "channel-summary-latest";
  const latestDate = channel.latestAtLabel ? ` · ${channel.latestAtLabel}` : "";
  latest.textContent = `${channel.latestTitle || "최근 업로드 없음"}${latestDate}`;

  card.append(channelAvatar(channel, "channel-summary-avatar"), label, count, caption, meta, latest);
  return card;
}

function setWorkspaceTab(tab) {
  state.workspaceTab = tab === "archive" ? "archive" : "active";
  renderWorkspaceTiles();
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
  const visible = activeWorkspaces();
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
    quickUploadFileList.classList.add("empty");
    return;
  }
  quickUploadFileList.classList.remove("empty");
  const audioCount = quickUploadFiles.length;
  const coverCount = quickUploadCoverFiles.length;
  const matchedCount = quickUploadFiles.filter((file, index) => matchingQuickUploadCover(file, index)).length;
  const summary = [`Audio ${audioCount}`];
  if (coverCount) summary.push(`Covers ${coverCount}`);
  if (matchedCount) summary.push(`Matched ${matchedCount}`);
  const lines = [summary.join(" · ")];
  if (quickUploadFiles.length) {
    lines.push("");
    quickUploadFiles.slice(0, 4).forEach((file, index) => {
      const cover = matchingQuickUploadCover(file, index);
      lines.push(`${index + 1}. ${file.name}${cover ? ` + ${cover.name}` : ""}`);
    });
    if (quickUploadFiles.length > 4) {
      lines.push(`+ ${quickUploadFiles.length - 4} more`);
    }
  } else if (quickUploadCoverFiles.length) {
    lines.push("");
    quickUploadCoverFiles.slice(0, 3).forEach((file, index) => lines.push(`${index + 1}. ${file.name}`));
    if (quickUploadCoverFiles.length > 3) {
      lines.push(`+ ${quickUploadCoverFiles.length - 3} more`);
    }
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
        ? "Suno 후보 2곡은 같은 Single Release 후보로 올리고, 둘 다 좋으면 각각 따로 publish합니다."
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

async function archiveWorkspaceForDeletion(workspace) {
  const purgeLabel = "7일 뒤 완전 삭제됩니다";
  const failedCopy = isFailedWorkspace(workspace) ? "이 실패한 release" : "이 release";
  const youtubeCopy = workspace.youtube_video_id
    ? "\n\n이미 올라간 YouTube 영상은 삭제하지 않고, 앱의 workspace 기록만 Archive로 이동합니다."
    : "";
  const proceed = window.confirm(
    `${failedCopy}를 삭제할까요?\n\n바로 지우지 않고 Archive로 이동합니다. ${purgeLabel}.\nArchive 탭에서 그 전까지 Restore할 수 있습니다.${youtubeCopy}`
  );
  if (!proceed) return;
  await api(`/api/playlists/${workspace.id}/archive`, {
    method: "POST",
    body: JSON.stringify({
      actor: "web-ui",
      archived: true,
      revive_rejected: false,
    }),
  });
  if (state.selectedWorkspaceId === workspace.id) {
    state.selectedWorkspaceId = "";
    if (state.releaseFocus) {
      closeWorkspaceFocus(true);
    } else {
      updateReleaseUrl("", true);
    }
  }
}

function workspaceDeleteButton(workspace, label = "Delete") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "more-button danger-more-button";
  button.textContent = label;
  button.addEventListener("click", async (event) => {
    event.stopPropagation();
    try {
      await archiveWorkspaceForDeletion(workspace);
      await refreshBoard();
    } catch (error) {
      alert(error.message);
    }
  });
  return button;
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
        form.append("lyrics", "");
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
  ensureWorkspaceDetailLoaded(workspaceId)
    .then((workspace) => {
      if (!workspace || state.selectedWorkspaceId !== workspaceId) return;
      renderWorkspaceTiles();
      renderWorkspaceDetail();
    })
    .catch((error) => {
      if (detailMeta && state.selectedWorkspaceId === workspaceId) {
        detailMeta.textContent = `Release detail load failed: ${error.message}`;
      }
    });
  if (scrollIntoView && state.releaseFocus && detailPanel && !detailPanel.hidden) {
    detailPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function renderWorkspaceTiles() {
  renderWorkspaceTabs();
  renderChannelSummary();
  workspaceGrid.innerHTML = "";
  renderArchivedWorkspaceTiles();

  if (state.workspaceTab !== "active") return;

  const visible = visibleWorkspaces();

  if (!visible.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = state.workspacesLoading
      ? "Release list loading..."
      : state.channelFilter === CHANNEL_FILTER_ALL
      ? "먼저 workspace를 하나 만들어 주세요."
      : "선택한 채널에 올라간 release가 없습니다.";
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
    const footer = fragment.querySelector(".workspace-footer");
    const pendingCount = pendingTracks(workspace.id).length;
    const currentStage = currentPipelineStage(workspace);

    renderWorkspaceArtwork(fragment, workspace);

    if (workspace.id === state.selectedWorkspaceId) {
      tile.classList.add("active");
    }

    mode.textContent = releaseModeLabel(workspace);
    name.textContent = displayTitle(workspace.title, "Untitled Release");
    stateEl.textContent = currentStage?.label || statusLabel(workspace.workflow_state);
    stateEl.classList.add(currentStage?.status || "current");
    copy.textContent = shortText(workspace.description || "Ready to collect approved tracks.", 120);
    const trackCount = releaseTrackCount(workspace);
    approvedStat.textContent = isSingleRelease(workspace)
      ? `${trackCount} / 2 selected`
      : `${trackCount} approved`;
    pendingStat.textContent = `${pendingCount} in review`;
    renderPipeline(pipeline, workspace, { compact: true });
    next.textContent = currentStage?.detail || "Next action is ready.";

    const publishedChannel = releasePublishedChannelLabel(workspace);
    if (publishedChannel) {
      const publishedAt = releasePublishedAtLabel(workspace);
      hint.textContent = `${releaseIsScheduled(workspace) ? "Scheduled" : "Published"} · ${publishedChannel}${publishedAt ? ` · ${publishedAt}` : ""}`;
      hint.classList.add("published-hint");
    } else {
      hint.textContent = workspace.workspace_mode === "single_track_video"
        ? "Approve one or both candidates"
        : `${formatDuration(workspace.actual_duration_seconds)} / ${formatDuration(workspace.target_duration_seconds)}`;
    }

    moreButton.textContent = "Open";
    moreButton.addEventListener("click", (event) => {
      event.stopPropagation();
      openWorkspaceFocus(workspace.id);
    });
    footer.appendChild(workspaceDeleteButton(workspace));

    tile.addEventListener("click", () => openWorkspaceFocus(workspace.id));
    workspaceGrid.appendChild(fragment);
  });
}

function renderArchivedWorkspaceTiles() {
  if (!archivedWorkspaceSection || !archivedWorkspaceGrid) return;
  if (state.workspaceTab !== "archive") {
    archivedWorkspaceGrid.innerHTML = "";
    return;
  }
  const archived = archivedWorkspaces();
  archivedWorkspaceGrid.innerHTML = "";
  if (!archived.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "Archive가 비어 있습니다.";
    archivedWorkspaceGrid.appendChild(empty);
    return;
  }
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

    renderWorkspaceArtwork(fragment, workspace);
    tile.classList.add("archived-tile");
    mode.textContent = `${releaseModeLabel(workspace)} · Archived`;
    name.textContent = displayTitle(workspace.title, "Archived Release");
    stateEl.textContent = "Archived";
    stateEl.classList.add("waiting");
    copy.textContent = shortText(workspace.note || workspace.description || "All candidates were rejected.", 140);
    pipeline.remove();
    next.textContent = workspace.purge_after
      ? `Restore 가능 · ${formatArchiveDate(workspace.purge_after)} 이후 자동 삭제`
      : "Restore하면 다시 active release로 돌아옵니다.";
    approvedStat.textContent = `${releaseTrackCount(workspace)} selected`;
    pendingStat.textContent = `${rejectedCount} rejected`;
    hint.textContent = "Archived";
    moreButton.textContent = "Restore";
    moreButton.addEventListener("click", async (event) => {
      event.stopPropagation();
      try {
        await api(`/api/playlists/${workspace.id}/archive`, {
          method: "POST",
          body: JSON.stringify({
            actor: "web-ui",
            archived: false,
            revive_rejected: true,
          }),
        });
        state.selectedWorkspaceId = workspace.id;
        state.workspaceTab = "active";
        await refresh();
      } catch (error) {
        alert(error.message);
      }
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
  if (workspace.__compact) {
    detailMeta.textContent = "Release detail loading...";
    detailPipeline.innerHTML = "";
    detailLinks.innerHTML = "";
    detailActions.innerHTML = "";
    queueGrid.innerHTML = "";
    approvedGrid.innerHTML = "";
    if (detailColumns) detailColumns.hidden = true;
    return;
  }
  const renderState = workspace.output_audio_path
    ? isSingleRelease(workspace) ? "audio ready" : "rendered"
    : workspace.status === "building"
      ? "rendering"
      : isSingleRelease(workspace) ? "source not ready" : "not rendered";
  const currentStage = currentPipelineStage(workspace);
  const pendingCount = tracksForReview.length;
  detailMeta.textContent = `${releaseModeLabel(workspace)} · ${currentStage?.label || statusLabel(workspace.workflow_state)} · ${releaseTrackCount(workspace)} approved · ${pendingCount} in review · ${renderState}`;
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

  const { element: detailActionGroupsElement, groups: detailActionGroups } = createDetailActionGroups();
  detailActions.appendChild(detailActionGroupsElement);

  const backButton = document.createElement("button");
  backButton.type = "button";
  backButton.className = "toolbar-button";
  backButton.textContent = "All Releases";
  backButton.addEventListener("click", () => closeWorkspaceFocus());
  appendDetailAction(detailActionGroups.release, backButton);
  if (!workspace.hidden) {
    appendDetailAction(
      detailActionGroups.release,
      actionButton("Delete Release", "action-button danger-button", async () => {
        await archiveWorkspaceForDeletion(workspace);
        await refreshBoard();
      })
    );
  }

  renderPipeline(detailPipeline, workspace);
  appendRenderStatus(workspace);
  appendRenderedAudioPlayer(workspace);
  appendCoverPreview(workspace);
  appendThumbnailPreview(workspace);
  appendLoopVideoPreview(workspace);
  appendVideoPreview(workspace);
  appendYouTubePreview(workspace);
  appendMetadataDraft(workspace);

  const youtubeReady = Boolean(state.youtubeStatus?.ready);
  const waitingForYouTubeAuth = workspace.workflow_state === "ready_for_youtube_auth" && !youtubeReady;
  const metadataEditing = state.editingMetadataReleaseId === workspace.id;
  const releaseLockedForPublish = Boolean(
    workspace.metadata_approved || workspace.publish_approved || workspace.youtube_video_id
  );
  const releaseReviewStage = isReleaseReviewStage(workspace);
  const showTrackReviewColumns = !releaseReviewStage;
  const busyStates = new Set(["render_queued", "rendering", "video_queued", "video_rendering", "publish_queued", "youtube_uploading"]);
  const videoBusy = ["video_queued", "video_rendering"].includes(workspace.workflow_state);
  const releaseBusy = workspace.status === "building" || busyStates.has(workspace.workflow_state);
  const orderEditingUnlocked = isOrderEditingUnlocked(workspace);
  const canUnlockOrder = !isSingleRelease(workspace) && workspace.tracks.length > 1 && !releaseBusy;
  if (canUnlockOrder && releaseReviewStage && !orderEditingUnlocked) {
    appendDetailAction(
      detailActionGroups.audio,
      localActionButton("Edit Order", "action-button secondary-button", () => {
        const confirmed = window.confirm(
          "순서를 다시 바꾸면 기존 rendered audio/video/metadata와 앱의 YouTube publish 상태가 초기화됩니다.\n\n순서 변경 후 Re-render Audio부터 다시 진행해야 합니다. 계속할까요?"
        );
        if (!confirmed) return;
        state.orderEditingByRelease[workspace.id] = true;
        renderWorkspaceDetail();
      })
    );
  } else if (orderEditingUnlocked) {
    const indicator = document.createElement("button");
    indicator.type = "button";
    indicator.className = "action-button secondary-button";
    indicator.textContent = "Order Editing On";
    indicator.disabled = true;
    appendDetailAction(detailActionGroups.audio, indicator);
  }
  if (workspace.tracks.length) {
    if (workspace.status === "building" && !videoBusy) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "action-button secondary-button";
      button.textContent = "Rendering Audio...";
      button.disabled = true;
      appendDetailAction(detailActionGroups.audio, button);
    } else if (!releaseLockedForPublish && !videoBusy && (!isSingleRelease(workspace) || !workspace.output_audio_path)) {
      appendDetailAction(
        detailActionGroups.audio,
        actionButton(
          isSingleRelease(workspace)
            ? "Use Approved Audio"
            : workspace.output_audio_path || workspace.workflow_state === "render_required"
            ? "Re-render Audio"
            : "Render Mix",
          "action-button secondary-button",
          async () => {
            await api(`/api/playlists/${workspace.id}/render-audio`, {
              method: "POST",
              body: JSON.stringify({
                actor: "web-ui",
                random: false,
              }),
            });
          }
        )
      );
      if (!isSingleRelease(workspace) && workspace.tracks.length > 1) {
        appendDetailAction(
          detailActionGroups.audio,
          actionButton("Shuffle Render", "action-button secondary-button", async () => {
            const proceed = window.confirm(
              "현재 Final Order를 랜덤으로 섞은 뒤 audio render를 시작합니다.\n\n수동으로 맞춘 순서를 유지하려면 취소하세요."
            );
            if (!proceed) return;
            await api(`/api/playlists/${workspace.id}/render-audio`, {
              method: "POST",
              body: JSON.stringify({
                actor: "web-ui",
                random: true,
              }),
            });
          })
        );
      }
    }
  }

  const visualAssetChangeBlocked = ["video_queued", "video_rendering", "publish_queued", "youtube_uploading"].includes(workspace.workflow_state);
  const canManageVisualAssets = Boolean(workspace.output_audio_path && !visualAssetChangeBlocked);
  if (canManageVisualAssets) {
    if (workspace.cover_image_path && !workspace.cover_approved) {
      appendDetailAction(
        detailActionGroups.visuals,
        actionButton("Approve Cover", "action-button primary-button", async () => {
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

    appendDetailAction(
      detailActionGroups.visuals,
      actionButton(
        workspace.cover_image_path ? "Replace Cover" : "Upload Cover",
        workspace.cover_image_path ? "action-button secondary-button" : "action-button primary-button",
        async () => {
          await pickCoverFile(workspace);
        }
      )
    );

    appendDetailAction(
      detailActionGroups.visuals,
      actionButton(
        workspace.youtube_thumbnail_path ? "Replace Thumbnail" : "Upload Thumbnail",
        workspace.youtube_thumbnail_path ? "action-button secondary-button" : "action-button primary-button",
        async () => {
          await pickThumbnailFile(workspace);
        }
      )
    );

    appendDetailAction(
      detailActionGroups.visuals,
      actionButton(
        workspace.loop_video_path ? "Replace 8s Loop Video" : "Upload 8s Loop Video",
        "action-button secondary-button",
        async () => {
          await pickLoopVideoFile(workspace);
        }
      )
    );

    appendDetailAction(
      detailActionGroups.visuals,
      actionButton(
        workspace.cover_image_path ? "New Draft Cover" : "Draft Cover",
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
      appendDetailAction(detailActionGroups.visuals, button);
    } else {
      appendDetailAction(
        detailActionGroups.visuals,
        actionButton(workspace.youtube_video_id ? "Render Video Before Re-upload" : "Render Video", "action-button primary-button", async () => {
          if (!workspace.loop_video_path) {
            window.alert(
              "8초 loop video가 아직 없습니다.\n\n먼저 Upload 8s Loop Video로 Dreamina/Seedance MP4를 업로드한 뒤 Render Video를 실행하세요."
            );
            return;
          }
          const videoSpectrumOverlayStyle = chooseVisualizerStyle(workspace);
          if (!videoSpectrumOverlayStyle) return;
          await api(`/api/playlists/${workspace.id}/video/render`, {
            method: "POST",
            body: JSON.stringify({
              actor: "web-ui",
              video_spectrum_overlay_style: videoSpectrumOverlayStyle,
            }),
          });
        })
      );
    }
  }

  if (workspace.output_video_path && !workspace.youtube_title && !workspace.publish_approved) {
    appendDetailAction(
      detailActionGroups.metadata,
      actionButton("Generate Metadata", "action-button secondary-button", async () => {
        await api(`/api/playlists/${workspace.id}/metadata/generate`, {
          method: "POST",
          body: JSON.stringify({
            actor: "web-ui",
          }),
        });
      })
    );
  } else if ((workspace.output_video_path || workspace.youtube_video_id) && workspace.youtube_title && workspace.metadata_approved) {
    if (metadataEditing) {
      appendDetailAction(
        detailActionGroups.metadata,
        actionButton("Save Metadata Changes", "action-button primary-button", async () => {
          await saveMetadataChanges(workspace);
        })
      );
      appendDetailAction(
        detailActionGroups.metadata,
        localActionButton("Cancel Metadata Edit", "action-button secondary-button", () => {
          state.editingMetadataReleaseId = "";
          renderWorkspaceDetail();
        })
      );
    } else {
      appendDetailAction(
        detailActionGroups.metadata,
        localActionButton("Edit Metadata", "action-button primary-button", () => {
          state.editingMetadataReleaseId = workspace.id;
          state.metadataExpandedByRelease[workspace.id] = true;
          renderWorkspaceDetail();
          window.setTimeout(() => {
            const language = activeMetadataLanguage(workspace);
            detailPanel
              .querySelector(`[data-metadata-field="localized-description"][data-metadata-lang="${language}"]`)
              ?.focus();
          }, 0);
        })
      );
    }
    if (!metadataEditing && workspace.output_video_path) {
      appendDetailAction(
        detailActionGroups.metadata,
        actionButton("Regenerate Draft", "action-button secondary-button", async () => {
          const proceed = window.confirm("승인된 metadata를 새 초안으로 다시 생성할까요? 다시 승인해야 publish/re-upload할 수 있습니다.");
          if (!proceed) return;
          await api(`/api/playlists/${workspace.id}/metadata/generate`, {
            method: "POST",
            body: JSON.stringify({
              actor: "web-ui",
            }),
          });
        })
      );
    }
  } else if (workspace.youtube_title && !workspace.metadata_approved) {
    appendDetailAction(
      detailActionGroups.metadata,
      actionButton("Approve Metadata", "action-button primary-button", async () => {
        await saveMetadataChanges(workspace);
      })
    );
    appendDetailAction(
      detailActionGroups.metadata,
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

  if (workspace.metadata_approved && !metadataEditing && !workspace.output_video_path) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "action-button secondary-button";
    button.textContent = workspace.youtube_video_id ? "Render Video Before Re-upload" : "Render Video Before Publish";
    button.disabled = true;
    appendDetailAction(detailActionGroups.publish, button);
  } else if (workspace.metadata_approved && !metadataEditing) {
    const publishBusy = workspace.workflow_state === "publish_queued";
    const needsYouTubeConnection = !youtubeReady;
    const connectedYouTubeChannels = state.youtubeStatus?.channels || [];
    if (publishBusy) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "action-button secondary-button";
      button.textContent = workspace.youtube_video_id ? "Re-upload Queued..." : "Publishing...";
      button.disabled = true;
      appendDetailAction(detailActionGroups.publish, button);
    } else if (waitingForYouTubeAuth || needsYouTubeConnection || !connectedYouTubeChannels.length) {
      appendDetailAction(
        detailActionGroups.publish,
        actionButton("Connect YouTube Channel", "action-button primary-button", async () => {
          window.location.href = `/api/youtube/connect?playlist_id=${encodeURIComponent(workspace.id)}`;
        })
      );
    } else {
      const channelPicker = buildYouTubeChannelPicker();
      if (channelPicker) {
        appendDetailAction(detailActionGroups.publish, channelPicker.element);
      }
      appendDetailAction(
        detailActionGroups.publish,
        actionButton(workspace.youtube_video_id ? "Re-upload to YouTube" : workspace.publish_approved ? "Retry Publish" : "Approve Publish", "action-button primary-button", async () => {
          const youtubeChannelId = await activateYouTubeChannelForUpload(channelPicker?.select.value);
          const channel = (state.youtubeStatus?.channels || []).find((item) => item.id === youtubeChannelId);
          const channelTitle = channel?.title || youtubeChannelId;
          if (workspace.youtube_video_id) {
            const proceed = window.confirm(
              `이미 YouTube에 업로드된 release입니다.\n\n현재 video id: ${workspace.youtube_video_id}\n업로드 채널: ${channelTitle}\n\n테스트용으로 새 영상을 다시 업로드할까요?`
            );
            if (!proceed) return;
          }
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
          if (!workspace.youtube_thumbnail_path) {
            alert("YouTube text thumbnail이 아직 없습니다. Upload Thumbnail로 글자가 있는 썸네일을 먼저 올려주세요.");
            return;
          }
          await api(`/api/playlists/${workspace.id}/approve-publish`, {
            method: "POST",
            body: JSON.stringify({
              actor: "web-ui",
              note: workspace.youtube_video_id ? "Re-upload requested from workspace detail." : "Approved from workspace detail.",
              force_under_target: forceUnderTarget,
              youtube_channel_id: youtubeChannelId,
            }),
          });
        })
      );
    }
  }

  if (workspace.youtube_video_id) {
    appendDetailAction(
      detailActionGroups.publish,
      actionButton("Request Next Playlist", "action-button secondary-button", async () => {
        const proceed = window.confirm(
          "OpenClaw Slack 채널에 OPENCLAW_RUN 명령으로 채널별 backlog queue 유지 요청을 보낼까요?"
        );
        if (!proceed) return;
        const result = await api(`/api/playlists/${workspace.id}/openclaw/request-next`, {
          method: "POST",
          body: JSON.stringify({
            actor: "web-ui",
          }),
        });
        if (result?.ok) {
          alert("OpenClaw Slack 채널에 OPENCLAW_RUN backlog queue 요청을 보냈습니다.");
        }
      })
    );
  }

  if (workspace.publish_approved && !workspace.youtube_video_id) {
    const manualBox = document.createElement("details");
    manualBox.className = "manual-upload-box";
    const summary = document.createElement("summary");
    summary.textContent = "Manual upload fallback";
    const content = document.createElement("div");
    content.className = "manual-upload-content";
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
          youtube_channel_id: workspace.youtube_channel_id || state.youtubeStatus?.selected_channel_id || null,
          note: "Marked uploaded from workspace detail.",
        }),
      });
    });
    content.appendChild(hint);
    content.appendChild(input);
    content.appendChild(button);
    manualBox.appendChild(summary);
    manualBox.appendChild(content);
    appendDetailAction(detailActionGroups.publish, manualBox);
  }

  const orderEditable = showTrackReviewColumns || orderEditingUnlocked;
  const showApprovedTrackList = showTrackReviewColumns || Boolean(workspace.tracks.length);
  if (detailColumns) {
    detailColumns.hidden = !showApprovedTrackList && !showTrackReviewColumns;
  }
  if (approvedColumn) {
    approvedColumn.hidden = !showApprovedTrackList;
  }
  if (queueColumn) {
    queueColumn.hidden = !showTrackReviewColumns;
  }
  if (!showTrackReviewColumns && !showApprovedTrackList) {
    return;
  }

  if (showTrackReviewColumns && !tracksForReview.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = isSingleRelease(workspace)
      ? "single candidate가 없습니다. 이 release에 곡 하나를 업로드하세요."
      : "review를 기다리는 곡이 없습니다.";
    queueGrid.appendChild(empty);
  } else if (showTrackReviewColumns) {
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
      const styleText = track.style || track.metadata_json?.style || "";

      image.src = imageUrl;
      image.alt = displayTitle(track.title, "Track");
      duration.textContent = formatDuration(track.duration_seconds);
      title.textContent = displayTitle(track.title, "Untitled Track");
      subtitle.textContent = shortText(styleText || track.metadata_json?.tags || track.source_track_id || "manual candidate", 64);
      status.textContent = statusLabel(track.status);
      status.classList.add(track.status);
      prompt.textContent = shortText(track.prompt || "Prompt not provided.", 160);
      if (styleText) {
        prompt.textContent = `${prompt.textContent}\nStyle: ${shortText(styleText, 220)}`;
      }
      if (track.lyrics || track.metadata_json?.lyrics) {
        prompt.textContent = `${prompt.textContent}\nLyrics: ${shortText(track.lyrics || track.metadata_json.lyrics, 220)}`;
      }

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

      appendTrackRatingButtons(actions, track);

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
    const styleText = track.style || track.metadata_json?.style || "";
    const lyricsText = track.lyrics || track.metadata_json?.lyrics || "";

    card.dataset.trackId = track.id;
    if (order) order.textContent = String(index + 1).padStart(2, "0");
    if (orderEditable && workspace.tracks.length > 1) {
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
          .then(() => renderWorkspaceDetail())
          .catch((error) => alert(error.message));
      });
    }

    if (image) {
      image.src = imageUrl;
      image.alt = displayTitle(track.title, "Track");
    }
    title.textContent = displayTitle(track.title, "Untitled Track");
    if (meta) {
      meta.textContent = shortText(
        [
          track.tags || "",
          styleText ? "style saved" : "",
          lyricsText ? "lyrics saved" : "",
        ].filter(Boolean).join(" · ") || "approved track",
        90
      );
    }
    duration.textContent = formatDuration(track.duration_seconds);

    if (audioUrl) {
      audio.src = audioUrl;
      audio.dataset.autoplayQueue = workspace.id;
      audio.dataset.queueIndex = String(index);
      audio.addEventListener("ended", () => playNextApprovedTrack(audio));
    } else {
      audio.remove();
    }
    if (links) {
      if (track.preview_url) links.appendChild(buildLink("Preview", track.preview_url));
      if (track.image_url) links.appendChild(buildLink("Cover", imageUrl));
    }
    appendTrackRatingButtons(actions, track);
    {
      const lyricsButton = localActionButton("Lyrics", "pill-action reorder", () => {
        openTextModal(`${displayTitle(track.title, "Track")} Lyrics`, lyricsText);
      });
      lyricsButton.disabled = !lyricsText;
      lyricsButton.title = lyricsText ? "Show saved lyrics" : "No lyrics saved";
      actions.appendChild(lyricsButton);
    }
    {
      const styleButton = localActionButton("Style", "pill-action reorder", () => {
        openTextModal(`${displayTitle(track.title, "Track")} Style`, styleText);
      });
      styleButton.disabled = !styleText;
      styleButton.title = styleText ? "Show saved style" : "No style saved";
      actions.appendChild(styleButton);
    }
    if (orderEditable && workspace.tracks.length > 1) {
      const upButton = localActionButton("Up", "pill-action reorder", async () => {
        upButton.disabled = true;
        try {
          await reorderApprovedTrack(workspace, index, -1);
          renderWorkspaceDetail();
        } catch (error) {
          alert(error.message);
          upButton.disabled = false;
        }
      });
      upButton.disabled = index === 0;
      actions.appendChild(upButton);

      const downButton = localActionButton("Down", "pill-action reorder", async () => {
        downButton.disabled = true;
        try {
          await reorderApprovedTrack(workspace, index, 1);
          renderWorkspaceDetail();
        } catch (error) {
          alert(error.message);
          downButton.disabled = false;
        }
      });
      downButton.disabled = index === workspace.tracks.length - 1;
      actions.appendChild(downButton);
    }
    if (showTrackReviewColumns) {
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
    } else {
      const status = document.createElement("span");
      status.className = "approved-lock-note";
      status.textContent = orderEditable ? "Order unlocked" : workspace.youtube_video_id ? "Published" : "Locked";
      actions.appendChild(status);
    }

    approvedGrid.appendChild(fragment);
  });
}

function renderSessionStatus(sessionStatus) {
  sessionTitle.textContent = `State: ${sessionStatus.state}`;
  sessionMessage.textContent = `${sessionStatus.message} Last sync: ${sessionStatus.last_synced_at || "never"}`;
}

function renderYouTubeStatus(youtubeStatus) {
  state.youtubeStatus = youtubeStatus;
  const channels = youtubeStatus.channels || [];
  const selectedChannelTitle = youtubeStatus.selected_channel_title || "default channel";
  youtubeTitle.textContent = youtubeStatus.ready
    ? `YouTube connected: ${selectedChannelTitle}`
    : youtubeStatus.configured
      ? "YouTube not authenticated"
      : "YouTube client secrets missing";
  youtubeMessage.textContent = youtubeStatus.ready
    ? `Uploads will use ${selectedChannelTitle}. Connect again to add another channel.`
    : youtubeStatus.error
      ? youtubeStatus.error
      : youtubeStatus.configured
        ? `Press Connect once and finish OAuth. Redirect URI: ${youtubeStatus.redirect_uri || "not set"}`
        : "Set AIMP_YOUTUBE_CLIENT_SECRETS_PATH in .env first.";
  if (youtubeChannelControls && youtubeChannelSelect) {
    youtubeChannelControls.hidden = !channels.length;
    youtubeChannelSelect.innerHTML = "";
    channels.forEach((channel) => {
      const option = document.createElement("option");
      option.value = channel.id;
      option.textContent = channel.title || channel.id;
      youtubeChannelSelect.appendChild(option);
    });
    if (youtubeStatus.selected_channel_id) {
      youtubeChannelSelect.value = youtubeStatus.selected_channel_id;
    }
    enhanceChannelSelect(youtubeChannelSelect, channels);
  }
  if (youtubeImportButton) {
    youtubeImportButton.disabled = !youtubeStatus.ready || !channels.length;
    youtubeImportButton.hidden = !channels.length;
  }
}

function applyBoardData(tracks, workspaces) {
  state.tracks = tracks;
  state.workspaces = workspaces;
  state.workspacesLoading = false;
  ensureChannelFilter();
  ensureSelectedWorkspace();
  renderLayoutMode();
  updateToolbarSummary();
  renderTrackWorkspaceOptions();
  renderWorkspaceTiles();
  renderWorkspaceDetail();
}

async function refreshBoard() {
  const [tracks, workspaces] = await Promise.all([
    fetchReviewTracks(),
    fetchWorkspaceList(),
  ]);
  applyBoardData(tracks, workspaces);
  if (state.releaseFocus && state.selectedWorkspaceId) {
    ensureWorkspaceDetailLoaded(state.selectedWorkspaceId)
      .then(() => {
        renderWorkspaceTiles();
        renderWorkspaceDetail();
      })
      .catch((error) => setStatus(trackStatus, error.message));
  }
}

async function refresh() {
  state.workspacesLoading = true;
  const [sessionStatus, youtubeStatus, channelSummaries] = await Promise.all([
    api("/api/suno/session-status"),
    api("/api/youtube/status"),
    fetchWorkspaceSummary(),
  ]);
  state.youtubeStatus = youtubeStatus;
  state.channelSummaries = channelSummaries;
  renderSessionStatus(sessionStatus);
  renderYouTubeStatus(youtubeStatus);
  ensureChannelFilter();
  renderLayoutMode();
  updateToolbarSummary();
  renderWorkspaceTiles();
  renderWorkspaceDetail();

  const [tracks, workspaces] = await Promise.all([
    fetchReviewTracks(),
    fetchWorkspaceList(),
  ]);
  applyBoardData(tracks, workspaces);
  if (state.releaseFocus && state.selectedWorkspaceId) {
    ensureWorkspaceDetailLoaded(state.selectedWorkspaceId)
      .then(() => {
        renderWorkspaceTiles();
        renderWorkspaceDetail();
      })
      .catch((error) => setStatus(trackStatus, error.message));
  }
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
workspaceTabButtons.forEach((button) => {
  button.addEventListener("click", () => setWorkspaceTab(button.dataset.workspaceTab));
});
workspaceSortButtons.forEach((button) => {
  button.addEventListener("click", () => setReleaseSort(button.dataset.releaseSort));
});
channelFilterSelect?.addEventListener("change", () => {
  setChannelFilter(channelFilterSelect.value || CHANNEL_FILTER_ALL);
});
refreshButton.addEventListener("click", () => refresh().catch((error) => alert(error.message)));
textModalCloseButton?.addEventListener("click", closeTextModal);
textModal?.addEventListener("click", (event) => {
  if (event.target?.hasAttribute?.("data-text-modal-close")) {
    closeTextModal();
  }
});
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && textModal && !textModal.hidden) {
    closeTextModal();
  }
});
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

if (youtubeChannelSelect) {
  youtubeChannelSelect.addEventListener("change", async () => {
    if (!youtubeChannelSelect.value) return;
    try {
      const result = await api("/api/youtube/channels/select", {
        method: "POST",
        body: JSON.stringify({
          channel_id: youtubeChannelSelect.value,
        }),
      });
      renderYouTubeStatus(result);
      renderWorkspaceDetail();
    } catch (error) {
      alert(error.message);
    }
  });
}

if (youtubeImportButton) {
  youtubeImportButton.addEventListener("click", async () => {
    const channels = state.youtubeStatus?.channels || [];
    const channelId = youtubeChannelSelect?.value || state.youtubeStatus?.selected_channel_id || "";
    const channel = channels.find((item) => item.id === channelId);
    if (!channelId) {
      alert("가져올 YouTube 채널을 먼저 선택하세요.");
      return;
    }
    const channelLabel = channel?.title || channelId;
    const proceed = window.confirm(`${channelLabel} 최근 업로드 20개를 웹앱으로 가져올까요?`);
    if (!proceed) return;
    youtubeImportButton.disabled = true;
    try {
      const result = await api("/api/youtube/import-uploads", {
        method: "POST",
        body: JSON.stringify({
          channel_id: channelId,
          max_results: 20,
          update_existing: true,
        }),
      });
      setStatus(
        workspaceStatus,
        `YouTube import complete. Imported ${result.imported?.length || 0}, updated ${result.updated?.length || 0}.`
      );
      await refresh();
    } catch (error) {
      alert(error.message);
    } finally {
      youtubeImportButton.disabled = false;
    }
  });
}

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
document.addEventListener("click", (event) => {
  document.querySelectorAll(".channel-avatar-select.open").forEach((picker) => {
    if (picker.contains(event.target)) return;
    picker.classList.remove("open");
    const menu = picker.querySelector(".channel-avatar-select-menu");
    const button = picker.querySelector(".channel-avatar-select-button");
    if (menu) menu.hidden = true;
    if (button) button.setAttribute("aria-expanded", "false");
  });
});
document.addEventListener("visibilitychange", resumeDeferredAutoRefresh);

window.setInterval(() => {
  autoRefresh().catch(() => {});
}, AUTO_REFRESH_INTERVAL_MS);
