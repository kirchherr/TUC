#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
test "$#" = 1 && test "$1" = --c11
export PYTHONPATH=.:src
umask 077
# --emit creates an exclusive private directory under repository tmp and does not
# execute native code. The default Python command is an entirely pure report.
evidence_dir=$(python3 examples/bounded_dag_c11.py --emit)
container_name="tuc-dag-c11-$$"
image_name="tuc-dag-c11-$$"
cleanup() { docker rm -f "$container_name" >/dev/null 2>&1 || true; }
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
run_worker() {
  image=$1; entry=$2
  # Docker's default seccomp profile remains enabled. No host bind mounts,
  # sockets, devices, network, extra capabilities or privileged container mode.
  timeout 30s docker run --rm --name "$container_name" --pull=never \
    --network=none --read-only --user=10001:10001 --workdir=/run/tuc \
    --cap-drop=ALL --security-opt=no-new-privileges:true --pids-limit=32 \
    --memory=1g --memory-swap=1g --cpus=1 --ipc=private --shm-size=16m \
    --tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m --ulimit=core=0 --ulimit=nofile=64:64 \
    --ulimit=fsize=1048576:1048576 --log-driver=none \
    --env=ASAN_OPTIONS=detect_leaks=0:abort_on_error=1 \
    --entrypoint="$entry" "$image"
}
for build in static sanitized; do
  timeout 600s docker build --network=none --target "$build" \
    -t "$image_name-$build" -f "$evidence_dir/Dockerfile" "$evidence_dir"
  image_id=$(docker image inspect "$image_name-$build" --format '{{.Id}}')
  printf '%s\n' "$image_id" > "$evidence_dir/$build-image-id.txt"
  if [ "$build" = static ]; then prefix=/opt/tuc; else prefix=/out/sanitized; fi
  run_worker "$image_id" "$prefix/proof" > "$evidence_dir/$build-proof.json"
  for mutation in skip-operation corrupt-output missing-publication; do
    status=0
    run_worker "$image_id" "$prefix/$mutation" > "$evidence_dir/$build-$mutation.json" || status=$?
    # Timeouts, crashes, sanitizer aborts and Docker failures are not controls.
    test "$status" = 1
  done
done
python3 examples/bounded_dag_c11.py --accept "$evidence_dir" > "$evidence_dir/record.json"
printf '%s\n' "$evidence_dir"
