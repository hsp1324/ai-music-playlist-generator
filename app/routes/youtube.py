from fastapi import APIRouter, HTTPException, Request

from app.services.registry import ServiceRegistry

router = APIRouter(prefix="/youtube", tags=["youtube"])


def get_services(request: Request) -> ServiceRegistry:
    return request.app.state.services


@router.get("/status")
def youtube_status(request: Request) -> dict:
    services = get_services(request)
    return services.youtube.get_status()


@router.post("/connect")
def youtube_connect(request: Request) -> dict:
    services = get_services(request)
    try:
        return services.youtube.authenticate_local()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
