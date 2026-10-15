"""Kiểm tra checksum tài liệu, lịch sử, cache RAR và media gốc của handoff."""

import hashlib
import json

from inspect_cache import ROOT


def main():
    bundle = ROOT.parent
    manifest = bundle / "07_MANIFESTS/SHA256SUMS.txt"
    results = []
    for line in manifest.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        expected, name = line.split(maxsplit=1)
        path = (bundle / name.strip()).resolve()
        if not path.is_relative_to(bundle.resolve()):
            raise ValueError("Manifest có đường dẫn vượt bundle")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        results.append({"file": name.strip(), "match": actual == expected})
    result = {
        "verified": len(results),
        "unchanged": all(row["match"] for row in results),
        "files": results,
    }
    (ROOT / "artifacts/bundle_integrity.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ("verified", "unchanged")}))
    if not result["unchanged"]:
        raise RuntimeError("Có file gốc khác checksum bàn giao")


if __name__ == "__main__":
    main()
