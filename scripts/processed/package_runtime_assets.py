"""Prepare the minimum server-side asset caches for the mobile app."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.processed.fetch_data import fetch_all_assets, load_storage_config


def package_runtime_assets(config_path: str = "configs/data_config.yaml") -> dict[str, str]:
    written_files = fetch_all_assets(config_path=config_path)
    config = load_storage_config(Path(config_path))

    manifest_path = config.raw_data_dir / "runtime_asset_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "description": "Minimum runtime asset caches for YourAce mobile API",
        "written_files": written_files,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    written_files["manifest"] = str(manifest_path)
    return written_files


if __name__ == "__main__":
    result = package_runtime_assets()
    for name, file_path in result.items():
        print(f"{name}: {file_path}")
