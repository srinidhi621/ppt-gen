# External Asset Sync Pipeline

This toolchain ingests pinned third-party icon packs into `./assets/external_assets/` and builds offline manifests for cue-to-asset lookup.

## Entrypoint

Run from repo root:

```bash
bash tools/external_assets/sync_external_assets.sh
```

This command performs:

1. Download pinned Iconify JSON payloads for `tabler`, `lucide`, and `fluent`.
2. Convert Iconify `icons.json` into standalone SVG files.
3. Download pinned AWS architecture icon ZIP.
4. Extract and copy AWS SVGs into normalized `aws/svg/` while preserving subfolders from the ZIP extraction root.
5. Generate per-pack `manifest.json`, per-pack `LICENSE.txt`, and a unified `registry.manifest.json`.

## Pinning and safe version bumps

All sources are version-pinned in `tools/external_assets/sync_external_assets.sh`. There is no use of `latest` URLs.

To bump versions safely:

1. Update the pinned URLs and version constants in `sync_external_assets.sh`.
2. Re-run sync.
3. Diff resulting `manifest.json` and `registry.manifest.json` for expected changes.
4. Keep deterministic ordering (already enforced by scripts) so diffs remain reviewable.

## Tooling constraints

The pipeline only uses:

- `bash`
- `curl`
- `unzip`
- `python3`

No `node`/`npm` dependency is required.

## Output layout

Under `./assets/external_assets/`:

- `tabler/`
  - `raw/iconify/icons.json`
  - `raw/iconify/info.json`
  - `raw/iconify/metadata.json`
  - `svg/<icon_name>.svg`
  - `LICENSE.txt`
  - `manifest.json`
- `lucide/` (same structure as tabler)
- `fluent/` (same structure as tabler)
- `aws/`
  - `raw/aws_zip/icon-package.zip`
  - `raw/aws_zip/extracted/...`
  - `svg/<preserved_extracted_subpath>/*.svg`
  - `LICENSE.txt`
  - `manifest.json`
- `registry.manifest.json`

### AWS SVG structure note

`aws/svg/` preserves all path segments under `aws/raw/aws_zip/extracted/` for each `.svg` file. Example shape:

- `aws/svg/<zip-folder>/<category>/<service>/<asset>.svg`

Exact folder names depend on the ZIP contents and are intentionally preserved.

## Manifest schema

Each pack has `manifest.json`:

```json
{
  "pack": "tabler|lucide|fluent|aws",
  "pack_version": "pinned version or AWS zip label",
  "license": {
    "type": "MIT|ISC|MIT (MS)|AWS brand assets",
    "source": "URL",
    "notes": "short note"
  },
  "source": {
    "download_urls": ["..."],
    "pinned": true
  },
  "icons": [
    {
      "id": "pack:icon_name",
      "name": "icon_name",
      "svg_path": "relative/path/to/svg",
      "tags": ["..."],
      "categories": ["..."],
      "aliases": ["..."],
      "search_text": "space-joined search tokens"
    }
  ]
}
```

`registry.manifest.json` is a flattened cross-pack index:

```json
{
  "generated_at": "ISO-8601 UTC timestamp",
  "packs": ["tabler", "lucide", "fluent", "aws"],
  "icons": [
    {
      "id": "pack:icon_name",
      "pack": "pack_name",
      "pack_version": "version",
      "name": "icon_name",
      "svg_path": "relative/path",
      "tags": ["..."],
      "categories": ["..."],
      "aliases": ["..."],
      "search_text": "..."
    }
  ]
}
```

## Offline usage

After a successful sync, consumers can read:

- `./assets/external_assets/registry.manifest.json`
- `./assets/external_assets/<pack>/manifest.json`
- `./assets/external_assets/<pack>/svg/...`

No network is required unless re-syncing to refresh source assets.
