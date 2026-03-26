"""
FastAPI app for AAF Reader.

Provides a single /api/parse endpoint that accepts an AAF file upload
and returns parsed metadata as JSON. Serves the frontend as static files.
"""

from __future__ import annotations

import tempfile
import os
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from aaf_parser import parse_aaf

app = FastAPI(title="AAF Reader", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@app.post("/api/parse")
async def parse_aaf_file(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".aaf"):
        raise HTTPException(status_code=400, detail="File must be an .aaf file")

    tmp_path = None
    try:
        contents = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".aaf") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        result = parse_aaf(tmp_path)
        result["file"]["name"] = file.filename
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse AAF file: {str(e)}",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


EXAMPLE_DIR = Path(__file__).parent.parent / "Example AAFs"


@app.get("/api/preview")
async def preview():
    """Parse the bundled example AAF and return JSON (for development screenshots)."""
    examples = list(EXAMPLE_DIR.glob("*.aaf"))
    if not examples:
        raise HTTPException(status_code=404, detail="No example AAF found")
    result = parse_aaf(str(examples[0]))
    result["file"]["name"] = examples[0].name
    return result


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
