# /// script
# dependencies = [
#     "mapbox-earcut==2.1.0",
#     "marimo>=0.25.2",
#     "matplotlib==3.11.2",
#     "networkx==3.7",
#     "numpy==2.5.4",
#     "plotly==7.1.0",
#     "rtree==1.4.1",
#     "scipy==1.18.1",
#     "shapely==2.2.0",
#     "trimesh==5.2.0",
# ]
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import io
    import pathlib

    import matplotlib.pyplot as plt
    import numpy as np
    import plotly.graph_objects as go
    import trimesh


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Sails Calculations
    This notebook contains my main calculations for the transatlantic rigid sail. My goals are to have a centralized and easily-editable and reproducable log of my engineering calculations and decisions. Ideally, the same code should be used to both find information and convey it, if possible.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Geometry Imports

    To start, we import the current CAD geometry as an STL file and prepare it for analysis. The model is a single solid containing the hull, keel and rudder together, so there is one import and one mesh, `hull`. The keel and rudder are part of that mesh, so they count toward displacement, wetted surface and the righting arm.
    """)
    return


@app.cell
def _():
    # Target convention: x forward (bow +x), y to port, z up, metres.
    _SW_YUP_TO_ZUP = np.array([
        [1, 0, 0, 0],
        [0, 0, -1, 0],   # new y = -old z
        [0, 1, 0, 0],    # new z =  old y
        [0, 0, 0, 1],
    ], dtype=float)  # proper rotation (+90 deg about x), no mirroring


    def geometry_form(name, filename, center=True):
        """One UI element holding every import setting for an STL."""
        return mo.ui.dictionary({
            "file": mo.ui.file(filetypes=[".stl"], label=f"Upload {name} STL"),
            "path": mo.ui.text(
                value=str(mo.notebook_dir().parent / "data" / filename),
                label="...or path to STL", full_width=True),
            "units": mo.ui.dropdown(
                {"mm": 0.001, "cm": 0.01, "m": 1.0, "in": 0.0254}, value="mm", label="STL units"),
            "axes": mo.ui.dropdown(
                ["SolidWorks (Y-up)", "Z-up (as exported)"], value="Z-up (as exported)", label="Export axes"),
            "flip": mo.ui.checkbox(label="Flip bow/stern (rotate 180 deg about vertical)"),
            "center": mo.ui.checkbox(
                value=center, label="Recenter: x=0 at stern, y=0 on centerline, z=0 at keel tip"),
        })


    def load_geometry(form):
        """Load the STL chosen in `form` as a trimesh in x-fwd / y-port / z-up metres."""
        v = form.value
        if v["file"]:
            data = form["file"].contents()
        elif v["path"].strip():
            data = pathlib.Path(v["path"].strip().strip('"')).read_bytes()
        else:
            return None
        mesh = trimesh.load(io.BytesIO(data), file_type="stl", force="mesh")
        mesh.apply_scale(v["units"])
        if v["axes"].startswith("SolidWorks"):
            mesh.apply_transform(_SW_YUP_TO_ZUP)
        if v["flip"]:
            mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1]))
        if mesh.is_watertight and mesh.volume < 0:
            trimesh.repair.fix_inversion(mesh)  # inside-out normals
        if v["center"]:
            lo, hi = mesh.bounds
            mesh.apply_translation([-lo[0], -(lo[1] + hi[1]) / 2, -lo[2]])
        return mesh


    return geometry_form, load_geometry


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Hull Import
    Imports the 3D CAD model of the complete underwater body (hull, keel and rudder in one STL) for analysis. After import the model is placed in the notebook frame (x forward, y to port, z up, metres), with x = 0 at the stern, y = 0 on the centerline and **z = 0 at the keel tip**. Every height in the notebook (waterline height, KG, VCB) is measured up from that point, not from the bottom of the hull shell.
    """)
    return


@app.cell
def _(geometry_form):
    hull_form = geometry_form("hull", "Hull Form.STL")
    hull_form
    return (hull_form,)


@app.cell
def _(hull_form, load_geometry):
    hull = load_geometry(hull_form)
    mo.stop(hull is None, mo.callout("Upload an STL or enter a path to begin.", kind="info"))
    return (hull,)


