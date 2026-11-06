# /// script
# dependencies = [
#     "mapbox-earcut==2.1.0",
#     "marimo>=0.25.2",
#     "matplotlib==3.11.2",
#     "networkx==3.7",
#     "neuralfoil==0.3.3",
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
                      key=lambda f: -f.bounds[0, 0])  # bow is +x, so descending x is fore to aft
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
    return air_front, air_side, fb_top, fb_x


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
    return form, form_sac, form_x


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
    return avs_angle, df_angle, use_angle


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


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Mass Moments of Inertia and Added Mass
    Rotational inertia and added mass for roll, pitch, yaw and the translations. The hull geometry alone does not fix the mass distribution (ballast, payload and structure dominate), so two views are given.

    - **Radii of gyration from the mesh:** the hull treated as a uniform solid, and the submerged (buoyant) volume alone, about their own centroids. A real boat is hollow with its weight low, so these are only a geometric reference.
    - **Dry inertia from assumed radii:** `I = m k^2` about the CG at the mass, KG and LCG set in the GZ section, with `k` as a fraction of beam (roll) or length (pitch, yaw). Typical values are `kxx` of 0.30-0.40 B and `kyy`, `kzz` of 0.22-0.28 L, so adjust these once the weight breakdown exists.
    - **Added mass (strip theory with a 3D fin correction):** each underwater section is treated as a half ellipse of half-breadth `b` and depth `T`, giving `a33 = rho pi/2 b^2` (heave) and `a22 = rho pi/2 T^2` (sway). Strips overestimate the sway added mass of a short, deep keel, so the part of `a22` that the keel and rudder add over the bare hull is scaled by a finite-span factor `J`. `J` compares Lamb's exact added mass for an elliptical plate (the fin plus its free-surface image, with the same area as the mean-chord rectangle) with the strip sum for the same plate. Pitch and yaw added inertia integrate `a33` and `a22` with the squared distance from the LCG, and roll uses `a22` times the squared distance from the section centre to the CG. Surge is taken as 5% of displacement. The hull itself stays a plain strip (it is slender), and there is no frequency dependence or free-surface correction, so treat all of it as an estimate.

    The natural roll period is `T = 2 pi sqrt((I44 + A44) / (m g GMt))`.
    """)
    return


@app.cell
def _():
    kxx_in = mo.ui.number(start=0.1, stop=0.6, step=0.01, value=0.35, label="Roll radius kxx / beam")
    kyy_in = mo.ui.number(start=0.1, stop=0.5, step=0.01, value=0.25, label="Pitch radius kyy / length")
    kzz_in = mo.ui.number(start=0.1, stop=0.5, step=0.01, value=0.25, label="Yaw radius kzz / length")
    mo.hstack([kxx_in, kyy_in, kzz_in], justify="start")
    return kxx_in, kyy_in, kzz_in


@app.cell
def _():
    from scipy.special import ellipe


    def section_bT(body, draft, xs):
        """Half-breadth b and depth T (waterline to lowest point) of `body` sections at stations xs."""
        sub = body.slice_plane([0, 0, draft], [0, 0, -1], cap=True)
        b, T = np.zeros(len(xs)), np.zeros(len(xs))
        for k, x in enumerate(xs):
            sec = sub.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
            if sec is None:
                continue
            pts = np.vstack(sec.discrete)
            b[k] = np.abs(pts[:, 1]).max()
            T[k] = draft - pts[:, 2].min()
        return b, T


    def fin_3d_factor(fin, draft, z_bot):
        """Finite-span factor J (3D / strip) on a fin's sway added mass.

        The immersed fin plus its free-surface image is an elliptical plate with vertical semi-axis
        s (tip to waterline) and the same area as the mean-chord rectangle, so semi-chord
        a = 2 c / pi. Lamb's exact added mass for an ellipse moving normal to its plane is
        4 pi/3 rho M m^2 / E(e) (M, m major and minor semi-axes), against 4 pi/3 rho s^2 a from
        strips along the chord; J is their ratio (about 1 for a slender fin, small for a deep short one).
        """
        s = draft - (z_bot - fin["span"])
        a = 2 * fin["mean_chord"] / np.pi
        M, m = max(s, a), min(s, a)
        return float(M * m**2 / ellipe(1 - (m / M) ** 2) / (s**2 * a))


    def strip_added_mass(body, shell, fins, draft, rho, xcg, zcg, z_bot, n=80, correct=True):
        """Strip-theory added mass and inertia of the submerged `body` (upright).

        Sections are half ellipses of half-breadth b and depth T: heave a33 = rho pi/2 b^2,
        sway a22 = rho pi/2 T^2. The part of a22 that the keel and rudder add over the hull `shell`
        is scaled by each fin's 3D factor (`fin_3d_factor`) when `correct`. Returns the integrated
        A22, A33, A44, A55, A66 plus the fin factors.
        """
        sub = body.slice_plane([0, 0, draft], [0, 0, -1], cap=True)
        xs = np.linspace(sub.bounds[0, 0], sub.bounds[1, 0], n + 2)[1:-1]
        b, T = section_bT(body, draft, xs)
        _, T_hull = section_bT(shell, draft, xs)
        a33 = rho * np.pi / 2 * b**2
        a22_hull = rho * np.pi / 2 * T_hull**2
        inc = np.maximum(rho * np.pi / 2 * T**2 - a22_hull, 0.0)
        J = [fin_3d_factor(f, draft, z_bot) for f in fins]
        if correct:
            for f, j in zip(fins, J):
                inc = np.where((xs >= f["x_le"]) & (xs <= f["x_te"]), inc * j, inc)
        a22 = a22_hull + inc
        zc = draft - T / 2  # section centre height
        I = lambda f: float(np.trapezoid(f, xs))
        return dict(
            xs=xs, a22=a22, a33=a33, J=J,
            A22=I(a22), A33=I(a33),
            A44=I(a22 * (zc - zcg) ** 2),
            A55=I(a33 * (xs - xcg) ** 2),
            A66=I(a22 * (xs - xcg) ** 2),
        )

    return (strip_added_mass,)


@app.cell
def _(
    draft_in,
    hs,
    hull,
    hull_body,
    hull_body_z,
    kg_in,
    kxx_in,
    kyy_in,
    kzz_in,
    lcg_in,
    mass_in,
    rho_in,
    strip_added_mass,
    up,
):
    _m, _g = mass_in.value, 9.80665
    _beam, _len = hull.extents[1], hull.extents[0]
    _wl = draft_in.value
    _subv = hull.slice_plane([0, 0, _wl], [0, 0, -1], cap=True)


    def _radii(mesh):
        I = np.diag(mesh.moment_inertia) / mesh.volume  # per unit mass: k^2 about x, y, z
        return np.sqrt(I)


    k_solid, k_buoy = _radii(hull), _radii(_subv)
    k_dry = np.array([kxx_in.value * _beam, kyy_in.value * _len, kzz_in.value * _len])
    I_dry = _m * k_dry**2
    _fins = up["fins"]
    am = strip_added_mass(hull, hull_body, _fins, _wl, rho_in.value, lcg_in.value, kg_in.value, hull_body_z)
    am_strip = strip_added_mass(hull, hull_body, _fins, _wl, rho_in.value, lcg_in.value, kg_in.value, hull_body_z, correct=False)
    A11 = 0.05 * hs["mass"]
    A_rot = np.array([am["A44"], am["A55"], am["A66"]])
    _gmt = hs["kmt"] - kg_in.value
    roll_period = (2 * np.pi * np.sqrt((I_dry[0] + A_rot[0]) / (hs["mass"] * _g * _gmt))
                   if _gmt > 0 else float("nan"))

    _rows = [
        ("Radius of gyration k44 / k55 / k66: uniform solid hull (m)", " / ".join(f"{v:.3f}" for v in k_solid)),
        ("Radius of gyration k44 / k55 / k66: submerged volume (m)", " / ".join(f"{v:.3f}" for v in k_buoy)),
        ("Radius of gyration k44 / k55 / k66: assumed ratios (m)", " / ".join(f"{v:.3f}" for v in k_dry)),
        (f"Dry inertia I44 / I55 / I66 at {_m:.1f} kg (kg.m^2)", " / ".join(f"{v:.2f}" for v in I_dry)),
        ("Fin 3D factor J: keel / rudder", " / ".join(f"{v:.2f}" for v in am["J"])),
        ("Sway added mass A22: plain strips -> with 3D correction (kg)", f"{am_strip['A22']:.1f} -> {am['A22']:.1f}"),
        ("Added mass A11 / A22 / A33 (kg)", f"{A11:.1f} / {am['A22']:.1f} / {am['A33']:.1f}"),
        ("Added inertia A44 / A55 / A66 (kg.m^2)", " / ".join(f"{v:.2f}" for v in A_rot)),
        ("Added / dry inertia, roll / pitch / yaw", " / ".join(f"{v:.2f}" for v in A_rot / I_dry)),
        ("Natural roll period (s)", f"{roll_period:.2f}"),
    ]
    mo.ui.table([{"Property": k, "Value": v} for k, v in _rows], selection=None, pagination=False)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Mast Step and Sail-Plan Datum
    Fixes where the rig attaches to the hull and the frame the sail design will work in. The **sail datum** is the mast step: a point on the centerline (or offset by `y`) at the hull's top surface at the chosen `x`, plus an optional height offset for a mast foot or step plate. Sail geometry is then given relative to it, as `p_hull = mast_step + p_sail`, with the same axes as the hull (x forward, y to port, z up, metres). Heights above the waterline use the draft set in the hydrostatics section.

    The air-draft limit is the greatest allowed height of the top of the rig above the waterline, from any bridge, lock or handling limit. The default is a placeholder, so replace it with the real figure. The lead is the longitudinal distance from the centre of lateral resistance to the mast step, positive when the mast is ahead of it. The sail's centre of effort will normally sit a little ahead of the CLP.
    """)
    return


