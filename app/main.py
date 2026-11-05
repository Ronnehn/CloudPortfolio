import hmac
import json
import os
import re
import time
from pathlib import Path

import markdown as md_lib
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from starlette.middleware.sessions import SessionMiddleware

from . import db

BASE = Path(__file__).resolve().parent.parent
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
MAX_UPLOAD = 8 * 1024 * 1024  # 8 MB per file
ON_RENDER = bool(os.getenv("RENDER"))

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=ON_RENDER,
    max_age=60 * 60 * 12,
)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")


# ---------- template helpers ----------
def render_md(text):
    if not text:
        return Markup("")
    return Markup(md_lib.markdown(text, extensions=["fenced_code", "tables", "sane_lists"]))


def split_lines(text):
    return [l.strip().lstrip("-•* ").strip() for l in (text or "").splitlines() if l.strip()]


def split_tags(text):
    return [t.strip().lstrip("#") for t in re.split(r"[,\n]", text or "") if t.strip().lstrip("#")]


def parse_apps(text):
    """'Amazon EKS | Managed Kubernetes' -> {'name':..., 'why':...}"""
    out = []
    for line in split_lines(text):
        parts = re.split(r"\s*(?:\||\s—\s|\s–\s|\s-\s|:)\s*", line, maxsplit=1)
        out.append({"name": parts[0], "why": parts[1] if len(parts) > 1 else ""})
    return out


def video_embed(url):
    if not url:
        return None
    m = re.search(r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([\w-]{11})", url)
    if m:
        return f"https://www.youtube-nocookie.com/embed/{m.group(1)}"
    m = re.search(r"vimeo\.com/(\d+)", url)
    if m:
        return f"https://player.vimeo.com/video/{m.group(1)}"
    m = re.search(r"loom\.com/share/(\w+)", url)
    if m:
        return f"https://www.loom.com/embed/{m.group(1)}"
    return None


templates.env.filters["md"] = render_md
templates.env.filters["lines"] = split_lines
templates.env.filters["tags"] = split_tags
templates.env.filters["apps"] = parse_apps
templates.env.globals["video_embed"] = video_embed


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "project"


def unique_slug(title, project_id=None):
    base = slugify(title)
    slug, n = base, 2
    while True:
        row = db.one("SELECT id FROM pf_projects WHERE slug = ?", (slug,))
        if not row or row["id"] == project_id:
            return slug
        slug, n = f"{base}-{n}", n + 1


def profile():
    return db.one("SELECT * FROM pf_profile WHERE id = 1") or {}


def page(request, name, **ctx):
    ctx.setdefault("profile", profile())
    ctx["is_admin"] = bool(request.session.get("admin"))
    return templates.TemplateResponse(request, name, ctx)


@app.on_event("startup")
def _startup():
    db.init_db()
    if not ADMIN_PASSWORD:
        print("WARNING: ADMIN_PASSWORD is not set; the admin login is disabled.")


# ---------- files (diagrams, photo, resume) ----------
async def save_upload(upload: UploadFile | None, allowed=("image/", "application/pdf")):
    if not upload or not upload.filename:
        return None
    data = await upload.read()
    if not data:
        return None
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, f"{upload.filename} is larger than 8 MB")
    ctype = upload.content_type or "application/octet-stream"
    if not any(ctype.startswith(a) for a in allowed):
        raise HTTPException(415, f"{upload.filename}: unsupported file type {ctype}")
    return db.execute(
        "INSERT INTO pf_files (filename, content_type, data) VALUES (?, ?, ?)",
        (upload.filename, ctype, data),
    )


@app.get("/files/{file_id}")
def get_file(file_id: int):
    f = db.one("SELECT filename, content_type, data FROM pf_files WHERE id = ?", (file_id,))
    if not f:
        raise HTTPException(404)
    return Response(
        content=bytes(f["data"]),
        media_type=f["content_type"],
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Disposition": f'inline; filename="{f["filename"]}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


# ---------- public pages ----------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    projects = db.query(
        "SELECT * FROM pf_projects WHERE published = 1 ORDER BY featured DESC, position, created_at DESC"
    )
    all_tags = sorted({t for p in projects for t in split_tags(p["tags"])}, key=str.lower)
    return page(request, "home.html", projects=projects, all_tags=all_tags,
                featured=[p for p in projects if p["featured"]][:4])


