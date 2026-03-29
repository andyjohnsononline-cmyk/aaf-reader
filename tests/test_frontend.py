"""
Frontend smoke tests.

Validates HTML structure, CSS custom property usage, asset paths,
and worker.js integrity without a browser.
"""

import os
import re
from pathlib import Path

FRONTEND = Path(__file__).parent.parent / "frontend"


class TestHTMLStructure:
    @classmethod
    def setup_class(cls):
        cls.html = (FRONTEND / "index.html").read_text()

    def test_has_doctype(self):
        assert self.html.strip().startswith("<!DOCTYPE html>")

    def test_has_lang_attribute(self):
        assert 'lang="en"' in self.html

    def test_has_viewport_meta(self):
        assert 'name="viewport"' in self.html

    def test_has_title(self):
        assert "<title>AAF Reader</title>" in self.html

    def test_stylesheet_uses_relative_path(self):
        assert 'href="style.css"' in self.html
        assert 'href="/static/style.css"' not in self.html

    def test_script_uses_relative_path(self):
        assert 'src="app.js"' in self.html
        assert 'src="/static/app.js"' not in self.html

    def test_has_dropzone(self):
        assert 'id="dropzone"' in self.html

    def test_has_file_input(self):
        assert 'id="file-input"' in self.html
        assert 'accept=".aaf"' in self.html

    def test_has_loading_elements(self):
        assert 'id="loading"' in self.html
        assert 'id="loading-text"' in self.html
        assert 'id="loading-stage"' in self.html

    def test_has_error_banner(self):
        assert 'id="error"' in self.html

    def test_has_results_sections(self):
        for section_id in ["overview-content", "media-content", "compositions-content",
                           "clips-content", "clip-metadata-content", "sources-content"]:
            assert f'id="{section_id}"' in self.html, f"Missing {section_id}"

    def test_has_google_fonts_link(self):
        assert "fonts.googleapis.com" in self.html
        assert "DM+Sans" in self.html
        assert "JetBrains+Mono" in self.html

    def test_has_preconnect(self):
        assert 'rel="preconnect"' in self.html

    def test_privacy_footer(self):
        assert "Your files never leave your browser" in self.html


class TestAppJS:
    @classmethod
    def setup_class(cls):
        cls.js = (FRONTEND / "app.js").read_text()

    def test_is_iife(self):
        assert self.js.strip().startswith("(() => {")
        assert self.js.strip().endswith("})();")

    def test_no_fetch_api_call(self):
        assert "fetch(" not in self.js or "fetch(parserBase" not in self.js
        assert '"/api/parse"' not in self.js

    def test_uses_worker(self):
        assert 'new Worker("worker.js")' in self.js

    def test_has_file_size_limit(self):
        assert "MAX_FILE_SIZE" in self.js

    def test_has_esc_function(self):
        assert "function esc(" in self.js

    def test_esc_uses_textcontent(self):
        assert "textContent" in self.js

    def test_has_stage_labels(self):
        assert "STAGE_LABELS" in self.js
        assert "Loading parser engine" in self.js
        assert "Installing packages" in self.js
        assert "Parsing AAF file" in self.js

    def test_handles_aaf_extension_check(self):
        assert ".aaf" in self.js

    def test_handles_worker_error(self):
        assert "handleWorkerError" in self.js

    def test_has_progress_handling(self):
        assert '"progress"' in self.js


class TestWorkerJS:
    @classmethod
    def setup_class(cls):
        cls.js = (FRONTEND / "worker.js").read_text()

    def test_imports_pyodide(self):
        assert "importScripts" in self.js
        assert "pyodide" in self.js

    def test_loads_vendored_wheels(self):
        assert "olefile" in self.js
        assert "pyaaf2" in self.js
        assert "wheels/" in self.js

    def test_has_message_handler(self):
        assert "self.onmessage" in self.js

    def test_sends_progress_messages(self):
        assert '"loading"' in self.js
        assert '"installing"' in self.js
        assert '"parsing"' in self.js

    def test_cleans_up_temp_file(self):
        assert "unlink" in self.js

    def test_sends_structured_responses(self):
        assert "ok: true" in self.js
        assert "ok: false" in self.js

    def test_has_error_code(self):
        assert "PARSE_ERROR" in self.js
        assert "UNKNOWN_OP" in self.js

    def test_partial_init_protection(self):
        """pyodide should only be set after full init succeeds."""
        assert "pyodide = py;" in self.js
        lines = self.js.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("pyodide = ") and "py;" not in stripped and "null" not in stripped:
                raise AssertionError(f"Found premature pyodide assignment: {stripped}")

    def test_loads_parser_via_fs(self):
        assert "FS.writeFile" in self.js
        assert "aaf_parser.py" in self.js


class TestCSS:
    @classmethod
    def setup_class(cls):
        cls.css = (FRONTEND / "style.css").read_text()

    def test_has_root_variables(self):
        assert ":root" in self.css

    def test_has_design_system_colors(self):
        assert "--accent" in self.css
        assert "--bg" in self.css
        assert "--surface" in self.css

    def test_has_font_variables(self):
        assert "--font-body" in self.css
        assert "--font-mono" in self.css
        assert "--font-display" in self.css

    def test_has_satoshi_font_face(self):
        assert "@font-face" in self.css
        assert "Satoshi" in self.css

    def test_satoshi_uses_local_files(self):
        assert "fonts/satoshi" in self.css

    def test_no_absolute_paths(self):
        assert "/static/" not in self.css


class TestAssets:
    def test_wheels_exist(self):
        wheels = FRONTEND / "wheels"
        assert wheels.is_dir()
        whl_files = list(wheels.glob("*.whl"))
        assert len(whl_files) >= 2
        names = [f.name for f in whl_files]
        assert any("pyaaf2" in n for n in names)
        assert any("olefile" in n for n in names)

    def test_fonts_exist(self):
        fonts = FRONTEND / "fonts"
        assert fonts.is_dir()
        woff2_files = list(fonts.glob("*.woff2"))
        assert len(woff2_files) >= 3
        assert any("satoshi" in f.name.lower() for f in woff2_files)

    def test_parser_exists(self):
        assert (FRONTEND / "aaf_parser.py").is_file()

    def test_worker_exists(self):
        assert (FRONTEND / "worker.js").is_file()