@app.cell
def _(hull):
    step_x_in = mo.ui.number(start=0.0, stop=float(hull.bounds[1, 0]), step=0.01, value=1.0, label="Mast step x from stern (m)")
    step_y_in = mo.ui.number(start=-0.3, stop=0.3, step=0.005, value=0.0, label="Mast step y, + port (m)")
    step_dz_in = mo.ui.number(start=-0.2, stop=0.5, step=0.005, value=0.0, label="Step height above hull top (m)")
    airdraft_in = mo.ui.number(start=0.5, stop=30.0, step=0.1, value=5.0, label="Air-draft limit above waterline (m)")
    mo.hstack([step_x_in, step_y_in, step_dz_in, airdraft_in], justify="start")
    return airdraft_in, step_dz_in, step_x_in, step_y_in


@app.cell
def _(
    air_side,
    airdraft_in,
    draft_in,
    fb_top,
    fb_x,
    hs,
    hull,
    kg_in,
    lcg_in,
    step_dz_in,
    step_x_in,
    step_y_in,
    up,
):
    _deck = float(np.interp(step_x_in.value, fb_x, fb_top))
    mast_step = np.array([step_x_in.value, step_y_in.value, _deck + step_dz_in.value])
    _wl = draft_in.value
    _lwl = hs["wp"]["lwl"]
    _rows = [
        ("Mast step (x, y, z) in hull frame (m)", ", ".join(f"{v:.4f}" for v in mast_step)),
        ("Hull top at step station, above keel tip (m)", f"{_deck:.4f}"),
        ("Step height above waterline (m)", f"{mast_step[2] - _wl:.4f}"),
        ("Step position, fraction of LWL from bow", f"{(hull.bounds[1, 0] - mast_step[0]) / _lwl:.3f}"),
        ("Lead: step ahead of CLP (m)", f"{mast_step[0] - up['clp_x']:+.4f}"),
        ("Step ahead of LCB / LCF / LCG (m)", " / ".join(
            f"{mast_step[0] - v:+.4f}" for v in (hs["cb"][0], hs["wp"]["lcf"], lcg_in.value))),
        ("Height of step above CLP (m)", f"{mast_step[2] - up['clp_z']:+.4f}"),
        ("Rig height available above the step (m)", f"{_wl + airdraft_in.value - mast_step[2]:.4f}"),
    ]
    _fig, _ax = plt.subplots(figsize=(8, 3.2))
    for _g, _c in [(up["profile"], "steelblue"), (air_side, "lightsteelblue")]:
        for _p in (_g.geoms if hasattr(_g, "geoms") else [_g]):
            _ax.fill(*_p.exterior.xy, color=_c, alpha=0.7)
    _ax.axhline(_wl, color="deepskyblue", ls="--", lw=1, label="waterline")
    _ax.axhline(_wl + airdraft_in.value, color="gray", ls=":", lw=1, label="air-draft limit")
    _ax.plot([mast_step[0]], [mast_step[2]], "k^", ms=9, label="mast step")
    _ax.plot([up["clp_x"]], [up["clp_z"]], "r+", ms=11, mew=2, label="CLP")
    _ax.plot([hs["cb"][0]], [hs["cb"][2]], "go", ms=6, label="CB")
    _ax.plot([lcg_in.value], [kg_in.value], "mx", ms=8, mew=2, label="CG")
    _ax.set_xlabel("x from stern (m)")
    _ax.set_ylabel("z above keel tip (m)")
    _ax.set_ylim(0, _wl + min(airdraft_in.value, 1.5))
    _ax.set_aspect("equal")
    _ax.legend(loc="upper left", fontsize=8, ncol=3)
    _ax.grid(alpha=0.3)
    mo.vstack([
        mo.ui.table([{"Property": k, "Value": v} for k, v in _rows], selection=None, pagination=False),
        _fig,
    ])
    return (mast_step,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Sail Design

    With the hull characterised, the remaining sections design the rigid sail and check it against the hull. Each section below will be filled in turn, and each one feeds the next.

    1. **Environment and Constraints:** wind and air properties, the crossing target, and the limits the design must respect.
    2. **Hydrodynamic Forces:** hull resistance against speed, and keel and rudder lift and drag with leeway.
    3. **Wing-Sail Aerodynamics:** section data, finite-span corrections, flap or tail control, centre of effort.
    4. **Force Balance and Heel:** sail force against hydrodynamic force, equilibrium speed, heel and helm over points of sail.
    5. **Structural Loads:** mast and step load cases from the design and survival winds.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Environment and Constraints
    The conditions the rig must work in, the crossing it must achieve, and the limits it must respect. Every value here is a **placeholder** to be replaced once the real mission and weight budget exist.

    ### Wind and Air
    True wind is given at a reference height as a power-law profile, `V(z) = V_ref (z / z_ref)^alpha`, with `alpha` about 0.11 over open sea. Three wind states bound the design: a **minimum** at which the boat should still make way, a **design** wind that sets the sail area and balance, and a **survival** wind for the structural check. Air density follows the ideal gas law from temperature and pressure, and dynamic pressure is `q = rho V^2 / 2`.
    """)
    return


@app.cell
def _():
    air_temp_in = mo.ui.number(start=-10, stop=40, step=0.5, value=15.0, label="Air temperature (deg C)")
    pressure_in = mo.ui.number(start=950, stop=1050, step=1, value=1013, label="Pressure (hPa)")
    zref_in = mo.ui.number(start=2.0, stop=20.0, step=0.5, value=10.0, label="Wind reference height z_ref (m)")
    alpha_in = mo.ui.number(start=0.05, stop=0.3, step=0.01, value=0.11, label="Shear exponent alpha")
    vmin_in = mo.ui.number(start=1, stop=30, step=0.5, value=6.0, label="Minimum wind (kn)")
    vdes_in = mo.ui.number(start=1, stop=40, step=0.5, value=15.0, label="Design wind (kn)")
    vsurv_in = mo.ui.number(start=10, stop=100, step=1, value=45.0, label="Survival wind (kn)")
    mo.vstack([
        mo.hstack([air_temp_in, pressure_in, zref_in, alpha_in], justify="start"),
        mo.hstack([vmin_in, vdes_in, vsurv_in], justify="start"),
    ])
    return (
        air_temp_in,
        alpha_in,
        pressure_in,
        vdes_in,
        vmin_in,
        vsurv_in,
        zref_in,
    )


@app.cell
def _(
    air_temp_in,
    airdraft_in,
    alpha_in,
    pressure_in,
    vdes_in,
    vmin_in,
    vsurv_in,
    zref_in,
):
    KNOT = 0.514444  # m/s per knot


    def wind_at(z, v_ref, z_ref, alpha):
        """Power-law wind speed (m/s) at height z (m) above the waterline, given v_ref (m/s) at z_ref."""
        return v_ref * (np.maximum(z, 0.1) / z_ref) ** alpha


    rho_air = pressure_in.value * 100.0 / (287.05 * (air_temp_in.value + 273.15))
    wind_states = {
        "Minimum": vmin_in.value * KNOT,
        "Design": vdes_in.value * KNOT,
        "Survival": vsurv_in.value * KNOT,
    }

    _top = airdraft_in.value
    _rows = []
    for _name, _v in wind_states.items():
        _vt = float(wind_at(_top, _v, zref_in.value, alpha_in.value))
        _rows.append({
            "State": _name,
            "V at z_ref (m/s)": f"{_v:.2f}",
            f"V at rig top, {_top:.1f} m (m/s)": f"{_vt:.2f}",
            "q at rig top (Pa)": f"{0.5 * rho_air * _vt**2:.1f}",
        })

    _z = np.linspace(0.1, _top, 60)
    _fig, _ax = plt.subplots(figsize=(5, 3.2))
    for _name, _v in wind_states.items():
        _ax.plot(wind_at(_z, _v, zref_in.value, alpha_in.value) / KNOT, _z, label=_name)
    _ax.set_xlabel("Wind speed (kn)")
    _ax.set_ylabel("Height above waterline (m)")
    _ax.grid(alpha=0.3)
    _ax.legend()
    mo.vstack([
        mo.md(f"Air density: **{rho_air:.4f} kg/m^3**"),
        mo.ui.table(_rows, selection=None, pagination=False),
        _fig,
    ])
    return KNOT, rho_air, wind_at


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Crossing Target and Design Limits
    The required average speed follows from the distance and the time allowed. The limits below are the acceptance criteria for later sections: the steady heel at the design wind must stay under `max heel`, which itself must sit inside the usable stability range; the sail's centre of effort must stay within `max lead` of the centre of lateral resistance (as a fraction of LWL) to hold helm in check; and the rig must fit under the air-draft limit with a mass no greater than `max rig mass`.
    """)
    return


