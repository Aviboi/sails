# Design Study Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a design-study section to `notebooks/notebook.py` that sweeps sail area, aspect ratio, mast step and mast tube (OD, ID), and shows survivability and stability margins against speed, mass and manufacturing thresholds.

**Architecture:** One function, `evaluate(design)`, takes explicit design values and returns performance and a margin per check. It reuses the existing force-balance and structural code, made callable with explicit step position and tube. A fast righting-moment path avoids re-slicing the hull mesh per design. Plots are maps (area × AR) and margin-line panels (mast tube, mast step). The single-design cells and widgets stay unchanged.

**Tech Stack:** marimo (sandbox mode), numpy, scipy, trimesh, matplotlib.

**Spec:** `docs/superpowers/specs/2026-11-10-design-study-design.md`

## Global Constraints

- Work only through a live marimo session with `/marimo-pair`, started with `marimo edit --sandbox notebooks/notebook.py`. Never edit `notebook.py` on disk while it runs (project `CLAUDE.md`).
- Frame: x forward, y to port, z up, metres. Heights are measured from the keel tip.
- No hard-coded defaults or magic numbers: every new number is a `Param` in the right group (`design`, `requirements`, `estimates`, `assumptions`, `constants`).
- Existing single-design cells keep working and give the same numbers as before at default inputs.
- Carbon tube: `estimates.sigma_ult` 500 MPa, `tube_e` 70 GPa, `tube_rho` 1600 kg/m³, safety factor `requirements.sf_strength` 2.0 (existing).
- There is no test suite. Each task is verified by running `assert` snippets in the live kernel.
- Commit only when the user asks.

## Review Focus

- **ID ≥ OD, or a wall below `wall_min`:** `evaluate` returns negative wall margin and finite other margins, no exception.
- **Rig so heavy the total mass exceeds the hull's buoyancy:** `evaluate` returns NaN stability margins and a FAIL on mass, not a `ValueError` from `gz_curve`.
- **Step x outside the hull or beyond the interpolation range (`fb_x`):** clipped to the hull, with a warning flag in the result.
- **No stock tube near the requested OD/ID:** snapping picks the nearest listed size and reports it.
- **A sail that cannot make way (speed 0 from `balance`):** speed margin is -100%, not a division error.
- **Sail taller than the air-draft limit:** fails the air-draft check but still evaluates, so the map has no holes.

---

### Task 1: Parameterise the rig by step position and measure evaluation cost

**Files:**
- Modify: `notebooks/notebook.py` (cells containing `make_rig`, `rig_for`, `mast_step`)

**Interfaces:**
- Consumes: existing `make_rig(sail_, sp_, cn_, ar_eff)`, `rig_for(area, ar)`, `mast_step` array `[x, y, z]`.
- Produces:
  - `step_at(x: float, dz: float, y: float = 0.0) -> np.ndarray`: step vector `[x, y, deck(x) + dz]`, with x clipped to the hull bounds. Same formula as the `mast_step` cell.
  - `make_rig(sail_, sp_, cn_, ar_eff, step=None)`: `step=None` means the global `mast_step`.
  - `rig_for(area, ar, step=None)`: same default.
  - `timings` (dict, seconds) for `rig_for`, `best_trim` at one TWA, and `gz_curve`, recorded in the task notes.

- [ ] **Step 1: Verification snippet first.** In the kernel, assert `rig_for(sail["S"], sail["ar"])["ce_wl"]` equals `rig0["ce_wl"]` to 1e-9, and the same for `["arm"]`. Run it now (it passes, since both use `mast_step`).
- [ ] **Step 2: Add `step_at` to the `mast_step` cell** and make `mast_step = step_at(step_x_in.value, step_dz_in.value, step_y_in.value)`.
- [ ] **Step 3: Add the `step` argument** to `make_rig` and `rig_for`; `ce_wl` and `arm` use it. `rig_for` also uses it for the wind height `wind_at(step[2] - draft + s["z_mac"], ...)`.
- [ ] **Step 4: Verification:** the Step 1 assert still passes, and `rig_for(0.75, 2.0, step_at(0.8, 0.1))["ce_wl"] - rig0["ce_wl"]` has the sign of (deck height at 0.8 + 0.1 − current step z).
- [ ] **Step 5: Time the cost.** Use `time.perf_counter` for one `rig_for`, one `best_trim(120, wind_states["Design"], maxheel_in.value, rg)`, and one `gz_curve(hull, total_mass, rho_in.value, cg_all, gz_heel)`. Write the three numbers into the plan's notes (below). They decide the grid sizes in Task 6.

**Task notes (fill in):** `rig_for` ___ s, `best_trim` ___ s, `gz_curve` ___ s.

---

### Task 2: Uniform mast tube response

**Files:**
- Modify: `notebooks/notebook.py` (new cell after the "Mast sizing" section; add `Param`s)

