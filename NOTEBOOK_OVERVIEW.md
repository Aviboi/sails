# Overview of `notebooks/notebook.py` (2735 lines)

The notebook runs in one chain. It imports a hull STL and computes hydrostatics, stability and added mass. Then it designs a wing sail, balances sail force against hull force, sizes the structure and motor, and ends with a pass/fail summary.

## 1. Inputs

### A. Geometry and file inputs
| Input | Default | Notes |
|---|---|---|
| `hull_form` (file or path, units, axes, flip, recenter) | `data/Hull Form.STL`, mm, Z-up, recenter | The only CAD input. It is a single solid containing hull, keel and rudder. |

### B. Design decisions (free choices)
| Input | Default | Used by |
|---|---|---|
| `sail_area_in` S | 0.65 m² | Sail planform, forces, structure, mass |
| `sail_ar_in` | 1.75 | Planform, span (must fit under the air-draft limit) |
| `sail_taper_in` | 1.0 | Planform, Glauert e |
| `sail_tc_in` | 12 (NACA 0012) | Section polar, mast diameter, skin mass |
| `sail_mast_in` | 0.25 chord | Mast torque, helm, mast tube size |
| `step_x_in`, `step_y_in`, `step_dz_in` | 1.0 m, 0, 0 | Mast step position; sets sail height, lead and heeling arm |
| `twa_min_in`, `twa_step_in` | 40°, 10° | Which points of sail are swept |
| `sweep_twa_in` | 120° | TWA used in the sail-sizing sweep |
| `gear_in`, `eta_in` | N=100, η=0.75 | Gearbox choices (η is really an estimate) |
| `slew_in`, `acc_t_in` | 10°/s, 1 s | Required sail slew performance |
| `bspan_in` | 0.3 m | Bearing spacing |
| `mcont_in`, `mpeak_in`, `mrpm_in`, `km_in`, `gbox_in` | 0.10 / 0.30 N·m, 3000 rpm, 0.03, 30 N·m | Motor and gearbox ratings. These are generic placeholders until real parts are chosen. |
| `dfrac_in` | 0.8 | Mast OD as a fraction of section thickness |
| `maxheel_in`, `maxlead_in`, `maxrig_in`, `airdraft_in`, `dist_in`, `days_in` | 25°, 0.10 LWL, 25 kg, 5 m, 3000 nm, 40 d | These act as **requirements** (the acceptance criteria). The air-draft limit is a flagged placeholder. |
| `taper_in` (transom fairing) | 0.2 m | A modelling choice that strongly affects wave resistance. The notebook plots the 0–0.45 m band. |
| `draft_in` | 0.668 m | The operating waterline. It could also be called a derived quantity, because it should match mass/ρ. |

### C. Estimates or placeholders (weight and physical guesses)
| Input | Default |
|---|---|
| `mass_in` | 80 kg |
| `kg_in` | 0.15 m |
| `lcg_in`, `tcg_in` | 1.1 m, 0 |
| `kxx_in`, `kyy_in`, `kzz_in` | 0.35 B, 0.25 L, 0.25 L |
| `dfy_in`, `dfz_in` (downflooding point) | 0, 0.78 m |
| `fixed_in` (motor, bearing and plate mass) | 2 kg |
| `skin_in` | 0.8 kg/m² |
| `tmin_in` | 0.6 mm |
| `mu_in`, `seal_in` | 0.005, 0.5 N·m |
| `sigma_in`, `emod_in`, `rho_mat_in` | 500 MPa, 70 GPa, 1600 kg/m³ (carbon tube) |
| `sf_in` (strength safety factor) | 2.0 |
| `tsf_in` (torque safety factor) | 2.0 |
| `cn_lock_in` | 1.2 |
| `vmin_in`, `vdes_in`, `vsurv_in` | 6 / 15 / 45 kn (environmental design assumptions) |

### D. Modelling assumptions and parameters
These are physical or empirical coefficients that you can tune.
- **Environment:** `air_temp_in` (15 °C), `pressure_in` (1013 hPa), `zref_in` (10 m), `alpha_in` (shear exponent 0.11), `rho_in` (sea water 1025), `nu_in` (1.19e-6), `dcf_in` (roughness 0.0003), `vmax_in` (display range).
- **Heel and trim:** `heel_in` and `trim_in` are single-point hydrostatics settings. `heelmax_in` and `heelstep_in` set the GZ sweep.
- **End-plate factors:** `arf_in` (fins, 1.3) and `sail_arf_in` (sail, 1.0).
- **Hardcoded constants:**
  - Gravity: 9.80665.
  - Knot: 0.514444 m/s.
  - Gas constant: 287.05.
  - Sutherland's law constants.
  - Surge added mass: 5% of displacement.
  - Leeway cap: 12°.
  - Viterna `CD_max = 1.11 + 0.018 AR`.
  - `hull_shell` threshold: `frac = 0.05`.
  - Fin thickness factor: `1 + 2 t/c + 60 (t/c)^4`.
  - Fin sample points: root and tip chord read at 90% and 10% of span.
  - Michell grid and integration limits.
  - Summary margin threshold: 10%.
  - Deflection limit: 10% of span.
  - Alpha grids.

## 2. Calculated values

