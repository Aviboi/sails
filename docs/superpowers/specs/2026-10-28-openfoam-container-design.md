# OpenFOAM container + AWS Batch for the 2D section sweep: design

## Intent
The 2D sail-section study currently runs on Ansys Fluent through PyFluent (`data/cfd_sections/build_case.py`, `run_fluent_sweep.py`). It needs a Fluent install and licence, so it only runs on one laptop. The goal is a **portable, licence-free** version: one Docker image that runs the same sweep on any machine with Docker, and on AWS Batch for runs too large for the laptop (finer meshes, more cases, later 3D).

Portability is the priority. Matching Fluent to the last digit is not.

## Goals
- One image, same behaviour on a laptop (`docker run`) and on AWS Batch (Fargate Spot or EC2 Spot).
- Same inputs and outputs as today: section CSVs and `run_matrix.csv` in; `results.csv` with the existing columns out (`tag, camber_pct, wind, Re, alpha_deg, V_mps, Fx_N, Fy_N, Mz_Nm, CL, CD, Cm_pivot, iterations, converged, seconds`).
- Same physics as `build_case.py`: steady incompressible air (rho 1.225, mu 1.7894e-5), transition model, inlet turbulence intensity 0.1 % or 0.5 %, viscosity ratio 5, second-order upwind, pressure outlet at 0 gauge. Angle of attack set by rotating the inflow, never the geometry.
- Spot-safe: an interrupted job, once retried, resumes without redoing finished angles.
- Terraform that creates all the AWS infrastructure from scratch and can be destroyed cleanly.

## Non-goals
- Bit-for-bit agreement with Fluent. OpenFOAM's `kOmegaSSTLM` differs from Fluent's Transition SST.
- Transient runs above stall (not scripted today either).
- Multi-node MPI. One job is one container.
- A CI pipeline, a UI, or cost dashboards.
- Removing the Fluent scripts. They stay in place.

## Anti-goals (would make this a failure even if it runs)
- Anything that needs a licence, an AWS access key baked into the image, or a manual step on the AWS machine.
- A design where one failed or interrupted angle forces a whole-sweep rerun.
- Infrastructure that cannot be torn down with `terraform destroy` (S3 results are the one intended exception: see Terraform).

## Layout (all new, under `cfd_openfoam/` at the repo root)
```
cfd_openfoam/
  Dockerfile
  entrypoint.py            # Batch / local entry: resolve work item, sync, run, upload
  sweep/                   # python package: matrix, case build, run, forces, resume
  templates/               # OpenFOAM case template (system/, constant/, 0/)
  scripts/                 # run_local.sh / .ps1, build_and_push.sh (ECR), submit.sh
  tests/                   # no-OpenFOAM unit tests + one in-container smoke test
  README.md
  terraform/               # AWS infrastructure
```
`make_mesh.py` and `check_msh.py` are copied into the image from `data/cfd_sections/` at build time, not duplicated in git.

## Container
- Base: OpenFOAM v2406 (ESI, `opencfd/openfoam-default` or an equivalent official image; builder picks). This is my call, chosen because ESI ships `kOmegaSSTLM`.
- Adds Python 3, numpy, gmsh (>= 4.11, needed by `make_mesh.py`), and boto3 (for S3).
- Runs as a non-root user. No credentials in the image.
- One entrypoint, with every option available as a flag or environment variable.

## Pipeline for one work item
A work item is `(camber_pct, wind, tag)` where `tag` is the turbulence intensity label (`tu0.1` or `tu0.5`), with all its angles in ascending order.

1. Fetch inputs: section CSV and `run_matrix.csv` from `INPUT_URI` (S3 prefix or local folder).
2. `make_mesh.py` writes the Fluent `.msh`; `check_msh.py` must say OK or the item fails.
3. `fluentMeshToFoam` converts it. Patches `wall`, `inlet`, `outlet` are mapped from the Fluent zones; the 2D back and front faces become `empty`.
4. Fill the template: velocity components, `k`/`omega`/`nut`/transition fields from turbulence intensity and viscosity ratio, force/moment centre at the pivot (0.325, 0, 0).
5. For each angle not already in the results: set the inlet vector, run `simpleFoam` (MPI via `decomposePar` if `NP` > 1), iterate in chunks, and stop when CL and Cm each change by less than `tol` (default 0.002) over a chunk, or at `max_chunks`. The next angle starts from the previous solution. Forces come from the `forces` function object. Lift, drag and the coefficients are computed by the same formulas as `run_fluent_sweep.py` (L = -Fx sin a + Fy cos a, D = Fx cos a + Fy sin a, q = 0.5 rho V^2, c = 0.65 m, Cm about the pivot, nose-up positive).
6. After each angle: append the results row, write a small restart marker (last finished angle plus the latest time directory), and upload both to `OUTPUT_URI`.
7. On finish, upload logs, residual history and `y+` stats per angle.