**Interfaces:**
- Consumes: `rig_for`, `wind_at`, `wind_states`, `rho_air`, `cn_lock_in`, `v_req`, `KNOT`, `requirements`, `estimates`.
- Produces:
  - `mast_loads(rig: dict, step: np.ndarray) -> dict`: for `"Design"` and `"Survival"`, `{"z": span grid (m), "moment": N·m array root-to-tip, "shear_root": N, "heel_m": N·m}`. Same load model as `mast_opt` (design wind + `v_req`, max `CN` for alpha 0–30°; survival with `cn_lock`). Refactor `mast_opt` to call it.
  - `tube_response(moment, z, od: float, id_: float) -> dict`: constant tube; `stress` (Pa) = `M_root·(od/2)/I`, `I = π(od⁴ − id_⁴)/64`; `strength_margin = 1 − stress·sf/σ_ult`; `defl_frac` (tip deflection / span, integrating `M/(E·I)` twice); `mass` (kg) = `ρ·π/4·(od² − id_²)·length`; `wall = (od − id_)/2`.
  - New `Param`s: `estimates` has `wall_min` already (0.6 mm). Add to `requirements`: `od_max` (mm, drivetrain mount limit, placeholder 60), `mast_len_max` (m, placeholder 2.5), `area_max` (m², placeholder 3.0), `mass_max` (kg, placeholder 60, total mass cap). Add to `assumptions`: `tube_stock` (list of `(OD mm, ID mm)` pairs, common carbon tube range, placeholder).

- [ ] **Step 1: Write the check snippets.** Thin-wall hand case: `od=0.040`, `id_=0.036`, root moment 10 N·m uniform over a 1.0 m span gives `stress = 10·0.02/I` with `I = π(0.04⁴ − 0.036⁴)/64`; assert `tube_response` matches to 1e-6. Deflection: constant moment M over length L gives `M·L²/(2·E·I)`; assert to 1e-3 relative.
- [ ] **Step 2: Run them to see them fail** (functions not defined).
- [ ] **Step 3: Implement `tube_response`**, then `mast_loads`, refactoring `mast_opt` to use it.
- [ ] **Step 4: Run the snippets; also assert** the current design's `mast_loads(rig0, mast_step)["Survival"]["heel_m"]` equals `struct["Survival"]["heel_m"]` within 1%. (The two use different grids, so exact equality is not expected.)
- [ ] **Step 5: Add the `Param`s** and show them in the `inputs_drift` table in the same style as the others.

---

### Task 3: Fast all-up righting moment

**Files:**
- Modify: `notebooks/notebook.py` (new cell after the "All-up mass and stability" cell)

**Interfaces:**
- Consumes: `gz_curve`, `solve_draft`, `hull`, `rho_in`, `gz_heel`, `G`, `total_mass`, `cg_all`.
- Produces:
  - `cb_table`: for `masses = np.linspace(mass_in.value, mass_max, n)` and each `gz_heel` angle, the earth-frame `cb_y` from `gz_curve` (CB depends on displacement only). `n` from a new `assumptions.cb_table_n` Param (placeholder 6).
  - `rm_peak_fast(total_mass: float, cg: np.ndarray) -> float`: interpolates `cb_y` at `total_mass`; `gz(φ) = (y of the hull-fixed cg after rotating φ about the keel-level midship pivot) − cb_y(φ)`; returns `max(gz)·total_mass·G` up to the first peak, same convention as the all-up cell (`rm_peak_all`).
  - Returns `nan` when `total_mass >= hull.volume·rho_in.value`.

- [ ] **Step 1: Check snippet.** For the current design, assert `rm_peak_fast(total_mass, cg_all)` is within 1% of `rm_peak_all`. For a heavier case (`total_mass + 8`, same `cg_all`), assert within 2% of `gz_curve`-based peak computed directly.
- [ ] **Step 2: Run it to see it fail**, implement, rerun.
- [ ] **Step 3: Assert the buoyancy guard:** `np.isnan(rm_peak_fast(1e4, cg_all))`.

---

### Task 4: `evaluate`

**Files:**
- Modify: `notebooks/notebook.py` (new cell after Task 3)

**Interfaces:**
- Consumes: Tasks 1–3, `best_trim`, `sail_runs` TWA grid and wind states, `drive`-independent checks only.
- Produces: `evaluate(d: dict) -> dict`, with `d` keys `area, ar, step_x, gap, od, id` (floats; the rest from the existing inputs). The result has:
  - `margins`: dict name → fractional margin (positive = pass, `1 − value/limit` style, same sign convention as the Design Summary), with these names: `survival` (moment vs righting moment with rig), `deflection`, `strength`, `stability_range` (max heel vs usable range), `speed_min_wind`, `speed_reach` (slowest at TWA ≥ 90° at design wind), `speed_design`, `mass`, `wall`, `od`, `mast_len`, `area`, `air_draft`, `lead`, `fit` (OD ≤ section thickness at the tip).
  - `values`: raw numbers (speed kn, total mass, rig mass, span, mast length = span + max(gap, 0), chord and a `bulk` figure).
  - `flags`: list of strings (clipped step, snapped tube).
  - Rig mass is `spar (tube_response mass) + skin_mass formula (existing) + fixed`; no exceptions escape (NaN margins instead).