@app.cell
def _():
    dist_in = mo.ui.number(start=100, stop=6000, step=50, value=3000, label="Crossing distance (nm)")
    days_in = mo.ui.number(start=5, stop=120, step=1, value=40, label="Time allowed (days)")
    maxheel_in = mo.ui.number(start=5, stop=60, step=1, value=25, label="Max steady heel (deg)")
    maxlead_in = mo.ui.number(start=0.0, stop=0.3, step=0.005, value=0.10, label="Max CE-CLP lead (fraction of LWL)")
    maxrig_in = mo.ui.number(start=0.0, stop=500, step=1, value=25, label="Max rig mass (kg)")
    mo.vstack([
        mo.hstack([dist_in, days_in], justify="start"),
        mo.hstack([maxheel_in, maxlead_in, maxrig_in], justify="start"),
    ])
    return days_in, dist_in, maxheel_in, maxlead_in, maxrig_in


@app.cell
def _(
    KNOT,
    airdraft_in,
    days_in,
    dist_in,
    draft_in,
    gz_heel,
    hs,
    mass_in,
    mast_step,
    maxheel_in,
    maxlead_in,
    maxrig_in,
    use_angle,
    vdes_in,
    vsurv_in,
):
    v_req = dist_in.value / (days_in.value * 24.0)  # required average speed, kn
    _rig_h = draft_in.value + airdraft_in.value - mast_step[2]
    _heel_cap = use_angle if use_angle is not None else gz_heel[-1]
    _lwl = hs["wp"]["lwl"]
    _rows = [
        ("Required average speed (kn)", f"{v_req:.2f}", f"{v_req * KNOT:.2f} m/s"),
        ("Required Froude number v / sqrt(g LWL)",
         f"{v_req * KNOT / np.sqrt(9.80665 * _lwl):.3f}", ""),
        ("Max steady heel (deg)", f"{maxheel_in.value:.1f}",
         f"usable range ends at {_heel_cap:.1f} deg: " + ("OK" if maxheel_in.value < _heel_cap else "EXCEEDS")),
        ("Max CE-CLP lead (m)", f"{maxlead_in.value * _lwl:.3f}",
         f"{maxlead_in.value:.0%} of LWL {_lwl:.3f} m"),
        ("Rig height available above step (m)", f"{_rig_h:.3f}", "from the air-draft limit"),
        ("Max rig mass (kg)", f"{maxrig_in.value:.1f}", f"{maxrig_in.value / mass_in.value:.0%} of total mass"),
        ("Design / survival wind (kn)", f"{vdes_in.value:.1f} / {vsurv_in.value:.1f}", ""),
    ]
    mo.ui.table(
        [{"Constraint": a, "Value": b, "Note": c} for a, b, c in _rows],
        selection=None, pagination=False,
    )
    return (v_req,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Hydrodynamic Forces
    The water-side forces the sail has to balance: resistance against speed, and the side force the keel and rudder can produce as the boat makes leeway. Both are built from the underwater geometry already measured above, and both are written as functions (`calm_resistance`, `appendage_side_force`) so the force-balance section can call them at any speed and leeway.

    ### Calm-Water Resistance
    Resistance is split into components that add at each speed `V`, with Froude number `Fn = V / sqrt(g LWL)`.

    - **Hull friction:** the ITTC-1957 line `Cf = 0.075 / (log10 Re - 2)^2` with `Re = V L / nu`, plus a roughness allowance `dCf`, acting on the wetted area of the hull shell.
    - **Hull form factor:** `1 + k` from the Holtrop-Mennen regression (no transom term), which raises the friction to account for the hull's pressure drag due to viscosity. It is an estimate for a conventional displacement hull, so check its value.
    - **Appendages:** the keel and rudder are flat-plate friction at their own chord Reynolds number, times a section thickness factor `1 + 2 t/c + 60 (t/c)^4`.

    - **Wave-making:** Michell's thin-ship integral over the hull offsets, in the next subsection.

    `total_resistance` adds the three components. The result is for the upright, untrimmed hull at the set draft, with no allowance for sea state, wind-wave added resistance or appendage interference.
    """)
    return


@app.cell
def _():
    nu_in = mo.ui.number(start=0.8e-6, stop=1.8e-6, step=0.01e-6, value=1.19e-6, label="Water kinematic viscosity (m^2/s; 1.19e-6 sea water at 15 deg C)")
    dcf_in = mo.ui.number(start=0.0, stop=0.001, step=0.0001, value=0.0003, label="Roughness allowance dCf")
    vmax_in = mo.ui.number(start=2, stop=15, step=0.5, value=6.0, label="Max speed shown (kn)")
    mo.hstack([nu_in, dcf_in, vmax_in], justify="start")
    return dcf_in, nu_in, vmax_in


@app.cell
def _(KNOT, dcf_in, form, hs, nu_in, rho_in, up, v_req, vmax_in):
    G = 9.80665


    def cf_ittc(re):
        """ITTC-1957 model-ship correlation line."""
        return 0.075 / (np.log10(re) - 2.0) ** 2


    # Holtrop-Mennen form factor 1 + k1 for the bare hull shell (no transom term)
    _L, _B, _T = form["lwl"], hs["wp"]["bwl"], hs["draft_true"]
    _cp, _lcb = form["cp"], form["lcb_pct"]
    _Lr = _L * (1 - _cp + 0.06 * _cp * _lcb / (4 * _cp - 1))
    hull_form_factor = 0.93 + (_T / _L) ** 0.2228446 * (_B / _Lr) ** 0.92497 * (
        (0.95 - _cp) ** -0.521448) * (1 - _cp + 0.0225 * _lcb) ** 0.6906


    def calm_resistance(V, hull_wetted, fins, rho, nu, dcf):
        """Viscous resistance (N) of the hull shell and of the fins, at speeds V (m/s).

        Returns (hull, fins) as arrays, each the sum over its parts. Wave-making is not included.
        """
        V = np.asarray(V, dtype=float)
        q = 0.5 * rho * V**2
        hull_r = q * hull_wetted * hull_form_factor * (cf_ittc(V * form["lwl"] / nu) + dcf)
        fin_r = np.zeros_like(V)
        for f in fins:
            tc = f["tc_max"]
            fin_r += q * f["wetted"] * (cf_ittc(V * f["mean_chord"] / nu) + dcf) * (1 + 2 * tc + 60 * tc**4)
        return hull_r, fin_r


    _kn = np.linspace(0.25, vmax_in.value, 50)
    _V = _kn * KNOT
    _h, _f = calm_resistance(_V, up["shell_wetted"], up["fins"], rho_in.value, nu_in.value, dcf_in.value)
    _vr = v_req * KNOT
    _hr, _fr = calm_resistance(_vr, up["shell_wetted"], up["fins"], rho_in.value, nu_in.value, dcf_in.value)

    _rows = []
    for _k in np.arange(1, vmax_in.value + 1e-9):
        _v = _k * KNOT
        _a, _b = calm_resistance(_v, up["shell_wetted"], up["fins"], rho_in.value, nu_in.value, dcf_in.value)
        _rows.append({
            "V (kn)": f"{_k:.0f}", "Fn": f"{_v / np.sqrt(G * form['lwl']):.3f}",
            "Re (hull)": f"{_v * form['lwl'] / nu_in.value:.2e}",
            "Hull (N)": f"{float(_a):.2f}", "Fins (N)": f"{float(_b):.2f}", "Total (N)": f"{float(_a + _b):.2f}",
        })

    _fig, _ax = plt.subplots(figsize=(7, 3.4))
    _ax.stackplot(_kn, _h, _f, labels=["hull friction + form", "keel + rudder friction"], alpha=0.7)
    _ax.plot([v_req], [float(_hr + _fr)], "k^", ms=9, label=f"required speed, {float(_hr + _fr):.1f} N")
    _ax.set_xlabel("Speed (kn)")
    _ax.set_ylabel("Viscous resistance (N)")
    _ax.grid(alpha=0.3)
    _ax.legend(loc="upper left")
    mo.vstack([
        mo.md(
            f"Hull form factor **1 + k = {hull_form_factor:.3f}**, "
            f"hull shell wetted area **{up['shell_wetted']:.3f} m^2**, "
            f"appendage wetted area **{sum(f['wetted'] for f in up['fins']):.3f} m^2**. "
            f"At the required {v_req:.2f} kn: Fn = {_vr / np.sqrt(G * form['lwl']):.3f}, "
            f"viscous resistance **{float(_hr + _fr):.2f} N** (wave-making excluded)."
        ),
        mo.ui.table(_rows, selection=None, pagination=False),
        _fig,
    ])
    return G, calm_resistance


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Wave-Making Resistance (Michell)
    Michell's thin-ship integral gives the wave resistance of a slender body from its offsets alone. With half-breadth `b(x, z)` (the full underwater body, so the keel and rudder are included), `k0 = g / V^2` and `lambda = sec(theta)` the angle of each wave component,

    `R_w = (4 rho k0^2 V^2 / pi) * integral from 1 to inf of (I^2 + J^2) lambda^2 / sqrt(lambda^2 - 1) d lambda`, with `I + iJ = integral of (db/dx) exp(k0 lambda^2 z + i k0 lambda x) dx dz`

    taken over the body below the waterline (`z <= 0`). Substituting `lambda = cosh u` removes the singularity at `lambda = 1`. The offsets are sampled on a grid, treated as piecewise linear, and the exponential weights are integrated exactly over each cell, so the result does not depend on how fine the vertical grid is relative to the wave decay depth.

    The implementation was checked on a Wigley hull, where it converges with grid and integration limits and shows the known humps and hollows near `Fn` = 0.3, 0.35 and 0.5. **It is still thin-ship theory.** It assumes small hull slopes, ignores viscosity, sinkage and trim, and is known to overpredict the humps and miss the hollows between them for real hulls. It also assumes the hull is upright at the draft set above.

    **The transom needs a decision.** Taken literally, the blunt stern is a vertical wall that the theory sees as a strong wave maker, even at speeds where the real transom is dry. The **transom fairing length** therefore extends the stern aft as a linear taper to zero beam, standing in for the hollow a dry transom leaves in the wake. The result is sensitive to it, so the plot shades the range from no fairing to a 0.45 m fairing. Use the result for the trend with speed rather than for exact values.
    """)
    return


