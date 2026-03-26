"""
AAF metadata parser using pyaaf2.

Walks the AAF object tree and extracts all useful metadata into a
JSON-serializable dict suitable for display in the web frontend.
"""

from __future__ import annotations

import aaf2
from pathlib import Path


def _frames_to_tc(frames: int, fps: float) -> str:
    fps_int = int(round(fps))
    if fps_int == 0:
        return "00:00:00:00"
    remaining = int(frames)
    h = remaining // (fps_int * 3600)
    remaining %= fps_int * 3600
    m = remaining // (fps_int * 60)
    remaining %= fps_int * 60
    s = remaining // fps_int
    f = remaining % fps_int
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"


def _rational_to_float(rational) -> float | None:
    try:
        return float(rational.numerator) / float(rational.denominator)
    except Exception:
        return None


def _safe_get(obj, key, default=None):
    try:
        prop = obj.get(key)
        if prop is None:
            return default
        return prop.value
    except Exception:
        return default


def _parse_identification(header) -> dict:
    result = {
        "company": None,
        "product": None,
        "product_version": None,
        "platform": None,
        "toolkit_version": None,
        "date": None,
    }
    try:
        ident_list = header["IdentificationList"].value
        if not ident_list:
            return result
        ident = ident_list[0]
        result["company"] = _safe_get(ident, "CompanyName")
        result["product"] = _safe_get(ident, "ProductName")
        result["product_version"] = _safe_get(ident, "ProductVersionString")
        result["platform"] = _safe_get(ident, "Platform")
        toolkit = _safe_get(ident, "ToolkitVersion")
        if isinstance(toolkit, dict):
            result["toolkit_version"] = (
                f"{toolkit.get('major', '')}.{toolkit.get('minor', '')}"
                f".{toolkit.get('tertiary', '')}"
            )
        date_val = _safe_get(ident, "Date")
        if date_val is not None:
            result["date"] = str(date_val)
    except Exception:
        pass
    return result


def _parse_header(header) -> dict:
    info = {}
    version = _safe_get(header, "Version")
    if isinstance(version, dict):
        info["aaf_version"] = f"{version.get('major', '?')}.{version.get('minor', '?')}"
    else:
        info["aaf_version"] = str(version) if version else None

    last_modified = _safe_get(header, "LastModified")
    info["last_modified"] = str(last_modified) if last_modified else None

    byte_order_val = _safe_get(header, "ByteOrder")
    if byte_order_val == 0x4949 or byte_order_val == 18761:
        info["byte_order"] = "Little-Endian"
    elif byte_order_val == 0x4D4D or byte_order_val == 19789:
        info["byte_order"] = "Big-Endian"
    else:
        info["byte_order"] = str(byte_order_val) if byte_order_val else None

    return info


def _parse_video_descriptor(desc) -> dict:
    info = {"type": "video", "codec": desc.__class__.__name__}
    info["stored_width"] = _safe_get(desc, "StoredWidth")
    info["stored_height"] = _safe_get(desc, "StoredHeight")
    info["display_width"] = _safe_get(desc, "DisplayWidth")
    info["display_height"] = _safe_get(desc, "DisplayHeight")
    info["frame_layout"] = str(_safe_get(desc, "FrameLayout", ""))

    aspect = _safe_get(desc, "ImageAspectRatio")
    if aspect is not None:
        info["aspect_ratio"] = _rational_to_float(aspect)

    info["component_width"] = _safe_get(desc, "ComponentWidth")
    info["horizontal_subsampling"] = _safe_get(desc, "HorizontalSubsampling")
    info["vertical_subsampling"] = _safe_get(desc, "VerticalSubsampling")
    info["color_siting"] = str(_safe_get(desc, "ColorSiting", ""))
    info["coding_equations"] = str(_safe_get(desc, "CodingEquations", ""))
    info["transfer_characteristic"] = str(
        _safe_get(desc, "TransferCharacteristic", "")
    )

    compression = _safe_get(desc, "Compression")
    info["compression"] = str(compression) if compression else None

    info["video_line_map"] = _safe_get(desc, "VideoLineMap")
    info["image_size"] = _safe_get(desc, "ImageSize")

    sample_rate = _safe_get(desc, "SampleRate")
    if sample_rate is not None:
        info["sample_rate"] = _rational_to_float(sample_rate)

    info["length"] = _safe_get(desc, "Length")
    return info


