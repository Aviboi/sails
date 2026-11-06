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


    def hull_shell(hull, frac=0.05, dz=0.005):
        """Hull without keel/rudder: `hull` cut off below the lowest height where the
        section area exceeds `frac` of its maximum (the keel and rudder are thin
        fins, the shell is the wide body above them). Returns (shell, z_bottom)."""
        zs = np.arange(dz, hull.bounds[1, 2], dz)
        area = np.array([(waterplane_props(hull, z) or {"area": 0.0})["area"] for z in zs])
        z_bot = float(zs[np.argmax(area > frac * area.max())])
        return hull.slice_plane([0, 0, z_bot], [0, 0, 1], cap=True), z_bot


    def hydrostatics(hull, draft, heel_deg, trim_deg, rho, pivot_z=None, shell=None):
        """Upright/heeled/trimmed hydrostatics.

        The hull is rotated about the midship centerline point at height `pivot_z`
        (default: `draft`; heel about x, then trim about y); the water plane is z = draft.
        Centre of buoyancy is returned in hull-fixed coordinates. If `shell` (the hull
        without keel and rudder, see `hull_shell`) is given, the block and waterplane
        coefficients (cb_coef, cwp) and draft_true use the shell alone; otherwise the
        whole body.
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
        # Form coefficients: shell only (appendages excluded), else the whole body.
        body = rot if shell is None else shell.copy()
        if shell is not None:
            body.apply_transform(M)
        if body.bounds[0, 2] < draft < body.bounds[1, 2]:
            body_vol = body.slice_plane([0, 0, draft], [0, 0, -1], cap=True).volume
            body_wp = waterplane_props(body, draft)
            t_body = draft - body.bounds[0, 2]
            cb_coef = body_vol / (body_wp["lwl"] * body_wp["bwl"] * t_body)
            cwp = body_wp["area"] / (body_wp["lwl"] * body_wp["bwl"])
        else:
            t_body = cb_coef = cwp = float("nan")  # waterline below/above the shell
        return dict(
            rot=rot, sub=sub, M=M, wp=wp,
            volume=vol, mass=vol * rho, cb=cb, cb_earth=cb_earth,
            wetted=sub.area - wp["area"], watertight=sub.is_watertight,
            bm_t=bm_t, bm_l=bm_l, kmt=cb_earth[2] + bm_t,
            draft_true=t_body, cb_coef=cb_coef, cwp=cwp,
        )

    return Polygon, hull_shell, hydrostatics, reduce


@app.cell
def _(hull, hull_shell):
    hull_body, hull_body_z = hull_shell(hull)
    return hull_body, hull_body_z


@app.cell
def _(
    draft_in,
    heel_in,
    hull,
    hull_body,
    hull_body_z,
    hydrostatics,
    rho_in,
    trim_in,
):
    hs = hydrostatics(hull, draft_in.value, heel_in.value, trim_in.value, rho_in.value, shell=hull_body)
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
        (f"Hull-shell draft T, waterline to shell bottom at z={hull_body_z:.3f} (m)", hs["draft_true"], ".4f"),
            ("Block coefficient Cb, hull shell only", hs["cb_coef"], ".4f"),
        ("Waterplane coefficient Cwp, hull shell only", hs["cwp"], ".4f"),
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
    ### Wetted Surface and Lateral Plane
    Splits the submerged body into **hull shell**, **keel** and **rudder**, using the same cut height as `hull_shell` (`hull_body_z`): everything below it is a fin, and the keel and rudder are told apart because they are separate pieces there. Wetted area is the mesh area of each piece below the waterline. The lateral plane is the underwater profile projected onto the centreline (x-z) plane, with its centroid (CLP) and each fin's planform. These are taken upright at the draft set above, so heel and trim are ignored.

    Chord is the x extent of a horizontal section and thickness its y extent. `t/c` is the maximum over the span, and root and tip chords are read at 90% and 10% of the fin span. Aspect ratio is span^2 / planform area (geometric, with no end-plate correction).
    """)
    return


