# TODO

Open work on `notebooks/notebook.py`, as of the force balance / structural loads commit. Sorted by priority, then by topic. See `NOTEBOOK_OVERVIEW.md` for the inputs and outputs of each section.

## P1: Design results to resolve

The Design Summary section reported these against a 1.5 m^2 sail. The notebook default is now 0.65 m^2, so re-run and refresh the numbers below before acting on them.

- **Survival knockdown margin is 2%.** The survival heeling moment (about 401 N m, sail locked beam-on) is close to the peak righting moment (about 409 N m). Check the locked-sail case, or add a feathering or reefing rule, and consider more ballast or a lower KG.
- **Downwind speed fails.** The slowest speed from TWA 90 deg aft is about 2.6 kn against 3.1 kn required. The "TWA 90 deg and aft" row in the summary is my own criterion, so keep or drop it depending on the real route.
- **Minimum-wind speed fails.** The best speed at the 6 kn minimum wind is about 1.5 kn. Decide whether that wind needs to meet the required speed, or loosen the placeholder.
- **Best design-wind speed is marginal.** About 3.3 kn against 3.1 kn required, around 6% over.

## P2: Model correctness and consistency

Resolved in this pass (kept short for reference):

- **Keel and rudder labelling.** The hull was imported unflipped, so the bow pointed to -x and the "rudder" sat toward the wrong end. The hull importer now flips by default (`flip=True` for the hull form), and fins are sorted and labelled by area (keel is the larger), not by position. Keel at x = 0.93 m, rudder at x = 0.35 m.
- **Draft, mass and displaced volume.** `draft_in` is gone. `draft` is solved from `mass_in` (hull mass, no rig) with `solve_draft`, so resistance, windage and stability share one waterline. The mass, KG, LCG and TCG inputs moved up to the Hydrostatics section.
- **Total mass and CG.** A new "All-up mass and stability" cell after the structural loads adds the rig (spar + skin at the sail centroid, fixed allowance at the step) to the hull, recomputes the GZ curve and reports the shift in draft, GM and righting moment. The Design Summary survival row now uses it. It is a one-way correction: resistance, the force balance and the structural loads still use the hull-only waterline and righting moment.
- **Hull windage.** The hull's frontal and side areas are now in the force balance (drag, side force and heeling moment, with placeholder drag coefficients 0.6 and 1.0) and in the survival heeling moment. At the design wind the effect is under 2% of speed and 0.2 deg of heel; in survival it adds about 8 N m.
- **Transom fairing.** A sensitivity cell reruns the sweeps with 0 m and 0.45 m fairing, and the Design Summary shows the range beside the three speed rows.
- **Exactly two fins.** The guard stays, with a message that explains the cause. `hull_shell` gives two fins for thresholds of about 3% to 20%, so the 5% default is not fragile, but it fails below about 3%.

Still open:

- **Hull windage drag coefficients** (`hull_cdf_in`, `hull_cds_in`) are guesses.
- **The all-up correction is not iterated.** If the rig mass becomes large, move the draft and righting moment into the structural loads.
- **Fairing spread is large.** Best speed at the 6 kn minimum wind runs from about 0.8 kn (unfaired) to 1.8 kn (0.45 m), so the minimum-wind result depends mostly on the stern treatment.

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
