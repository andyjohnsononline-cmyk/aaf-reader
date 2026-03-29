"""
Tests for the AAF metadata parser.

Tests helper functions with synthetic inputs and the full parse_aaf()
against the real example AAF file.
"""

import sys
import os
import json
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "frontend"))

from aaf_parser import (
    _frames_to_tc,
    _rational_to_float,
    _human_size,
    _categorize_key,
    _dedupe_media_summary,
    parse_aaf,
)


EXAMPLE_AAF = Path(__file__).parent.parent / "Example AAFs" / "voetbalouders-aaftest-to-protools.aaf"


class TestFramesToTimecode:
    def test_zero_frames(self):
        assert _frames_to_tc(0, 25.0) == "00:00:00:00"

    def test_one_second_at_25fps(self):
        assert _frames_to_tc(25, 25.0) == "00:00:01:00"

    def test_one_minute(self):
        assert _frames_to_tc(25 * 60, 25.0) == "00:01:00:00"

    def test_one_hour(self):
        assert _frames_to_tc(25 * 3600, 25.0) == "01:00:00:00"

    def test_complex_timecode_25fps(self):
        frames = 25 * 3600 + 25 * 60 * 2 + 25 * 3 + 12
        assert _frames_to_tc(frames, 25.0) == "01:02:03:12"

    def test_24fps(self):
        assert _frames_to_tc(24, 24.0) == "00:00:01:00"
        assert _frames_to_tc(48, 24.0) == "00:00:02:00"

    def test_30fps(self):
        assert _frames_to_tc(30, 30.0) == "00:00:01:00"
        assert _frames_to_tc(30 * 60 + 15, 30.0) == "00:01:00:15"

    def test_zero_fps_returns_zeros(self):
        assert _frames_to_tc(100, 0.0) == "00:00:00:00"

    def test_fractional_fps_rounds(self):
        assert _frames_to_tc(24, 23.976) == "00:00:01:00"

    def test_large_frame_count(self):
        frames = 25 * 86400
        result = _frames_to_tc(frames, 25.0)
        assert result == "24:00:00:00"


class TestRationalToFloat:
    def test_simple_rational(self):
        r = SimpleNamespace(numerator=25, denominator=1)
        assert _rational_to_float(r) == 25.0

    def test_fractional_rational(self):
        r = SimpleNamespace(numerator=48000, denominator=1)
        assert _rational_to_float(r) == 48000.0

    def test_true_fraction(self):
        r = SimpleNamespace(numerator=24000, denominator=1001)
        result = _rational_to_float(r)
        assert abs(result - 23.976) < 0.01

    def test_none_on_exception(self):
        assert _rational_to_float("not a rational") is None

    def test_none_on_missing_attrs(self):
        assert _rational_to_float(SimpleNamespace()) is None


class TestHumanSize:
    def test_bytes(self):
        assert _human_size(500) == "500.0 B"

    def test_kilobytes(self):
        result = _human_size(2048)
        assert "KB" in result

    def test_megabytes(self):
        result = _human_size(2 * 1024 * 1024)
        assert "MB" in result

    def test_gigabytes(self):
        result = _human_size(3 * 1024 * 1024 * 1024)
        assert "GB" in result

    def test_zero(self):
        assert _human_size(0) == "0.0 B"


class TestCategorizeKey:
    def test_editorial_keys(self):
        assert _categorize_key("Scene") == "editorial"
        assert _categorize_key("Slate") == "editorial"
        assert _categorize_key("Take") == "editorial"
        assert _categorize_key("Soundroll") == "editorial"
        assert _categorize_key("Comments") == "editorial"

    def test_camera_keys(self):
        assert _categorize_key("CameraModel") == "camera"
        assert _categorize_key("CameraType") == "camera"
        assert _categorize_key("ISO") == "camera"
        assert _categorize_key("ShutterAngle") == "camera"

    def test_lens_keys(self):
        assert _categorize_key("FocalLength") == "lens"
        assert _categorize_key("LensType") == "lens"
        assert _categorize_key("Iris") == "lens"

    def test_color_keys(self):
        assert _categorize_key("ASC_SOP") == "color"
        assert _categorize_key("CDLValue") == "color"
        assert _categorize_key("LUTName") == "color"
        assert _categorize_key("WhiteBalance") == "color"

    def test_unknown_defaults_to_other(self):
        assert _categorize_key("RandomKey") == "other"
        assert _categorize_key("xyz123") == "other"

    def test_case_insensitive(self):
        assert _categorize_key("scene") == "editorial"
        assert _categorize_key("SCENE") == "editorial"
        assert _categorize_key("cameramodel") == "camera"


