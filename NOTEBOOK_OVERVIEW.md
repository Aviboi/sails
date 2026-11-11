# Overview of `notebooks/notebook.py` (3712 lines)

The notebook runs in one chain. It imports a hull STL and computes hydrostatics and stability. Then it designs a wing sail, balances sail force against hull force, sizes the structure and motor, and ends with a pass/fail summary.

## 1. Inputs

Every default lives in the **Inputs** section near the top of the notebook, in five cells (`design`, `requirements`, `estimates`, `assumptions`, `constants`). Each entry is a `Param(value, unit, note)`. The widgets in the tables below (`*_in`) sit next to their calculations and take their default from those cells, so edit the default there to make it persist across kernel restarts; a value changed in a widget only lasts for the session. The drift table at the end of the Inputs section lists the widgets that currently differ from their defaults. The groups below are the same as the five cells, except that the file-import settings (`hull_file`, `hull_units`, `hull_axes`, `hull_flip`, `hull_center`) live in `design`, and the summary margin flag (10%) and the survival deflection limit (10% of span) live in `requirements`. Empirical modelling coefficients that used to be hard-coded (leeway cap, Viterna `CD_max` coefficients, polar switch angle, `hull_shell` fraction) are in `assumptions`, and fixed physical values (gravity, knot, gas constant, Sutherland constants) are in `constants`, not widgets.

### A. Geometry and file inputs
| Input | Default | Notes |
|---|---|---|
| `hull_form` (file or path, units, axes, flip, recenter) | `data/Hull Form.stl`, mm, Z-up, flip, recenter | The only CAD input. It is a single solid containing hull, keel and rudder. The hull form flips by default so the bow points to +x. |

### B. Design decisions (free choices)
| Input | Default | Used by |
|---|---|---|
| `sail_area_in` S | 0.75 m² | Sail planform, forces, structure, mass |
| `sail_ar_in` | 2.0 | Planform, span (must fit under the air-draft limit) |
| `sail_taper_in` | 1.0 | Planform, Glauert e |
| `sail_tc_in` | 12 (NACA 0012) | Section polar, mast diameter, skin mass |
| `sail_mast_in` | 0.24 chord | Mast torque, helm, mast tube size |
| `step_x_in`, `step_y_in`, `step_dz_in` | 1.0 m, 0, 0 | Mast step position; sets sail height, lead and heeling arm |
| `twa_min_in`, `twa_step_in` | 40°, 10° | Which points of sail are swept |
| `sweep_twa_in` | 120° | TWA used in the sail-sizing sweep |
| `gear_in`, `eta_in` | N=100, η=0.75 | Gearbox choices (η is really an estimate) |
| `slew_in`, `acc_t_in` | 10°/s, 1 s | Required sail slew performance |
| `bspan_in` | 0.3 m | Bearing spacing |
| `mcont_in`, `mpeak_in`, `mrpm_in`, `km_in`, `gbox_in` | 0.10 / 0.30 N·m, 3000 rpm, 0.03, 30 N·m | Motor and gearbox ratings. These are generic placeholders until real parts are chosen. |
| `dfrac_in` | 0.8 | Mast OD as a fraction of section thickness |
| `maxheel_in`, `maxlead_in`, `maxrig_in`, `airdraft_in`, `dist_in`, `days_in` | 25°, 0.10 LWL, 25 kg, 5 m, 1000 nm, 40 d | These act as **requirements** (the acceptance criteria). The air-draft limit is a flagged placeholder. |
| `taper_in` (transom fairing) | 0.2 m | A modelling choice that strongly affects wave resistance. The notebook plots the 0–0.45 m band. |

### C. Estimates or placeholders (weight and physical guesses)
| Input | Default |
|---|---|
| `mass_in` (hull mass, no rig) | 30 kg |
| `kg_in` | 0.125 m |
| `lcg_in`, `tcg_in` | 0.94 m, 0 |
| `dfy_in`, `dfz_in` (downflooding point) | 0, 0.78 m |
| `fixed_in` (motor, bearing and plate mass) | 2 kg |
| `skin_in` | 0.8 kg/m² |
| `tmin_in` | 0.6 mm |
| `mu_in`, `seal_in` | 0.005, 0.5 N·m |
| `sigma_in`, `emod_in`, `rho_mat_in` | 500 MPa, 70 GPa, 1600 kg/m³ (carbon tube) |
| `sf_in` (strength safety factor) | 2.0 |
| `tsf_in` (torque safety factor) | 2.0 |
| `cn_lock_in` | 1.2 |
| `hull_cdf_in`, `hull_cds_in` (hull windage drag, frontal and side) | 0.6, 1.0 (guesses) |
| `vmin_in`, `vdes_in`, `vsurv_in` | 3 / 12 / 45 kn (environmental design assumptions) |

