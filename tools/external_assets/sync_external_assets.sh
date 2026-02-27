#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ASSETS_ROOT="${REPO_ROOT}/assets/external_assets"

TABLER_VERSION="1.2.17"
LUCIDE_VERSION="1.2.5"
FLUENT_VERSION="1.2.38"
AWS_ZIP_LABEL="Icon-package_01302026"

TABLER_URLS=(
  "https://unpkg.com/@iconify-json/tabler@1.2.17/icons.json"
  "https://unpkg.com/@iconify-json/tabler@1.2.17/info.json"
  "https://unpkg.com/@iconify-json/tabler@1.2.17/metadata.json"
)
LUCIDE_URLS=(
  "https://unpkg.com/@iconify-json/lucide@1.2.5/icons.json"
  "https://unpkg.com/@iconify-json/lucide@1.2.5/info.json"
  "https://unpkg.com/@iconify-json/lucide@1.2.5/metadata.json"
)
FLUENT_URLS=(
  "https://unpkg.com/@iconify-json/fluent@1.2.38/icons.json"
  "https://unpkg.com/@iconify-json/fluent@1.2.38/info.json"
  "https://unpkg.com/@iconify-json/fluent@1.2.38/metadata.json"
)
AWS_ZIP_URL="https://d1.awsstatic.com/onedam/marketing-channels/website/aws/en_US/architecture/approved/architecture-icons/Icon-package_01302026.31b40d126ed27079b708594940ad577a86150582.zip"

curl_fetch() {
  local url="$1"
  local out="$2"
  mkdir -p "$(dirname "${out}")"
  echo "Downloading ${url}"
  curl -L --fail --retry 3 --retry-delay 1 -o "${out}" "${url}"
}

download_iconify_pack() {
  local pack="$1"
  shift
  local urls=("$@")
  local raw_dir="${ASSETS_ROOT}/${pack}/raw/iconify"
  mkdir -p "${raw_dir}"

  for url in "${urls[@]}"; do
    local name
    name="$(basename "${url}")"
    curl_fetch "${url}" "${raw_dir}/${name}"
  done

  python3 "${SCRIPT_DIR}/iconify_to_svg.py" \
    --icons-json "${raw_dir}/icons.json" \
    --output-dir "${ASSETS_ROOT}/${pack}/svg"
}

sync_aws_pack() {
  local raw_zip_dir="${ASSETS_ROOT}/aws/raw/aws_zip"
  local zip_path="${raw_zip_dir}/icon-package.zip"
  local extracted_dir="${raw_zip_dir}/extracted"
  local aws_svg_root="${ASSETS_ROOT}/aws/svg"

  mkdir -p "${raw_zip_dir}" "${aws_svg_root}"
  curl_fetch "${AWS_ZIP_URL}" "${zip_path}"

  rm -rf "${extracted_dir}"
  mkdir -p "${extracted_dir}"
  unzip -oq "${zip_path}" -d "${extracted_dir}"

  # Rebuild normalized AWS SVG tree deterministically from extracted ZIP contents.
  rm -rf "${aws_svg_root}"
  mkdir -p "${aws_svg_root}"

  while IFS= read -r svg_file; do
    local rel
    rel="${svg_file#${extracted_dir}/}"
    local target="${aws_svg_root}/${rel}"
    mkdir -p "$(dirname "${target}")"
    cp "${svg_file}" "${target}"
  done < <(find "${extracted_dir}" -type f -name '*.svg' | LC_ALL=C sort)
}

main() {
  mkdir -p "${ASSETS_ROOT}"

  download_iconify_pack "tabler" "${TABLER_URLS[@]}"
  download_iconify_pack "lucide" "${LUCIDE_URLS[@]}"
  download_iconify_pack "fluent" "${FLUENT_URLS[@]}"

  sync_aws_pack

  python3 "${SCRIPT_DIR}/build_manifest.py" \
    --assets-root "${ASSETS_ROOT}" \
    --tabler-version "${TABLER_VERSION}" \
    --lucide-version "${LUCIDE_VERSION}" \
    --fluent-version "${FLUENT_VERSION}" \
    --aws-zip-label "${AWS_ZIP_LABEL}" \
    --tabler-url "${TABLER_URLS[0]}" --tabler-url "${TABLER_URLS[1]}" --tabler-url "${TABLER_URLS[2]}" \
    --lucide-url "${LUCIDE_URLS[0]}" --lucide-url "${LUCIDE_URLS[1]}" --lucide-url "${LUCIDE_URLS[2]}" \
    --fluent-url "${FLUENT_URLS[0]}" --fluent-url "${FLUENT_URLS[1]}" --fluent-url "${FLUENT_URLS[2]}" \
    --aws-url "${AWS_ZIP_URL}"

  echo "Sync complete. Outputs written to ${ASSETS_ROOT}"
}

main "$@"
