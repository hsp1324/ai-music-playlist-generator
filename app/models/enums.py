from enum import Enum


class TrackStatus(str, Enum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    held = "held"
    uploaded = "uploaded"
    failed = "failed"


class DecisionValue(str, Enum):
    approve = "approve"
    reject = "reject"
    hold = "hold"
    regenerate = "regenerate"


class DecisionSource(str, Enum):
    human = "human"
    agent = "agent"
    system = "system"
    slack = "slack"


class PlaylistStatus(str, Enum):
    draft = "draft"
    building = "building"
    ready = "ready"
    uploaded = "uploaded"
    failed = "failed"


class JobType(str, Enum):
    generate_track = "generate_track"
    review_track = "review_track"
    build_playlist = "build_playlist"
    build_video = "build_video"
    upload_youtube = "upload_youtube"
    sync_slack = "sync_slack"


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
