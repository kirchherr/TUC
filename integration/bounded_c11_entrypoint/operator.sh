#!/bin/sh
set -eu
test "$#" = 1 && test "$1" = --c11
cd "$(dirname "$0")"
unset PYTHONPATH
umask 077
evidence_dir=$(python3 -I consumer.py --emit)
container_name="tuc-c11-entrypoint-$$"
image_name="tuc-c11-entrypoint-$$"
cleanup() { docker rm -f "$container_name" >/dev/null 2>&1 || true; }
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
run_worker() {
  image=$1; entry=$2
  shift 2
  timeout 30s docker run --rm --name "$container_name" --pull=never \
    --network=none --read-only --user=10001:10001 --workdir=/run/tuc \
    --cap-drop=ALL --security-opt=no-new-privileges:true --pids-limit=32 \
    --memory=1g --memory-swap=1g --cpus=1 --ipc=private --shm-size=16m \
    --tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m --ulimit=core=0 --ulimit=nofile=64:64 \
    --ulimit=fsize=1048576:1048576 --log-driver=none \
    --env=ASAN_OPTIONS=detect_leaks=0:abort_on_error=1 \
    --entrypoint="$entry" "$image" "$@"
}
for build in static sanitized; do
  timeout 600s docker build --network=none --target "$build" \
    -t "$image_name-$build" -f "$evidence_dir/Dockerfile" "$evidence_dir"
  image_id=$(docker image inspect "$image_name-$build" --format '{{.Id}}')
  printf '%s\n' "$image_id" > "$evidence_dir/$build-image-id.txt"
  if [ "$build" = static ]; then prefix=/opt/tuc; else prefix=/out/sanitized; fi
  run_worker "$image_id" "$prefix/proof" > "$evidence_dir/$build-proof.json"
  for fault in 1 2 3; do
    status=0
    run_worker "$image_id" "$prefix/fault$fault" > "$evidence_dir/$build-fault$fault.json" || status=$?
    test "$status" = 1
  done
  status=0
  run_worker "$image_id" "$prefix/proof" --unknown > "$evidence_dir/$build-invalid.json" || status=$?
  test "$status" = 2
done
python3 -I consumer.py --accept "$evidence_dir" > "$evidence_dir/record.json"
printf '%s\n' "$evidence_dir"
