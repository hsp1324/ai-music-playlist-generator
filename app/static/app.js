const state = {
  tracks: [],
  workspaces: [],
};

const queueGrid = document.querySelector("#queue-grid");
const workspaceGrid = document.querySelector("#workspace-grid");
const trackForm = document.querySelector("#track-form");
const workspaceForm = document.querySelector("#workspace-form");
const trackStatus = document.querySelector("#track-status");
const workspaceStatus = document.querySelector("#workspace-status");
const refreshButton = document.querySelector("#refresh-button");
const queueTemplate = document.querySelector("#queue-card-template");
const workspaceTemplate = document.querySelector("#workspace-card-template");
const sessionTitle = document.querySelector("#session-title");
const sessionMessage = document.querySelector("#session-message");
const sessionOpenButton = document.querySelector("#session-open-button");
const sessionAlertButton = document.querySelector("#session-alert-button");
const youtubeTitle = document.querySelector("#youtube-title");
const youtubeMessage = document.querySelector("#youtube-message");
const youtubeConnectButton = document.querySelector("#youtube-connect-button");

function normalizeMediaUrl(path) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (path.startsWith("storage/")) return `/media/${path.slice("storage/".length)}`;
  return path;
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

function updateMetrics() {
  const pending = state.tracks.filter((track) => ["pending_review", "held"].includes(track.status)).length;
  const ready = state.workspaces.filter((workspace) => workspace.publish_ready && !workspace.publish_approved).length;
  document.querySelector("#metric-pending").textContent = pending;
  document.querySelector("#metric-workspaces").textContent = state.workspaces.length;
  document.querySelector("#metric-ready").textContent = ready;
}

function workspaceOptions(selectedId = "") {
  const defaultOption = `<option value="">Choose playlist workspace</option>`;
  const options = state.workspaces
    .map((workspace) => {
      const selected = workspace.id === selectedId ? "selected" : "";
      return `<option value="${workspace.id}" ${selected}>${workspace.title}</option>`;
    })
    .join("");
  return `${defaultOption}${options}`;
}

function renderQueue() {
  const queueTracks = state.tracks.filter((track) => ["pending_review", "held"].includes(track.status));
  queueGrid.innerHTML = "";

  if (!queueTracks.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "큐에 남아 있는 곡이 없습니다.";
    queueGrid.appendChild(empty);
    return;
  }

  queueTracks.forEach((track) => {
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
    image.alt = track.title;
    duration.textContent = formatDuration(track.duration_seconds);
    title.textContent = track.title;
    subtitle.textContent = track.metadata_json?.tags || track.source_track_id || "manual candidate";
    status.textContent = track.status.replaceAll("_", " ");
    status.classList.add(track.status);
    prompt.textContent = track.prompt || "Prompt not provided.";

    if (audioUrl) {
      audio.src = audioUrl;
    } else {
      audio.remove();
    }

    if (track.preview_url) links.appendChild(buildLink("Preview", track.preview_url));
    if (track.metadata_json?.source_audio_url) links.appendChild(buildLink("Source", track.metadata_json.source_audio_url));
    if (imageUrl) links.appendChild(buildLink("Cover", imageUrl));

    select.innerHTML = workspaceOptions();

    actions.appendChild(
      actionButton("Approve", "pill-action approve", async () => {
        if (!select.value) {
          throw new Error("Approve before choosing a playlist workspace.");
        }
        await api(`/api/tracks/${track.id}/decisions`, {
          method: "POST",
          body: JSON.stringify({
            decision: "approve",
            source: "human",
            actor: "web-ui",
            rationale: "Approved from workspace queue.",
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
            rationale: "Held from workspace queue.",
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
            rationale: "Rejected from workspace queue.",
          }),
        });
      })
    );

    card.dataset.trackId = track.id;
    queueGrid.appendChild(fragment);
  });
}

function workspaceTrackChip(track) {
  const chip = document.createElement("div");
  chip.className = "workspace-track";
  const title = document.createElement("strong");
  title.textContent = track.title;
  const meta = document.createElement("span");
  meta.textContent = `${formatDuration(track.duration_seconds)}${track.tags ? ` • ${track.tags}` : ""}`;
  chip.appendChild(title);
  chip.appendChild(meta);
  return chip;
}

