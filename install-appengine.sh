DL_PATH="https://developers.google.com/appengine/downloads"
TMPFILE="$(mktemp)"
 
wget "$DL_PATH" -O "$TMPFILE"
 
do_exit() {
  rm "$TMPFILE"
  trap - INT EXIT
  exit $1
}
trap do_exit INT EXIT
 
DL_URL="$(egrep -m 1 -o 'http[^"]+google_appengine_[.0-9]+\.zip' "$TMPFILE")"
DL_FILE="${DL_URL##*/}"
DL_SHA1="$(egrep -A2 'google_appengine.*\.zip' "$TMPFILE" | egrep -m 1 -o '[a-f0-9]{40}')"
echo "URL: $DL_URL"
echo "SHA1: $DL_SHA1"
echo
 
if [[ ( -z $DL_URL ) || ( -z $DL_FILE ) || ( -z $DL_SHA1 ) ]]; then
  echo "Can't parse out required information to download." >&2
  do_exit 1
fi
 
if wget "$DL_URL"; then
  SHA1="$(sha1sum "$DL_FILE" | egrep -m 1 -o '[a-f0-9]{40}')"
  if [[ "$DL_SHA1" != "$SHA1" ]]; then
    echo "$DL_FILE $SHA1" >&2
    echo "Hashes do not match." >&2
    do_exit 1
  fi
 
  rm -rf google_appengine
  if unzip "$DL_FILE"; then
    rm "$DL_FILE"
  fi
fi