def _parse_audio_descriptor(desc) -> dict:
    info = {"type": "audio", "codec": desc.__class__.__name__}

    sample_rate = _safe_get(desc, "AudioSamplingRate")
    if sample_rate is not None:
        info["sample_rate"] = _rational_to_float(sample_rate)

    info["channels"] = _safe_get(desc, "Channels")
    info["quantization_bits"] = _safe_get(desc, "QuantizationBits")
    info["block_align"] = _safe_get(desc, "BlockAlign")
    info["average_bps"] = _safe_get(desc, "AverageBPS")
    info["locked"] = _safe_get(desc, "Locked")
    info["dial_norm"] = _safe_get(desc, "DialNorm")
    info["audio_ref_level"] = _safe_get(desc, "AudioRefLevel")
    info["electro_spatial"] = str(_safe_get(desc, "ElectroSpatial", ""))
    info["length"] = _safe_get(desc, "Length")
    return info


def _parse_descriptor(desc) -> dict | None:
    if desc is None:
        return None

    class_name = desc.__class__.__name__
    video_types = ("CDCIDescriptor", "RGBADescriptor", "DigitalImageDescriptor")
    audio_types = ("PCMDescriptor", "WAVEDescriptor", "SoundDescriptor", "AIFCDescriptor")

    if class_name in video_types:
        return _parse_video_descriptor(desc)
    elif class_name in audio_types:
        return _parse_audio_descriptor(desc)
    elif class_name == "TapeDescriptor":
        return {"type": "tape", "codec": "TapeDescriptor"}
    elif class_name == "ImportDescriptor":
        return {"type": "import", "codec": "ImportDescriptor"}
    elif class_name == "MultipleDescriptor":
        sub_descriptors = []
        try:
            for sub in desc["FileDescriptors"].value:
                parsed = _parse_descriptor(sub)
                if parsed:
                    sub_descriptors.append(parsed)
        except Exception:
            pass
        return {"type": "multiple", "codec": "MultipleDescriptor", "sub_descriptors": sub_descriptors}
    else:
        return {"type": "unknown", "codec": class_name}


def _parse_locators(desc) -> list[dict]:
    locators = []
    try:
        loc_prop = desc.get("Locator")
        if loc_prop is None:
            return locators
        for loc in loc_prop.value:
            url = _safe_get(loc, "URLString")
            if url:
                locators.append({"type": "NetworkLocator", "path": str(url)})
    except Exception:
        pass
    return locators


def _parse_timecodes(mob) -> list[dict]:
    timecodes = []
    for slot in mob.slots:
        seg = slot.segment
        if seg.__class__.__name__ == "Timecode":
            fps = seg.fps
            start = seg.start
            timecodes.append({
                "slot_id": slot.slot_id,
                "fps": fps,
                "start_frame": start,
                "start_tc": _frames_to_tc(start, fps),
                "edit_rate": _rational_to_float(slot.edit_rate) if hasattr(slot, "edit_rate") else None,
            })
    return timecodes


def _parse_sequence_components(sequence, edit_rate_float: float) -> list[dict]:
    components = []
    try:
        comp_list = sequence["Components"].value
    except Exception:
        return components

    for item in comp_list:
        cls = item.__class__.__name__
        length = _safe_get(item, "Length")
        entry = {
            "type": cls,
            "length_frames": length,
            "length_tc": _frames_to_tc(length, edit_rate_float) if length else None,
        }
        if cls == "SourceClip":
            entry["start_frame"] = _safe_get(item, "StartTime")
            try:
                ref = _safe_get(item, "SourceReference")
                if ref and isinstance(ref, dict):
                    entry["source_mob_id"] = str(ref.get("mob_id", ""))
            except Exception:
                pass
        elif cls == "Transition":
            entry["cut_point"] = _safe_get(item, "CutPoint")
        components.append(entry)
    return components


