# OpenFOAM Container + AWS Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the PyFluent section sweep with a licence-free OpenFOAM Docker image that runs the same sweep locally and as an AWS Batch array job, with Terraform for the infrastructure.

**Architecture:** A Python package (`cfd_openfoam/sweep/`) holds all logic behind small interfaces (matrix, storage, case templating, solver backend), so everything except the OpenFOAM calls is unit-testable without Docker. The container entrypoint selects one work item (one section, wind speed, turbulence tag, all angles), syncs inputs and results through a storage abstraction (S3 or local folder), and resumes after interruption. Terraform provisions ECR, S3, IAM and Batch.

**Tech Stack:** Python 3.11+, pytest, boto3, gmsh, OpenFOAM v2406 (ESI), Docker + docker compose, MinIO (local S3), Terraform >= 1.6 with the AWS provider.

**Spec:** `docs/superpowers/specs/2026-10-28-openfoam-container-design.md`

## Global Constraints
- Output file is `results.csv` with columns exactly: `tag, camber_pct, wind, Re, alpha_deg, V_mps, Fx_N, Fy_N, Mz_Nm, CL, CD, Cm_pivot, iterations, converged, seconds`.
- Physics: rho 1.225 kg/m^3, mu 1.7894e-5 Pa s, chord 0.65 m, pivot (0.325, 0, 0), viscosity ratio 5, turbulence intensity 0.1 % or 0.5 %, outlet 0 gauge, second-order upwind; angle set by rotating the inflow vector `(V*flow_x, V*flow_y)`, never the geometry.
- L = -Fx sin a + Fy cos a; D = Fx cos a + Fy sin a; q = 0.5 rho V^2; CL = L/(q c); CD = D/(q c); Cm_pivot = Mz/(q c^2), nose-up positive.
- Convergence: CL and Cm each change by less than `tol` (default 0.002) over a chunk (default 200 iterations); `max_chunks` default 10.
- Image: OpenFOAM v2406 (ESI), gmsh >= 4.11, non-root user, no credentials baked in.
- Batch work item selection via `AWS_BATCH_JOB_ARRAY_INDEX`; default job 4 vCPU / 8 GiB, 3 attempts; Fargate max 16 vCPU / 120 GB.
- Terraform: results bucket has `prevent_destroy = true`, versioning, encryption, public access blocked. `terraform fmt -check` and `terraform validate` must pass. Never `apply` in this work.
- New code lives in `cfd_openfoam/`. The Fluent scripts in `data/cfd_sections/` are not modified; the image build copies `make_mesh.py` and `check_msh.py` from there.
- The Fluent mesh `.msh` zone names are `interior`, `wall`, `inlet`, `outlet`.

## Review Focus
1. Array index beyond the number of work items (oversized array or retry): log and exit 0 without touching S3. Pinned in Task 1.
2. Filters match no rows (typo in camber or wind): clear error, non-zero exit, nothing uploaded. Pinned in Task 6.
3. `results.csv` cut off mid-line by a killed upload or container: resume ignores the partial last line instead of crashing. Pinned in Task 2.
4. Solver diverges (NaN or inf forces): that angle is recorded with `converged=False`, the next angle is re-initialised rather than warm-started, and the job continues. Pinned in Task 4.
5. Wind labels contain a space (`"8 kn"`): item ids, S3 keys and CLI/env values round-trip correctly. Pinned in Task 1.

---

## File Structure
```
cfd_openfoam/
  pyproject.toml                 # package metadata, pytest config (pythonpath = .)
  sweep/__init__.py
  sweep/matrix.py                # WorkItem, matrix loading, selection
  sweep/coeffs.py                # constants, force rotation, coefficients, forces.dat parsing, convergence
  sweep/results.py               # RESULT_COLUMNS, tolerant read, append
  sweep/storage.py               # Store protocol, LocalStore, S3Store
  sweep/case.py                  # inlet/turbulence state, template rendering
  sweep/backend.py               # SolverBackend protocol + OpenFoamBackend (subprocess)
  sweep/runner.py                # run_item orchestration + resume
  entrypoint.py                  # CLI
  templates/                     # OpenFOAM case skeleton (0/, constant/, system/)
  tests/                         # unit tests + fake backend
  tests/smoke/                   # in-container smoke test
  Dockerfile
  docker-compose.test.yml        # job image + MinIO
  scripts/run_local.sh|.ps1, test_batch_local.sh|.ps1, build_and_push.sh, submit.sh
  terraform/ (main.tf, variables.tf, outputs.tf, versions.tf, iam.tf, batch.tf, s3.tf, ecr.tf)
  README.md
```

