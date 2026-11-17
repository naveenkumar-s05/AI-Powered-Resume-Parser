from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import JOB
from app.db.session import get_db
from app.dependencies.auth import get_user_from_request
from app.models.enums import UserStatus

router = APIRouter(tags=["Pages"])
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def _render(request: Request, name: str, **context):
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={"request": request, "job": JOB, **context},
    )


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    return _render(request, "landing.html", active="home")


@router.get("/apply", response_class=HTMLResponse)
async def apply_page(request: Request):
    return _render(request, "upload.html", active="apply")


@router.get("/apply/details", response_class=HTMLResponse)
async def apply_details_page(request: Request):
    return _render(request, "apply_details.html", active="apply")


@router.get("/apply/password", response_class=HTMLResponse)
async def apply_password_page(request: Request):
    return _render(request, "apply_password.html", active="apply")


@router.get("/upload", include_in_schema=False)
async def old_upload_page():
    return RedirectResponse(url="/apply", status_code=307)


@router.get("/register", include_in_schema=False)
async def old_register_page():
    return RedirectResponse(url="/apply", status_code=307)


@router.get("/verify", response_class=HTMLResponse)
async def verify_page(request: Request):
    return _render(request, "verify.html", active="verify")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return _render(request, "login.html", active="login")


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_user_from_request(request, db)
    if not user or user.status != UserStatus.active:
        return RedirectResponse(url="/login")
    return _render(request, "profile.html", active="profile")


@router.get("/dashboard", include_in_schema=False)
async def dashboard_redirect():
    return RedirectResponse(url="/dashboard/student", status_code=307)


@router.get("/dashboard/student", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_user_from_request(request, db)
    if not user or user.status != UserStatus.active:
        return RedirectResponse(url="/login")
    return _render(
        request,
        "dashboard.html",
        active="dashboard",
        full_name=user.full_name,
    )
