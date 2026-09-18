# Installed Source Intent C11 conformance

This client carries RFC 0321's application from an installed TUC wheel through
the public compiler API into actual C11 conformance execution. It adds a fixed
CPU test route; normal compilation continues to return inert artifacts.

The application projects four inputs through three Matmuls, two ReLUs and two
row Sums. Both public outputs are checked against an independent binary32
oracle. Three fixed input corpora run twice with fresh poisoned storage.

The [standalone client](../integration/bounded_source_c11/consumer.py) emits a
bounded context without compiling or executing it. Its explicit
[operator](../integration/bounded_source_c11/operator.sh) builds a static binary
and an ASan/UBSan binary in the existing pinned toolchain container, then runs
them without network, devices, host mounts or writable root filesystems.

Each successful build must observe six runs, 42 primitive calls, 36 terminal
scalar checks and twelve publications. Thirteen compiled fault variants test
each missing operation, corrupted and missing public outputs, swapped returns
and incomplete scalar coverage. Unexpected command-line input also rejects.
Crashes and sanitizer failures do not count as successful rejection tests.

The [CI workflow](../.github/workflows/bounded-source-c11.yml) builds and installs
the wheel, copies the client outside the checkout, verifies the isolated import
path, and performs generation and acceptance through that installation. Context
verification binds wheel/source/artifact digests, build scripts and image IDs
to all thirty required receipts. The aggregate is retained as a CI artifact.
Each native receipt carries a compiled binding digest so stale receipts cannot
be paired with a newly generated context.
It is a locally checked observation record, not an authenticated attestation.

See the [client instructions](../integration/bounded_source_c11/README.md) and
[RFC 0322](../rfcs/0322-installed-source-c11-conformance.md) for setup and the
trust boundary. Native acceptance is established by the dedicated workflow's
verified receipt for the reviewed source revision.

The earlier DAG CPU/GPU matrix remains evidence for its original graphs only.
This application has no CUDA observation or general native runtime admission.
Arbitrary inputs, dynamic shapes, performance and third-party reproduction
remain outside this conformance slice.