Grouped by area, with a flag for whether later cells use them and whether they are critical.

### Geometry and hydrostatics
| Output | Used downstream | Critical |
|---|---|---|
| `hull` mesh | Everything | **Yes** |
| `hull_body`, `hull_body_z` (shell, and the cut height separating shell from fins) | Fin split, form coefficients, added mass | Yes |
| `hs` (volume, mass, CB, waterplane, wetted area, BMt, BML, KMt, Cb, Cwp) | Form, resistance, GM, helm and the other later cells | **Yes** |
| `up` (shell wetted area, `fins` list, CLP, lateral area) | Resistance, fin forces, heel arm, helm | **Yes**, and fragile: it expects exactly 2 fins |
| `form` (Cm, Cp, LCB%, half-angle of entrance, LWL) | Holtrop form factor | Yes |
| `air_side`, `air_front`, `fb_top`, `fb_x` | Mast step height (`fb_*`), step plot (`air_side`) | Medium. `air_front` and the freeboard table are only reported. |
| `mast_step` | Sail height, heeling arm, rig height available | **Yes** |

### Stability
| Output | Used downstream | Critical |
|---|---|---|
| `gz_heel`, `gz_val`, `gz_draft` | Downflooding, heel solve (via `rm_val`), summary | **Yes** |
| `use_angle`, `df_angle`, `avs_angle` | Constraints table, summary | **Yes** (limits the usable heel range) |
| GM table, MCT1cm, GM-from-slope | Report only | Informational |

### Dynamics (report only)
These are `k_solid`, `k_buoy`, `I_dry`, the added masses `am`, `A11`, and the roll period. No downstream cell uses them. They are all marked as estimates and are the least critical block.

### Environment
- `rho_air`, `wind_states`, `wind_at`, `KNOT`: used almost everywhere. Critical.
- `v_req`: the required speed (3000 nm / 40 d = 3.1 kn). It is the headline requirement.

### Hydrodynamics
- `hull_form_factor`, `calm_resistance`, `mich_*`, `total_resistance`: Critical. `res_R` is the resistance curve for the speed solve.
- **`R_req`**: not used later. It is a headline number, but the sensitive part is the wave term, which depends on `taper_in`.
- `appendage_side_force`: Critical. It sets leeway and induced drag.

### Aerodynamics
- `sail` (planform), `sec`/`sec_ref`, `re_sail`, `v_sail`, `sail_z`, `sp` (finite-span polar): Critical. Everything in the force balance is built from these.
- `sail_cn`, `sail_ce_height`, `mast_torque`, `v_surv`: used by the structure and drivetrain.
- `nu_air`: used in the sizing sweep.

### Force balance
- `rig0`, `rm_val`, `heel_for`, `balance`, `best_trim`, `helm`: the core solver.
- **`sail_runs`**: Critical. It holds speed, heel and lead by TWA, and the summary reads it directly.
- `sweep`: a trade study (area × AR). It is not used later, but it informs the sail-size decision.

### Structure and drivetrain
| Output | Used downstream | Critical |
|---|---|---|
| `struct` (loads, wall, deflection, spar mass, heeling moment) | Drivetrain friction, summary | **Yes** |
| `rig_mass`, `skin_mass` | Drivetrain, summary | **Yes** |
| `mast_D`, `span_z` | Friction radius, plots | Medium |
| `drive` (hold, peak and survival torque, motor torques, rpm, power) | Summary | **Yes** |

### Final outputs (all in the Design Summary)
There are 14 PASS / MARGINAL / FAIL checks:
- Speed: best at design wind, slowest at TWA ≥ 90°, best at minimum wind.
- Heel: peak steady heel, and the heel limit against the usable stability range.
- Helm: peak CE–CLP lead.
- Rig: mass, and span against the air-draft limit.
- Survival: heeling moment, and tip deflection.
- Drivetrain: motor continuous torque, motor peak torque, motor speed, gearbox rating.

## 3. Things worth knowing about the data flow

- **The input the final answer depends on most:** the sail area, aspect ratio, mast step, `mass_in`/`kg_in`, and the three wind speeds.
- **Consistency gaps between inputs:**
  - `draft_in` (0.668 m), `mass_in` (80 kg) and the hull's displaced volume are independent inputs. `draft_in` isn't forced to match the mass. The GZ curve solves the waterline from mass, but the resistance and wetted area use `draft_in`.
  - `lcg_in` and `kg_in` are single placeholders. The rig mass and motor mass don't feed back into them.
  - The hull mass and the rig mass computed in the structure section are never combined into a total.
- **Cells that report values nothing else uses:** the dynamics block, `air_front`, the freeboard table, `R_req`, and `sweep`.
- **Weakest assumptions that drive critical outputs:**
  - `taper_in` (wave resistance).
  - The 12° leeway cap and the end-plate factors (`arf_in`, `sail_arf_in`).
  - The post-stall Viterna extension past 30° (sail runs at TWA > 90°).
  - The minimum wind is only 6 kn.
  - The 5 m air-draft limit.
  - Elliptical lift loading, used for both the heeling arm and the structure.
- **Not modelled** (the notebook says so): torsion and buckling, sea state and added resistance, rudder drag, trim and sinkage, and the flap or tail control (listed as To do).
