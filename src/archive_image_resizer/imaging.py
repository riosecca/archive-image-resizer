"""Image conversion. The scale factor is decided by the height in pixels."""
import io
from pathlib import Path

from PIL import Image, ImageOps


def pick_scale(height, rules):
    for r in sorted(rules, key=lambda r: -r["min_height"]):
        if height >= r["min_height"]:
            return r["scale"]
    return 1.0


def _is_animated(im):
    return getattr(im, "is_animated", False) and getattr(im, "n_frames", 1) > 1


def _has_alpha(im):
    if im.mode in ("RGBA", "LA"):
        return im.getchannel("A").getextrema()[0] < 255
    return im.mode == "P" and "transparency" in im.info


def convert(path: Path, cfg: dict):
    """Convert and return (arcname_suffix or None, bytes or None, info).

    When bytes is None, the original file is used as is.
    """
    icfg = cfg["image"]
    size = path.stat().st_size
    ext = path.suffix.lstrip(".").lower()
    info = {"orig_size": size}
    if ext not in icfg["convert_extensions"]:
        return None, None, {**info, "action": "copy(not target)"}
    if size <= icfg["skip_below_bytes"]:
        return None, None, {**info, "action": "copy(<=1MB)"}
    try:
        im = Image.open(path)
        if _is_animated(im):
            return None, None, {**info, "action": "copy(animated)"}
        try:
            im = ImageOps.exif_transpose(im)  # bake in the EXIF orientation; height is measured after this
        except Exception:  # broken EXIF: continue without orientation correction
            im = Image.open(path)
        w, h = im.size
        scale = pick_scale(h, icfg["height_rules"])
        info.update(width=w, height=h, scale=scale)
        if im.mode in ("I;16", "I;16L", "I;16B", "I;16N", "I"):  # 16-bit gray: scale to 8 bits instead of clipping
            im = im.convert("I").point(lambda i: i * (1 / 256)).convert("L")
        elif im.mode == "F":
            return None, None, {**info, "action": "copy(unsupported mode)"}
        if scale < 1.0:
            im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
        buf = io.BytesIO()
        fmt, out_ext = "JPEG", ".jpg"
        if _has_alpha(im):  # composite transparency onto white and convert to JPEG
            rgba = im.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.getchannel("A"))
            im = bg
        im.convert("RGB").save(buf, "JPEG", quality=icfg["quality"], optimize=True)
        data = buf.getvalue()  # metadata such as EXIF is not saved, so it is dropped
    except Exception as e:  # broken images etc.: copy the original
        return None, None, {**info, "action": "copy(error)", "error": str(e)}
    info.update(quality=icfg["quality"], new_size=len(data), new_size_px=im.size)
    if len(data) >= size:
        return None, None, {**info, "action": "copy(larger)"}
    return out_ext, data, {**info, "action": f"convert({fmt})"}
