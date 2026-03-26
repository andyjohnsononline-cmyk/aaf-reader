# AAF Reader

A web-based AAF (Advanced Authoring Format) metadata inspector. Drop an AAF file in the browser and instantly see what's inside — no NLE required.

## What it extracts

- **File overview** — creating application, version, platform, creation date, AAF version
- **Media summary** — video resolution, codec, frame rate, color space, bit depth; audio sample rate, bit depth, channels
- **Compositions** — name, duration, edit rate, timecodes, track counts
- **Master clips** — clip names and slot counts
- **Source references** — network locator paths (MXF media references), tape source names, per-source media descriptors
- **Mob counts** — total mobs, compositions, master mobs, source mobs

## Quick start

### With Python (local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 and drop an AAF file.

### With Docker

```bash
docker compose up --build
```

Open http://localhost:8000.

## Privacy

Files are uploaded to the server for parsing and **immediately discarded** — nothing is written to disk beyond a temporary file that is deleted after processing. For maximum privacy, run locally or self-host with Docker.

## Tech stack

- **Backend** — Python, FastAPI, [pyaaf2](https://github.com/markreidvfx/pyaaf2)
- **Frontend** — Vanilla HTML/JS/CSS (no framework)
- **Deployment** — Docker / docker-compose

## Supported AAF sources

Tested with exports from Avid Media Composer. Should work with AAFs from any application that writes standard AAF files (Premiere Pro, DaVinci Resolve, etc.) since pyaaf2 implements the full AAF object specification.

## License

MIT
