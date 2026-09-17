#!/bin/sh
# Explicit operator procedure, never called from the normal TUC executor.
set -eu
cd "$(dirname "$0")/../.."
if [ "$#" != 1 ]; then exit 2; fi
case "$1" in
    --c11) target=c11 ;;
    --cuda-reviewed) target=mixed ;;
    *) printf '%s\n' 'Requires --c11 or --cuda-reviewed after host security review.' >&2; exit 2 ;;
esac
build_target=c11
if [ "$target" = mixed ]; then build_target=cuda; fi
extra=""
if [ "$target" = mixed ]; then extra=skip-transfer; fi
export PYTHONPATH=.:src
python3 examples/bounded_mixed_native.py > /dev/null
umask 077
mkdir -p tmp
evidence_dir=$(mktemp -d "tmp/mixed-native-$target.XXXXXXXX")
container_name="tuc-mixed-$target-$$"
image_name="tuc-mixed-$target-$$"
cleanup() { docker rm -f "$container_name" > /dev/null 2>&1 || true; }
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
timeout 600s docker build --network=none --target "$build_target-runtime" \
    -t "$image_name:runtime" -f docker/mixed-native/Dockerfile .
image_id=$(docker image inspect --format '{{.Id}}' "$image_name:runtime")
run_worker() {
    worker_image=$1
    entry=$2
    mode=$3
    set --
    if [ "$target" = mixed ]; then set -- --runtime=nvidia --gpus=device=0; fi
    timeout 30s docker run --rm --name "$container_name" --pull=never "$@" \
        --network=none --read-only --user=10001:10001 --workdir=/run/tuc \
        --cap-drop=ALL --security-opt=no-new-privileges:true --pids-limit=32 \
        --memory=1g --memory-swap=1g --cpus=1 --ipc=private --shm-size=16m \
        --tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m --ulimit=core=0 --ulimit=nofile=64:64 \
        --log-driver=none --env=ASAN_OPTIONS=detect_leaks=0:abort_on_error=1 \
        --entrypoint="$entry" "$worker_image" "$mode"
}
run_worker "$image_id" /opt/tuc/proof --preflight > "$evidence_dir/preflight.json"
python3 examples/bounded_mixed_native.py --target "$target" --preflight \
    --validate "$evidence_dir/preflight.json"
run_worker "$image_id" /opt/tuc/proof --execute > "$evidence_dir/execution.json"
python3 examples/bounded_mixed_native.py --target "$target" \
    --validate "$evidence_dir/execution.json" --image-id "$image_id" > "$evidence_dir/record.json"
for mutation in bypass-relu late-relu missing-sum wrong-stride incomplete-coverage over-budget nonfinite schedule-count schedule-slot schedule-space schedule-order schedule-size schedule-duplicate skip-publish $extra; do
    result=0
    run_worker "$image_id" "/opt/tuc/$mutation" --execute \
        > "$evidence_dir/$mutation.json" || result=$?
    test "$result" = 1
    python3 examples/bounded_mixed_native.py --target "$target" \
        --negative "$mutation" --validate "$evidence_dir/$mutation.json"
done
if [ "$target" = c11 ]; then
    timeout 600s docker build --network=none --target c11-sanitizer \
        -t "$image_name:sanitizer" -f docker/mixed-native/Dockerfile .
    sanitizer_id=$(docker image inspect --format '{{.Id}}' "$image_name:sanitizer")
    run_worker "$sanitizer_id" /out/sanitized --execute > "$evidence_dir/sanitized.json"
    python3 examples/bounded_mixed_native.py --target c11 --validate "$evidence_dir/sanitized.json"
fi
printf 'Shared residency %s: PASS, 10 vectors + replay, all negative probes rejected.\n' "$target"
printf 'Evidence directory: %s\n' "$evidence_dir"
