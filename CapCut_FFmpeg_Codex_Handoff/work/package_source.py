"""Đóng gói duy nhất mã nguồn tự viết; loại cache, media và đầu ra thử nghiệm."""

import hashlib
import json
from zipfile import ZIP_DEFLATED, ZipFile

from inspect_cache import ROOT


def main():
    own = [
        path
        for path in ROOT.iterdir()
        if path.is_file()
        and path.suffix in (".py", ".md", ".ps1", ".bat", ".json", ".txt")
    ]
    own.extend((ROOT / "presets").glob("*.json"))
    license_path = ROOT.parents[1] / "LICENSE"
    output = ROOT / "artifacts/capcut_gpu_source.zip"
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(own):
            archive.write(path, path.relative_to(ROOT))
        if license_path.exists():
            archive.write(license_path, "LICENSE")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".sha256").write_text(f"{digest}  {output.name}\n")
    print(
        json.dumps(
            {
                "files": len(own) + int(license_path.exists()),
                "bytes": output.stat().st_size,
                "sha256": digest,
            }
        )
    )


if __name__ == "__main__":
    main()
