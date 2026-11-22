#!/bin/sh
# Backup watcher: backs up every new version of the data file and restores it
# when the file is lost, invalid, or changed without changing its version.
#
# Backups live in $BACKUP_DIR:
#   orders-<version>.json    copy of the data of that version
#   orders-<version>.sha256  hash of that copy
#   latest                   last valid version seen

DATA_FILE=${DATA_FILE:-/data/orders.json}
BACKUP_DIR=${BACKUP_DIR:-/backups}
INTERVAL=${INTERVAL:-5}
ONCE=${ONCE:-}   # any value: run one check and exit (used by the tests)

# One JSON line per event.
log() {
    jq -nc --arg event "$1" --arg version "$2" --arg detail "$3" \
        '{ts: (now | todate), event: $event, version: $version, detail: $detail}'
}

sha() {
    if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1
}

# Prints the version of the data file if the file is valid, nothing otherwise.
# The version becomes part of a file name, so only safe characters are accepted.
read_version() {
    jq -er '
        select(
            (.data_version | type == "string" and test("^[A-Za-z0-9._-]+$"))
            and (.orders | type == "array")
            and (.orders | all(
                (.id | type == "string") and (.zone | type == "string")
                and (.status | IN("pending", "preparing", "in_transit", "delivered"))
            ))
        ) | .data_version' "$DATA_FILE" 2>/dev/null
}

# restore <version> <reason>: the copy replaces the file in one step, so readers never see half a file.
restore() {
    start=$(date +%s)
    tmp="$DATA_FILE.restoring"

    if cp "$BACKUP_DIR/orders-$1.json" "$tmp" && mv "$tmp" "$DATA_FILE"; then
        log restore_ok "$1" "$2 (took $(($(date +%s) - start))s)"
    else
        log restore_failed "$1" "$2"
    fi
}

check() {
    version=$(read_version)

    if [ -n "$version" ]; then
        copy="$BACKUP_DIR/orders-$version.json"

        if [ ! -f "$copy" ]; then
            cp "$DATA_FILE" "$copy" && sha "$copy" > "$BACKUP_DIR/orders-$version.sha256"
            log backup "$version" "new version backed up"
        elif [ "$(sha "$DATA_FILE")" != "$(cat "$BACKUP_DIR/orders-$version.sha256")" ]; then
            restore "$version" "content changed without changing the version"
        fi

        echo "$version" > "$BACKUP_DIR/latest"
        return
    fi

    last=$(cat "$BACKUP_DIR/latest" 2>/dev/null)

    if [ -n "$last" ] && [ -f "$BACKUP_DIR/orders-$last.json" ]; then
        restore "$last" "data file missing or invalid"
    else
        log error "" "data file missing or invalid, and there is no backup to restore"
    fi
}

mkdir -p "$BACKUP_DIR"

while true; do
    check
    [ -n "$ONCE" ] && exit 0
    sleep "$INTERVAL"
done
