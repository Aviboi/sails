# Transatlantic Sail: calculations

**CUSail · Sails subsystem · Avram Dreyer**

Engineering calculations for the transatlantic rigid sail, kept as a single [marimo](https://marimo.io) notebook. The notebook is both the calculation and its documentation, so the same code is used to find results and to present them.

The notebook imports the hull STL and computes hydrostatics and stability. It then designs a NACA 00xx wing sail, balances sail force against hull and appendage force across the points of sail, sizes the mast structure and drivetrain motor, and ends with a PASS / MARGINAL / FAIL design summary against the crossing requirements.

## Repository layout
- `notebooks/notebook.py`: the marimo notebook.
- `data/`: STL geometry used by the notebook (`Hull Form.stl`, a single solid holding hull, keel and rudder).
- `NOTEBOOK_OVERVIEW.md`: every input and calculated value, grouped by role, with what depends on what.
- `TODO.md`: open work, sorted by priority.
- `CLAUDE.md`: guidance for Claude Code working in this repository.

## Notebook sections
1. Geometry import, hydrostatics (draft solved from the hull mass), GZ curve, stability limits, inertias and added mass, mast step.
2. Environment and constraints: wind states, crossing target, design limits.
3. Hydrodynamic forces: calm-water resistance, Michell wave resistance, keel and rudder side force.
4. Wing-sail aerodynamics: planform, section data (NeuralFoil), finite-span and post-stall corrections, centre of effort and mast torque.
5. Force balance and heel across the points of sail, including hull windage, a transom-fairing sensitivity, and a sail sizing sweep.
6. Structural loads, then an all-up mass and stability correction that adds the rig to the hull.
7. Mast drivetrain and motor sizing.
8. Design Summary.

## Running the notebook
Requires [`uv`](https://docs.astral.sh/uv/) or `pip` with `marimo`. The notebook has an inline (PEP 723) dependency header, so it must always be run in sandbox mode to get the pinned dependencies (marimo, numpy, scipy, matplotlib, plotly, shapely, trimesh, networkx, mapbox-earcut, neuralfoil, rtree):

```
marimo edit --sandbox notebooks/notebook.py
```

When working with Claude Code, use the `/marimo-pair` skill to edit the notebook through the live session rather than editing `notebook.py` on disk.

## Notes
- Coordinates: x forward (bow +x), y to port, z up, metres. Imported STLs are converted into this frame, with z = 0 at the keel tip.
- Meshes must be watertight for volume and centroid results to be valid; the notebook warns when they aren't.
- Many inputs are placeholders (weights, wind states, structure, drivetrain ratings). `TODO.md` lists them under P5.
- There is no build, lint or test setup. Running the notebook from scratch is the only check.