@app.get("/projects/{slug}", response_class=HTMLResponse)
def project_page(request: Request, slug: str):
    p = db.one("SELECT * FROM pf_projects WHERE slug = ?", (slug,))
    if not p or (not p["published"] and not request.session.get("admin")):
        raise HTTPException(404)
    diagrams = db.query("SELECT * FROM pf_diagrams WHERE project_id = ? ORDER BY position, id", (p["id"],))
    steps = json.loads(p["steps_json"] or "[]")
    others = db.query(
        "SELECT slug, title, hook FROM pf_projects WHERE published = 1 AND id != ? ORDER BY featured DESC, created_at DESC LIMIT 3",
        (p["id"],),
    )
    return page(request, "project.html", p=p, diagrams=diagrams, steps=steps, others=others)


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return page(request, "about.html")


@app.get("/resume")
def resume():
    prof = profile()
    if not prof.get("resume_id"):
        raise HTTPException(404, "No resume uploaded yet")
    return get_file(prof["resume_id"])


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse(
        request, "404.html", {"profile": profile(), "is_admin": False}, status_code=404
    )


# ---------- auth ----------
_fails: dict[str, list[float]] = {}


def require_admin(request: Request):
    if not request.session.get("admin"):
        raise HTTPException(303, headers={"Location": "/admin/login"})


@app.get("/admin/login", response_class=HTMLResponse)
def login_form(request: Request):
    return page(request, "admin/login.html", error=None)


@app.post("/admin/login")
def login(request: Request, username: str = Form(""), password: str = Form("")):
    ip = request.client.host if request.client else "?"  # real IP via --proxy-headers
    now = time.time()
    recent = [t for t in _fails.get(ip, []) if now - t < 600]
    if len(recent) >= 5:
        return page(request, "admin/login.html", error="Too many attempts. Try again in 10 minutes.")
    ok = (
        bool(ADMIN_PASSWORD)
        and hmac.compare_digest(username.encode(), ADMIN_USERNAME.encode())
        and hmac.compare_digest(password.encode(), ADMIN_PASSWORD.encode())
    )
    if not ok:
        _fails[ip] = recent + [now]
        time.sleep(1)
        msg = "ADMIN_PASSWORD is not set on the server." if not ADMIN_PASSWORD else "Wrong username or password."
        return page(request, "admin/login.html", error=msg)
    _fails.pop(ip, None)
    request.session["admin"] = True
    return RedirectResponse("/admin", 303)


@app.get("/admin/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", 303)


# ---------- admin: dashboard & projects ----------
@app.get("/admin", response_class=HTMLResponse)
def dashboard(request: Request):
    require_admin(request)
    projects = db.query("SELECT * FROM pf_projects ORDER BY position, created_at DESC")
    return page(request, "admin/dashboard.html", projects=projects)


@app.get("/admin/projects/new", response_class=HTMLResponse)
def new_project(request: Request):
    require_admin(request)
    return page(request, "admin/project_form.html", p={}, diagrams=[], steps=[])


@app.get("/admin/projects/{pid}", response_class=HTMLResponse)
def edit_project(request: Request, pid: int):
    require_admin(request)
    p = db.one("SELECT * FROM pf_projects WHERE id = ?", (pid,))
    if not p:
        raise HTTPException(404)
    diagrams = db.query("SELECT * FROM pf_diagrams WHERE project_id = ? ORDER BY position, id", (pid,))
    return page(request, "admin/project_form.html", p=p, diagrams=diagrams,
                steps=json.loads(p["steps_json"] or "[]"))


