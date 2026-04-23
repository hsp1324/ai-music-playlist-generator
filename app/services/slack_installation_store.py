from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.slack_installation import SlackInstallation


class SlackInstallationStore:
    def get_active_installation(self, db: Session, team_id: str | None = None) -> SlackInstallation | None:
        statement = select(SlackInstallation).where(SlackInstallation.is_active.is_(True))
        if team_id:
            statement = statement.where(SlackInstallation.team_id == team_id)
        statement = statement.order_by(SlackInstallation.updated_at.desc())
        return db.scalars(statement).first()

    def upsert_installation(self, db: Session, installation: SlackInstallation) -> SlackInstallation:
        existing = db.scalars(
            select(SlackInstallation).where(SlackInstallation.team_id == installation.team_id)
        ).first()

        if existing:
            existing.team_name = installation.team_name
            existing.enterprise_id = installation.enterprise_id
            existing.app_id = installation.app_id
            existing.bot_user_id = installation.bot_user_id
            existing.bot_token = installation.bot_token
            existing.scope = installation.scope
            existing.installed_by_user_id = installation.installed_by_user_id
            existing.is_active = True
            db.add(existing)
            db.flush()
            return existing

        db.add(installation)
        db.flush()
        return installation
