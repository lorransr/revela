#!/bin/sh
set -eu
: "${ICLOUD_USER:?defina ICLOUD_USER no .env}"
: "${ALBUM:?defina ALBUM no .env}"

mkdir -p -m 700 /data/session
icloudpd --username "$ICLOUD_USER" --cookie-directory /data/session \
  --directory /data/icloud --album "$ALBUM" --size adjusted \
  --folder-structure "{:%Y-%m-%d}" --skip-videos --skip-live-photos "$@"

# O fotobuch ignora HEIC sem avisar. /data/photos espelha /data/icloud com HEIC
# convertido para JPEG e o resto como hardlink, então o download continua incremental.
cd /data/icloud
find . -type f ! -name '.*' | while read -r f; do
  case "$f" in
    *.[hH][eE][iI][cC]) out="/data/photos/${f%.*}.jpg" ;;
    *) out="/data/photos/$f" ;;
  esac
  [ -e "$out" ] && continue
  mkdir -p "$(dirname "$out")"
  case "$f" in
    *.[hH][eE][iI][cC]) heif-convert --quiet -q 95 "$f" "$out" && touch -r "$f" "$out" ;;
    *) ln "$f" "$out" ;;
  esac
done