@app.post("/admin/projects/save")
async def save_project(request: Request):
    require_admin(request)
    form = await request.form()
    pid = int(form.get("id") or 0) or None
    title = (form.get("title") or "").strip() or "Untitled project"

    try:
        steps = [
            {"title": (s.get("title") or "").strip(), "body": (s.get("body") or "").strip()}
            for s in json.loads(form.get("steps_json") or "[]")
            if (s.get("title") or "").strip() or (s.get("body") or "").strip()
        ]
    except (ValueError, AttributeError):
        steps = []

    fields = {
        "title": title,
        "slug": unique_slug(form.get("slug") or title, pid),
        "hook": form.get("hook", ""),
        "objective": form.get("objective", ""),
        "goals": form.get("goals", ""),
        "applications": form.get("applications", ""),
        "steps_json": json.dumps(steps),
        "mermaid": form.get("mermaid", ""),
        "learned": form.get("learned", ""),
        "video_url": (form.get("video_url") or "").strip(),
        "github_url": (form.get("github_url") or "").strip(),
        "tags": form.get("tags", ""),
        "published": 1 if form.get("published") else 0,
        "featured": 1 if form.get("featured") else 0,
        "position": int(form.get("position") or 0),
    }

    cover = await save_upload(form.get("cover"), allowed=("image/",))
    if cover:
        fields["cover_id"] = cover
    if form.get("remove_cover"):
        fields["cover_id"] = None

    if pid:
        sets = ", ".join(f"{k} = ?" for k in fields)
        db.execute(f"UPDATE pf_projects SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                   (*fields.values(), pid))
    else:
        cols = ", ".join(fields)
        marks = ", ".join("?" for _ in fields)
        pid = db.execute(f"INSERT INTO pf_projects ({cols}) VALUES ({marks})", tuple(fields.values()))

    # existing diagrams: captions, order, deletions
    for d in db.query("SELECT id FROM pf_diagrams WHERE project_id = ?", (pid,)):
        if form.get(f"diagram_delete_{d['id']}"):
            db.execute("DELETE FROM pf_diagrams WHERE id = ?", (d["id"],))
        else:
            db.execute("UPDATE pf_diagrams SET caption = ?, position = ? WHERE id = ?",
                       (form.get(f"diagram_caption_{d['id']}", ""),
                        int(form.get(f"diagram_pos_{d['id']}") or 0), d["id"]))

    # new diagrams
    uploads = form.getlist("new_diagrams")
    captions = form.getlist("new_diagram_captions")
    for i, up in enumerate(uploads):
        fid = await save_upload(up, allowed=("image/",))
        if fid:
            cap = captions[i] if i < len(captions) else ""
            db.execute("INSERT INTO pf_diagrams (project_id, file_id, caption, position) VALUES (?, ?, ?, ?)",
                       (pid, fid, cap, 100 + i))

    db.execute("DELETE FROM pf_files WHERE id NOT IN (SELECT file_id FROM pf_diagrams) "
               "AND id NOT IN (SELECT cover_id FROM pf_projects WHERE cover_id IS NOT NULL) "
               "AND id NOT IN (SELECT photo_id FROM pf_profile WHERE photo_id IS NOT NULL) "
               "AND id NOT IN (SELECT resume_id FROM pf_profile WHERE resume_id IS NOT NULL)")

    dest = f"/projects/{fields['slug']}" if form.get("action") == "view" else f"/admin/projects/{pid}?saved=1"
    return RedirectResponse(dest, 303)


@app.post("/admin/projects/{pid}/delete")
def delete_project(request: Request, pid: int):
    require_admin(request)
    db.execute("DELETE FROM pf_diagrams WHERE project_id = ?", (pid,))
    db.execute("DELETE FROM pf_projects WHERE id = ?", (pid,))
    return RedirectResponse("/admin", 303)


@app.post("/admin/projects/{pid}/toggle")
def toggle_project(request: Request, pid: int):
    require_admin(request)
    db.execute("UPDATE pf_projects SET published = 1 - published WHERE id = ?", (pid,))
    return RedirectResponse("/admin", 303)


# ---------- admin: profile & resume ----------
@app.get("/admin/profile", response_class=HTMLResponse)
def edit_profile(request: Request):
    require_admin(request)
    return page(request, "admin/profile_form.html")


@app.post("/admin/profile")
async def save_profile(request: Request):
    require_admin(request)
    form = await request.form()
    keys = ["name", "headline", "intro", "about_md", "callout", "quote", "location",
            "email", "linkedin", "github", "skills", "certifications", "pillars"]
    fields = {k: form.get(k, "") for k in keys}
    photo = await save_upload(form.get("photo"), allowed=("image/",))
    if photo:
        fields["photo_id"] = photo
    resume_file = await save_upload(form.get("resume"), allowed=("application/pdf",))
    if resume_file:
        fields["resume_id"] = resume_file
    if form.get("remove_photo"):
        fields["photo_id"] = None
    if form.get("remove_resume"):
        fields["resume_id"] = None
    sets = ", ".join(f"{k} = ?" for k in fields)
    db.execute(f"UPDATE pf_profile SET {sets} WHERE id = 1", tuple(fields.values()))
    return RedirectResponse("/admin/profile?saved=1", 303)


@app.get("/healthz")
def health():
    return {"ok": True}
