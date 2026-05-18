import sys
import json
import shutil
import subprocess
from pathlib import Path


def ensure_deno_available() -> None:
    if shutil.which("deno") is None:
        raise RuntimeError(
            "Deno is required for yt-dlp JavaScript execution. "
            "Install Deno and make sure 'deno' is available on PATH."
        )


def fetch_comments(
    video_id: str,
    raw_dir: Path,
    output_stem: str | None = None,
    remote_components: bool = False,
    comment_limit: str | None = None,
) -> Path:
    ensure_deno_available()
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(raw_dir / "%(id)s.%(ext)s")

    remote_args = ["--remote-components", "ejs:github"] if remote_components else []
    extractor_options = ["comment_sort=top"]
    if comment_limit:
        extractor_options.append(f"max_comments={comment_limit}")
    extractor_args = ["--extractor-args", f"youtube:{';'.join(extractor_options)}"]
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--skip-download",
        "--write-info-json",
        "--write-comments",
        "--sleep-requests", "1",
        "--js-runtimes", "deno",
        *remote_args,
        *extractor_args,
        "--output", output_template,
        f"https://youtu.be/{video_id}",
    ]

    subprocess.run(cmd, check=True)

    temp_path = raw_dir / f"{video_id}.info.json"
    with open(temp_path, encoding="utf-8-sig") as f:
        channel_id = json.load(f).get("channel_id", "unknown")

    stem = output_stem if output_stem else f"{channel_id}_{video_id}"
    final_path = raw_dir / f"{stem}.info.json"
    temp_path.rename(final_path)

    return final_path
