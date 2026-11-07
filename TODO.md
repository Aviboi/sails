# TODO

Open work on `notebooks/notebook.py`, as of the force balance / structural loads commit. Sorted by priority, then by topic. See `NOTEBOOK_OVERVIEW.md` for the inputs and outputs of each section.

## P1: Design results to resolve

The Design Summary section reported these against a 1.5 m^2 sail. The notebook default is now 0.65 m^2, so re-run and refresh the numbers below before acting on them.

- **Survival knockdown margin is 2%.** The survival heeling moment (about 401 N m, sail locked beam-on) is close to the peak righting moment (about 409 N m). Check the locked-sail case, or add a feathering or reefing rule, and consider more ballast or a lower KG.
- **Downwind speed fails.** The slowest speed from TWA 90 deg aft is about 2.6 kn against 3.1 kn required. The "TWA 90 deg and aft" row in the summary is my own criterion, so keep or drop it depending on the real route.
- **Minimum-wind speed fails.** The best speed at the 6 kn minimum wind is about 1.5 kn. Decide whether that wind needs to meet the required speed, or loosen the placeholder.
- **Best design-wind speed is marginal.** About 3.3 kn against 3.1 kn required, around 6% over.

## P2: Model correctness and consistency

Things that could make the headline results wrong or inconsistent with each other.

- **Keel and rudder labelling.** `underwater_profile` sorts the fins fore to aft (descending x, bow is +x), so `keel_p, rudder_p = up["fins"]` makes the *most forward* fin the "keel". After the hull flip the larger fin (planform 0.16 m^2) sits at x about 1.0 m and the smaller (0.024 m^2) at x about 1.6 m, toward the bow. So that table names them the wrong way round, while the force balance picks them by planform area (larger = keel). Settle which is which, label the table by area, and check the rudder arm and rudder angle that depend on it.
- **Draft, mass and displaced volume are independent inputs.** `draft_in` (0.668 m) drives wetted area, resistance, wave-making, form coefficients and the windage split, while `mass_in` (80 kg) drives the GZ curve, which solves its own waterline per heel. Nothing forces the two to agree, so the resistance can be computed at a different waterline from the stability. Either solve `draft_in` from `mass_in` or add a check that flags a mismatch.
- **Total mass and CG are not built up.** The rig mass from Structural Loads (mast, skin, motor) is never added to `mass_in`, `kg_in` or `lcg_in`. A tall rig raises KG, which reduces GZ and the survival margin.
- **Exactly two fins are assumed.** `underwater_profile` stops the notebook if `hull_body_z` splits the underwater body into anything other than two pieces. This depends on the 5% waterplane-area threshold in `hull_shell`, so a CAD change could break every later cell.
- **Hull and rig windage are ignored in the force balance.** `air_side` and `air_front` are computed but never used, so there is no hull windage drag or heeling moment. The notebook text says so, but the effect is not quantified, and it matters most upwind and in the survival case.
- **Wave-making depends strongly on the transom fairing.** `taper_in` (0.2 m) moves the wave resistance at the required speed across a wide band (the plot shows 0 to 0.45 m). The force balance and the speed margin inherit that spread, so run the summary at both ends.

## P3: Model fidelity (known simplifications)

- **Post-stall polar is an extrapolation.** Beyond 30 deg the sail polar is a Viterna-Corrigan model matched to NeuralFoil at 30 deg. Compare against wind-tunnel or CFD data if the run and broad-reach results matter. The downwind failure above depends on it.
- **Sail forces are not reduced for heel.** Beyond the `cos(phi)` terms, nothing accounts for it.
- **Leeway is not fed back into the apparent wind.** Leeway is also capped at 12 deg.
- **Sea state, wave added resistance, trim, sinkage and rudder drag are ignored.**
- **Fin side force uses an assumed end-plate factor.** `arf_in` (1.3) sets leeway and induced drag, and it is a guess between 1 and 2. The hull's own side force is ignored.
- **Elliptical spanwise loading** is assumed for both the heeling arm and the structural loads. A low-aspect-ratio sail near a deck may load differently.
- **Sail sizing sweep is one wind angle.** It runs at a single TWA (120 deg default) and does not recompute rig mass.

## P4: Unfinished sections

- **Structural checks not done:** torsion from the mast torque, wall buckling (the wall is at the 0.6 mm minimum on a tube of about 60 to 90 mm), joints and fatigue, and the step attachment.
- **Flap or tail control** is listed as "To do" in the Wing-Sail Aerodynamics section.
- **Sail sizing sweep does not recompute rig mass.** Spar and rig mass are only computed for the current sail, so check any other sail against the Structural Loads section.
- **Gust response and motor torque limits** are not modelled in the drivetrain section.

## P5: Placeholder inputs to replace

Replace these once the real mission and weight budget exist.

- **Weights and CG:** `mass_in` (80 kg), `kg_in`, `lcg_in`, `tcg_in`, `fixed_in`.
- **Radii of gyration:** `kxx_in`, `kyy_in`, `kzz_in`. Only the dynamics block uses them, which no later cell reads.
- **Structure:** material strength, modulus, density, skin density, safety factor, `CN_lock`, minimum wall.
- **Limits and environment:** the air-draft limit (5 m), the 6 / 15 / 45 kn wind states, the crossing distance and time.
- **Downflooding point:** `dfy_in`, `dfz_in` (0, 0.78 m) is a guess, and it sets the usable stability range that the heel limit is checked against.
- **Drivetrain:** gear ratio, efficiency, bearing and seal friction, and the motor and gearbox ratings are generic until real parts are chosen.

## P6: Housekeeping

- **`README.md` is stale.** It refers to `notebooks/2_Calculations.py` and other notebooks that no longer exist.
- **Project `CLAUDE.md`** does not mention the new sections or the cross-cell names they define (`balance`, `best_trim`, `make_rig`, `rig_for`, `struct`, `rig_mass`).
- **`NOTEBOOK_OVERVIEW.md`** is new and uncommitted. It will go stale as inputs change, so update it with the notebook or fold it into the README rewrite.
- **Unused outputs.** The dynamics block, `air_front`, the freeboard table and `R_req` are not read by any later cell. Keep them as documentation, or hook them into the Design Summary.
- **Fresh-run check.** Run `marimo edit --sandbox notebooks/notebook.py` from scratch to confirm the pinned dependencies resolve and every cell works. There is no test setup, so this is the only check.
