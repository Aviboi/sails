# Transatlantic Sail: calculations

**CUSail · Sails subsystem · Avram Dreyer**

Engineering calculations for the transatlantic rigid sail, kept as a single [marimo](https://marimo.io) notebook. The notebook is both the calculation and its documentation, so the same code is used to find results and to present them.

## Repository layout
- `notebooks/notebook.py`: the marimo notebook (hull import, hydrostatics, GZ curve).
- `data/`: STL geometry used by the notebook (currently `Hull Form.STL`).

## Running the notebook
Requires Python 3.9+ and [`uv`](https://docs.astral.sh/uv/) or `pip` with `marimo`. The notebook has an inline (PEP 723) dependency header, so it must always be run in sandbox mode to get the pinned dependencies (marimo, numpy, scipy, matplotlib, plotly, shapely, trimesh, networkx, mapbox-earcut):

```
marimo edit --sandbox notebooks/notebook.py
```

When working with Claude Code, always use the `/marimo-pair` skill to edit the notebook through the live session rather than editing `notebook.py` on disk.

## Notes
- Coordinates: x forward (bow +x), y to port, z up, metres. Imported STLs are converted into this frame.
- Meshes must be watertight for volume and centroid results to be valid; the notebook warns when they aren't.
- Keel and rudder geometry sections are still placeholders.