@app.cell
def _(Polygon, draft_in, form, hs, hull, reduce, shapely):
    def michell_offsets(body, wl, nx=80, nz=30):
        """Half-breadth grid b[i, j] of `body` below the waterline wl, at stations x[i] and heights z[j] (relative to wl)."""
        sub = body.slice_plane([0, 0, wl], [0, 0, -1], cap=True)
        x = np.linspace(sub.bounds[0, 0], sub.bounds[1, 0], nx)
        z = np.linspace(sub.bounds[0, 2], wl, nz) - wl
        zq = z + wl
        zq[-1] -= 1e-4  # sample just below the waterline cap
        b = np.zeros((nx, nz))
        for i in range(1, nx - 1):
            sec = sub.section(plane_origin=[x[i], 0, 0], plane_normal=[1, 0, 0])
            if sec is None:
                continue
            loops = [Polygon(p[:, [1, 2]]) for p in sec.discrete if len(p) >= 3]
            poly = reduce(lambda a, c: a.symmetric_difference(c), loops)  # even-odd, as for the waterplane
            if not poly.is_valid:
                poly = shapely.make_valid(poly)
            ymax = np.abs(np.vstack(sec.discrete)[:, 1]).max() + 1.0
            lines = np.empty((nz, 2, 2))
            lines[:, 0, 0], lines[:, 1, 0] = -ymax, ymax
            lines[:, :, 1] = zq[:, None]
            b[i] = shapely.length(shapely.intersection(poly, shapely.linestrings(lines))) / 2
        b[:, 0] = 0.0  # closed at the keel tip, bow and stern
        return x, z, b


    mich_x, mich_z, mich_b = michell_offsets(hull, draft_in.value)
    _slope = np.abs(np.gradient(mich_b, mich_x, axis=0)).max()
    mo.md(
        f"Offset grid: {len(mich_x)} stations by {len(mich_z)} levels. Largest hull slope |db/dx| = **{_slope:.2f}** "
        f"(thin-ship theory wants this well under 1; the blunt transom face is what makes it large), beam / length = {hs['wp']['bwl'] / form['lwl']:.2f}."
    )
    return mich_b, mich_x, mich_z


