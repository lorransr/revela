#!/bin/sh
# revela-sync "Album name" downloads an iCloud album and the list of favorites.
# revela-sync --auth-only logs in, with the 2FA code.
set -eu
: "${ICLOUD_USER:?set ICLOUD_USER in .env}"
mkdir -p -m 700 /data/session
fetch() {
  icloudpd --username "$ICLOUD_USER" --cookie-directory /data/session --size adjusted \
    --skip-videos --skip-live-photos "$@"
}
case "${1:-}" in -*|"") fetch "$@"; exit ;; esac

album=$1
shift
dir=/data/albums/$(PYTHONPATH=/app python3 -c 'import sys, revela; print(revela.slug(sys.argv[1]))' "$album")
mkdir -p "$dir/photos"
fetch --directory "$dir/icloud" --album "$album" --folder-structure "{:%Y-%m-%d}" "$@"

# An empty directory, because --only-print-filenames skips the files that it finds there.
fetch --directory /tmp/favorites --album Favorites --only-print-filenames "$@" \
  | sed 's|.*/||; s|\.[^.]*$||' > "$dir/favorites.txt"

# revela skips HEIC. photos/ mirrors icloud/ with HEIC as JPEG and the rest as hardlinks,
# so the next download stays incremental.
cd "$dir/icloud"
find . -type f ! -name '.*' | while read -r f; do
  case "$f" in
    *.[hH][eE][iI][cC]) out="$dir/photos/${f%.*}.jpg" ;;
    *) out="$dir/photos/$f" ;;
  esac
  [ -e "$out" ] && continue
  mkdir -p "$(dirname "$out")"
  case "$f" in
    *.[hH][eE][iI][cC]) heif-convert --quiet -q 95 "$f" "$out" && touch -r "$f" "$out" ;;
    *) ln "$f" "$out" ;;
  esac
done
echo "$(find "$dir/photos" -type f | wc -l) photos and $(wc -l < "$dir/favorites.txt") favorites in $dir"
