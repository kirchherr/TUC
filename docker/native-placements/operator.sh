#!/bin/sh
# Explicit operator experiment, not called by the normal TUC runtime.
set -eu
cd "$(dirname "$0")/../.."
test "$#" = 1
case "$1" in
    --c11) worker=c11; build_target=c11; profiles=ccc ;;
    --matrix-reviewed) worker=matrix; build_target=cuda; profiles="ccc ccg cgc cgg gcc gcg ggc ggg" ;;
    *) exit 2 ;;
esac
export PYTHONPATH=.:src
python3 examples/bounded_native_placements.py > /dev/null
umask 077
mkdir -p tmp
evidence_dir=$(mktemp -d "tmp/native-placements-$worker.XXXXXXXX")
container_name="tuc-placements-$worker-$$"
image_name="tuc-placements-$worker-$$"
cleanup() { docker rm -f "$container_name" > /dev/null 2>&1 || true; }
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
timeout 600s docker build --network=none --target "$build_target-runtime" \
    -t "$image_name:runtime" -f docker/native-placements/Dockerfile .
image_id=$(docker image inspect --format '{{.Id}}' "$image_name:runtime")
run_worker() {
    image=$1; entry=$2; profile=$3; mode=$4
    set --
    if [ "$worker" = matrix ]; then set -- --runtime=nvidia --gpus=device=0; fi
    timeout 30s docker run --rm --name "$container_name" --pull=never "$@" \
        --network=none --read-only --user=10001:10001 --workdir=/run/tuc \
        --cap-drop=ALL --security-opt=no-new-privileges:true --pids-limit=32 \
        --memory=1g --memory-swap=1g --cpus=1 --ipc=private --shm-size=16m \
        --tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m --ulimit=core=0 --ulimit=nofile=64:64 \
        --log-driver=none --env=ASAN_OPTIONS=detect_leaks=0:abort_on_error=1 \
        --entrypoint="$entry" "$image" "$profile" "$mode"
}
for profile in $profiles; do
    run_worker "$image_id" /opt/tuc/proof "$profile" --preflight > "$evidence_dir/$profile-preflight.json"
    run_worker "$image_id" /opt/tuc/proof "$profile" --execute > "$evidence_dir/$profile-execution.json"
    extra=""
    if [ "$profile" != ccc ]; then extra=skip-transfer; fi
    for mutation in bypass-relu late-relu missing-sum wrong-stride incomplete-coverage over-budget nonfinite schedule-count schedule-slot schedule-space schedule-order schedule-size schedule-duplicate schedule-placement skip-publish $extra; do
        result=0
        run_worker "$image_id" "/opt/tuc/$mutation" "$profile" --execute \
            > "$evidence_dir/$profile-$mutation.json" || result=$?
        test "$result" = 1
    done
done
result=0
run_worker "$image_id" /opt/tuc/proof ccc-extra --execute > "$evidence_dir/unknown-profile.json" || result=$?
test "$result" = 1
if [ "$worker" = c11 ]; then
    timeout 600s docker build --network=none --target c11-sanitizer \
        -t "$image_name:sanitizer" -f docker/native-placements/Dockerfile .
    sanitizer_id=$(docker image inspect --format '{{.Id}}' "$image_name:sanitizer")
    run_worker "$sanitizer_id" /out/sanitized ccc --execute > "$evidence_dir/sanitized.json"
    run_worker "$sanitizer_id" /out/contract-sanitized ccc --execute > "$evidence_dir/contract-sanitized.json"
fi
python3 examples/bounded_native_placements.py --worker "$worker" --image-id "$image_id" \
    --accept "$evidence_dir" > "$evidence_dir/record.json"
printf 'Native placement matrix %s: PASS, all requested profiles and controls.\n' "$worker"
printf 'Evidence directory: %s\n' "$evidence_dir"