class TestDedupeMediaSummary:
    def test_dedupes_identical_video(self):
        descs = [
            {"type": "video", "stored_width": 1920, "stored_height": 1080, "codec": "CDCI", "component_width": 10, "frame_layout": "FullFrame"},
            {"type": "video", "stored_width": 1920, "stored_height": 1080, "codec": "CDCI", "component_width": 10, "frame_layout": "FullFrame"},
        ]
        result = _dedupe_media_summary(descs)
        assert len(result) == 1

    def test_keeps_different_video(self):
        descs = [
            {"type": "video", "stored_width": 1920, "stored_height": 1080, "codec": "CDCI", "component_width": 10, "frame_layout": "FullFrame"},
            {"type": "video", "stored_width": 3840, "stored_height": 2160, "codec": "CDCI", "component_width": 10, "frame_layout": "FullFrame"},
        ]
        result = _dedupe_media_summary(descs)
        assert len(result) == 2

    def test_dedupes_identical_audio(self):
        descs = [
            {"type": "audio", "sample_rate": 48000, "quantization_bits": 24, "channels": 1, "codec": "PCM"},
            {"type": "audio", "sample_rate": 48000, "quantization_bits": 24, "channels": 1, "codec": "PCM"},
        ]
        result = _dedupe_media_summary(descs)
        assert len(result) == 1

    def test_empty_list(self):
        assert _dedupe_media_summary([]) == []


class TestParseAAFIntegration:
    """Integration tests using the real example AAF file."""

    @classmethod
    def setup_class(cls):
        if not EXAMPLE_AAF.exists():
            import pytest
            pytest.skip(f"Example AAF not found: {EXAMPLE_AAF}")
        cls.result = parse_aaf(str(EXAMPLE_AAF))

    def test_returns_dict(self):
        assert isinstance(self.result, dict)

    def test_json_serializable(self):
        json_str = json.dumps(self.result)
        assert len(json_str) > 100

    def test_has_file_info(self):
        f = self.result["file"]
        assert f["name"] == "voetbalouders-aaftest-to-protools.aaf"
        assert f["size_bytes"] > 0
        assert "MB" in f["size_human"] or "KB" in f["size_human"] or "B" in f["size_human"]

    def test_has_identification(self):
        ident = self.result["identification"]
        assert isinstance(ident, dict)
        assert "product" in ident
        assert "company" in ident

    def test_has_header(self):
        hdr = self.result["header"]
        assert isinstance(hdr, dict)
        assert "byte_order" in hdr

    def test_has_mob_counts(self):
        mc = self.result["mob_counts"]
        assert mc["total"] > 0
        assert isinstance(mc["compositions"], int)
        assert isinstance(mc["master_mobs"], int)
        assert isinstance(mc["source_mobs"], int)
        assert mc["total"] == mc["compositions"] + mc["master_mobs"] + mc["source_mobs"]

    def test_has_compositions(self):
        comps = self.result["compositions"]
        assert isinstance(comps, list)

    def test_compositions_have_required_fields(self):
        for comp in self.result["compositions"]:
            assert "name" in comp
            assert "mob_id" in comp
            assert "edit_rate" in comp
            assert "total_duration_tc" in comp
            assert "track_count" in comp

    def test_has_master_mobs(self):
        masters = self.result["master_mobs"]
        assert isinstance(masters, list)

    def test_master_mobs_have_required_fields(self):
        for mm in self.result["master_mobs"]:
            assert "name" in mm
            assert "mob_id" in mm
            assert "slot_count" in mm

    def test_has_source_mobs(self):
        sources = self.result["source_mobs"]
        assert isinstance(sources, list)

    def test_source_mobs_have_required_fields(self):
        for sm in self.result["source_mobs"]:
            assert "name" in sm
            assert "mob_id" in sm
            assert "descriptor" in sm

    def test_has_media_summary(self):
        ms = self.result["media_summary"]
        assert isinstance(ms, dict)
        assert "video_formats" in ms
        assert "audio_formats" in ms
        assert "tape_sources" in ms

    def test_has_toplevel_compositions(self):
        assert "toplevel_compositions" in self.result
        assert isinstance(self.result["toplevel_compositions"], list)

    def test_timecodes_are_valid_format(self):
        for comp in self.result["compositions"]:
            tc = comp.get("total_duration_tc", "")
            if tc:
                parts = tc.split(":")
                assert len(parts) == 4, f"Invalid timecode format: {tc}"
                for p in parts:
                    assert p.isdigit(), f"Non-numeric timecode part: {p} in {tc}"
