# AWS Project Portfolio

A personal portfolio for AWS projects with a private editor. Each project follows one template:
**hook → objective → project goals → applications used → architecture & diagrams → steps → demo → what I learned**.
There is also an About page with your photo, skills, certifications and resume (PDF).

- Public site: `/`, `/projects/<slug>`, `/about`, `/resume`
- Your editor: `/admin` (login with `ADMIN_USERNAME` / `ADMIN_PASSWORD`)

Stack: FastAPI + Jinja templates and its own free Turso (libSQL) database, running as a separate Render web service
next to Tooltrick. Images and the resume are stored in the database too, because Render's disk is wiped on every deploy.

---

## 1. Run it on your own computer

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
ADMIN_PASSWORD=test123 uvicorn app.main:app --reload --port 8090
```

Open http://localhost:8090/admin and log in as `admin` / `test123`. Without Turso variables it uses a local
`portfolio.db` file, so you can play around safely.

## 2. Create the separate Turso database (free)

The portfolio gets its own database, so it never touches Tooltrick's data.

**In the browser:** go to app.turso.tech → *Create Database* → name it `portfolio` → open it →
copy the **URL** (`libsql://portfolio-<your-org>.turso.io`) and click *Create Token* → copy the token.

**Or with the Turso CLI:**

```bash
turso db create portfolio
turso db show portfolio --url          # → libsql://portfolio-<your-org>.turso.io
turso db tokens create portfolio       # → long token, keep it secret
```

The free plan allows several databases, so this costs nothing extra. Tables are created automatically on first start,
already filled with your name, headline, certifications and the four pillars from your banner.

## 3. Deploy on Render, next to Tooltrick

1. Put this folder in a new GitHub repo (or a subfolder of an existing one; then set *Root Directory* in Render).
2. Render dashboard → **New → Blueprint** → select the repo. It reads `render.yaml`.
   (Or **New → Web Service** and copy the build/start commands from `render.yaml`.)
3. Fill in the secret variables when asked:
   - `ADMIN_PASSWORD`: a long password, this is your login
   - `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`: the **portfolio** database from step 2 (not Tooltrick's)
   - `SECRET_KEY` is generated for you
4. Deploy. Your site is at `https://aws-portfolio.onrender.com` (or whatever name you pick).
5. Optional: Settings → **Custom Domains** to use e.g. `yourname.nl`, with Tooltrick on `tooltrick.yourname.nl`.

> The free plan sleeps after 15 minutes without visitors; the first visit then takes ~30–50 seconds.
> If recruiters will visit, the Starter plan keeps it awake.

## 4. Fill it in

1. `/admin/profile`: name, headline, about text, photo, **resume PDF**, skills, certifications, links.
2. `/admin/projects/new`: fill the template. Tip: paste a LinkedIn post into **Quick fill** to prefill
   the hook, demo link, tags, applications and lessons, then clean it up.
3. Tick **Published** to make a project public, **Featured** to put it in the chips at the top.

## Customise the look

The colours come from your LinkedIn banner (navy, blue `#2b6cd4`, orange `#ee8f2f`) and are tokens at the top of
`static/style.css`. The banner itself is `static/banner.png`: it shows on the About page and as the link preview image
when you share the site. Replace that file when you earn a new cert.

## Files

```
app/main.py        routes: public pages, admin, uploads, login
app/db.py          SQLite locally / Turso in production, table definitions
templates/         public pages + admin/ editor pages
static/style.css   theme
render.yaml        Render deploy config
```