@app.cell
def _():
    import shapely


    def profile_union(m, axes=(0, 2)):
        """Union of the mesh's triangles projected onto the plane of two coordinate axes
        (default x-z, the side view) as a shapely geometry."""
        t = m.triangles[:, :, list(axes)]
        a = ((t[:, 1, 0] - t[:, 0, 0]) * (t[:, 2, 1] - t[:, 0, 1])
             - (t[:, 1, 1] - t[:, 0, 1]) * (t[:, 2, 0] - t[:, 0, 0]))
        return shapely.union_all(shapely.make_valid(shapely.polygons(t[np.abs(a) > 1e-12])))


    def fin_props(fin, n=15):
        """Wetted area, planform and section properties of one fin (open mesh)."""
        prof = profile_union(fin)
        z0, z1 = fin.bounds[0, 2], fin.bounds[1, 2]
        zs = np.linspace(z0, z1, n + 2)[1:-1]
        zc, chord, thick = [], [], []
        for z in zs:
            s = fin.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            if s is None or not len(s.discrete):
                continue  # open cut edge at the shell, no closed loop
            loops = s.discrete
            pts = np.vstack(loops)
            zc.append(z)
            chord.append(np.ptp(pts[:, 0]))                      # all pieces, incl. gaps between them
            thick.append(max(np.ptp(d[:, 1]) for d in loops))    # thickest single piece (slots are small)
        zs, chord, thick = np.array(zc), np.array(chord), np.array(thick)
        span = z1 - z0
        return dict(
            wetted=fin.area, planform=prof.area, span=span,
            clp_x=prof.centroid.x, clp_z=prof.centroid.y,
            mean_chord=prof.area / span, aspect_ratio=span**2 / prof.area,
            root_chord=float(np.interp(z0 + 0.9 * span, zs, chord)),
            tip_chord=float(np.interp(z0 + 0.1 * span, zs, chord)),
            tc_max=float((thick / chord).max()), x_le=fin.bounds[0, 0], x_te=fin.bounds[1, 0],
        )


    def underwater_profile(hull, draft, z_bot):
        """Wetted areas and lateral plane of the upright hull below z = draft.

        z_bot is the hull-shell cut height (`hull_shell`); faces below it are fins,
        sorted fore to aft (keel, then rudder).
        """
        sub = hull.slice_plane([0, 0, draft], [0, 0, -1], cap=False)
        low = sub.triangles_center[:, 2] < z_bot
        shell = sub.submesh([np.where(~low)[0]], append=True)
        fins = sorted(sub.submesh([np.where(low)[0]], append=True).split(only_watertight=False),
                      key=lambda f: f.bounds[0, 0])
        prof = profile_union(sub)
        return dict(
            sub=sub, profile=prof, shell_wetted=shell.area, total_wetted=sub.area,
            lat_area=prof.area, clp_x=prof.centroid.x, clp_z=prof.centroid.y,
            fins=[fin_props(f) for f in fins],
        )

    return profile_union, shapely, underwater_profile


