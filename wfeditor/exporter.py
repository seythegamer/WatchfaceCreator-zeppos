from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

from . import codegen, imaging
from .model import Project
from .resources import Resources


def render_preview(project: Project, path: Path, size: int | None = None) -> Path:
    from .render import make_preview_png

    make_preview_png(project, path, size)
    return path


def _copy_image(
    source: Path,
    target: Path,
    width: int,
    height: int,
    crop: tuple[int, int, int, int] | None = None,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    image = imaging.load_image(source)
    if image is None:
        shutil.copy2(source, target)
        return
    if width > 0 and height > 0:
        image = imaging.resize_image(image, width, height)
    if crop is not None:
        x, y, crop_w, crop_h = crop
        image = image.copy(x, y, crop_w, crop_h)
    if not imaging.write_png(image, target):
        shutil.copy2(source, target)


def _write_zip(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source).as_posix()
            # ZipFile.write sam dodaje "/" dla katalogów - dzięki temu w
            # archiwum są wpisy katalogów, tak jak w oficjalnych paczkach.
            archive.write(path, relative)
    return target


def build_device_tree(
    project: Project,
    root: Path,
    *,
    mode: str = "preview",
    lockscreen: int = 1,
    package_info: bool = True,
) -> Path:
    project.ensure_assets()
    resources = Resources(project)
    device = root / "device"
    watchface = device / "watchface"
    assets = device / "assets"
    watchface.mkdir(parents=True, exist_ok=True)
    (assets / "fonts").mkdir(parents=True, exist_ok=True)

    (device / "app.json").write_text(
        codegen.build_app_json(
            project,
            package_info=package_info,
            mode=mode,
            lockscreen=lockscreen,
        ),
        encoding="utf-8",
    )
    (device / "app.js").write_text(codegen.build_app_js(), encoding="utf-8")
    (watchface / "index.js").write_text(
        codegen.build_index_js(project, resources),
        encoding="utf-8",
    )

    for target, src, width, height in resources.entries():
        source = project.asset_file(src)
        if source is None:
            continue
        _copy_image(
            source,
            assets / target,
            width,
            height,
            resources.crop_for(target),
        )

    for font in resources.fonts():
        source = project.asset_file(font)
        if source is None:
            continue
        target = assets / font
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    frames = resources.generated_frames()
    if frames:
        from .render import render_bar_frame

        for target, el, ratio in frames:
            render_bar_frame(project, el, ratio, assets / target)

    text_images = resources.generated_text_images()
    if text_images:
        from .render import render_text_image

        for target, el in text_images:
            render_text_image(project, el, assets / target)

    render_preview(project, assets / "Preview.png", project.device.get("preview_size", 314))
    if any(el.type == "shortcut" and el.visible for el in project.elements):
        Image.new("RGBA", (8, 8), (0, 0, 0, 0)).save(assets / "empty.png", "PNG")

    side = root / "app-side"
    side.mkdir(parents=True, exist_ok=True)
    (side / "app.json").write_text(codegen.build_side_json(project), encoding="utf-8")
    return device


def export_zpk(project: Project, target: Path) -> Path:
    target = Path(target)
    with tempfile.TemporaryDirectory(prefix="wfstudio_") as tmp:
        root = Path(tmp)
        build_device_tree(project, root)
        device_zip = _write_zip(root / "device", root / "device.zip")
        side_zip = _write_zip(root / "app-side", root / "app-side.zip")
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(device_zip, "device.zip")
            archive.write(side_zip, "app-side.zip")
    return target


def export_source_zip(project: Project, target: Path) -> Path:
    target = Path(target)
    with tempfile.TemporaryDirectory(prefix="wfstudio_") as tmp:
        root = Path(tmp)
        device = build_device_tree(
            project,
            root,
            mode="production",
            lockscreen=0,
            package_info=True,
        )
        _write_zip(device, target)
    return target


def export_preview_png(project: Project, target: Path, size: int = 466) -> Path:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    return render_preview(project, target, size)