function renderWorkspaces() {
  workspaceGrid.innerHTML = "";

  if (!state.workspaces.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "먼저 playlist workspace를 하나 만들어 주세요.";
    workspaceGrid.appendChild(empty);
    return;
  }

  state.workspaces.forEach((workspace) => {
    const fragment = workspaceTemplate.content.cloneNode(true);
    const title = fragment.querySelector(".workspace-title");
    const kicker = fragment.querySelector(".workspace-kicker");
    const status = fragment.querySelector(".workspace-status");
    const description = fragment.querySelector(".workspace-description");
    const progressBar = fragment.querySelector(".workspace-progress-bar");
    const meta = fragment.querySelector(".workspace-meta");
    const links = fragment.querySelector(".workspace-links");
    const note = fragment.querySelector(".workspace-note");
    const actions = fragment.querySelector(".workspace-actions");
    const tracks = fragment.querySelector(".workspace-tracks");

    title.textContent = workspace.title;
    kicker.textContent = workspace.workflow_state.replaceAll("_", " ");
    status.textContent = workspace.status;
    status.classList.add(workspace.status);
    description.textContent = workspace.description || "Description not set.";
    progressBar.style.width = `${Math.max(workspace.progress_ratio * 100, 2)}%`;
    meta.textContent = `${formatDuration(workspace.actual_duration_seconds)} / ${formatDuration(workspace.target_duration_seconds)} • ${workspace.tracks.length} tracks`;

    if (workspace.output_audio_path) {
      links.appendChild(buildLink("Rendered Audio", normalizeMediaUrl(workspace.output_audio_path)));
    }
    if (workspace.cover_image_path) {
      links.appendChild(buildLink("Generated Cover", normalizeMediaUrl(workspace.cover_image_path)));
    }

    if (workspace.publish_ready && !workspace.publish_approved) {
      note.textContent = "1시간 분량이 채워졌습니다. Publish 승인 시 cover를 만들고 업로드 단계로 넘깁니다.";
      actions.appendChild(
        actionButton("Approve Publish", "primary-button", async () => {
          await api(`/api/playlists/${workspace.id}/approve-publish`, {
            method: "POST",
            body: JSON.stringify({
              actor: "web-ui",
              note: "Approved from web workspace.",
            }),
          });
        })
      );
    } else if (workspace.publish_approved && !workspace.youtube_video_id) {
      note.textContent = workspace.note || "Cover와 video asset이 준비되었습니다. 자동 업로드가 꺼져 있거나 인증이 없으면 수동 업로드 후 video id를 기록하세요.";
      const input = document.createElement("input");
      input.type = "text";
      input.placeholder = "YouTube video id";
      const button = actionButton("Mark Uploaded", "secondary-button", async () => {
        await api(`/api/playlists/${workspace.id}/mark-uploaded`, {
          method: "POST",
          body: JSON.stringify({
            actor: "web-ui",
            youtube_video_id: input.value || null,
            note: "Marked uploaded from workspace.",
          }),
        });
      });
      actions.appendChild(input);
      actions.appendChild(button);
    } else if (workspace.youtube_video_id) {
      note.textContent = `Uploaded as ${workspace.youtube_video_id}`;
    } else if (workspace.note) {
      note.textContent = workspace.note;
    }

    workspace.tracks.forEach((track) => tracks.appendChild(workspaceTrackChip(track)));
    workspaceGrid.appendChild(fragment);
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
      ? "Press Connect YouTube once and finish the OAuth flow in your browser."
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
  updateMetrics();
  renderSessionStatus(sessionStatus);
  renderYouTubeStatus(youtubeStatus);
  renderQueue();
  renderWorkspaces();
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
        description: form.get("description"),
        cover_prompt: form.get("cover_prompt"),
      }),
    });
    setStatus(workspaceStatus, result);
    await refresh();
  } catch (error) {
    setStatus(workspaceStatus, error.message);
  }
});

refreshButton.addEventListener("click", () => refresh().catch((error) => alert(error.message)));
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