def _parse_composition(mob) -> dict:
    edit_rate_float = 25.0
    timecodes = _parse_timecodes(mob)

    slots = []
    for slot in mob.slots:
        seg = slot.segment
        seg_class = seg.__class__.__name__
        er = _rational_to_float(slot.edit_rate) if hasattr(slot, "edit_rate") else None
        if er:
            edit_rate_float = er

        slot_info = {
            "slot_id": slot.slot_id,
            "segment_type": seg_class,
            "edit_rate": er,
        }

        if seg_class == "Sequence":
            components = _parse_sequence_components(seg, edit_rate_float)
            slot_info["component_count"] = len(components)
            slot_info["components"] = components
            total_length = sum(c.get("length_frames", 0) or 0 for c in components)
            slot_info["total_length_frames"] = total_length
            slot_info["total_length_tc"] = _frames_to_tc(total_length, edit_rate_float)
        elif seg_class == "Timecode":
            slot_info["fps"] = seg.fps
            slot_info["start_frame"] = seg.start
            slot_info["start_tc"] = _frames_to_tc(seg.start, seg.fps)

        slots.append(slot_info)

    video_tracks = sum(
        1 for s in slots
        if s["segment_type"] == "Sequence"
        and any(c.get("type") == "SourceClip" for c in s.get("components", []))
    )
    tc_tracks = sum(1 for s in slots if s["segment_type"] == "Timecode")

    total_duration_frames = 0
    for s in slots:
        if s["segment_type"] == "Sequence" and s.get("total_length_frames", 0) > 0:
            total_duration_frames = max(total_duration_frames, s["total_length_frames"])

    return {
        "name": mob.name,
        "mob_id": str(mob.mob_id),
        "edit_rate": edit_rate_float,
        "total_duration_frames": total_duration_frames,
        "total_duration_tc": _frames_to_tc(total_duration_frames, edit_rate_float),
        "timecodes": timecodes,
        "track_count": len(slots),
        "video_track_count": video_tracks,
        "timecode_track_count": tc_tracks,
        "slots": slots,
    }


_EDITORIAL_PATTERNS = {
    "scene", "slate", "take", "episode", "comments", "soundroll", "camroll",
    "labroll", "filename", "filepath", "audiofile", "audiotrack", "camera tc",
    "sound tc", "master_tc", "circletake", "uid", "cameraclipname",
    "metadataclipname", "clipname", "reelname", "srcreelname", "roll",
}

_COLOR_PATTERNS = {
    "asc_", "cdl", "color", "lut", "look", "whitebalance", "tint",
    "gamut", "logc", "transfer", "ndfilter", "nd_filter", "blacklevel",
    "saturation", "whitepoint", "primaries", "transfercurve",
    "scenecol", "targetcolor",
}

_LENS_PATTERNS = {
    "lens", "focal", "focus", "iris", "aperture", "entrance", "encoder",
    "lds", "optic",
}

_CAMERA_PATTERNS = {
    "camera", "cameramodel", "cameratype", "cameraid", "iso", "asa",
    "exposureindex", "exposuretime", "shutter", "framerate", "flip", "flop",
    "resolution", "width", "height", "sensor", "format", "firmware",
    "software", "arri", "codec", "imagerectangle", "displaywidth",
    "displayheight", "dropframe", "interlaced", "storedwidth", "storedheight",
    "sampledwidth", "sampledheight", "activeimage", "customresolution",
    "mirrorshutter", "cameraserial", "camerasoftware", "camerarevision",
    "pictureessence", "pipeline", "arriraw",
}


def _categorize_key(key: str) -> str:
    kl = key.lower()
    for pat in _EDITORIAL_PATTERNS:
        if pat in kl:
            return "editorial"
    for pat in _COLOR_PATTERNS:
        if pat in kl:
            return "color"
    for pat in _LENS_PATTERNS:
        if pat in kl:
            return "lens"
    for pat in _CAMERA_PATTERNS:
        if pat in kl:
            return "camera"
    return "other"


def _extract_mob_metadata(mob) -> dict:
    """Extract UserComments and Attributes from a mob, categorized."""
    raw = {}
    for prop_name in ("UserComments", "Attributes"):
        try:
            prop = mob.get(prop_name)
            if prop is None:
                continue
            for item in prop.value:
                name_prop = item.get("Name")
                val_prop = item.get("Value")
                if not name_prop:
                    continue
                n = name_prop.value if hasattr(name_prop, "value") else str(name_prop)
                v = val_prop.value if hasattr(val_prop, "value") else str(val_prop)
                raw[n] = str(v) if v is not None else ""
        except Exception:
            continue

    if not raw:
        return {}

    categorized = {
        "editorial": {},
        "camera": {},
        "lens": {},
        "color": {},
        "other": {},
    }
    for k, v in raw.items():
        cat = _categorize_key(k)
        categorized[cat][k] = v

    return {cat: entries for cat, entries in categorized.items() if entries}