@app.cell
def _():
    taper_in = mo.ui.number(start=0.0, stop=1.0, step=0.05, value=0.2, label="Transom fairing length (m)")
    taper_in
    return (taper_in,)


@app.cell
def _(
    G,
    KNOT,
    calm_resistance,
    dcf_in,
    form,
    mich_b,
    mich_x,
    mich_z,
    nu_in,
    rho_in,
    taper_in,
    up,
    v_req,
    vmax_in,
):
    def hat_weights(nodes, a):
        """Weights w[k, i] with  integral f(s) exp(a[k] s) ds  =  sum_i w[k, i] f(nodes[i])  for f linear between
        the uniformly spaced nodes. a may be complex with Re(a) >= 0; each cell is integrated exactly."""
        a = np.asarray(a, dtype=complex)[:, None]
        h = nodes[1] - nodes[0]
        s = a * h
        small = np.abs(s) < 0.05  # series where the closed form cancels
        ss = np.where(small, 1.0, s)
        em = np.exp(-ss)
        p1 = np.where(small, 0.5 - s / 3 + s**2 / 8, (1 - em * (1 + ss)) / ss**2)
        p2 = np.where(small, 0.5 - s / 6 + s**2 / 24, (ss - 1 + em) / ss**2)
        e = np.exp(a * nodes[1:][None, :])
        w = np.zeros((a.shape[0], len(nodes)), dtype=complex)
        w[:, :-1] += e * h * p1
        w[:, 1:] += e * h * p2
        return w


    def fair_blunt_end(x, b, length):
        """Extend the blunter end of the offsets by `length` m, shrinking its last section linearly to zero.

        A transom runs dry once the boat is moving, so the water sees a hull that continues aft as a hollow in
        the wake. Fairing the offsets this way stands in for that. A pointed end (under 5% of the maximum
        half-breadth) is left alone, as is length 0.
        """
        n = int(round(length / (x[1] - x[0])))
        dx = x[1] - x[0]
        hi, lo = b[-2], b[1]
        if n == 0 or max(hi.max(), lo.max()) < 0.05 * b.max():
            return x, b
        k = np.arange(1, n + 2)
        if hi.max() >= lo.max():
            return (np.concatenate([x[:-1], x[-2] + dx * k]),
                    np.vstack([b[:-1], np.outer(1 - k / (n + 1), hi)]))
        k = k[::-1]
        return (np.concatenate([x[1] - dx * k, x[1:]]),
                np.vstack([np.outer(1 - k / (n + 1), lo), b[1:]]))


    def michell_wave_resistance(V, x, z, b, rho, n_u=2500, u_max=4.0):
        """Michell thin-ship wave resistance (N) at speed V (m/s) for half-breadths b[x, z] (z <= 0 at the waterline)."""
        k0 = G / V**2
        u = np.linspace(0.0, u_max, n_u)
        lam = np.cosh(u)
        kap = k0 * lam
        wx = hat_weights(x, 1j * kap)
        wz = hat_weights(z, k0 * lam**2).real
        amp = -1j * kap * np.einsum("ui,ij,uj->u", wx, b, wz)  # I + iJ, with integration by parts in x
        return 4 * rho * k0**2 * V**2 / np.pi * np.trapezoid(np.abs(amp) ** 2 * lam**2, u)


    mich_xf, mich_bf = fair_blunt_end(mich_x, mich_b, taper_in.value)


    def total_resistance(V, hull_wetted, fins, rho, nu, dcf, wave_grid=None):
        """Calm-water resistance (N) at speeds V (m/s): returns (hull viscous, fin viscous, wave) arrays.

        The wave term uses the faired offsets unless another (x, b) grid is passed as `wave_grid`.
        """
        V = np.atleast_1d(np.asarray(V, dtype=float))
        xw, bw = wave_grid if wave_grid is not None else (mich_xf, mich_bf)
        hull_r, fin_r = calm_resistance(V, hull_wetted, fins, rho, nu, dcf)
        wave = np.array([michell_wave_resistance(v, xw, mich_z, bw, rho) for v in V])
        return hull_r, fin_r, wave


    _kn = np.linspace(0.5, vmax_in.value, 50)
    _args = (up["shell_wetted"], up["fins"], rho_in.value, nu_in.value, dcf_in.value)
    _h, _f, _w = total_resistance(_kn * KNOT, *_args)
    _hr, _fr, _wr = (float(a[0]) for a in total_resistance(v_req * KNOT, *_args))
    R_req = _hr + _fr + _wr  # total calm-water resistance at the required speed

    # spread from the transom treatment: unfaired (upper) and a long 0.45 m fairing (lower)
    _w_raw = total_resistance(_kn * KNOT, *_args, wave_grid=(mich_x, mich_b))[2]
    _w_long = total_resistance(_kn * KNOT, *_args, wave_grid=fair_blunt_end(mich_x, mich_b, 0.45))[2]
    _band = lambda v: tuple(float(total_resistance(v_req * KNOT, *_args, wave_grid=g)[2][0])
                            for g in ((mich_x, mich_b), fair_blunt_end(mich_x, mich_b, 0.45)))
    _wr_raw, _wr_long = _band(v_req)

    _rows = []
    for _k in np.arange(1, vmax_in.value + 1e-9):
        _a, _b, _c = (float(r[0]) for r in total_resistance(_k * KNOT, *_args))
        _rows.append({
            "V (kn)": f"{_k:.0f}", "Fn": f"{_k * KNOT / np.sqrt(G * form['lwl']):.3f}",
            "Viscous (N)": f"{_a + _b:.2f}", "Wave (N)": f"{_c:.2f}", "Total (N)": f"{_a + _b + _c:.2f}",
            "Wave / total": f"{_c / (_a + _b + _c):.0%}",
        })

    _fig, _axs = plt.subplots(1, 2, figsize=(11, 3.6))
    _axs[0].stackplot(_kn, _h, _f, _w, labels=["hull friction + form", "keel + rudder friction", "wave-making (Michell)"], alpha=0.7)
    _axs[0].plot([v_req], [R_req], "k^", ms=9, label=f"required speed, {R_req:.1f} N")
    _axs[0].set_ylabel("Calm-water resistance (N)")
    _axs[0].legend(loc="upper left", fontsize=8)
    _axs[1].plot(_kn, _w, color="C2", label=f"faired {taper_in.value:.2f} m")
    _axs[1].fill_between(_kn, _w_long, _w_raw, color="C2", alpha=0.2, label="unfaired to 0.45 m fairing")
    _axs[1].axvline(v_req, color="gray", ls=":", lw=1)
    _axs[1].set_ylabel("Wave resistance (N)")
    _axs[1].legend(loc="upper left", fontsize=8)
    for _ax in _axs:
        _ax.set_xlabel("Speed (kn)")
        _ax.grid(alpha=0.3)
    mo.vstack([
        mo.md(
            f"At the required {v_req:.2f} kn: viscous **{_hr + _fr:.2f} N**, wave-making **{_wr:.2f} N**, "
            f"total **{R_req:.2f} N** (`R_req`). Wave-making ranges from {_wr_long:.1f} N (0.45 m fairing) "
            f"to {_wr_raw:.1f} N (unfaired transom) depending on how the stern is treated."
        ),
        mo.ui.table(_rows, selection=None, pagination=False),
        _fig,
    ])
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Keel and Rudder Side Force
    With the boat making leeway angle `lambda`, the keel and rudder (rudder fixed at zero deflection) work as lifting surfaces. Their lift slope comes from Helmbold's low-aspect-ratio formula,

    `CL_alpha = 2 pi AR_e / (2 + sqrt(4 + AR_e^2))` per radian, with `CL = CL_alpha lambda` and induced drag `CDi = CL^2 / (pi AR_e)`,

    where `AR_e` is the geometric aspect ratio times an **end-plate factor**. The hull and free surface act as an end plate that raises the effective aspect ratio towards twice the geometric value, so 1.0 is the conservative end and 2.0 the optimistic one. The hull's own side force is ignored, and the fins are taken as unstalled (keep leeway under about 10 degrees).
    """)
    return


@app.cell
def _():
    arf_in = mo.ui.number(start=1.0, stop=2.0, step=0.05, value=1.3, label="End-plate factor on aspect ratio")
    arf_in
    return (arf_in,)


@app.cell
def _(KNOT, arf_in, rho_in, up, v_req):
    def appendage_side_force(V, leeway_deg, fins, rho, ar_factor):
        """Side force Y (N) and induced drag Di (N) of the fins at speed V (m/s) and leeway (deg).

        Y acts to windward of the boat, opposing the sail's side force; Di adds to the resistance.
        """
        V, a = np.broadcast_arrays(np.asarray(V, dtype=float), np.radians(leeway_deg))
        q = 0.5 * rho * V**2
        Y, Di = np.zeros_like(q), np.zeros_like(q)
        for f in fins:
            ar = ar_factor * f["aspect_ratio"]
            cl = 2 * np.pi * ar / (2 + np.sqrt(4 + ar**2)) * a
            Y += q * f["planform"] * cl
            Di += q * f["planform"] * cl**2 / (np.pi * ar)
        return Y, Di


    _rows = []
    for _name, _f in zip(("Keel", "Rudder"), up["fins"]):
        _ar = arf_in.value * _f["aspect_ratio"]
        _s = 2 * np.pi * _ar / (2 + np.sqrt(4 + _ar**2))
        _y, _ = appendage_side_force(v_req * KNOT, 1.0, [_f], rho_in.value, arf_in.value)
        _rows.append({
            "Fin": _name, "Planform (m^2)": f"{_f['planform']:.4f}",
            "Geometric AR": f"{_f['aspect_ratio']:.2f}", "Effective AR": f"{_ar:.2f}",
            "CL_alpha (1/deg)": f"{_s * np.pi / 180:.4f}",
            f"Side force per deg at {v_req:.2f} kn (N)": f"{float(_y):.2f}",
        })

    _lee = np.linspace(0, 10, 41)
    _fig, _axs = plt.subplots(1, 2, figsize=(10, 3.4))
    for _k in (2, 3, 4, 5):
        _y, _d = appendage_side_force(_k * KNOT, _lee, up["fins"], rho_in.value, arf_in.value)
        _axs[0].plot(_lee, _y, label=f"{_k} kn")
        _axs[1].plot(_lee, _d, label=f"{_k} kn")
    _axs[0].set_ylabel("Fin side force (N)")
    _axs[1].set_ylabel("Induced drag (N)")
    for _ax in _axs:
        _ax.set_xlabel("Leeway (deg)")
        _ax.grid(alpha=0.3)
        _ax.legend()
    mo.vstack([mo.ui.table(_rows, selection=None, pagination=False), _fig])
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Wing-Sail Aerodynamics
    The sail is one rigid, symmetric wing (NACA 00xx) turned about its mast by a motor, so there is no sheet trim and no camber, and the angle of attack is set directly. Lift and drag are built in three steps: the planform from area, aspect ratio and taper; two-dimensional section data from NeuralFoil at the sail's Reynolds number; and finite-span corrections for lift slope and induced drag. A last step finds the centre of effort and the torque the mast motor must hold. _To do:_ flap or tail control.

    ### Planform
    The span is `b = sqrt(AR S)`, the root chord `c_r = 2 S / (b (1 + lambda))` and the tip chord `lambda c_r`, where `lambda` is the taper ratio. The mean aerodynamic chord (MAC) and its distance from the root follow from the trapezoid formulas. The root sits on the mast step. The **end-plate factor** multiplies the aspect ratio in the lift and drag calculations only: a sail close to the deck behaves as if it were longer, up to a factor of 2 for a perfect end plate, and 1 means no benefit assumed.
    """)
    return


