#!/bin/sh
# Explicit research operator procedure; never called by TUC's runtime.
set -eu
cd "$(dirname "$0")/.."
python examples/bounded_reduction_c11.py > /dev/null
evidence_dir=$(mktemp -d)
container_name="tuc-reduction-proof-$$"
image_name="tuc-reduction-c11-$$"
cleanup() {
    docker rm -f "$container_name" > /dev/null 2>&1 || true
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

for target in runtime mutation-tests sanitizer-tests; do
    docker build --network=none --target "$target" \
        -t "$image_name:$target" docker/reduction-c11
done

run_worker() {
    image_id=$(docker image inspect --format '{{.Id}}' "$image_name:$1")
    shift
    timeout 20s docker run --rm --name "$container_name" --pull=never \
        --network=none --read-only --user=10001:10001 --workdir=/run/tuc \
        --cap-drop=ALL --security-opt=no-new-privileges:true \
        --pids-limit=8 --memory=128m --memory-swap=128m --cpus=1 \
        --ipc=private --shm-size=4m --ulimit=core=0 --ulimit=nofile=32:32 \
        --log-driver=none --env=LANG=C --env=LC_ALL=C \
        --env=ASAN_OPTIONS=detect_leaks=0:abort_on_error=1 \
        --entrypoint="$1" "$image_id" "$2"
}

run_worker runtime /opt/tuc/proof --preflight > "$evidence_dir/preflight.json"
python examples/bounded_reduction_c11.py --preflight \
    --validate-observation "$evidence_dir/preflight.json"
run_worker runtime /opt/tuc/proof --execute > "$evidence_dir/execution.json"
python examples/bounded_reduction_c11.py \
    --validate-observation "$evidence_dir/execution.json"
run_worker sanitizer-tests /out/sanitized --execute > "$evidence_dir/sanitized.json"
python examples/bounded_reduction_c11.py \
    --validate-observation "$evidence_dir/sanitized.json"

for mutation in missing-sum accidental-relu wrong-axis; do
    result=0
    run_worker mutation-tests "/opt/tuc/$mutation" --execute \
        > "$evidence_dir/$mutation.json" || result=$?
    test "$result" = 1
    python - "$evidence_dir/$mutation.json" <<'PY'
import sys
from pathlib import Path
from examples.bounded_compiler_emission import _load_json
from examples.bounded_reduction_c11 import expected_observation, verify_artifacts
expected = expected_observation("execute", verify_artifacts().plan)
expected.update(status="ERROR", reason_code="reference_mismatch", reference_correctness=False)
assert _load_json(Path(sys.argv[1])) == expected, "wrong-code probe did not reach the oracle"
PY
done
printf '%s\n' 'Bounded reduction C11: execution PASS; ASan/UBSan PASS; 3 wrong-code probes rejected.'