@app.cell
def _(hull):
    _ext = hull.extents
    _ok = hull.is_watertight and hull.is_winding_consistent
    _rows = [
        ("Watertight", hull.is_watertight),
        ("Triangles", len(hull.faces)),
        ("Length x (m)", round(_ext[0], 4)),
        ("Beam y (m)", round(_ext[1], 4)),
        ("Overall height z, keel tip to deck (m)", round(_ext[2], 4)),
        ("Volume (m^3)", round(hull.volume, 5) if hull.is_watertight else "n/a"),
    ]
    mo.vstack([
        mo.callout(
            "Mesh is a closed solid." if _ok else
            "Mesh is NOT watertight - volume and centroid will be unreliable. "
            "Export a solid body (or cap the hull) from SolidWorks.",
            kind="success" if _ok else "danger",
        ),
        mo.ui.table([{"Property": k, "Value": str(v)} for k, v in _rows], selection=None),
    ])
    return


@app.cell
def _(hull):
    _v, _f = hull.vertices, hull.faces
    _fig = go.Figure(go.Mesh3d(
        x=_v[:, 0], y=_v[:, 1], z=_v[:, 2],
        i=_f[:, 0], j=_f[:, 1], k=_f[:, 2],
        color="steelblue", opacity=1.0, flatshading=True,
    ))
    _fig.update_layout(
        scene=dict(aspectmode="data", xaxis_title="x (fwd)", yaxis_title="y (port)", zaxis_title="z (up)"),
        margin=dict(l=0, r=0, t=0, b=0), height=450,
    )
    _fig
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Hydrostatics
    Runs hydrostatic calculations on the imported geometry. The waterline height is measured up from the keel tip, so the keel is wetted first and the hull shell only enters the water higher up. Displaced volume, wetted surface and the centre of buoyancy include the keel and rudder, while the waterplane (area, LWL, BWL, inertias) is whatever the waterline cuts, so it is only the hull shell once the waterline is above the top of the keel and rudder.
    """)
    return


@app.cell
def _():
    draft_in = mo.ui.number(
        start=0.0, stop=2.0, step=0.005, value=0.668,
        label="Draft at midship (m above keel)",
    )
    heel_in = mo.ui.number(start=-90, stop=90, step=0.5, value=0.0, label="Heel (deg, + = starboard down)")
    trim_in = mo.ui.number(start=-30, stop=30, step=0.1, value=0.0, label="Trim (deg, + = bow down)")
    rho_in = mo.ui.dropdown(
        {"Sea water (1025)": 1025.0, "Fresh water (1000)": 1000.0},
        value="Sea water (1025)",
        label="Water density",
    )
    mo.vstack([
        mo.hstack([draft_in, heel_in, trim_in, rho_in], justify="start"),
    ])
    return draft_in, heel_in, rho_in, trim_in


@app.cell
def _():
    from functools import reduce

    from shapely.geometry import MultiPolygon, Polygon
    from shapely.geometry.polygon import orient


    def _ring_props(c):
        """Signed area, first moments and second moments (about origin) of a closed ring."""
        x, y = c[:-1, 0], c[:-1, 1]
        x1, y1 = np.roll(x, -1), np.roll(y, -1)
        k = x * y1 - x1 * y
        return (
            k.sum() / 2,
            ((x + x1) * k).sum() / 6,                # int x dA
            ((y + y1) * k).sum() / 6,                # int y dA
            ((y * y + y * y1 + y1 * y1) * k).sum() / 12,  # int y^2 dA
            ((x * x + x * x1 + x1 * x1) * k).sum() / 12,  # int x^2 dA
        )


    def waterplane_props(mesh, z):
        """Area, centroid, LWL/BWL and inertias of the section of `mesh` at height z."""
        sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if sec is None:
            return None
        loops = [Polygon(d[:, :2]).buffer(0) for d in sec.discrete if len(d) >= 4]
        geom = reduce(lambda a, b: a.symmetric_difference(b), loops)  # even-odd => holes
        polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
        tot = np.zeros(5)
        for p in polys:
            p = orient(p, 1.0)  # exterior ccw (+), interiors cw (-)
            for ring in [p.exterior, *p.interiors]:
                tot += _ring_props(np.asarray(ring.coords))
        area, sx, sy, iyy_o, ixx_o = tot  # note: [A, int x, int y, int y^2, int x^2]
        xf, yf = sx / area, sy / area
        minx, miny, maxx, maxy = geom.bounds
        return dict(
            area=area, lcf=xf, tcf=yf,
            I_T=iyy_o - area * yf**2,   # about waterplane centroid, transverse
            I_L=ixx_o - area * xf**2,   # about waterplane centroid, longitudinal
            lwl=maxx - minx, bwl=maxy - miny, geom=geom,
        )


    def hydrostatics(hull, draft, heel_deg, trim_deg, rho, pivot_z=None):
        """Upright/heeled/trimmed hydrostatics.

        The hull is rotated about the midship centerline point at height `pivot_z`
        (default: `draft`; heel about x, then trim about y); the water plane is z = draft.
        Centre of buoyancy is returned in hull-fixed coordinates.
        """
        pivot = [hull.bounds[:, 0].mean(), 0.0, draft if pivot_z is None else pivot_z]
        R = trimesh.transformations.rotation_matrix
        M = R(np.radians(trim_deg), [0, 1, 0], pivot) @ R(np.radians(heel_deg), [1, 0, 0], pivot)
        rot = hull.copy()
        rot.apply_transform(M)
        if rot.bounds[0, 2] >= draft:
            return None  # nothing submerged
        if rot.bounds[1, 2] <= draft:
            return None  # fully submerged
        sub = rot.slice_plane([0, 0, draft], [0, 0, -1], cap=True)
        wp = waterplane_props(rot, draft)
        vol = sub.volume
        cb_earth = sub.center_mass
        cb = (np.linalg.inv(M) @ np.append(cb_earth, 1.0))[:3]
        bm_t, bm_l = wp["I_T"] / vol, wp["I_L"] / vol
        return dict(
            rot=rot, sub=sub, M=M, wp=wp,
            volume=vol, mass=vol * rho, cb=cb, cb_earth=cb_earth,
            wetted=sub.area - wp["area"], watertight=sub.is_watertight,
            bm_t=bm_t, bm_l=bm_l, kmt=cb_earth[2] + bm_t,
            cb_coef=vol / (wp["lwl"] * wp["bwl"] * draft),
            cwp=wp["area"] / (wp["lwl"] * wp["bwl"]),
        )

    return (hydrostatics,)


@app.cell
def _(draft_in, heel_in, hull, hydrostatics, rho_in, trim_in):
    hs = hydrostatics(hull, draft_in.value, heel_in.value, trim_in.value, rho_in.value)
    mo.stop(hs is None, mo.callout(
        "Draft puts the hull fully out of, or fully under, the water - nothing to compute.",
        kind="warn"))
    _wp = hs["wp"]
    _rows = [
        ("Displaced volume (m^3)", hs["volume"], ".5f"),
        ("Displacement (kg)", hs["mass"], ".2f"),
        ("LCB from stern (m)", hs["cb"][0], ".4f"),
        ("TCB, + port (m)", hs["cb"][1], ".4f"),
        ("VCB above keel, hull frame (m)", hs["cb"][2], ".4f"),
        ("Waterplane area (m^2)", _wp["area"], ".4f"),
        ("LCF from stern (m)", _wp["lcf"], ".4f"),
        ("LWL / BWL (m)", f"{_wp['lwl']:.4f} / {_wp['bwl']:.4f}", ""),
        ("Wetted surface (m^2)", hs["wetted"], ".4f"),
        ("BMt (m)", hs["bm_t"], ".4f"),
        ("BML (m)", hs["bm_l"], ".4f"),
        ("KMt = KB + BMt (m)", hs["kmt"], ".4f"),
        ("Block coefficient Cb", hs["cb_coef"], ".4f"),
        ("Waterplane coefficient Cwp", hs["cwp"], ".4f"),
    ]
    mo.vstack([
        mo.callout("Submerged volume is a closed mesh." if hs["watertight"]
                   else "Submerged mesh is not watertight - results unreliable.",
                   kind="success" if hs["watertight"] else "danger"),
        mo.ui.table(
            [{"Property": k, "Value": format(v, f) if f else v} for k, v, f in _rows],
            selection=None, pagination=False,
        ),
    ])
    return (hs,)


@app.cell
def _(draft_in, hs):
    _h, _s = hs["rot"], hs["sub"]
    _b = _h.bounds
    _xs, _ys = [_b[0, 0], _b[1, 0]], [_b[0, 1], _b[1, 1]]
    _z = draft_in.value
    _fig = go.Figure([
        go.Mesh3d(x=_h.vertices[:, 0], y=_h.vertices[:, 1], z=_h.vertices[:, 2],
                  i=_h.faces[:, 0], j=_h.faces[:, 1], k=_h.faces[:, 2],
                  color="lightgray", opacity=0.25, name="hull"),
        go.Mesh3d(x=_s.vertices[:, 0], y=_s.vertices[:, 1], z=_s.vertices[:, 2],
                  i=_s.faces[:, 0], j=_s.faces[:, 1], k=_s.faces[:, 2],
                  color="steelblue", opacity=1.0, flatshading=True, name="submerged"),
        go.Mesh3d(x=[_xs[0], _xs[1], _xs[1], _xs[0]], y=[_ys[0], _ys[0], _ys[1], _ys[1]],
                  z=[_z] * 4, i=[0, 0], j=[1, 2], k=[2, 3],
                  color="deepskyblue", opacity=0.2, name="water"),
        go.Scatter3d(x=[hs["cb_earth"][0]], y=[hs["cb_earth"][1]], z=[hs["cb_earth"][2]],
                     mode="markers", marker=dict(size=5, color="red"), name="CB"),
    ])
    _fig.update_layout(
        scene=dict(aspectmode="data", xaxis_title="x", yaxis_title="y", zaxis_title="z"),
        margin=dict(l=0, r=0, t=0, b=0), height=450, showlegend=False,
    )
    _fig
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Righting arm (GZ) curve
    Calculate and display the heeling stability curve of the current hull.
    """)
    return


