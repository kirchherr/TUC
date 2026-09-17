#!/bin/sh
# Explicit fixed-source experiment; never invoked by the ordinary runtime.
set -eu
cd "$(dirname "$0")/../.."
test "$#" = 1
case "$1" in
    --c11) worker=c11; build_target=c11; profiles=cccc ;;
    --matrix-reviewed) worker=matrix; build_target=cuda; profiles="cccc gccc gggg" ;;
    *) exit 2 ;;
esac
export PYTHONPATH=.:src
python3 examples/bounded_native_fanout.py > /dev/null
umask 077
mkdir -p tmp
evidence_dir=$(mktemp -d "tmp/native-fanout-$worker.XXXXXXXX")
container_name="tuc-fanout-$worker-$$"
image_name="tuc-fanout-$worker-$$"
cleanup() { docker rm -f "$container_name" > /dev/null 2>&1 || true; }
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
timeout 600s docker build --network=none --target "$build_target-runtime" \
    -t "$image_name:runtime" -f docker/native-fanout/Dockerfile .
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
    if [ "$profile" != cccc ]; then extra=skip-transfer; fi
    for mutation in bypass-relu late-relu missing-sum wrong-stride incomplete-coverage over-budget nonfinite schedule-count schedule-slot schedule-space schedule-order schedule-size schedule-duplicate schedule-placement schedule-fanout schedule-output skip-publish skip-second-publish invalidate-shared clobber-shared $extra; do
        result=0
        run_worker "$image_id" "/opt/tuc/$mutation" "$profile" --execute \
            > "$evidence_dir/$profile-$mutation.json" || result=$?
        test "$result" = 1
    done
done
result=0
run_worker "$image_id" /opt/tuc/proof cccc-extra --execute > "$evidence_dir/unknown-profile.json" || result=$?
test "$result" = 1
if [ "$worker" = c11 ]; then
    timeout 600s docker build --network=none --target c11-sanitizer \
        -t "$image_name:sanitizer" -f docker/native-fanout/Dockerfile .
    sanitizer_id=$(docker image inspect --format '{{.Id}}' "$image_name:sanitizer")
    run_worker "$sanitizer_id" /out/sanitized cccc --execute > "$evidence_dir/sanitized.json"
    run_worker "$sanitizer_id" /out/contract-sanitized cccc --execute > "$evidence_dir/contract-sanitized.json"
fi
python3 examples/bounded_native_fanout.py --worker "$worker" --image-id "$image_id" \
    --accept "$evidence_dir" > "$evidence_dir/record.json"
printf 'Native fanout %s: PASS, all requested profiles and controls.\n' "$worker"
printf 'Evidence directory: %s\n' "$evidence_dir"
