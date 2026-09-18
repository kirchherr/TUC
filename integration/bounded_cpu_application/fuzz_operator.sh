#!/bin/sh
set -eu
test "$#" = 1 && test "$1" = --fuzz
cd "$(dirname "$0")"
unset PYTHONPATH
umask 077
python3 -I consumer.py --emit-fuzz > contexts.txt
name="tuc-application-fuzz-$$"
cleanup() { docker rm -f "$name" >/dev/null 2>&1 || true; }
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
run() {
  entry=$1
  timeout 30s docker run --rm -i --name "$name" --pull=never --network=none \
    --read-only --user=10001:10001 --workdir=/run/tuc --cap-drop=ALL \
    --security-opt=no-new-privileges:true --pids-limit=32 --memory=1g --memory-swap=1g \
    --cpus=1 --ipc=private --shm-size=16m --tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m \
    --ulimit=core=0 --ulimit=nofile=64:64 --ulimit=fsize=1048576:1048576 \
    --env=ASAN_OPTIONS=detect_leaks=0:abort_on_error=1 --log-driver=none \
    --entrypoint="$entry" "$image"
}
while IFS= read -r context; do
  timeout 600s docker build --network=none -t "$name" -f "$context/fuzz.Dockerfile" "$context"
  image=$(docker image inspect "$name" --format '{{.Id}}')
  run /opt/fuzz < /dev/null > "$context/fuzz-result.json"
  run /opt/application < "$context/request.bin" > "$context/response.bin"
  cmp "$context/expected.bin" "$context/response.bin"
  for input in truncated extra wrong-program; do
    status=0
    run /opt/application < "$context/$input.bin" > "$context/$input-response.bin" || status=$?
    test "$status" = 2
    test ! -s "$context/$input-response.bin"
  done
done < contexts.txt