**Work item selection:** explicit flags (`--camber`, `--wind`, `--tag`) for local runs. Under Batch, `--from-array-index` maps `AWS_BATCH_JOB_ARRAY_INDEX` onto the sorted list of work items in `run_matrix.csv`, so the array size is the number of items and no child needs to know about the others. `--list-items` prints the list so the submit script can size the array.

**Resume:** on start, download any existing `results.csv` rows and restart marker for this item from `OUTPUT_URI`. Finished angles are skipped. If a restart marker exists, the solver starts from that time directory; otherwise it starts fresh. A retry after a Spot interruption therefore loses at most the angle in progress.

## Local use
`scripts/run_local.*` builds the image if needed and runs one work item with folders mounted in place of S3 (`INPUT_URI=/in`, `OUTPUT_URI=/out`). It has a `--smoke` mode: one coarse mesh, one angle, a few dozen iterations, for checking that the image works on a new machine.

## Local testing of the Batch path (approved addition)
Everything that runs on Batch must be exercisable on a laptop with only Docker:
- `docker compose` file with the job image plus a **MinIO** container as a stand-in S3 (the entrypoint takes an `S3_ENDPOINT_URL` override). `INPUT_URI`/`OUTPUT_URI` then use real `s3://` paths, so the same S3 code runs locally and on AWS.
- `scripts/test_batch_local.*` simulates Batch: it sets `AWS_BATCH_JOB_ARRAY_INDEX` for each child in turn and runs the container with the same environment variables the job definition sets.
- **Spot-interruption test:** start a smoke-size item, kill the container after the first angle's upload, rerun it, and assert that the finished angle is skipped and the final `results.csv` has every angle exactly once.
- Three test levels, each runnable on its own: (1) unit tests, Python only, no Docker; (2) container smoke test, Docker only; (3) the MinIO Batch simulation above, including the interruption test. The README gives one command per level.
- The smoke and simulation tests use the coarse mesh so the whole suite finishes in minutes.

## Terraform (`cfd_openfoam/terraform/`)
Resources:
- ECR repository for the image.
- S3 bucket for inputs and results (versioning on, public access blocked, encryption on). `prevent_destroy` is on and `force_destroy` is off, so a stray `terraform destroy` cannot delete results.
- IAM: Batch service role; ECS instance profile (EC2 mode); task execution role; job role limited to read on the input prefix and read/write on the output prefix.
- AWS Batch: compute environment (`FARGATE_SPOT` or `EC2` with `SPOT_CAPACITY_OPTIMIZED`, chosen by a variable), job queue, job definition (vCPU, memory, retry strategy of 3 attempts on Spot reclaim, timeout), CloudWatch log group with retention.
- Networking: uses the default VPC by default, with `vpc_id` / `subnet_ids` variables to override. Egress-only security group; no inbound.

Variables: region, project name, `compute_type`, `vcpus`, `memory_mib`, `max_vcpus`, image tag, bucket name (optional), log retention, tags.
Outputs: ECR URL, bucket name, queue name, job definition name, the submit command.

State is local by default, with a commented-out S3 backend block. Remote state setup is not part of this work.

`scripts/build_and_push.sh` builds the image and pushes it to ECR. `scripts/submit.sh` uploads inputs to the bucket and submits the array job.

## Constraints
- Fargate: at most 16 vCPU and 120 GB per task. Larger runs need `compute_type = "EC2"`. Default job size is 4 vCPU, 8 GiB, which suits the 118k-cell meshes. This is my call.
- The Windows laptop runs Docker Desktop; shell scripts need PowerShell twins.
- No AWS account access is assumed in this session. Terraform is validated with `terraform validate` and `fmt`, not applied.

## Verification plan
- Unit tests (no OpenFOAM, run anywhere): matrix and work-item selection, array-index mapping, resume logic, force rotation and coefficients (ported from the Fluent script's `--selftest`), template filling, S3 URI handling against a fake.
- In-container smoke test: coarse mesh, one angle, converts and runs, `results.csv` has the right columns and finite values.
- **Physics check against Fluent/NeuralFoil is a manual first run**, not an automated test: one 8 % section, 8 kn, alpha 4 deg and 12 deg, compare CL, CD, Cm. Expect differences; the README says what size of difference is plausible and what is a red flag (for example CL off by more than about 10 % below stall). I cannot run this part without Docker and your results, so it is reported as unverified until you do.
- `terraform fmt -check` and `terraform validate`.

## Left to the builder
Exact OpenFOAM image tag, `kOmegaSSTLM` field setup and wall-function choices (y+ about 1 mesh, so low-Re treatment), the choice of `forces` vs `forceCoeffs`, `fvSolution` relaxation or consistent-SIMPLE settings, MPI core-count defaults, container file layout, naming.

## Calls I made (please check these)
1. OpenFOAM v2406 ESI, `simpleFoam` + `kOmegaSSTLM`.
2. A work item is one camber, wind and tag with all its angles in order; warm start between angles.
3. Default job size 4 vCPU / 8 GiB; retry up to 3 times.
4. S3 results bucket protected from `terraform destroy`.
5. Default VPC, local Terraform state.
6. Fluent scripts stay untouched; new code lives in `cfd_openfoam/`.
