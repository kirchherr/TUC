#!/bin/sh
# Operator procedure only. No backend admission or device discovery in TUC.
set -eu
cd "$(dirname "$0")/.."
if [ "$#" != 1 ]; then exit 2; fi
case "$1" in
    --c11) target=c11 ;;
    --cuda-reviewed) target=cuda ;;
    *) printf '%s\n' 'Requires --c11 or --cuda-reviewed after host security review.' >&2; exit 2 ;;
esac
export PYTHONPATH=.:src
python3 examples/reduction_input_portfolio.py > /dev/null
umask 077
mkdir -p tmp
evidence_dir=$(mktemp -d "tmp/portfolio-$target.XXXXXXXX")
container_name="tuc-portfolio-$target-$$"
image_name="tuc-portfolio-$target-$$"
cleanup() { docker rm -f "$container_name" > /dev/null 2>&1 || true; }
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
timeout 600s docker build --network=none --target "$target-runtime" \
    -t "$image_name:runtime" docker/reduction-portfolio
image_id=$(docker image inspect --format '{{.Id}}' "$image_name:runtime")
run_worker() {
    worker_image=$1
    entry=$2
    mode=$3
    set --
    if [ "$target" = cuda ]; then set -- --runtime=nvidia --gpus=device=0; fi
    timeout 30s docker run --rm --name "$container_name" --pull=never "$@" \
        --network=none --read-only --user=10001:10001 --workdir=/run/tuc \
        --cap-drop=ALL --security-opt=no-new-privileges:true --pids-limit=32 \
        --memory=1g --memory-swap=1g --cpus=1 --ipc=private --shm-size=16m \
        --tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m --ulimit=core=0 --ulimit=nofile=64:64 \
        --log-driver=none --env=ASAN_OPTIONS=detect_leaks=0:abort_on_error=1 \
        --entrypoint="$entry" "$worker_image" "$mode"
}
run_worker "$image_id" /opt/tuc/proof --preflight > "$evidence_dir/preflight.json"
python3 examples/reduction_input_portfolio.py --target "$target" --preflight \
    --validate "$evidence_dir/preflight.json"
run_worker "$image_id" /opt/tuc/proof --execute > "$evidence_dir/execution.json"
python3 examples/reduction_input_portfolio.py --target "$target" \
    --validate "$evidence_dir/execution.json" --image-id "$image_id" > "$evidence_dir/record.json"
for mutation in missing-sum accidental-relu wrong-axis frozen-output; do
    result=0
    run_worker "$image_id" "/opt/tuc/$mutation" --execute \
        > "$evidence_dir/$mutation.json" || result=$?
    test "$result" = 1
    python3 examples/reduction_input_portfolio.py --target "$target" \
        --negative "$mutation" --validate "$evidence_dir/$mutation.json"
done
if [ "$target" = c11 ]; then
    timeout 600s docker build --network=none --target c11-sanitizer \
        -t "$image_name:sanitizer" docker/reduction-portfolio
    sanitizer_id=$(docker image inspect --format '{{.Id}}' "$image_name:sanitizer")
    run_worker "$sanitizer_id" /out/sanitized --execute > "$evidence_dir/sanitized.json"
    python3 examples/reduction_input_portfolio.py --target c11 --validate "$evidence_dir/sanitized.json"
fi
printf 'Portfolio %s: PASS, 20 vectors + baseline replay, four wrong-code probes rejected.\n' "$target"
printf 'Evidence directory: %s\n' "$evidence_dir"
