#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
test "$#" = 1
case "$1" in
  --c11) worker=c11; builds="static sanitized"; step=3 ;;
  # Manual only, after fresh approval bound to the emitted source and context.
  # This branch is deliberately absent from the CPU-only GitHub Actions job.
  --matrix) worker=matrix; builds=matrix; step=1 ;;
  *) exit 2 ;;
esac
export PYTHONPATH=.:src
umask 077
evidence_dir=$(python3 examples/bounded_dag_native.py --emit)
container_name="tuc-dag-native-$worker-$$"
image_name="tuc-dag-native-$worker-$$"
cleanup() { docker rm -f "$container_name" >/dev/null 2>&1 || true; }
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
run_worker() {
  image=$1; entry=$2
  shift 2
  if [ "$worker" = matrix ]; then
    set -- --runtime=nvidia --gpus=device=0 --entrypoint="$entry" "$image" "$@"
  else
    set -- --entrypoint="$entry" "$image" "$@"
  fi
  # Default seccomp remains enabled. No bind mounts, Docker socket, privilege,
  # network or added capabilities; GPU 0 is exposed only by the reviewed mode.
  timeout 30s docker run --rm --name "$container_name" --pull=never \
    --network=none --read-only --user=10001:10001 --workdir=/run/tuc \
    --cap-drop=ALL --security-opt=no-new-privileges:true --pids-limit=32 \
    --memory=1g --memory-swap=1g --cpus=1 --ipc=private --shm-size=16m \
    --tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m --ulimit=core=0 --ulimit=nofile=64:64 \
    --ulimit=fsize=1048576:1048576 --log-driver=none \
    --env=ASAN_OPTIONS=detect_leaks=0:abort_on_error=1 "$@"
}
for build in $builds; do
  case "$build" in
    static) target=c11-runtime; prefix=/opt/tuc ;;
    sanitized) target=c11-sanitizer; prefix=/out/sanitized ;;
    matrix) target=cuda-runtime; prefix=/opt/tuc ;;
  esac
  timeout 600s docker build --network=none --target "$target" \
    -t "$image_name-$build" -f "$evidence_dir/Dockerfile" "$evidence_dir"
  image_id=$(docker image inspect "$image_name-$build" --format '{{.Id}}')
  printf '%s\n' "$image_id" > "$evidence_dir/$build-image-id.txt"
  index=0
  while [ "$index" -lt 36 ]; do
    run_worker "$image_id" "$prefix/proof" "$index" --preflight \
      > "$evidence_dir/$build-$index-preflight.json"
    run_worker "$image_id" "$prefix/proof" "$index" --execute \
      > "$evidence_dir/$build-$index-execute.json"
    faults="1 2 3"
    if [ "$worker" = matrix ] && [ "$((index % 3))" != 0 ]; then faults="1 2 3 4"; fi
    for fault in $faults; do
      status=0
      run_worker "$image_id" "$prefix/fault$fault" "$index" --execute \
        > "$evidence_dir/$build-$index-fault$fault.json" || status=$?
      # A timeout, crash or Docker failure is never a successful negative control.
      test "$status" = 1
    done
    index=$((index + step))
  done
  status=0
  run_worker "$image_id" "$prefix/proof" 99 --execute \
    > "$evidence_dir/$build-invalid-plan.json" || status=$?
  test "$status" = 2
  status=0
  run_worker "$image_id" "$prefix/proof" 0 --unknown \
    > "$evidence_dir/$build-invalid-mode.json" || status=$?
  test "$status" = 2
  if [ "$build" = sanitized ]; then
    run_worker "$image_id" /out/sanitized/contract-test > "$evidence_dir/sanitized-contract.json"
  fi
done
python3 examples/bounded_dag_native.py --accept "$evidence_dir" --worker "$worker" \
  > "$evidence_dir/record.json"
printf '%s\n' "$evidence_dir"