@app.cell
def _(draft_in, hull, hull_body_z, underwater_profile):
    up = underwater_profile(hull, draft_in.value, hull_body_z)
    mo.stop(len(up["fins"]) != 2, mo.callout(
        f"Expected 2 fins (keel, rudder) below z={hull_body_z:.3f} m but found {len(up['fins'])}.", kind="warn"))
    keel_p, rudder_p = up["fins"]
    _rows = [
        ("Wetted: hull shell (m^2)", up["shell_wetted"], ".4f"),
        ("Wetted: keel (m^2)", keel_p["wetted"], ".4f"),
        ("Wetted: rudder (m^2)", rudder_p["wetted"], ".4f"),
        ("Wetted: total (m^2)", up["total_wetted"], ".4f"),
        ("Lateral plane area, whole underwater body (m^2)", up["lat_area"], ".4f"),
        ("CLP from stern (m)", up["clp_x"], ".4f"),
        ("CLP above keel tip (m)", up["clp_z"], ".4f"),
    ]
    for _name, _p in [("Keel", keel_p), ("Rudder", rudder_p)]:
        _rows += [
            (f"{_name}: planform area (m^2)", _p["planform"], ".4f"),
            (f"{_name}: span below shell (m)", _p["span"], ".4f"),
            (f"{_name}: mean chord (m)", _p["mean_chord"], ".4f"),
            (f"{_name}: root / tip chord (m)", f"{_p['root_chord']:.4f} / {_p['tip_chord']:.4f}", ""),
            (f"{_name}: aspect ratio", _p["aspect_ratio"], ".3f"),
            (f"{_name}: max t/c", _p["tc_max"], ".3f"),
            (f"{_name}: leading / trailing edge x (m)", f"{_p['x_le']:.4f} / {_p['x_te']:.4f}", ""),
            (f"{_name}: planform centroid x, z (m)", f"{_p['clp_x']:.4f}, {_p['clp_z']:.4f}", ""),
        ]
    mo.ui.table(
        [{"Property": k, "Value": format(v, f) if f else v} for k, v, f in _rows],
        selection=None, pagination=False,
    )
    return (up,)


@app.cell
def _(draft_in, up):
    _fig, _ax = plt.subplots(figsize=(8, 3))
    _geoms = up["profile"].geoms if hasattr(up["profile"], "geoms") else [up["profile"]]
    for _g in _geoms:
        _x, _y = _g.exterior.xy
        _ax.fill(_x, _y, color="steelblue", alpha=0.6)
    _ax.axhline(draft_in.value, color="deepskyblue", ls="--", lw=1, label="waterline")
    _ax.plot(up["clp_x"], up["clp_z"], "r+", ms=12, mew=2, label="CLP")
    _ax.set_aspect("equal")
    _ax.set_xlabel("x from stern (m)")
    _ax.set_ylabel("z above keel tip (m)")
    _ax.set_title("Lateral plane (underwater profile)")
    _ax.legend(loc="upper left")
    _ax.grid(alpha=0.3)
    _fig
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Windage and Freeboard
    The hull above the waterline, upright at the draft set above, projected onto the centerline plane (**side** area, for leeway and the lateral wind force) and onto the transverse plane (**frontal** area, for head-on drag). Centroids are given above the waterline, because their height is the arm of the wind heeling moment. Freeboard is the top of the hull at a station minus the waterline height. Only the hull is counted here, so the rig and any crew or equipment on deck are not.
    """)
    return


@app.cell
def _(draft_in, hull, profile_union):
    air = hull.slice_plane([0, 0, draft_in.value], [0, 0, 1], cap=False)
    air_side = profile_union(air, (0, 2))
    air_front = profile_union(air, (1, 2))
    _x0, _x1 = hull.bounds[0, 0], hull.bounds[1, 0]
    fb_x = np.linspace(_x0, _x1, 121)[1:-1]
    fb_top = np.array([np.vstack(hull.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0]).discrete)[:, 2].max()
                       for x in fb_x])
    fb = fb_top - draft_in.value


    def _fb_at(frac):
        return float(np.interp(_x0 + frac * (_x1 - _x0), fb_x, fb))


    _i = int(np.argmin(fb))
    _rows = [
        ("Side (lateral) area above waterline (m^2)", air_side.area, ".4f"),
        ("Side area centroid: x from stern (m)", air_side.centroid.x, ".4f"),
        ("Side area centroid: height above waterline (m)", air_side.centroid.y - draft_in.value, ".4f"),
        ("Frontal area above waterline (m^2)", air_front.area, ".4f"),
        ("Frontal area centroid: height above waterline (m)", air_front.centroid.y - draft_in.value, ".4f"),
        ("Frontal area centroid: y, + port (m)", air_front.centroid.x, ".4f"),
        ("Freeboard at 5% / 50% / 95% of length (m)", f"{_fb_at(0.05):.4f} / {_fb_at(0.5):.4f} / {_fb_at(0.95):.4f}", ""),
        ("Minimum freeboard (m)", f"{fb[_i]:.4f} at x = {fb_x[_i]:.3f} m", ""),
        ("Highest point above waterline (m)", hull.bounds[1, 2] - draft_in.value, ".4f"),
    ]
    mo.ui.table([{"Property": k, "Value": format(v, f) if f else v} for k, v, f in _rows],
                selection=None, pagination=False)
    return air_front, air_side


@app.cell
def _(air_front, air_side, draft_in):
    _fig, _axs = plt.subplots(1, 2, figsize=(10, 3))
    for _ax, _g, _lab in [(_axs[0], air_side, "x from stern (m)"), (_axs[1], air_front, "y, + port (m)")]:
        for _p in (_g.geoms if hasattr(_g, "geoms") else [_g]):
            _ax.fill(*_p.exterior.xy, color="steelblue", alpha=0.6)
        _ax.axhline(draft_in.value, color="deepskyblue", ls="--", lw=1)
        _ax.plot(_g.centroid.x, _g.centroid.y, "r+", ms=12, mew=2)
        _ax.set_aspect("equal")
        _ax.set_xlabel(_lab)
        _ax.set_ylabel("z above keel tip (m)")
        _ax.grid(alpha=0.3)
    _axs[0].set_title("Side area above waterline")
    _axs[1].set_title("Frontal area above waterline")
    _fig.tight_layout()
    _fig
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Form Coefficients
    Longitudinal form of the **hull shell** below the waterline (keel and rudder excluded, as for Cb and Cwp). The midship section coefficient is `Cm = Am / (BWL x T)` with `Am` the largest submerged transverse section area, and the prismatic coefficient is `Cp = V / (Am x LWL) = Cb / Cm`. LCB is given as a percentage of LWL measured forward (+) or aft (-) of the middle of the waterline length. The half-angle of entrance is the angle of the waterline to the centreline, measured between 5% and 15% of LWL aft of the bow. The first few percent of the bow are left out because the waterline rounds off there.
    """)
    return


