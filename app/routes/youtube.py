from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.services.registry import ServiceRegistry

router = APIRouter(prefix="/youtube", tags=["youtube"])


def get_services(request: Request) -> ServiceRegistry:
    return request.app.state.services


@router.get("/status")
def youtube_status(request: Request) -> dict:
    services = get_services(request)
    return services.youtube.get_status()


@router.get("/connect")
def youtube_connect_redirect(request: Request) -> RedirectResponse:
    services = get_services(request)
    try:
        payload = services.youtube.build_authorization_url()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return RedirectResponse(payload["authorization_url"])


@router.post("/connect")
def youtube_connect(request: Request) -> dict:
    services = get_services(request)
    try:
        return services.youtube.build_authorization_url()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/oauth/callback")
def youtube_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error:
        raise HTTPException(status_code=400, detail=f"YouTube OAuth failed: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="YouTube OAuth callback is missing code.")

    services = get_services(request)
    try:
        services.youtube.exchange_web_code(code, state)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return RedirectResponse("/?youtube=connected")