def _parse_master_mob(mob) -> dict:
    slots = []
    for slot in mob.slots:
        seg = slot.segment
        er = _rational_to_float(slot.edit_rate) if hasattr(slot, "edit_rate") else None
        slots.append({
            "slot_id": slot.slot_id,
            "segment_type": seg.__class__.__name__,
            "edit_rate": er,
        })

    metadata = _extract_mob_metadata(mob)

    return {
        "name": mob.name,
        "mob_id": str(mob.mob_id),
        "slot_count": len(slots),
        "slots": slots,
        "metadata": metadata,
    }


def _parse_source_mob(mob) -> dict:
    descriptor = _parse_descriptor(mob.descriptor) if mob.descriptor else None
    locators = _parse_locators(mob.descriptor) if mob.descriptor else []
    timecodes = _parse_timecodes(mob)

    return {
        "name": mob.name or "(unnamed)",
        "mob_id": str(mob.mob_id),
        "descriptor": descriptor,
        "locators": locators,
        "timecodes": timecodes,
    }


def parse_aaf(filepath: str) -> dict:
    """
    Parse an AAF file and return a structured dict with all metadata.
    """
    path = Path(filepath)
    file_size = path.stat().st_size

    with aaf2.open(filepath, "r") as f:
        identification = _parse_identification(f.header)
        header_info = _parse_header(f.header)

        all_mobs = list(f.content.mobs)
        comp_mobs = [m for m in all_mobs if m.__class__.__name__ == "CompositionMob"]
        master_mobs = [m for m in all_mobs if m.__class__.__name__ == "MasterMob"]
        source_mobs = [m for m in all_mobs if m.__class__.__name__ == "SourceMob"]

        compositions = [_parse_composition(m) for m in comp_mobs]
        masters = [_parse_master_mob(m) for m in master_mobs]
        sources = [_parse_source_mob(m) for m in source_mobs]

        toplevel_names = [m.name for m in f.content.toplevel()]

        video_descriptors = []
        audio_descriptors = []
        tape_descriptors = []
        for src in sources:
            desc = src.get("descriptor")
            if not desc:
                continue
            if desc["type"] == "video":
                video_descriptors.append(desc)
            elif desc["type"] == "audio":
                audio_descriptors.append(desc)
            elif desc["type"] == "tape":
                tape_descriptors.append(desc)
            elif desc["type"] == "multiple":
                for sub in desc.get("sub_descriptors", []):
                    if sub["type"] == "video":
                        video_descriptors.append(sub)
                    elif sub["type"] == "audio":
                        audio_descriptors.append(sub)

        unique_video = _dedupe_media_summary(video_descriptors)
        unique_audio = _dedupe_media_summary(audio_descriptors)

    return {
        "file": {
            "name": path.name,
            "size_bytes": file_size,
            "size_human": _human_size(file_size),
        },
        "identification": identification,
        "header": header_info,
        "mob_counts": {
            "total": len(all_mobs),
            "compositions": len(comp_mobs),
            "master_mobs": len(master_mobs),
            "source_mobs": len(source_mobs),
        },
        "toplevel_compositions": toplevel_names,
        "compositions": compositions,
        "master_mobs": masters,
        "source_mobs": sources,
        "media_summary": {
            "video_formats": unique_video,
            "audio_formats": unique_audio,
            "tape_sources": len(tape_descriptors),
        },
    }


def _dedupe_media_summary(descriptors: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for d in descriptors:
        if d["type"] == "video":
            key = (
                d.get("stored_width"),
                d.get("stored_height"),
                d.get("codec"),
                d.get("component_width"),
                d.get("frame_layout"),
            )
        elif d["type"] == "audio":
            key = (
                d.get("sample_rate"),
                d.get("quantization_bits"),
                d.get("channels"),
                d.get("codec"),
            )
        else:
            continue
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


def _human_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} PB"