@app.cell
def _(Polygon, reduce, shapely):
    def section_area(mesh, x):
        """Area of the transverse (y-z) section of a closed mesh at station x."""
        sec = mesh.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
        if sec is None:
            return 0.0
        loops = [Polygon(d[:, 1:]).buffer(0) for d in sec.discrete if len(d) >= 4]
        return reduce(lambda a, b: a.symmetric_difference(b), loops).area  # even-odd


    def half_breadth(geom, x):
        """Half the width of a waterplane geometry at station x."""
        cut = geom.intersection(shapely.geometry.LineString([(x, -10), (x, 10)]))
        return 0.0 if cut.is_empty else cut.bounds[3] - cut.bounds[1]

    return half_breadth, section_area


@app.cell
def _(draft_in, half_breadth, hs, hull_body, section_area):
    shell_sub = hull_body.slice_plane([0, 0, draft_in.value], [0, 0, -1], cap=True)
    _wp = hs["wp"]
    _x0, _x1 = _wp["geom"].bounds[0], _wp["geom"].bounds[2]
    _lwl = _x1 - _x0
    form_x = np.linspace(_x0, _x1, 81)[1:-1]
    form_sac = np.array([section_area(shell_sub, x) for x in form_x])
    _am = form_sac.max()
    _cm = _am / (_wp["bwl"] * hs["draft_true"])
    _cp = shell_sub.volume / (_am * _lwl)
    _lcb = shell_sub.center_mass[0]
    _xa, _xb = _x1 - 0.15 * _lwl, _x1 - 0.05 * _lwl
    _ie = np.degrees(np.arctan2((half_breadth(_wp["geom"], _xb) - half_breadth(_wp["geom"], _xa)) / 2, _xb - _xa)) * -1
    form = dict(am=_am, cm=_cm, cp=_cp, lcb_pct=100 * ((_lcb - _x0) / _lwl - 0.5),
                lcb_whole_pct=100 * ((hs["cb"][0] - _x0) / _lwl - 0.5), ie=_ie, lwl=_lwl, x0=_x0)
    mo.ui.table([{"Property": k, "Value": format(v, f)} for k, v, f in [
        ("LWL (m)", _lwl, ".4f"),
        ("Max section area Am (m^2)", _am, ".5f"),
        ("Midship section coefficient Cm", _cm, ".4f"),
        ("Prismatic coefficient Cp", _cp, ".4f"),
        ("Cm x Cp (equals Cb of the hull shell)", _cm * _cp, ".4f"),
        ("LCB, hull shell (% LWL from midpoint, + fwd)", form["lcb_pct"], "+.2f"),
        ("LCB, whole body incl. keel and rudder (% LWL, + fwd)", form["lcb_whole_pct"], "+.2f"),
        ("Half-angle of entrance (deg)", _ie, ".2f"),
    ]], selection=None, pagination=False)
    return form_sac, form_x


