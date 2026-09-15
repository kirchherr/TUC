#!/bin/sh
# Explicit operator-only execution. No normal TUC runtime entry point.
set -eu
cd "$(dirname "$0")/.."
if [ "$#" != 1 ] || [ "$1" != --execute-reviewed-gpu ]; then
    printf '%s\n' 'Requires --execute-reviewed-gpu after driver, toolkit and shared-device review.' >&2
    exit 2
fi
export PYTHONPATH=.:src
python3 examples/bounded_reduction_cuda.py > /dev/null
umask 077
mkdir -p tmp
evidence_dir=$(mktemp -d tmp/reduction-cuda.XXXXXXXX)
container_name="tuc-reduction-cuda-$$"
image_name="tuc-reduction-cuda-$$"
cleanup() { docker rm -f "$container_name" > /dev/null 2>&1 || true; }
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

for target in runtime mutation-tests; do
    timeout 600s docker build --network=none --target "$target" \
        -t "$image_name:$target" docker/reduction-cuda
done
runtime_id=$(docker image inspect --format '{{.Id}}' "$image_name:runtime")
mutation_id=$(docker image inspect --format '{{.Id}}' "$image_name:mutation-tests")
run_worker() {
    timeout 30s docker run --rm --name "$container_name" --pull=never \
        --runtime=nvidia --gpus=device=0 --network=none --read-only \
        --user=10001:10001 --workdir=/run/tuc --cap-drop=ALL \
        --security-opt=no-new-privileges:true --pids-limit=32 \
        --memory=1g --memory-swap=1g --cpus=1 --ipc=private --shm-size=16m \
        --tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m --ulimit=core=0 --ulimit=nofile=64:64 \
        --log-driver=none --entrypoint="$2" "$1" "$3"
}
run_worker "$runtime_id" /opt/tuc/proof --preflight > "$evidence_dir/preflight.json"
python3 examples/bounded_reduction_cuda.py --preflight \
    --validate-observation "$evidence_dir/preflight.json"
run_worker "$runtime_id" /opt/tuc/proof --execute > "$evidence_dir/execution.json"
python3 examples/bounded_reduction_cuda.py --validate-observation "$evidence_dir/execution.json" \
    --record-image-id "$runtime_id" > "$evidence_dir/record.json"
for mutation in missing-sum accidental-relu wrong-axis; do
    result=0
    run_worker "$mutation_id" "/opt/tuc/$mutation" --execute \
        > "$evidence_dir/$mutation.json" || result=$?
    test "$result" = 1
    python3 - "$evidence_dir/$mutation.json" <<'PY'
import sys
from pathlib import Path
from examples.bounded_compiler_emission import _canonical_json
from examples.bounded_reduction_c11 import load_observation
from examples.bounded_reduction_cuda import expected_observation
expected = expected_observation("execute")
expected.update(status="ERROR", reason_code="reference_mismatch", reference_correctness=False)
if _canonical_json(load_observation(Path(sys.argv[1]))) != _canonical_json(expected):
    raise SystemExit("wrong-code probe did not reach the reference check")
PY
done
python3 examples/bounded_reduction_cuda.py --compare-record "$evidence_dir/record.json" \
    > "$evidence_dir/equivalence.json"
printf '%s\n' 'CUDA reduction: execution PASS; three wrong-code probes rejected.'
printf 'Evidence directory: %s\n' "$evidence_dir"