@app.cell
def _():
    sail_tc_in = mo.ui.number(start=6, stop=24, step=1, value=12, label="Thickness ratio t/c (%, the xx in NACA 00xx)")
    sail_area_in = mo.ui.number(start=0.1, stop=5.0, step=0.01, value=0.65, label="Sail area S (m^2)")
    sail_ar_in = mo.ui.number(start=0.5, stop=6.0, step=0.05, value=1.75, label="Aspect ratio b^2 / S")
    sail_taper_in = mo.ui.number(start=0.2, stop=1.0, step=0.05, value=1.0, label="Taper ratio (tip chord / root chord)")
    sail_arf_in = mo.ui.number(start=1.0, stop=2.0, step=0.05, value=1.0, label="End-plate factor on aspect ratio")
    mo.vstack([
        mo.hstack([sail_tc_in, sail_area_in], justify="start"),
        mo.hstack([sail_ar_in, sail_taper_in, sail_arf_in], justify="start"),
    ])
    return sail_ar_in, sail_area_in, sail_arf_in, sail_taper_in, sail_tc_in


@app.cell
def _(
    airdraft_in,
    draft_in,
    mast_step,
    sail_ar_in,
    sail_area_in,
    sail_arf_in,
    sail_taper_in,
):
    def sail_planform(S, ar, taper):
        """Trapezoidal planform: span, root and tip chord, MAC and its distance from the root (m)."""
        b = np.sqrt(ar * S)
        c_root = 2 * S / (b * (1 + taper))
        return {
            "S": S, "ar": ar, "taper": taper, "b": b, "c_root": c_root, "c_tip": taper * c_root,
            "mac": 2 / 3 * c_root * (1 + taper + taper**2) / (1 + taper),
            "z_mac": b / 6 * (1 + 2 * taper) / (1 + taper),
        }


    sail = sail_planform(sail_area_in.value, sail_ar_in.value, sail_taper_in.value)
    _rig_h = draft_in.value + airdraft_in.value - mast_step[2]
    _rows = [
        ("Span b (m)", f"{sail['b']:.3f}",
         f"{_rig_h:.3f} m available above the step: " + ("OK" if sail["b"] <= _rig_h else "EXCEEDS")),
        ("Root / tip chord (m)", f"{sail['c_root']:.3f} / {sail['c_tip']:.3f}", ""),
        ("Mean aerodynamic chord (m)", f"{sail['mac']:.3f}", f"{sail['z_mac']:.3f} m above the root"),
        ("Effective aspect ratio", f"{sail_arf_in.value * sail['ar']:.2f}", f"geometric {sail['ar']:.2f}"),
    ]

    _c = lambda z: sail["c_root"] + (sail["c_tip"] - sail["c_root"]) * z / sail["b"]
    _x = lambda z: 0.25 * (sail["c_root"] - _c(z))  # unswept quarter-chord line
    _fig, _ax = plt.subplots(figsize=(4.5, 3.6))
    _ax.fill([_x(0), _x(0) + _c(0), _x(sail["b"]) + _c(sail["b"]), _x(sail["b"])],
             [0, 0, sail["b"], sail["b"]], color="steelblue", alpha=0.7)
    _ax.axvline(0.25 * sail["c_root"], color="k", ls="--", lw=1, label="quarter-chord line")
    _ax.axhline(sail["z_mac"], color="r", ls=":", lw=1, label="MAC")
    _ax.set_xlabel("Chordwise (m)")
    _ax.set_ylabel("Above the root (m)")
    _ax.set_aspect("equal")
    _ax.legend(fontsize=8)
    _ax.grid(alpha=0.3)
    mo.hstack([
        mo.ui.table([{"Property": a, "Value": b, "Note": c} for a, b, c in _rows], selection=None, pagination=False),
        _fig,
    ], justify="start")
    return (sail,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Section Data
    Section lift, drag and moment come from NeuralFoil (a neural surrogate for XFOIL) run on the exact NACA 00xx outline, so the thickness ratio above is a live input. The Reynolds number is set by the **design wind** at the height of the mean chord, with the wind taken as the apparent wind for now: `Re = V c_MAC / nu`, and air viscosity from Sutherland's law. The grey curves are the same section at `Re = 3e6`, the usual wind-tunnel reference condition for tabulated NACA data, so the two can be compared. The **analysis confidence** NeuralFoil reports drops where it is extrapolating, which at this low Reynolds number happens past stall.
    """)
    return


@app.cell
def _(
    KNOT,
    air_temp_in,
    alpha_in,
    draft_in,
    mast_step,
    rho_air,
    sail,
    sail_tc_in,
    vdes_in,
    wind_at,
    zref_in,
):
    import neuralfoil as nf


    def section_coords(tc, n=101):
        """NACA 00xx outline (x/c, y/c), trailing edge to leading edge on top, then back along the bottom."""
        s = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))
        yt = 5 * tc * (0.2969 * np.sqrt(s) - 0.1260 * s - 0.3516 * s**2 + 0.2843 * s**3 - 0.1036 * s**4)
        return np.vstack([np.c_[s[::-1], yt[::-1]], np.c_[s[1:], -yt[1:]]])


    SEC_ALPHA = np.arange(-30.0, 30.01, 0.5)


    def section_polar(tc, re, alpha=SEC_ALPHA):
        """Section CL, CD and CM (about the quarter chord) against angle of attack (deg)."""
        r = nf.get_aero_from_coordinates(section_coords(tc), alpha=alpha, Re=re, model_size="xxxlarge")
        return {"alpha": np.asarray(alpha), **{k: np.asarray(r[k]) for k in ("CL", "CD", "CM", "analysis_confidence")}}


    _T = air_temp_in.value + 273.15
    nu_air = 1.716e-5 * (_T / 273.15) ** 1.5 * (273.15 + 110.4) / (_T + 110.4) / rho_air
    sail_z = mast_step[2] - draft_in.value + sail["z_mac"]  # height of the MAC above the waterline
    v_sail = float(wind_at(sail_z, vdes_in.value * KNOT, zref_in.value, alpha_in.value))
    re_sail = v_sail * sail["mac"] / nu_air
    sec = section_polar(sail_tc_in.value / 100, re_sail)
    sec_ref = section_polar(sail_tc_in.value / 100, 3e6)

    _i = np.argmax(sec["CL"])
    _slope = (np.interp(1, sec["alpha"], sec["CL"]) - np.interp(-1, sec["alpha"], sec["CL"])) / 2
    _rows = [
        ("Wind at the MAC (m/s)", f"{v_sail:.2f}", f"design wind, {sail_z:.2f} m above the waterline"),
        ("Reynolds number", f"{re_sail:.3g}", f"MAC {sail['mac']:.3f} m, nu {nu_air:.3g} m^2/s"),
        ("CL slope (per deg)", f"{_slope:.4f}", f"thin-airfoil theory 2 pi: {2 * np.pi * np.pi / 180:.4f}"),
        ("CL max / stall angle (deg)", f"{sec['CL'][_i]:.3f} / {sec['alpha'][_i]:.1f}", ""),
        ("CD at zero lift", f"{np.interp(0, sec['alpha'], sec['CD']):.4f}", ""),
    ]
    _fig, _axs = plt.subplots(1, 3, figsize=(11, 3.3))
    for _s, _kw in ((sec_ref, dict(color="gray", ls="--", label="Re = 3e6")),
                    (sec, dict(color="C0", label=f"Re = {re_sail:.2g}"))):
        _axs[0].plot(_s["alpha"], _s["CL"], **_kw)
        _axs[1].plot(_s["CD"], _s["CL"], **_kw)
        _axs[2].plot(_s["alpha"], _s["CM"], **_kw)
    _axs[0].set(xlabel="Angle of attack (deg)", ylabel="Section CL", xlim=(-30, 30))
    _axs[1].set(xlabel="Section CD", ylabel="Section CL", xlim=(0, 0.25))
    _axs[2].set(xlabel="Angle of attack (deg)", ylabel="Section CM about c/4", xlim=(-30, 30))
    for _ax in _axs:
        _ax.grid(alpha=0.3)
    _axs[0].legend()
    _low = sec["alpha"][sec["analysis_confidence"] < 0.8]
    mo.vstack([
        mo.ui.table([{"Property": a, "Value": b, "Note": c} for a, b, c in _rows], selection=None, pagination=False),
        _fig,
        mo.md(f"NeuralFoil confidence is below 0.8 for {len(_low)} of {len(sec['alpha'])} angles"
              + (f" (|alpha| from {np.abs(_low).min():.1f} deg)." if len(_low) else ".")),
    ])
    return re_sail, sail_z, section_polar, v_sail


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Finite-Span Corrections
    The sail's aspect ratio is low, so the section data cannot be used directly. Three corrections turn the section polar into a sail polar, all using the effective aspect ratio `AR_eff`.

    - **Lift slope:** Helmbold's formula, `a = pi AR_eff / (1 + sqrt(1 + (pi AR_eff / a0)^2))`, with `a0` the section lift slope from NeuralFoil. It stays accurate at low aspect ratio, where lifting-line theory over-predicts the slope.
    - **Downwash:** the angle of attack is reduced by an induced angle proportional to the lift, `alpha_eff = alpha - kappa CL` with `kappa = 1/a - 1/a0`. Reading the section polar at `alpha_eff` keeps the section's stall shape while the linear slope is exactly Helmbold's.
    - **Induced drag:** `CD = cd(alpha_eff) + CL^2 / (pi AR_eff e)`. The span efficiency `e` comes from a Glauert lifting-line solution for the taper ratio.

    Low aspect ratio wings stall later and softer than the section does because of tip-vortex lift, which this model does not capture, so the stall region is conservative.
    """)
    return


