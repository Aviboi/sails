# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Engineering calculations for a transatlantic rigid sail (CUSail), kept as a single marimo notebook, `notebooks/notebook.py`. The notebook is meant to be both the calculation and its documentation, so code cells should stay short enough to sit under explanatory markdown cells. There is no build, lint or test setup.

Related docs: `README.md` (overview and how to run), `NOTEBOOK_OVERVIEW.md` (every input and output, and what depends on what) and `TODO.md` (open work by priority). Update `NOTEBOOK_OVERVIEW.md` and `TODO.md` when a change affects them.

## Running

**Always run the notebook in sandbox mode.** It has a PEP 723 dependency header, and without `--sandbox` the pinned dependencies are ignored:

```
marimo edit --sandbox notebooks/notebook.py
```

**Always use the `/marimo-pair` skill** to inspect or change the notebook. Invoke it before touching `notebook.py`, and make changes through the live session (using `marimo._code_mode`), letting marimo save. Don't edit `notebook.py` on disk while a marimo session is running, because the kernel owns the file and will overwrite it.

## Conventions and architecture

- **Inputs:** all defaults are set in the Inputs section at the top of the notebook, in five cells named `design`, `requirements`, `estimates`, `assumptions` and `constants`, each a `Group` of `Param(value, unit, note)`. Widgets stay next to their calculations and take `value=group.name.value`; never hard-code a default in a widget or a magic number in a calculation, add a `Param` instead. Pick the group by what the number is: a free choice (design), an acceptance criterion (requirements), a value we don't know yet (estimates), a modelling or environment choice (assumptions), or a fixed physical value (constants, not a widget). The `inputs_drift` cell lists widgets that differ from their defaults.

- **Coordinate convention:** x forward (bow +x), y to port, z up, metres. `load_geometry` converts every imported STL into this frame (scale, then SolidWorks Y-up to Z-up if selected, then optional 180° flip, then recentering to x=0 at stern, y=0 on centerline, z=0 at keel).
- **Geometry import:** `geometry_form(name, filename, center=True)` returns one `mo.ui.dictionary` holding all import settings, and `load_geometry(form)` turns it into a trimesh (or `None` if nothing was chosen). The STL (`data/Hull Form.STL`) is a single solid containing hull, keel and rudder, so there is one form/load pair and one mesh, `hull`; there are no separate keel or rudder imports. Recentering puts z=0 at the keel tip, so all heights (waterline, KG, VCB) are measured from the keel tip, and the hull shell itself only starts partway up. STL files live in `data/`.
- **Hydrostatics:** `hydrostatics(hull, draft, heel, trim, rho, pivot_z)` rotates the hull about a midship centerline pivot, slices at z = draft with `slice_plane(cap=True)`, and takes the waterplane from `waterplane_props` (shapely, even-odd loops, exact ring-integral inertias). Centre of buoyancy is returned both in earth and hull-fixed frames.
- **GZ curve:** `gz_curve` holds displacement constant and solves the waterline height per heel angle with `brentq` on `submerged_volume`, pivoting at keel level (`pivot_z=0`), so draft here is waterline height rather than the "draft at midship" input used for single-point hydrostatics. GZ is the y-offset of the hull-fixed CG from the centre of buoyancy.
- **Keel and rudder:** the hull importer flips by default (`flip=True`) so the bow points to +x. `hull_shell` splits the body into shell and exactly two fins, labelled by area (the larger is the keel), not by position. The notebook guards on exactly two fins.
- **Draft and mass:** `mass_in` is the hull mass without the rig. `draft` is solved from it with `solve_draft`, so resistance, windage and stability share one waterline; there is no draft input.
- **Sections after hydrostatics:** environment and constraints, hydrodynamic forces, wing-sail aerodynamics, force balance, structural loads, an all-up mass and stability cell, the mast drivetrain, then the Design Summary.
- **Cross-cell names:** `sail` (planform), `sp` (finite-span polar), `make_rig` and `rig0` (sail-force model), `heel_for`, `balance` and `best_trim` (force balance and trim solve), `sail_runs` (results by wind state and TWA), `hull_wind` (hull windage areas), `taper_band` (transom-fairing sensitivity), `rig_for` (rebuilds a rig for another area and aspect ratio, used by the sizing sweep), `struct` (structural load cases), `rig_mass`, `skin_mass`, and `total_mass`, `cg_all`, `rm_peak_all`, `surv_moment` (all-up correction). The all-up correction is one-way: resistance, the force balance and the structural loads keep the hull-only waterline and righting moment.
- The meshes must be watertight for volume and centroid results to be valid. The notebook shows a callout when they aren't.