@app.cell
def _():
    mass_in = mo.ui.number(start=1.0, stop=5000.0, step=0.5, value=80.0, label="Mass (kg)")
    kg_in = mo.ui.number(start=0.0, stop=2.0, step=0.005, value=0.15, label="KG: CG above keel (m)")
    lcg_in = mo.ui.number(start=0.0, stop=20.0, step=0.01, value=1.1, label="LCG from stern (m)")
    tcg_in = mo.ui.number(start=-1.0, stop=1.0, step=0.001, value=0.0, label="TCG, + port (m)")
    heelmax_in = mo.ui.number(start=10, stop=180, step=5, value=90, label="Max heel (deg)")
    heelstep_in = mo.ui.number(start=0.5, stop=10, step=0.5, value=5, label="Heel step (deg)")
    mo.vstack([
        mo.hstack([mass_in, kg_in, lcg_in, tcg_in], justify="start"),
        mo.hstack([heelmax_in, heelstep_in], justify="start"),
    ])
    return heelmax_in, heelstep_in, kg_in, lcg_in, mass_in, tcg_in


@app.cell
def _(hydrostatics):
    from scipy.optimize import brentq


    def submerged_volume(hull, draft, heel_deg, trim_deg):
        """Volume below z = draft after heeling/trimming about the keel-level midship pivot."""
        pivot = [hull.bounds[:, 0].mean(), 0.0, 0.0]
        R = trimesh.transformations.rotation_matrix
        M = R(np.radians(trim_deg), [0, 1, 0], pivot) @ R(np.radians(heel_deg), [1, 0, 0], pivot)
        rot = hull.copy()
        rot.apply_transform(M)
        if rot.bounds[0, 2] >= draft:
            return 0.0
        if rot.bounds[1, 2] <= draft:
            return hull.volume
        return rot.slice_plane([0, 0, draft], [0, 0, -1], cap=True).volume


    def solve_draft(hull, target_volume, heel_deg, trim_deg):
        """Waterline height (z, pivot at keel) whose submerged volume equals target_volume."""
        span = float(np.linalg.norm(hull.extents))
        return brentq(
            lambda d: submerged_volume(hull, d, heel_deg, trim_deg) - target_volume,
            -span, span, xtol=1e-7,
        )


    def gz_curve(hull, mass, rho, cg, heels, trim_deg=0.0):
        """GZ at constant displacement (waterline height solved per heel, trim held fixed).

        cg is the hull-fixed (LCG, TCG, KG). GZ = horizontal (y) offset of the
        centre of gravity from the centre of buoyancy; positive = righting.
        """
        target = mass / rho
        if target >= hull.volume:
            raise ValueError("Mass exceeds the buoyancy of the fully submerged hull.")
        rows = []
        for h in heels:
            d = solve_draft(hull, target, h, trim_deg)
            s = hydrostatics(hull, d, h, trim_deg, rho, pivot_z=0.0)
            g_earth = (s["M"] @ np.append(cg, 1.0))[:3]
            rows.append(dict(heel=h, draft=d, gz=g_earth[1] - s["cb_earth"][1],
                             cb=s["cb_earth"], volume=s["volume"]))
        return rows

    return (gz_curve,)