- [ ] **Step 1: Consistency snippet.** `evaluate` at the current inputs with the current tube (`od = mast_D[0]`, `id = od − 2·struct["Survival"]["t"][0]`) agrees with the Design Summary: `survival` margin within 2% of `1 − surv_moment/rm_peak_all`, `speed_design` within 1% of `max(r["V"] for r in sail_runs["Design"])/KNOT/v_req − 1`. (Tolerances reflect the uniform-tube and fast-path approximations.)
- [ ] **Step 2: Review-focus snippets:** `id ≥ od` (wall margin negative, no exception); area 8 m² (finite margins, mass FAIL); `step_x` = −1 or 99 (flag, finite results); sail that stalls (speed margin −1.0).
- [ ] **Step 3: Run them to see them fail, implement `evaluate`, rerun.**
- [ ] **Step 4: Report the runtime** of one `evaluate` and update the Task 1 notes with the grid sizes it allows (target: a 12×8 map in under about two minutes; otherwise lower the TWA grid and note it).

---

### Task 5: Study inputs and tube snapping

**Files:**
- Modify: `notebooks/notebook.py` (inputs cells and a new "Design study" section header cell)

**Interfaces:**
- Produces:
  - `design` Params for sweep ranges, one pair per variable: `area_range`, `ar_range`, `step_x_range`, `gap_range`, with point counts from `assumptions.study_points` (placeholder 12 for maps, 9 for lines).
  - `snap_tube(od_mm: float, id_mm: float) -> tuple[float, float]`: nearest pair in `assumptions.tube_stock` by OD first, then by wall.
  - `study_base`: the current design as a dict `{area, ar, step_x, gap, od, id}` taken from the widgets, `od, id` from the nearest stock tube to the current sized tube.

- [ ] **Step 1: Check snippet:** `snap_tube` returns a member of `tube_stock` for off-grid and out-of-range inputs; `study_base` round-trips through `evaluate` with no flags except `snapped`.
- [ ] **Step 2: Implement, rerun the snippet.** Show the study grids in the Inputs drift table.

---

### Task 6: Plots

**Files:**
- Modify: `notebooks/notebook.py` (new cells under "Design study")

**Interfaces:**
- Consumes: `evaluate`, `study_base`, `snap_tube`.
- Produces:
  - Cell 1 (map): area × AR grid. Colour is the **minimum of the survival and stability margins**. Contours at margin 0 for each threshold (`speed_min_wind`, `speed_design`, `mass`, `mast_len`, `air_draft`, `area`, `fit`), infeasible side hatched, current design starred. A second, smaller map shows the bulk figure (chord-driven) on the same axes.
  - Cell 2 (mast tube margin lines): OD sweep and ID sweep on shared margin axes (survival-relevant `strength`, `deflection`, plus `wall`, `od`, `fit`), 0 dashed, current design marked.
  - Cell 3 (mast step margin lines): `step_x` sweep and `gap` sweep with `lead`, `survival`, `stability_range`, `air_draft`, `mast_len`.
  - A "what binds" table: the current design's margins, tightest first.
  - A `mo.ui.run_button` to recompute, so editing a widget does not trigger a long sweep by itself.

- [ ] **Step 1: Build the map cell**, assert the starred point's margins equal `evaluate(study_base)`.
- [ ] **Step 2: Build the two margin-line cells**, assert the marked point equals the base margins.
- [ ] **Step 3: Visual check.** In the live notebook, confirm the maps are not blank, the infeasible hatching sits on the side where the margin is negative, and the legend names every curve.

---

### Task 7: Documentation

**Files:**
- Modify: `NOTEBOOK_OVERVIEW.md`, `TODO.md`, `CLAUDE.md`

- [ ] **Step 1:** In `NOTEBOOK_OVERVIEW.md`, add the new inputs (Params and ranges), `evaluate`, `mast_loads`, `tube_response`, `rm_peak_fast`, `snap_tube`, and the study plots.
- [ ] **Step 2:** In `TODO.md`, record the uniform-tube simplification (the single-design cells still use the tapered tube), the approximations in `rm_peak_fast`, the placeholder limits and stock list, and that the sizing sweep and `mast_sweep` are now superseded.
- [ ] **Step 3:** In `CLAUDE.md`, add the new cross-cell names to the list and the rule that new limits are `Param`s.

---

## Self-review notes

- **Spec coverage:** design variables (Tasks 1, 2, 5), objectives and thresholds (Task 4), manufacturing limits and stock tubes (Tasks 2, 5), bulk (Tasks 4, 6), maps and margin lines (Task 6), open questions on cost and gap mapping (Tasks 1, 4; `step_dz` is the gap, "step height above hull top").
- **Builder's calls added here, not in the spec:** the study uses a **uniform tube**, whereas the existing single-design cells taper the tube with the chord. Mast length is `span + max(gap, 0)`. The fast righting moment is an interpolation approximation. The sweep runs from a run button.
- **Not covered:** the one-way all-up correction is still not iterated into resistance or loads; `evaluate` inherits this.