---

### Task 1: Matrix and work-item selection

**Files:**
- Create: `cfd_openfoam/pyproject.toml`, `cfd_openfoam/sweep/__init__.py`, `cfd_openfoam/sweep/matrix.py`
- Test: `cfd_openfoam/tests/test_matrix.py`, fixture `cfd_openfoam/tests/fixtures/run_matrix_small.csv` (copy of the first 12 data rows of `data/cfd_sections/run_matrix.csv`, covering two sections, two winds)

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class WorkItem: section: str; camber_pct: float; wind: str; tag: str` with property `item_id -> str` (`"section_f08.0pct__8kn__tu0.1"`: spaces removed from `wind`).
  - `load_rows(path: Path) -> list[dict[str, str]]`
  - `list_items(rows: list[dict], tags: list[str]) -> list[WorkItem]` sorted by (camber_pct, wind speed ascending by `V_mps`, tag).
  - `rows_for(item: WorkItem, rows: list[dict]) -> list[dict]` sorted by `float(alpha_deg)`.
  - `item_for_index(items: list[WorkItem], index: int) -> WorkItem | None` (None when out of range).

- [ ] **Step 1: Write failing tests** in `test_matrix.py`: `test_list_items_counts` (fixture gives sections x winds x 2 tags items, order by camber then speed), `test_rows_sorted_by_alpha`, `test_item_id_removes_spaces` (`"8 kn"` -> `"...__8kn__..."`), `test_item_for_index_in_range`, `test_item_for_index_out_of_range_returns_none`, `test_item_ids_unique`.
- [ ] **Step 2: Run** `pytest cfd_openfoam/tests/test_matrix.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** the signatures above in `matrix.py`; `pyproject.toml` sets `pythonpath = ["."]` for pytest.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat(cfd): work-item matrix selection`.

### Task 2: Coefficients, forces parsing, results file

**Files:**
- Create: `cfd_openfoam/sweep/coeffs.py`, `cfd_openfoam/sweep/results.py`
- Test: `cfd_openfoam/tests/test_coeffs.py`, `cfd_openfoam/tests/test_results.py`, fixture `tests/fixtures/forces.dat` (OpenFOAM v2406 `forces` output, 3 time rows, with the header comments)

**Interfaces:**
- Produces:
  - `coeffs.py`: constants `RHO=1.225`, `MU=1.7894e-5`, `CHORD=0.65`, `PIVOT=(0.325, 0.0)`; `rotate_forces(fx, fy, alpha_deg) -> tuple[float, float]`; `coefficients(fx, fy, mz, alpha_deg, v) -> tuple[float, float, float]` (CL, CD, Cm); `parse_forces_dat(path: Path) -> tuple[float, float, float]` (last row, total Fx, Fy, Mz, i.e. pressure + viscous); `has_converged(history: list[tuple[float, float]], tol: float) -> bool` where history is `(CL, Cm)` at chunk ends and the test is both changes < tol between the last two entries (False with fewer than two).
  - `results.py`: `RESULT_COLUMNS: list[str]` (exact order from Global Constraints); `read_done_alphas(path: Path, tag: str) -> set[float]`; `append_row(path: Path, row: dict) -> None` (writes header if the file is new).

- [ ] **Step 1: Write failing tests.** Port the Fluent `selftest` assertions (rotation round-trip at 0, 6, 12, 30 deg; `coefficients(0, 10, 2, 0, 4.12)` against hand-computed q); `test_parse_forces_dat_last_row` against the fixture; `test_has_converged_needs_two_entries`; `test_has_converged_threshold`; `test_append_row_writes_header_once`; `test_read_done_alphas_filters_by_tag`; `test_read_done_ignores_partial_last_line` (file ends mid-row without newline; the partial row is not counted and no exception is raised); `test_read_done_missing_file_is_empty`.
- [ ] **Step 2: Run** `pytest cfd_openfoam/tests/test_coeffs.py cfd_openfoam/tests/test_results.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the signatures above. `read_done_alphas` uses `csv.DictReader` and skips any row with missing fields.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat(cfd): coefficients, forces parsing, results file`.

### Task 3: Storage abstraction (local folder and S3)

**Files:**
- Create: `cfd_openfoam/sweep/storage.py`
- Test: `cfd_openfoam/tests/test_storage.py`

**Interfaces:**
- Produces:
  - `class Store(Protocol)`: `get_file(rel: str, dest: Path) -> bool` (False if missing); `put_file(src: Path, rel: str) -> None`; `list_keys(prefix: str) -> list[str]`.
  - `class LocalStore(root: Path)` and `class S3Store(bucket: str, prefix: str, endpoint_url: str | None = None)`.
  - `open_store(uri: str, endpoint_url: str | None = None) -> Store`: `s3://bucket/prefix` -> `S3Store`; anything else is a local path -> `LocalStore`.
  - `put_file` on `LocalStore` writes to a temp name then renames, so a killed run never leaves a partial file. S3 `put_object` is already atomic.

