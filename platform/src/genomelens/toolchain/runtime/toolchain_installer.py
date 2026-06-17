"""把缺失 runtime toolchains(运行时工具链) 下载并安装到项目缓存"""

# region import
from __future__ import annotations

import hashlib
import json
import re
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from genomelens.toolchain.runtime.resource_locator import project_root

# endregion


BLAST_LATEST_URL = "https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/"
IMAGEMAGICK_WINDOWS_ZIP_URL = "https://imagemagick.org/archive/windows/ImageMagick-windows.zip"
KNOWN_ARCHIVE_SHA256: dict[str, str] = {}


@dataclass(frozen=True)
class ToolchainInstallResult:
    """toolchain(工具链) 安装尝试的结果"""

    name: str
    status: str
    path: str = ""
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def downloads_root() -> Path:
    # 下载缓存和安装目录分离，便于重复安装时复用归档包。
    return project_root() / "references" / "downloads" / "toolchains"


def toolchains_root() -> Path:
    return project_root() / "toolchains"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_path(target: Path) -> Path:
    return target.with_suffix(target.suffix + ".sha256.json")


def _read_download_manifest(target: Path) -> dict[str, object]:
    path = _manifest_path(target)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_download_manifest(name: str, url: str, target: Path, digest: str) -> None:
    payload = {
        "name": name,
        "url": url,
        "archive": str(target),
        "sha256": digest,
    }
    _manifest_path(target).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _verify_archive(name: str, url: str, target: Path) -> bool:
    if not target.is_file() or target.stat().st_size <= 0:
        return False
    digest = _sha256(target)
    expected = KNOWN_ARCHIVE_SHA256.get(url, "")
    if expected and digest.lower() != expected.lower():
        raise RuntimeError(f"{name} archive SHA256 mismatch: expected {expected}, got {digest}")
    manifest = _read_download_manifest(target)
    recorded = str(manifest.get("sha256") or "")
    recorded_url = str(manifest.get("url") or "")
    if recorded and recorded != digest:
        return False
    if recorded_url and recorded_url != url:
        return False
    # 本地包一旦验证通过，就刷新 manifest，后续可直接信任缓存。
    _write_download_manifest(name, url, target, digest)
    return True


def _download(name: str, url: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if _verify_archive(name, url, target):
        return target
    if target.exists():
        target.unlink()
    tmp = target.with_suffix(target.suffix + ".part")
    # 先落到 .part，再替换目标文件，避免半截下载伪装成可用缓存。
    with urllib.request.urlopen(url, timeout=120) as response, tmp.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    tmp.replace(target)
    if not _verify_archive(name, url, target):
        raise RuntimeError(f"{name} archive verification failed: {target}")
    return target


def _ensure_within(root: Path, child: Path) -> None:
    root_resolved = root.resolve(strict=False)
    child_resolved = child.resolve(strict=False)
    if root_resolved == child_resolved:
        return
    if root_resolved not in child_resolved.parents:
        raise RuntimeError(f"Refusing to extract path outside target directory: {child}")


def _safe_extract_tar(archive: Path, target: Path) -> None:
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            if member.issym() or member.islnk():
                raise RuntimeError(f"Refusing to extract archive link: {member.name}")
            # 在真正 extractall 前先检查每个成员是否越界。
            _ensure_within(target, target / member.name)
        tar.extractall(target)


def _safe_extract_zip(archive: Path, target: Path) -> None:
    with zipfile.ZipFile(archive) as zip_handle:
        for info in zip_handle.infolist():
            _ensure_within(target, target / info.filename)
        zip_handle.extractall(target)


def _safe_replace_dir(source: Path, target: Path) -> None:
    root = toolchains_root().resolve(strict=False)
    resolved = target.resolve(strict=False)
    if not str(resolved).lower().startswith(str(root).lower()):
        raise RuntimeError(f"Refusing to replace path outside toolchains: {target}")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def _find_child_with_files(root: Path, required: list[str]) -> Path:
    required_lower = {item.lower() for item in required}
    for candidate in [root, *[item for item in root.rglob("*") if item.is_dir()]]:
        names = {item.name.lower() for item in candidate.iterdir() if item.is_file()}
        bin_dir = candidate / "bin"
        bin_names = {item.name.lower() for item in bin_dir.iterdir() if item.is_file()} if bin_dir.is_dir() else set()
        # 兼容“可执行文件在根目录”和“可执行文件在 bin/”两种归档布局。
        if required_lower.issubset(names) or required_lower.issubset(bin_names):
            return candidate
    raise FileNotFoundError(f"Downloaded archive did not contain required files: {required}")


def _latest_blast_windows_archive() -> str:
    with urllib.request.urlopen(BLAST_LATEST_URL, timeout=60) as response:
        listing = response.read().decode("utf-8", errors="replace")
    matches = re.findall(r'href="([^"]*ncbi-blast-[^"]+-x64-win64\.tar\.gz)"', listing)
    if not matches:
        raise RuntimeError("Could not find an x64 Windows BLAST+ tar.gz archive in NCBI LATEST")
    # 目录页里可能同时保留多个版本，按文件名排序后取最新值。
    return BLAST_LATEST_URL + sorted(matches)[-1]


def install_blast() -> ToolchainInstallResult:
    """下载并安装 BLAST+ 到 `toolchains/blast/current`"""

    try:
        url = _latest_blast_windows_archive()
        archive = downloads_root() / "blast" / Path(url).name
        _download("blast", url, archive)
        with tempfile.TemporaryDirectory(prefix="genomelens-blast-") as tmpdir:
            extract_root = Path(tmpdir)
            _safe_extract_tar(archive, extract_root)
            source = _find_child_with_files(extract_root, ["blastn.exe", "makeblastdb.exe"])
            target = toolchains_root() / "blast" / "current"
            _safe_replace_dir(source, target)
        return ToolchainInstallResult("blast", "ok", str(target), f"Installed BLAST+ from {url}")
    except Exception as exc:  # noqa: BLE001 - install command reports any download/extract failure
        return ToolchainInstallResult("blast", "error", message=str(exc))


def install_imagemagick() -> ToolchainInstallResult:
    """下载并安装 ImageMagick 到 `toolchains/imagemagick/current`"""

    try:
        archive = downloads_root() / "imagemagick" / "ImageMagick-windows.zip"
        _download("imagemagick", IMAGEMAGICK_WINDOWS_ZIP_URL, archive)
        with tempfile.TemporaryDirectory(prefix="genomelens-imagemagick-") as tmpdir:
            extract_root = Path(tmpdir)
            _safe_extract_zip(archive, extract_root)
            source = _find_child_with_files(extract_root, ["magick.exe"])
            target = toolchains_root() / "imagemagick" / "current"
            _safe_replace_dir(source, target)
        return ToolchainInstallResult(
            "imagemagick",
            "ok",
            str(target),
            f"Installed ImageMagick from {IMAGEMAGICK_WINDOWS_ZIP_URL}",
        )
    except Exception as exc:  # noqa: BLE001 - install command reports any download/extract failure
        return ToolchainInstallResult("imagemagick", "error", message=str(exc))


def install_toolchain(name: str) -> ToolchainInstallResult:
    """按公开名称安装受支持的 toolchain(工具链)"""

    # 统一的名称分发表同时服务于 CLI、配置和诊断模块。
    if name == "blast":
        return install_blast()
    if name == "imagemagick":
        return install_imagemagick()
    return ToolchainInstallResult(name, "unsupported", message=f"Unsupported toolchain: {name}")