@app.cell
def _(re_sail, sail, sail_arf_in, sail_taper_in, sail_tc_in, section_polar):
    def glauert_e(ar, taper, a0=2 * np.pi, n=40):
        """Span efficiency of a linearly tapered wing from the Glauert lifting-line series."""
        th = np.arange(1, n + 1) * np.pi / (2 * n)
        odd = np.arange(1, 2 * n, 2)
        mu = a0 * (1 - (1 - taper) * np.cos(th)) / (2 * ar * (1 + taper))
        A = np.linalg.solve(np.sin(np.outer(th, odd)) * (odd * mu[:, None] + np.sin(th)[:, None]), mu * np.sin(th))
        return 1 / (1 + np.sum(odd[1:] * (A[1:] / A[0]) ** 2))


    def sail_polar(tc, re, ar_eff, taper):
        """Sail CL and CD against angle of attack (deg), from the section polar and finite-span corrections."""
        s = section_polar(tc, re)
        a0 = (np.interp(1, s["alpha"], s["CL"]) - np.interp(-1, s["alpha"], s["CL"])) / np.radians(2)
        a = np.pi * ar_eff / (1 + np.sqrt(1 + (np.pi * ar_eff / a0) ** 2))
        kappa = np.degrees(1 / a - 1 / a0)
        e = glauert_e(ar_eff, taper)
        al = s["alpha"]
        cl = a * np.radians(al)
        for _ in range(100):  # damped fixed point for CL = cl_section(alpha - kappa CL)
            cl = 0.5 * cl + 0.5 * np.interp(al - kappa * cl, al, s["CL"])
        al_eff = al - kappa * cl
        cd = np.interp(al_eff, al, s["CD"]) + cl**2 / (np.pi * ar_eff * e)
        return {"alpha": al, "alpha_eff": al_eff, "CL": cl, "CD": cd, "a0": a0, "a": a, "e": e, "section": s}


    sail_ar_eff = sail_arf_in.value * sail["ar"]
    sp = sail_polar(sail_tc_in.value / 100, re_sail, sail_ar_eff, sail_taper_in.value)

    _m = (sp["alpha"] >= 0) & (sp["alpha"] <= 25)
    _i = np.argmax(sp["CL"][_m])
    _k = np.argmax((sp["CL"] / sp["CD"])[_m])
    _rows = [
        ("Section / sail lift slope (per deg)", f"{sp['a0'] * np.pi / 180:.4f} / {sp['a'] * np.pi / 180:.4f}", ""),
        ("Span efficiency e", f"{sp['e']:.3f}", f"Glauert, taper {sail_taper_in.value:.2f}"),
        ("CL max / stall angle (deg)", f"{sp['CL'][_m][_i]:.3f} / {sp['alpha'][_m][_i]:.1f}", ""),
        ("Best CL/CD / at angle (deg)", f"{(sp['CL'] / sp['CD'])[_m][_k]:.2f} / {sp['alpha'][_m][_k]:.1f}",
         f"CL {sp['CL'][_m][_k]:.3f}, CD {sp['CD'][_m][_k]:.4f}"),
    ]
    _fig, _axs = plt.subplots(1, 4, figsize=(13, 3.3))
    _s = sp["section"]
    _axs[0].plot(_s["alpha"], _s["CL"], "gray", ls="--", label="section")
    _axs[0].plot(sp["alpha"], sp["CL"], label="sail")
    _axs[1].plot(sp["alpha"], sp["CD"], label="sail")
    _axs[1].plot(_s["alpha"], _s["CD"], "gray", ls="--", label="section")
    _axs[2].plot(sp["CD"], sp["CL"])
    _axs[3].plot(sp["alpha"], sp["CL"] / sp["CD"])
    _axs[0].set(xlabel="Angle of attack (deg)", ylabel="CL", xlim=(-30, 30))
    _axs[1].set(xlabel="Angle of attack (deg)", ylabel="CD", xlim=(-30, 30), ylim=(0, 0.6))
    _axs[2].set(xlabel="CD", ylabel="CL", xlim=(0, 0.6))
    _axs[3].set(xlabel="Angle of attack (deg)", ylabel="CL / CD", xlim=(-30, 30))
    for _ax in _axs:
        _ax.grid(alpha=0.3)
    _axs[0].legend()
    _axs[1].legend()
    mo.vstack([mo.ui.table([{"Property": a, "Value": b, "Note": c} for a, b, c in _rows], selection=None, pagination=False), _fig])
    return (sp,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Centre of Effort and Mast Torque
    The sail turns about its mast, so the mast torque sets the motor size. For a symmetric section the lift acts at the quarter chord at small angles and the centre of pressure moves aft as the moment grows, `x_cp / c = 0.25 - CM / CN`, with `CM` the section moment about the quarter chord at the effective angle and `CN = CL cos(alpha) + CD sin(alpha)` the chord-normal force coefficient. The moment about a mast at chord fraction `x_m` is `CM_mast = CM + CN (x_m - 0.25)`, and the torque is `CM_mast q S c_MAC`. A mast at the quarter chord leaves only the small section moment; a mast ahead of it makes the sail try to feather, and one behind it makes it try to weathercock. Which of the two is the safe failure if the motor lets go is a design choice.

    Spanwise, the lift is assumed elliptical, which puts its centroid at `4 b / (3 pi)` above the root (the deck acts as the symmetry plane). That height, against the centre of lateral resistance, is the heeling arm used in the force balance. The fore-and-aft lead needs the sail angle to the boat, so it waits for that section.
    """)
    return


@app.cell
def _():
    sail_mast_in = mo.ui.number(start=0.0, stop=0.6, step=0.01, value=0.25, label="Mast axis, as a fraction of chord from the leading edge")
    sail_mast_in
    return (sail_mast_in,)


@app.cell
def _(
    KNOT,
    alpha_in,
    mast_step,
    rho_air,
    sail,
    sail_mast_in,
    sail_z,
    sp,
    up,
    v_sail,
    vdes_in,
    vsurv_in,
    wind_at,
    zref_in,
):
    _a = sp["alpha"]
    _cm_c4 = np.interp(sp["alpha_eff"], _a, sp["section"]["CM"])
    sail_cn = sp["CL"] * np.cos(np.radians(_a)) + sp["CD"] * np.sin(np.radians(_a))
    sail_cm_mast = _cm_c4 + sail_cn * (sail_mast_in.value - 0.25)
    _x_cp = np.where(np.abs(sail_cn) > 0.1, 0.25 - _cm_c4 / np.where(sail_cn == 0, 1, sail_cn), np.nan)


    def mast_torque(v):
        """Mast torque (N m) against angle of attack for an apparent wind v (m/s) at the MAC."""
        return sail_cm_mast * 0.5 * rho_air * v**2 * sail["S"] * sail["mac"]


    v_surv = float(wind_at(sail_z, vsurv_in.value * KNOT, zref_in.value, alpha_in.value))
    sail_ce_height = 4 * sail["b"] / (3 * np.pi)  # lift centroid above the root, elliptical loading
    _m = (_a >= 0) & (_a <= 30)
    _t_des, _t_surv = mast_torque(v_sail), mast_torque(v_surv)
    _id, _is = np.argmax(np.abs(_t_des[_m])), np.argmax(np.abs(_t_surv[_m]))
    _rows = [
        ("Lift centroid above the root (m)", f"{sail_ce_height:.3f}", f"{0.4244:.3f} b"),
        ("Centroid above the waterline (m)", f"{sail_z - sail['z_mac'] + sail_ce_height:.3f}", ""),
        ("Centroid above the CLP (m)", f"{mast_step[2] + sail_ce_height - up['clp_z']:.3f}", "heeling arm"),
        ("Max mast torque, design wind (N m)", f"{abs(_t_des[_m][_id]):.2f}",
         f"{v_sail:.1f} m/s, at {_a[_m][_id]:.1f} deg"),
        ("Max mast torque, survival wind (N m)", f"{abs(_t_surv[_m][_is]):.2f}",
         f"{v_surv:.1f} m/s, at {_a[_m][_is]:.1f} deg"),
    ]
    _fig, _axs = plt.subplots(1, 2, figsize=(9, 3.3))
    _axs[0].plot(_a, _x_cp)
    _axs[0].axhline(sail_mast_in.value, color="k", ls="--", lw=1, label="mast axis")
    _axs[0].set(xlabel="Angle of attack (deg)", ylabel="Centre of pressure, x / c", xlim=(0, 30), ylim=(0, 0.6))
    _axs[0].legend()
    _axs[1].plot(_a, _t_des, label=f"design wind {vdes_in.value:.0f} kn")
    _axs[1].plot(_a, _t_surv, label=f"survival wind {vsurv_in.value:.0f} kn")
    _axs[1].set(xlabel="Angle of attack (deg)", ylabel="Mast torque (N m)", xlim=(-30, 30))
    _axs[1].legend()
    for _ax in _axs:
        _ax.grid(alpha=0.3)
    mo.vstack([mo.ui.table([{"Property": a, "Value": b, "Note": c} for a, b, c in _rows], selection=None, pagination=False), _fig])
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Force Balance and Heel
    _To do:_ sail force against hydrodynamic force over the points of sail, equilibrium speed, heel and helm, checked against the limits above.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Structural Loads
    _To do:_ mast and step load cases from the design and survival winds, and the resulting rig mass estimate.
    """)
    return


if __name__ == "__main__":
    app.run()