### D. Modelling assumptions and parameters
These are physical or empirical coefficients that you can tune.
- **Environment:** `air_temp_in` (15 °C), `pressure_in` (1013 hPa), `zref_in` (10 m), `alpha_in` (shear exponent 0.11), `rho_in` (sea water 1025), `nu_in` (1.19e-6), `dcf_in` (roughness 0.0003), `vmax_in` (10 kn, display range and resistance-table grid).
- **Waterline:** there is no draft input. `draft` is solved from `mass_in` and `rho_in` by `solve_draft`.
- **Heel and trim:** `heel_in` and `trim_in` are single-point hydrostatics settings. `heelmax_in` and `heelstep_in` set the GZ sweep.
- **End-plate factors:** `arf_in` (fins, 1.3) and `sail_arf_in` (sail, 1.0).
- **Hardcoded constants:**
  - Gravity: 9.80665.
  - Knot: 0.514444 m/s.
  - Gas constant: 287.05.
  - Sutherland's law constants.
  - Leeway cap: 12°.
  - Viterna `CD_max = 1.11 + 0.018 AR`.
  - `hull_shell` threshold: `frac = 0.05`.
  - Fin thickness factor: `1 + 2 t/c + 60 (t/c)^4`.
  - Fin sample points: root and tip chord read at 90% and 10% of span.
  - Michell grid and integration limits.
  - Summary margin threshold: 10%.
  - Deflection limit: 10% of span.
  - Alpha grids.

### E. Design study inputs
New `Param`s read directly from the groups (no widgets, so the drift table does not list them).

| Input | Group | Default | Used by |
|---|---|---|---|
| `area_range`, `ar_range`, `step_x_range`, `gap_range` | design | (0.4, 2.0) m², (1.5, 4.0), (0.6, 1.6) m, (0.0, 0.3) m | Sweep ranges of the study |
| `od_max`, `mast_len_max`, `area_max`, `mass_max` | requirements | 60 mm, 2.5 m, 3.0 m², 60 kg | Manufacturing and mass thresholds (all placeholders) |
| `tube_stock` | assumptions | 16 (OD, ID) pairs, 20 to 60 mm | Stock carbon tube sizes (placeholder range, no supplier list yet) |
| `cb_table_n` | assumptions | 6 | Masses in the buoyancy-centre table behind the fast righting moment |
| `study_points_map`, `study_points_line` | assumptions | 12, 9 | Points per axis on a map, and per margin-line sweep |
| `study_twa_step` | assumptions | 20° | True-wind-angle step inside each evaluation (10° is 2.5x slower, within about 1.5% of speed) |

## 2. Calculated values

Grouped by area, with a flag for whether later cells use them and whether they are critical.

### Geometry and hydrostatics
| Output | Used downstream | Critical |
|---|---|---|
| `hull` mesh | Everything | **Yes** |
| `draft` (waterline solved from `mass_in`) | Resistance, windage, stability, sail height | **Yes** |
| `hull_body`, `hull_body_z` (shell, and the cut height separating shell from fins) | Fin split, form coefficients | Yes |
| `hs` (volume, mass, CB, waterplane, wetted area, BMt, BML, KMt, Cb, Cwp) | Form, resistance, GM, helm and the other later cells | **Yes** |
| `up` (shell wetted area, `fins` list, CLP, lateral area) | Resistance, fin forces, heel arm, helm | **Yes**, and fragile: it expects exactly 2 fins, labelled by area (keel is the larger). The 5% threshold gives two fins for about 3% to 20%. |
| `form` (Cm, Cp, LCB%, half-angle of entrance, LWL) | Holtrop form factor | Yes |
| `air_side`, `air_front`, `fb_top`, `fb_x` | Mast step height (`fb_*`), step plot (`air_side`) | Medium. `air_front` feeds `hull_wind` (windage drag); the freeboard table is only reported. |
| `hull_wind` (hull frontal and side areas, waterline height, heeling arm) | Force balance, survival heeling moment | Medium |
| `mast_step` | Sail height, heeling arm, rig height available | **Yes** |

### Stability
| Output | Used downstream | Critical |
|---|---|---|
| `gz_heel`, `gz_val`, `gz_draft` | Downflooding, heel solve (via `rm_val`), summary | **Yes** |
| `use_angle`, `df_angle`, `avs_angle` | Constraints table, summary | **Yes** (limits the usable heel range) |
| GM table, MCT1cm, GM-from-slope | Report only | Informational |

### Environment
- `rho_air`, `wind_states`, `wind_at`, `KNOT`: used almost everywhere. Critical.
- `v_req`: the required speed (1000 nm / 40 d = 1.04 kn). It is the headline requirement.

### Hydrodynamics
- `hull_form_factor`, `calm_resistance`, `mich_*`, `total_resistance`: Critical. `res_R` is the resistance curve for the speed solve.
- **`R_req`**: not used later. It is a headline number, but the sensitive part is the wave term, which depends on `taper_in`.
- `appendage_side_force`: Critical. It sets leeway and induced drag.

### Aerodynamics
- `sail` (planform), `sec`/`sec_ref`, `re_sail`, `v_sail`, `sail_z`, `sp` (finite-span polar): Critical. Everything in the force balance is built from these.
- `sail_cn`, `sail_ce_height`, `mast_torque`, `v_surv`: used by the structure and drivetrain.
- `nu_air`: used in the sizing sweep.

