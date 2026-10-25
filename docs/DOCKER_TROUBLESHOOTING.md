# Docker build recovery

## Package installation killed: cannot allocate memory

The observed build reached Debian's package repository and downloaded package indexes, then ended with `Killed` / `ResourceExhausted` / `cannot allocate memory`. This identifies resource exhaustion for that attempt; changing an API key does not address it.

The runtime image installs only Tesseract as an OS-level OCR dependency. PDF rendering and image handling use the locked PDFium and Pillow packages. Explicit OpenGL/GLib installation was removed because this runtime does not use OpenCV or a graphics UI. Tesseract still brings the libraries it needs transitively, while Mesa/LLVM and the OpenGL stack are avoided.

The base pins `python:3.13-slim-bookworm` to keep the Debian package-manager/libc release explicit. The previous floating slim tag resolved to Trixie; a local rebuild also exhausted memory there even with the smaller package list. This does not establish an upstream Trixie bug.

API, worker and bootstrap share `centralign-ai-runtime:local`. Build it once:

```sh
docker compose --progress plain build api
```

Then continue with `make bootstrap`. Its build step reuses the cache and the resulting image serves all three application roles. Do not run multiple independent build commands at the same time.

If memory exhaustion recurs:

1. Close unused applications and stop containers from unrelated projects.
2. Check `docker info` for the VM memory allocation and Docker Desktop's Resources settings. Do not allocate all host RAM to Docker; the Mac also needs memory.
3. Check host memory pressure in Activity Monitor and available disk space for Docker's swap/image storage.
4. Retry the single-image build. Keep its full log when reporting a failure.

Do not factory-reset Docker, delete its data directory, prune volumes, or use `docker compose down -v` as a build troubleshooting step. Those can remove unrelated work or ERP data.

## Capture a complete log

```sh
docker compose --progress plain build api 2>&1 | tee /tmp/centralign-build.log
```

In a pipeline, the final shell status can come from `tee`; read the build result in the log. On zsh/bash, `set -o pipefail` before the command makes a build failure propagate.

## Different errors require different fixes

- Docker Hub token timeout: check network/proxy connectivity.
- `apt-get` unable to fetch archives: inspect the exact mirror/network error.
- `cannot allocate memory`: investigate resource pressure.
- Python dependency conflict: inspect resolver output and the locked SDK bounds.

A successful image build is not proof that the full ERPNext/identity/model workflow works. Complete the bootstrap and demo checks afterward.

## Verified result for this change

The shared Bookworm runtime image built successfully on the local arm64 Docker engine. Its OS-package plan was 61 new packages, 29.9 MB downloaded and 96.5 MB installed, compared with the original Trixie/graphics plan of 97 packages, 72.5 MB downloaded and 302 MB installed.

An isolated container with networking disabled passed synthetic image OCR, PDF rendering followed by OCR, demo JSON fixture presence and `pip check`. This validates runtime dependencies; it does not establish model extraction accuracy or live ERP integration. The container runs as the unprivileged `app` user.

## Keycloak readiness fails: database role missing

If PostgreSQL reports `Role "keycloak" does not exist`, inspect its first-start log. A macOS bind-mounted shell initialization hook was observed failing with `bad interpreter: Permission denied`; PostgreSQL then preserved its initialized volume and skipped those hooks on restart.

The identity database initializer is now a SQL file. It reads the password from the container environment, creates the missing role/database if necessary, and aligns the role password with configuration. Bootstrap waits for PostgreSQL health and explicitly runs this idempotent initializer before starting Keycloak. Rerunning preserves existing databases and ERP volumes; no volume deletion is needed.

Recovery for an existing checkout:

```sh
make bootstrap
```

A local repair was verified by running initialization twice, checking both host and container OIDC discovery, and successfully configuring the Keycloak realm/client/users. Bootstrap then stopped at the expected ERP company setup wizard. This does not claim completion of the company setup or full agent workflow.