- [ ] **Step 1: Write failing tests** with `moto` (`pip install moto[s3]` as a test dependency): `test_local_roundtrip`, `test_local_get_missing_returns_false`, `test_local_put_is_atomic` (no `.tmp` file remains), `test_open_store_picks_backend`, `test_s3_roundtrip_with_moto`, `test_s3_list_keys_respects_prefix`, `test_s3_get_missing_returns_false`, `test_s3_endpoint_url_is_passed` (assert the boto3 client's `meta.endpoint_url`).
- [ ] **Step 2: Run** `pytest cfd_openfoam/tests/test_storage.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the signatures above (`boto3.client("s3", endpoint_url=...)`; treat `ClientError` 404/NoSuchKey as missing).
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat(cfd): storage abstraction for local and S3`.

### Task 4: Case state, solver backend interface, run orchestration

**Files:**
- Create: `cfd_openfoam/sweep/case.py`, `cfd_openfoam/sweep/backend.py` (protocol only in this task), `cfd_openfoam/sweep/runner.py`
- Test: `cfd_openfoam/tests/test_case.py`, `cfd_openfoam/tests/test_runner.py`, `cfd_openfoam/tests/fakes.py` (`FakeBackend`)

**Interfaces:**
- Consumes: Task 1 (`WorkItem`, `rows_for`), Task 2 (`coefficients`, `has_converged`, `read_done_alphas`, `append_row`, `RESULT_COLUMNS`), Task 3 (`Store`).
- Produces:
  - `case.py`: `inlet_state(v: float, flow_x: float, flow_y: float, tu_pct: float, visc_ratio: float = 5.0) -> dict` with keys `Ux, Uy, k, omega, nut, ReThetat, gammaInt`. Formulas: `k = 1.5 (Tu V)^2` with `Tu = tu_pct/100`; `nu = MU/RHO`; `nut = visc_ratio * nu`; `omega = k / nut`; `gammaInt = 1.0`; `ReThetat` from the Langtry-Menter correlation (`Tu_pct > 1.3: 331.5 (Tu_pct - 0.5658)^-0.671`; else `1173.51 - 589.428 Tu_pct + 0.2196 / Tu_pct^2`).
  - `backend.py`: `class SolverBackend(Protocol)`: `prepare(msh: Path, case_dir: Path, np: int) -> None`; `set_inlet(state: dict) -> None`; `initialise() -> None`; `iterate(n: int) -> tuple[float, float, float]` (runs n more iterations, returns total Fx, Fy, Mz); `save_restart() -> str` (restart token, e.g. latest time name); `load_restart(token: str) -> None`.
  - `runner.py`: `run_item(item: WorkItem, rows: list[dict], backend: SolverBackend, store: Store, workdir: Path, *, msh: Path, np: int = 4, tu_pct: float, tol: float = 0.002, chunk: int = 200, max_chunks: int = 10, log=print) -> list[dict]`. Behavior: downloads `<item_id>/results.csv` and `<item_id>/restart.json` from the store (if present) into `workdir`; skips angles already done; calls `backend.prepare`, then `load_restart` if a marker exists else `initialise`; for each remaining angle in ascending order: `set_inlet`, loop `iterate(chunk)` up to `max_chunks` checking `has_converged`; append the row to `workdir/results.csv`; upload `results.csv` and `restart.json` (the token plus the last finished alpha) to the store under `<item_id>/` before starting the next angle. A non-finite force aborts that angle's loop: the row has `converged=False` and `Fx_N/Fy_N/Mz_Nm/CL/CD/Cm_pivot` of `nan`, and the next angle calls `initialise()` instead of continuing.
- `FakeBackend` (tests only) returns scripted forces and records calls.

- [ ] **Step 1: Write failing tests.** `test_case.py`: `test_inlet_state_components` (V=8, flow (cos 6°, sin 6°) -> Ux, Uy), `test_inlet_state_k_and_omega` (Tu 0.1 %, V 4.12: k = 1.5 (0.001 x 4.12)^2; omega = k / (5 x MU/RHO)), `test_rethetat_both_branches` (Tu 0.1 % and 2 %). `test_runner.py`: `test_runs_all_angles_in_order`, `test_row_has_all_columns_and_correct_coefficients`, `test_uploads_after_each_angle` (fake store records put order: after angle 1 completes, `results.csv` has 1 row in the store before angle 2's `set_inlet` is called), `test_resume_skips_done_angles_and_loads_restart`, `test_unconverged_angle_is_recorded_and_job_continues` (`converged` is the string `False`), `test_divergent_angle_recorded_nan_and_next_reinitialises` (Review Focus 4), `test_stops_early_when_converged` (iterations equals chunks used x chunk).
- [ ] **Step 2: Run** `pytest cfd_openfoam/tests/test_case.py cfd_openfoam/tests/test_runner.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the signatures above; angle loop and resume rules exactly as stated.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat(cfd): case state and resumable run orchestration`.

### Task 5: OpenFOAM backend and case templates

**Files:**
- Create: `cfd_openfoam/sweep/backend.py` (add `OpenFoamBackend`), `cfd_openfoam/templates/{0,constant,system}/...`
- Test: `cfd_openfoam/tests/test_templates.py` (no OpenFOAM needed), `cfd_openfoam/tests/smoke/test_openfoam_smoke.py` (marked `@pytest.mark.docker`, skipped unless `simpleFoam` is on PATH)

**Interfaces:**
- Consumes: Task 4 (`SolverBackend`, `inlet_state`), Task 2 (`parse_forces_dat`, `PIVOT`).
- Produces: `class OpenFoamBackend(SolverBackend)` implementing the six methods with subprocess calls: `fluentMeshToFoam`, then fix patch types (`wall` -> `wall`, `inlet`/`outlet` as named, front/back -> `empty`) via `createPatch` or `changeDictionary`; `decomposePar`/`mpirun -np N simpleFoam -parallel`/`reconstructPar` when `np > 1`, plain `simpleFoam` otherwise; `iterate(n)` sets `endTime` to `current + n`, starts from `latestTime`, and reads forces with `parse_forces_dat`. Templates use `simpleFoam`, `kOmegaSSTLM`, `forces` function object (patch `wall`, `CofR (0.325 0 0)`, `rho rhoInf`, `rhoInf 1.225`), `bounded Gauss linearUpwind` (second order) for U/k/omega/ReThetat/gammaInt, `nu = MU/RHO`, outlet `p = 0`, inlet `fixedValue` for `U`, `k`, `omega`, `ReThetat`, `gammaInt`, and wall treatment suitable for y+ ~ 1.

- [ ] **Step 1: Write failing tests** in `test_templates.py`: `test_templates_contain_required_entries` (grep the template files for `kOmegaSSTLM`, `simpleFoam`, `0.325`, `1.225`, `empty`), `test_all_placeholders_have_state_keys` (every `{{key}}` in templates is a key returned by `inlet_state` or a documented constant). Smoke test: build a coarse mesh (`make_mesh.py --hs 6e-3 --h-edge 2e-3 --y1 1e-4 --bl-thickness 0.02 --section section_f08.0pct.csv`), `prepare`, `set_inlet(inlet_state(4.12, ...))`, `initialise`, `iterate(20)`, assert the three forces are finite.
- [ ] **Step 2: Run** `pytest cfd_openfoam/tests/test_templates.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the templates and `OpenFoamBackend`. Choices left to the builder: relaxation factors or SIMPLEC, wall-function types for the low-Re mesh, whether `fvSchemes` use `linearUpwind` or `limitedLinear 1`.
- [ ] **Step 4: Run** `pytest cfd_openfoam/tests/test_templates.py -v`. Expected: PASS. The smoke test is run in Task 7.
- [ ] **Step 5: Commit** `feat(cfd): OpenFOAM backend and case templates`.

### Task 6: Entrypoint CLI

**Files:**
- Create: `cfd_openfoam/entrypoint.py`
- Test: `cfd_openfoam/tests/test_entrypoint.py`

**Interfaces:**
- Consumes: Tasks 1, 3, 4, 5.
- Produces: `main(argv: list[str] | None = None, backend_factory: Callable[[], SolverBackend] = OpenFoamBackend, mesher: Callable[[Path, Path], Path] = make_mesh_and_check) -> int` (exit code). Flags, each also read from an environment variable when the flag is absent: `--input-uri` / `INPUT_URI`, `--output-uri` / `OUTPUT_URI`, `--s3-endpoint-url` / `S3_ENDPOINT_URL`, `--camber`, `--wind`, `--tag`, `--tags` (default `tu0.1,tu0.5`, with `tu0.1` -> 0.1 % and `tu0.5` -> 0.5 %), `--from-array-index` (reads `AWS_BATCH_JOB_ARRAY_INDEX`), `--list-items`, `--np` / `NP`, `--tol`, `--chunk`, `--max-chunks`, `--smoke` (coarse mesh, first angle only, 20 iterations). `--list-items` prints one `item_id` per line plus the count and exits 0. `make_mesh_and_check(section_csv: Path, out_dir: Path) -> Path` runs `make_mesh.py` then `check_msh.py` and raises if the result is not OK.

- [ ] **Step 1: Write failing tests** with fake backend, fake mesher and a `LocalStore` temp folder: `test_list_items_prints_ids_and_count`, `test_array_index_selects_item` (index 3 runs exactly item 3), `test_array_index_out_of_range_exits_zero_and_uploads_nothing` (Review Focus 1), `test_filters_matching_nothing_exit_nonzero_and_upload_nothing` (Review Focus 2: bad camber and bad wind), `test_wind_with_space_via_env_var` (Review Focus 5: `WIND="8 kn"` env selects the right rows; item_id key in the store has no space), `test_env_vars_used_when_flags_absent`, `test_failed_mesh_check_exits_nonzero`, `test_smoke_flag_runs_one_angle`.
- [ ] **Step 2: Run** `pytest cfd_openfoam/tests/test_entrypoint.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `main` and `make_mesh_and_check`. Inputs fetched from `INPUT_URI`: `run_matrix.csv` and `<section>.csv`. After a successful item, upload logs under `<item_id>/logs/`.
- [ ] **Step 4: Run** the same command, then `pytest cfd_openfoam/tests -v -m "not docker"`. Expected: all PASS.
- [ ] **Step 5: Commit** `feat(cfd): container entrypoint with Batch array-index selection`.

### Task 7: Dockerfile, local run scripts, container smoke test

**Files:**
- Create: `cfd_openfoam/Dockerfile`, `cfd_openfoam/scripts/run_local.sh`, `cfd_openfoam/scripts/run_local.ps1`, `cfd_openfoam/.dockerignore`

**Interfaces:**
- Consumes: Task 6 entrypoint. Produces: image `cfd-openfoam:local`; `run_local.{sh,ps1} [--smoke] [--camber C --wind W --tag T] [--np N]` mounts `./data/cfd_sections` as `/in` (read-only) and `./cfd_out` as `/out`, then runs the entrypoint with `INPUT_URI=/in OUTPUT_URI=/out`.

- [ ] **Step 1: Write the Dockerfile.** Base the ESI v2406 image; install Python 3, pip, `numpy`, `gmsh`, `boto3`; copy `cfd_openfoam/` and `data/cfd_sections/{make_mesh.py,check_msh.py}` (build context is the repo root); non-root user; `ENTRYPOINT ["python3", "/app/entrypoint.py"]`. Pin the base image tag in an `ARG`.
- [ ] **Step 2: Write both run scripts** (quote paths with spaces; the repo path contains spaces).
- [ ] **Step 3: Build and smoke-run.** Run: `docker build -f cfd_openfoam/Dockerfile -t cfd-openfoam:local .` then `cfd_openfoam/scripts/run_local.ps1 --smoke --camber 8 --wind "8 kn" --tag tu0.1`. Expected: exit 0 and `cfd_out/<item_id>/results.csv` with the exact header and one row of finite numbers. If Docker is not available in the session, report this task as **not verified** and say so.
- [ ] **Step 4: Run the in-container pytest smoke test.** Run: `docker run --rm --entrypoint pytest cfd-openfoam:local /app/tests/smoke -v`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(cfd): Dockerfile and local run scripts`.

### Task 8: Local Batch simulation with MinIO and the interruption test

**Files:**
- Create: `cfd_openfoam/docker-compose.test.yml`, `cfd_openfoam/scripts/test_batch_local.sh`, `cfd_openfoam/scripts/test_batch_local.ps1`

**Interfaces:**
- Consumes: Tasks 6, 7. Produces: one command per shell that exits non-zero on any failed assertion.

- [ ] **Step 1: Write the compose file:** services `minio` (with a bucket-creation init container using `mc`) and `job` (the image, env `S3_ENDPOINT_URL=http://minio:9000`, `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` set to the MinIO test credentials, `INPUT_URI=s3://test/in`, `OUTPUT_URI=s3://test/out`, `AWS_BATCH_JOB_ARRAY_INDEX` passed through).
- [ ] **Step 2: Write the test script** with these checks: (a) upload `data/cfd_sections` inputs to MinIO; (b) `--list-items` gives N items; (c) run array index 0 in `--smoke` mode and confirm `out/<item_id>/results.csv` exists in MinIO; (d) index N (out of range) exits 0 and creates no new keys; (e) **interruption:** run index 1 with `--smoke --smoke-angles 3`, `docker kill` the container once the first angle's row is visible in MinIO, rerun the same command, and assert the final `results.csv` has exactly 3 rows, each alpha once, and the log shows the first alpha was skipped. This needs a `--smoke-angles N` flag added to the entrypoint in this task (test first in `test_entrypoint.py`: `test_smoke_angles_limits_alpha_count`).
- [ ] **Step 3: Run** `cfd_openfoam/scripts/test_batch_local.ps1`. Expected: prints PASS for (a)-(e), exit 0. Not-verified rule from Task 7 applies if Docker is absent.
- [ ] **Step 4: Commit** `test(cfd): local Batch simulation with MinIO and interruption test`.

### Task 9: Terraform

**Files:**
- Create: `cfd_openfoam/terraform/{versions,variables,ecr,s3,iam,batch,outputs}.tf`, `cfd_openfoam/scripts/build_and_push.sh`, `cfd_openfoam/scripts/submit.sh`

**Interfaces:**
- Variables: `region`, `project_name` (default `cusail-cfd`), `compute_type` (`"FARGATE_SPOT"` or `"EC2_SPOT"`, validated), `vcpus` (4), `memory_mib` (8192), `max_vcpus` (64), `image_tag` (`"latest"`), `bucket_name` (optional), `log_retention_days` (30), `vpc_id`/`subnet_ids` (optional; default VPC when empty), `tags`.
- Outputs: `ecr_repository_url`, `bucket_name`, `job_queue_name`, `job_definition_name`, `submit_example`.

- [ ] **Step 1: Write `versions.tf`, `variables.tf`** (with a validation block on `compute_type`) and run `terraform -chdir=cfd_openfoam/terraform init -backend=false`. Expected: init succeeds.
- [ ] **Step 2: Write resources** per the spec's Terraform section: ECR (scan on push), S3 (versioning, SSE, public access block, `lifecycle { prevent_destroy = true }`), IAM roles (Batch service, ECS instance profile used only in EC2 mode via `count`, task execution, job role limited to `s3:GetObject` on `in/*` and `s3:GetObject/PutObject/ListBucket` on `out/*`), security group (egress only), compute environment (Fargate Spot or EC2 `SPOT_CAPACITY_OPTIMIZED` selected by `compute_type`), job queue, job definition (retry 3 attempts on `Host EC2*` status reasons, timeout, env `INPUT_URI`, `OUTPUT_URI`, `NP`), log group. Include a commented S3 backend block.
- [ ] **Step 3: Verify.** Run: `terraform -chdir=cfd_openfoam/terraform fmt -check` and `terraform -chdir=cfd_openfoam/terraform validate`. Expected: both succeed. Run `validate` once more with `-var compute_type=EC2_SPOT`. If `terraform` is not installed, report **not verified** and say so.
- [ ] **Step 4: Write the two scripts.** `build_and_push.sh` logs in to ECR with `aws ecr get-login-password`, builds, tags and pushes using the `ecr_repository_url` output. `submit.sh` syncs `data/cfd_sections` to `s3://<bucket>/in/`, runs the container image with `--list-items` (or counts items locally with the same Python) to get N, and runs `aws batch submit-job --array-properties size=N`.
- [ ] **Step 5: Commit** `feat(cfd): Terraform for ECR, S3, IAM and Batch`.

### Task 10: README

**Files:**
- Create: `cfd_openfoam/README.md`

- [ ] **Step 1: Write the README** covering: what it is; the three test levels with one command each (unit: `pytest cfd_openfoam/tests -m "not docker"`; container smoke: Task 7 step 3; Batch simulation: Task 8 step 3); local run examples for Windows and Linux; the AWS path (`terraform init/plan/apply`, `build_and_push.sh`, `submit.sh`, fetching results from S3); Fargate vs EC2 Spot sizing; cost notes (Spot, retries, destroy); the **manual physics check against Fluent/NeuralFoil** (8 % section, 8 kn, alpha 4 deg and 12 deg; what is plausible and what is a red flag); how to reproduce an interruption.
- [ ] **Step 2: Verify the commands in the README** are the ones used in Tasks 7 to 9 (copy, do not retype).
- [ ] **Step 3: Commit** `docs(cfd): README for the OpenFOAM container`.

---

## Self-review notes
- Spec coverage: container (T7), pipeline and resume (T4, T6), local run and smoke (T7), local Batch path with MinIO and interruption (T8), Terraform (T9), verification plan (T1 to T9 tests plus the README manual check in T10), non-goals respected (Fluent scripts untouched).
- Types checked across tasks: `WorkItem`, `SolverBackend`, `Store`, `inlet_state` keys and `RESULT_COLUMNS` are defined once and used by the same names later.
- Unverifiable here without Docker, AWS and your data: Tasks 7 and 8 runs, the OpenFOAM physics, and Terraform apply. They must be reported as not verified if skipped.