### Force balance
- `rig0`, `make_rig`, `rm_val`, `heel_for`, `balance`, `best_trim`, `helm`: the core solver. `balance` includes hull windage (drag, side force, heeling moment).
- **`sail_runs`**: Critical. It holds speed, heel and lead by TWA, and the summary reads it directly.
- `taper_band`: the same sweeps at 0 m and 0.45 m transom fairing. The Design Summary shows the range beside the three speed rows.
- `sweep` (grid `sweep_areas`, `sweep_ars`) and `rig_for`: a trade study (area × AR) at one TWA. It does not recompute rig mass, is not used later, and informs the sail-size decision.

### Structure and drivetrain
| Output | Used downstream | Critical |
|---|---|---|
| `struct` (loads, wall, deflection, spar mass, heeling moment) | Drivetrain friction, summary | **Yes** |
| `rig_mass`, `skin_mass` | Drivetrain, all-up mass, summary | **Yes** |
| `total_mass`, `cg_all`, `rm_peak_all`, `surv_moment` (hull + rig, GZ recomputed, survival moment with hull windage) | Summary survival row | **Yes** |
| `mast_D`, `span_z` | Friction radius, plots | Medium |
| `mast_opt`, `mast_sweep` (lightest mast meeting the survival deflection limit, by sail area × AR, on the same grid as `sweep_areas`/`sweep_ars`) | Not used later; informs the mast size (`dfrac_in`) | No |
| `drive` (hold, peak and survival torque, motor torques, rpm, power) | Summary | **Yes** |

### Design study (after the Design Summary)
| Output | Used downstream | Critical |
|---|---|---|
| `step_at(x, dz, y)` (mast step vector, x clipped to the hull) | `mast_step`, `evaluate` | Yes |
| `make_rig(..., step)`, `rig_for(area, ar, step)`, `helm(r, rig, step)` (the same functions with an optional step) | Study, sizing sweeps | Yes |
| `mast_loads(rig, step)` (design and survival moments, root shear, heeling moment) | `mast_opt`, `evaluate` | Yes |
| `tube_response(moment, z, od, id_, gap, shear_root)` (uniform tube: stress, strength margin, deflection fraction, mass, wall) | `evaluate` | Yes |
| `cb_masses`, `cb_y`, `gz_fast`, `rm_peak_fast` (righting moment for any total mass and CG without re-slicing the hull; matches `gz_curve` to about 1e-5) | `evaluate` | Yes |
| `evaluate(d)` (one design in, 17 margins, raw values and flags out) | Study cells, `study_base` | **Yes** |
| `snap_tube`, `study_base` | Study cells | Medium |
| `map_*` (area × AR grid), `line_*` (tube and step sweeps) | Plots only | No |

The study shades the **objectives** (survival, deflection, strength, usable stability range) and applies the **thresholds** (speeds, total mass, wall, OD, mast length, sail area, air draft, tube fit) as contours with the failing side hatched. A "Run design study" button gates the sweeps (about two minutes).

### Final outputs (all in the Design Summary)
There are 14 PASS / MARGINAL / FAIL checks. The three speed rows also show the 0 to 0.45 m transom-fairing range:
- Speed: best at design wind, slowest at TWA ≥ 90°, best at minimum wind.
- Heel: peak steady heel, and the heel limit against the usable stability range.
- Helm: peak CE–CLP lead.
- Rig: mass, and span against the air-draft limit.
- Survival: heeling moment against the righting moment with the rig, and tip deflection.
- Drivetrain: motor continuous torque, motor peak torque, motor speed, gearbox rating.

## 3. Things worth knowing about the data flow

- **The input the final answer depends on most:** the sail area, aspect ratio, mast step, `mass_in`/`kg_in`, and the three wind speeds.
- **Consistency:**
  - Draft, mass and displaced volume are consistent: `draft` is solved from `mass_in` (hull only) and shared by resistance, windage and stability.
  - The all-up cell adds the rig to the hull and recomputes the GZ curve and survival margin, but it is one-way. Resistance, the force balance and the structural loads keep the hull-only waterline and righting moment. If the rig mass becomes large, move the correction upstream.
  - `lcg_in` and `kg_in` are single placeholders for the hull.
- **Cells that report values nothing else uses:** the freeboard table, `R_req`, `sweep` and `mast_sweep`.
- **Weakest assumptions that drive critical outputs:**
  - `taper_in` (wave resistance; best speed at the minimum wind swings by about 1 kn across the fairing band).
  - `hull_cdf_in`, `hull_cds_in` (hull windage drag).
  - The 12° leeway cap and the end-plate factors (`arf_in`, `sail_arf_in`).
  - The post-stall Viterna extension past 30° (sail runs at TWA > 90°).
  - The minimum wind is only 3 kn.
  - The 5 m air-draft limit.
  - Elliptical lift loading, used for both the heeling arm and the structure.
- **Not modelled** (the notebook says so): sea state and added resistance, rudder drag, trim and sinkage.
