# TODO

Open work on `notebooks/notebook.py`, as of the force balance / structural loads commit. Sorted by priority, then by topic. See `NOTEBOOK_OVERVIEW.md` for the inputs and outputs of each section.

## P1: Design results to resolve

The Design Summary at the current defaults (0.75 m^2 sail, aspect ratio 2.0, 30 kg hull, 1000 nm in 40 days, 3 / 12 / 45 kn winds) has two failures. The other twelve checks pass.

- **Survival heeling moment exceeds the righting moment.** About 187 N m against 155 N m with the rig (-21%). Check the locked-sail case, or add a feathering or reefing rule, and consider more ballast or a lower KG.
- **Minimum-wind speed fails.** The best speed at the 3 kn minimum wind is about 0.6 kn against 1.04 kn required (0.49 to 0.61 kn across the fairing range). Decide whether that wind needs to meet the required speed, or loosen the placeholder.
- **Everything else has wide margins.** Best design-wind speed is 2.6 kn, the slowest speed from TWA 90 deg aft is 2.2 kn, and the CE-CLP lead has the thinnest margin of the passes (+13%). The margins are large partly because the 1.04 kn required speed (1000 nm in 40 days) is much easier than the earlier 3000 nm crossing, so check the distance before relying on them.

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
- **Fairing spread is large.** Best speed at the 3 kn minimum wind runs from about 0.49 kn (unfaired) to 0.61 kn (0.45 m), and at the design wind from 2.45 to 2.65 kn, so the stern treatment matters most at low wind.

## P3: Model fidelity (known simplifications)

- **Post-stall polar is an extrapolation.** Beyond 30 deg the sail polar is a Viterna-Corrigan model matched to NeuralFoil at 30 deg. Compare against wind-tunnel or CFD data if the run and broad-reach results matter. The slowest-speed row (TWA 90 deg aft) depends on it.
- **Sail forces are not reduced for heel.** Beyond the `cos(phi)` terms, nothing accounts for it.
- **Leeway is not fed back into the apparent wind.** Leeway is also capped at 12 deg.
- **Sea state, wave added resistance, trim, sinkage and rudder drag are ignored.**
- **Fin side force uses an assumed end-plate factor.** `arf_in` (1.3) sets leeway and induced drag, and it is a guess between 1 and 2. The hull's own side force is ignored.
- **Elliptical spanwise loading** is assumed for both the heeling arm and the structural loads. A low-aspect-ratio sail near a deck may load differently.
- **Sail sizing sweep is one wind angle.** It runs at a single TWA (120 deg default) and does not recompute rig mass.

## P4: Unfinished sections

- **Sail sizing sweep does not recompute rig mass.** The speed sweep ignores it. The Mast Sizing section gives the lightest spar for each area, but skin and fixed mass are not added to the sweep.
- **Gust response and motor torque limits** are not modelled in the drivetrain section.

## P5: Placeholder inputs to replace

Replace these once the real mission and weight budget exist.

- **Weights and CG:** `mass_in` (30 kg), `kg_in`, `lcg_in`, `tcg_in`, `fixed_in`.
- **Structure:** material strength, modulus, density, skin density, safety factor, `CN_lock`, minimum wall.
- **Limits and environment:** the air-draft limit (5 m), the 3 / 12 / 45 kn wind states, the crossing distance and time (1000 nm in 40 days; the earlier default was 3000 nm).
- **Downflooding point:** `dfy_in`, `dfz_in` (0, 0.78 m) is a guess, and it sets the usable stability range that the heel limit is checked against.
- **Drivetrain:** gear ratio, efficiency, bearing and seal friction, and the motor and gearbox ratings are generic until real parts are chosen.

## P6: Housekeeping

Resolved: `README.md` rewritten, project `CLAUDE.md` covers the new sections and cross-cell names, and `NOTEBOOK_OVERVIEW.md` updated for the P2 changes (keep it in step with the notebook when inputs change).

- **Unused outputs.** The freeboard table and `R_req` are not read by any later cell. Keep them as documentation, or hook them into the Design Summary.
- **Fresh-run check.** Run `marimo edit --sandbox notebooks/notebook.py` from scratch to confirm the pinned dependencies resolve and every cell works. There is no test setup, so this is the only check.