@app.cell
def _(
    gz_curve,
    heelmax_in,
    heelstep_in,
    hull,
    kg_in,
    lcg_in,
    mass_in,
    rho_in,
    tcg_in,
):
    _heels = np.arange(0.0, heelmax_in.value + 1e-9, heelstep_in.value)
    _cg = np.array([lcg_in.value, tcg_in.value, kg_in.value])
    gz_rows = gz_curve(hull, mass_in.value, rho_in.value, _cg, _heels)
    gz_heel = np.array([r["heel"] for r in gz_rows])
    gz_val = np.array([r["gz"] for r in gz_rows])
    gz_draft = np.array([r["draft"] for r in gz_rows])

    _i = int(np.argmax(gz_val))
    _pos = np.where((gz_val[_i:] <= 0))[0]
    if len(_pos):
        _k = _i + _pos[0]
        _avs = float(np.interp(0.0, [gz_val[_k], gz_val[_k - 1]], [gz_heel[_k], gz_heel[_k - 1]]))
    else:
        _avs = None


    def _area(limit):
        m = gz_heel <= limit
        if m.sum() < 2:
            return None
        return float(np.trapezoid(gz_val[m], np.radians(gz_heel[m])))


    _gm_slope = (gz_val[1] / np.sin(np.radians(gz_heel[1]))) if len(gz_heel) > 1 else None
    gz_metrics = {
        "Displacement (kg)": f"{mass_in.value:.1f}",
        "Upright draft (m)": f"{gz_draft[0]:.4f}",
        "GM from curve, small angle (m)": f"{_gm_slope:.4f}" if _gm_slope is not None else "n/a",
        "Max GZ (m)": f"{gz_val[_i]:.4f}",
        "Angle of max GZ (deg)": f"{gz_heel[_i]:.1f}",
        "Angle of vanishing stability (deg)": f"{_avs:.1f}" if _avs is not None else f"> {gz_heel[-1]:.0f}",
        "Area 0-30 deg (m.rad)": f"{_area(30):.4f}" if _area(30) is not None else "n/a",
        "Area 0-40 deg (m.rad)": f"{_area(40):.4f}" if _area(40) is not None else "n/a",
    }
    mo.ui.table([{"Metric": k, "Value": v} for k, v in gz_metrics.items()], selection=None, pagination=False)
    return gz_heel, gz_val


@app.cell
def _(gz_heel, gz_val):
    _fig, _ax = plt.subplots()
    _ax.plot(gz_heel, gz_val, "o-", ms=4, label="GZ")
    _ax.axhline(0, color="gray", lw=0.8)
    _ax.set_xlabel("Heel angle (deg)")
    _ax.set_ylabel("GZ (m)")
    _ax.set_title("GZ Curve")
    _ax.grid(alpha=0.3)
    _fig
    return


if __name__ == "__main__":
    app.run()