@app.cell
def _(form_sac, form_x, hs):
    _fig, _ax = plt.subplots(figsize=(8, 3))
    _ax.plot(form_x, form_sac, "-", label="section area")
    _ax.fill_between(form_x, form_sac, alpha=0.2)
    _ax.axvline(hs["cb"][0], color="r", ls="--", lw=1, label="LCB (whole body)")
    _ax.set_xlabel("x from stern (m)")
    _ax.set_ylabel("Section area (m^2)")
    _ax.set_title("Sectional area curve, hull shell")
    _ax.legend()
    _ax.grid(alpha=0.3)
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
    return gz_draft, gz_heel, gz_val


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


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Stability Limits
    Angles that bound the useful range of the GZ curve above. The hull is a closed lens with no gunwale (its widest point, z of about 0.65 m, is almost at the waterline), so there is no deck-edge immersion angle to read off. Instead, enter the **downflooding point**: the lowest opening that lets water in (a hatch or vent), as its half-breadth `|y|` from the centerline and its height `z` above the keel tip in the hull frame. It is taken on the leeward side, and its height above the waterline is `z cos(heel) - |y| sin(heel)` compared with the solved waterline height at each heel. The usable range ends at the first of downflooding or vanishing stability. Righting moment is `GZ x displacement x g`.
    """)
    return


@app.cell
def _():
    dfy_in = mo.ui.number(start=0.0, stop=0.3, step=0.005, value=0.0, label="Downflooding point |y| (m)")
    dfz_in = mo.ui.number(start=0.0, stop=1.0, step=0.005, value=0.78, label="Downflooding point z above keel tip (m)")
    mo.hstack([dfy_in, dfz_in], justify="start")
    return dfy_in, dfz_in


@app.cell
def _(dfy_in, dfz_in, gz_draft, gz_heel, gz_val, mass_in):
    def first_crossing(x, y):
        """First x where y falls through zero (linear interpolation), else None."""
        for k in range(1, len(x)):
            if y[k - 1] > 0 >= y[k]:
                return float(np.interp(0.0, [y[k], y[k - 1]], [x[k], x[k - 1]]))
        return None


    _h = np.radians(gz_heel)
    # height of the leeward downflooding point above the solved waterline
    df_margin = (dfz_in.value * np.cos(_h) - dfy_in.value * np.sin(_h)) - gz_draft
    df_angle = first_crossing(gz_heel, df_margin)
    avs_angle = first_crossing(gz_heel, gz_val)
    _lim = [a for a in (df_angle, avs_angle) if a is not None]
    use_angle = min(_lim) if _lim else None
    _in_range = gz_heel <= (use_angle if use_angle is not None else gz_heel[-1])
    _rm = gz_val * mass_in.value * 9.80665
    _j = int(np.argmax(np.where(_in_range, gz_val, -np.inf)))
    _gz_df = float(np.interp(df_angle, gz_heel, gz_val)) if df_angle is not None else None
    _area_use = (float(np.trapezoid(gz_val[_in_range], np.radians(gz_heel[_in_range])))
                 if _in_range.sum() > 1 else None)


    def _fmt(v, f):
        return format(v, f) if v is not None else "not reached"


    _rows = [
        ("Angle of vanishing stability (deg)", _fmt(avs_angle, ".1f") if avs_angle is not None else f"> {gz_heel[-1]:.0f}"),
        ("Downflooding angle (deg)", _fmt(df_angle, ".1f") if df_angle is not None else f"> {gz_heel[-1]:.0f}"),
        ("Usable range ends at (deg)", _fmt(use_angle, ".1f") if use_angle is not None else f"> {gz_heel[-1]:.0f}"),
        ("GZ at downflooding (m)", _fmt(_gz_df, ".4f")),
        ("Max GZ within usable range (m)", f"{gz_val[_j]:.4f} at {gz_heel[_j]:.1f} deg"),
        ("Max righting moment within usable range (N.m)", f"{_rm[_j]:.1f}"),
        ("GZ area within usable range (m.rad)", _fmt(_area_use, ".4f")),
    ]
    mo.ui.table([{"Property": k, "Value": v} for k, v in _rows], selection=None, pagination=False)
    return avs_angle, df_angle


@app.cell
def _(avs_angle, df_angle, gz_heel, gz_val):
    _fig, _ax = plt.subplots()
    _ax.plot(gz_heel, gz_val, "o-", ms=4, label="GZ")
    _ax.axhline(0, color="gray", lw=0.8)
    for _a, _c, _l in [(df_angle, "tab:orange", "downflooding"), (avs_angle, "tab:red", "vanishing stability")]:
        if _a is not None:
            _ax.axvline(_a, color=_c, ls="--", label=f"{_l} {_a:.1f} deg")
    _ax.set_xlabel("Heel angle (deg)")
    _ax.set_ylabel("GZ (m)")
    _ax.set_title("GZ curve with stability limits")
    _ax.legend()
    _ax.grid(alpha=0.3)
    _fig
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Metacentric Heights
    Initial stability and trim response at the draft, heel and trim set above, for the centre of gravity set in the GZ section (`KG`). `KMt = KB + BMt` and `KML = KB + BML` come from the waterplane inertias, and `GM = KM - KG`. `MCT1cm = displacement x GML / (100 x LWL)` is the moment needed to change trim by 1 cm over the waterline length. The displacement here is the one at the draft input, which may differ from the mass entered for the GZ curve.
    """)
    return


