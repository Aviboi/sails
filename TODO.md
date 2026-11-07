# TODO

Open work on `notebooks/notebook.py`, as of the force balance / structural loads commit.

## Design results to resolve

The Design Summary section currently shows these against the 1.5 m^2 sail:

- **Survival knockdown margin is 2%.** The survival heeling moment (about 401 N m, sail locked beam-on) is close to the peak righting moment (about 409 N m). Check the locked-sail case, or add a feathering or reefing rule, and consider more ballast or a lower KG.
- **Downwind speed fails.** The slowest speed from TWA 90 deg aft is about 2.6 kn against 3.1 kn required. The "TWA 90 deg and aft" row in the summary is my own criterion, so keep or drop it depending on the real route.
- **Minimum-wind speed fails.** The best speed at the 6 kn minimum wind is about 1.5 kn. Decide whether that wind needs to meet the required speed, or loosen the placeholder.
- **Best design-wind speed is marginal.** About 3.3 kn against 3.1 kn required, around 6% over.

## Open questions in the model

- **Keel and rudder labelling.** After the hull flip the larger fin (planform 0.16 m^2) sits at x about 1.0 m and the smaller (0.024 m^2) at x about 1.6 m, toward the bow. The force balance takes the larger as the keel and the smaller as the rudder. The older `keel_p, rudder_p = up["fins"]` cell may name them the other way round. Settle which is which, since the rudder arm and rudder angle depend on it.
- **Post-stall polar is an extrapolation.** Beyond 30 deg the sail polar is a Viterna-Corrigan model matched to NeuralFoil at 30 deg. Compare against wind-tunnel or CFD data if the run and broad-reach results matter.
- **Sail forces are not reduced for heel.** Beyond the `cos(phi)` terms, nothing accounts for it.
- **Leeway is not fed back into the apparent wind.**
- **Sea state, wave added resistance, trim, sinkage and rudder drag are ignored.**

## Unfinished sections

- **Structural checks not done:** torsion from the mast torque, wall buckling (the wall is at the 0.6 mm minimum on a tube of about 60 to 90 mm), joints and fatigue, and the step attachment.
- **Sail sizing sweep does not recompute rig mass.** Spar and rig mass are only computed for the current sail, so check any other sail against the Structural Loads section.
- **Placeholder inputs.** Material strength, modulus, density, skin density, safety factor, `CN_lock`, mass, KG, LCG and the air-draft limit are placeholders until the real mission and weight budget exist.

## Housekeeping

- **`README.md` is stale.** It refers to `notebooks/2_Calculations.py` and other notebooks that no longer exist.
- **Project `CLAUDE.md`** does not mention the new sections or the cross-cell names they define (`balance`, `best_trim`, `make_rig`, `rig_for`, `struct`, `rig_mass`).
- **Fresh-run check.** Run `marimo edit --sandbox notebooks/notebook.py` from scratch to confirm the pinned dependencies resolve and every cell works. There is no test setup, so this is the only check.
