from dataclasses import dataclass

from app.services.background_worker import BackgroundJobWorker
from app.config import Settings
from app.services.cover_art_service import CoverArtService
from app.services.codex_metadata_service import CodexMetadataService
from app.services.dreamina_service import DreaminaService
from app.services.release_metadata_service import ReleaseMetadataService
from app.services.slack_installation_store import SlackInstallationStore
from app.services.mcp_orchestrator import MCPReadyDecisionEngine
from app.services.playlist_builder import FFMpegPlaylistBuilder
from app.services.slack_service import SlackService
from app.services.suno_service import StubSunoGateway
from app.services.suno_session_service import SunoBrowserSessionService
from app.services.youtube_service import YouTubeService


@dataclass
class ServiceRegistry:
    settings: Settings
    slack: SlackService
    slack_installations: SlackInstallationStore
    playlist_builder: FFMpegPlaylistBuilder
    cover_art: CoverArtService
    suno: StubSunoGateway
    suno_session: SunoBrowserSessionService
    decision_engine: MCPReadyDecisionEngine
    youtube: YouTubeService
    dreamina: DreaminaService
    release_metadata: ReleaseMetadataService
    worker: BackgroundJobWorker


def build_service_registry(settings: Settings) -> ServiceRegistry:
    worker = BackgroundJobWorker(settings)
    registry = ServiceRegistry(
        settings=settings,
        slack=SlackService(settings),
        slack_installations=SlackInstallationStore(),
        playlist_builder=FFMpegPlaylistBuilder(settings),
        cover_art=CoverArtService(settings),
        suno=StubSunoGateway(settings),
        suno_session=SunoBrowserSessionService(settings),
        decision_engine=MCPReadyDecisionEngine(settings),
        youtube=YouTubeService(settings),
        dreamina=DreaminaService(settings),
        release_metadata=CodexMetadataService(settings, ReleaseMetadataService(settings)),
        worker=worker,
    )
    worker.bind_services(registry)
    return registry