@app.cell
def _(gz_heel, gz_val, hs, kg_in):
    _kb = hs["cb_earth"][2]
    _kml = _kb + hs["bm_l"]
    _gmt = hs["kmt"] - kg_in.value
    _gml = _kml - kg_in.value
    _mct = hs["mass"] * _gml / (100 * hs["wp"]["lwl"])
    _rows = [
        ("Displacement at this draft (kg)", hs["mass"], ".2f"),
        ("KB (m)", _kb, ".4f"),
        ("BMt (m)", hs["bm_t"], ".4f"),
        ("KMt (m)", hs["kmt"], ".4f"),
        ("KG (m)", kg_in.value, ".4f"),
        ("GMt (m)", _gmt, ".4f"),
        ("BML (m)", hs["bm_l"], ".4f"),
        ("KML (m)", _kml, ".4f"),
        ("GML (m)", _gml, ".4f"),
        ("MCT 1 cm (kg.m per cm)", _mct, ".3f"),
        ("GM from GZ slope at mass_in (m)", float(gz_val[1] / np.sin(np.radians(gz_heel[1]))), ".4f"),
    ]
    mo.vstack([
        mo.callout("GMt is negative: upright is unstable at this KG." if _gmt < 0 else "GMt is positive.",
                   kind="danger" if _gmt < 0 else "success"),
        mo.ui.table([{"Property": k, "Value": format(v, f)} for k, v, f in _rows],
                    selection=None, pagination=False),
    ])
    return


if __name__ == "__main__":
    app.run()
