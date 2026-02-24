#!/usr/bin/env bash
set -euo pipefail

DICOM_ROOT="${DICOM_ROOT:-/home/dicom}"
SCP_PORT="${SCP_PORT:-104}"
SCP_AET="${SCP_AET:-DICOMRS_SCP}"

mkdir -p "$DICOM_ROOT"

exec storescp \
  --verbose \
  --aetitle "$SCP_AET" \
  "$SCP_PORT" \
  --filename-extension .dcm \
  -od "$DICOM_ROOT"
