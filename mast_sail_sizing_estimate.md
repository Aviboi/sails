# Transatlantic Hull — Mast Position & Sail Sizing Estimate

**Status:** First-pass estimate. Keel and ballast are not yet modeled/designed, so several
inputs below are illustrative placeholders drawn from past CUSail designs. Re-run the
CAD procedures in this document once a keel STEP file and ballast mass exist.

**Sail system assumed:** freely-rotating solid (wing) sail on a rotating mast, self-steered
by a servo-controlled tail sail (no separate rudder — lateral resistance comes from the
keel only, per the Comp Hull "balance through keel" design decision).

---

## 1. Source legend

Every number below is tagged with where it came from:

- **[PPTX]** — stated directly in `Hull_Review_from_Jason_and_Skyler.pptx`
- **[CAD]** — computed numerically from `Hull_Form.STEP` (procedure included, reproducible)
- **[ASSUMED]** — placeholder scaled from past CUSail mechanical reports, not yet a real
  design value for this boat
- **[CALC]** — derived from the above via an equation (equation shown)

---

## 2. Inputs

| Quantity | Value | Source |
|---|---|---|
| Boat length (LOA) | 2.000 m | [PPTX] |
| Estimated total mass | 25 kg | [PPTX] (subject to change) |
| Designed max speed | 3 knots | [PPTX] |
| Max beam | 0.5 m | [PPTX] |
| Prismatic coefficient (Cp) | 0.55 | [PPTX] |
| Block coefficient (Cb) | 0.385 | [PPTX] |
| Water density (salt, ~15°C) | 1025 kg/m³ | standard reference value |
| Water kinematic viscosity (salt, ~15°C) | 1.19×10⁻⁶ m²/s | standard reference value |
| Air density | 1.225 kg/m³ | standard reference value |

---

## 3. CAD-derived geometry (reproducible)

### 3.1 Procedure

Requires `cadquery` (`pip install --break-system-packages cadquery`).

```python
import cadquery as cq
import numpy as np

hull = cq.importers.importStep("Hull_Form.STEP").val()
bb = hull.BoundingBox()

# --- Step 1: find the design waterline Z-height ---
# Binary-search the horizontal cutting plane whose submerged volume displaces
# the target mass at the chosen water density.
def submerged_volume(z_cut):
    z0 = bb.zmin - 20
    height = z_cut - z0
    box = cq.Solid.makeBox(bb.xlen + 40, bb.ylen + 40, height,
                            pnt=cq.Vector(bb.xmin - 20, bb.ymin - 20, z0))
    return hull.intersect(box).Volume()

def find_waterline(target_kg, rho):
    target_mm3 = target_kg / rho * 1e9
    lo, hi = bb.zmin, bb.zmax
    for _ in range(40):
        mid = (lo + hi) / 2
        if submerged_volume(mid) < target_mm3:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

z_wl = find_waterline(target_kg=25, rho=1025)  # saltwater, design mass

# --- Step 2: LWL, beam at waterline ---
# Sample stations along X; a station is "at or below" the waterline if the
# submerged solid has material there at z_wl.
xs = np.linspace(bb.xmin, bb.xmax, 401)
# ... (see full script: intersect thin slices, find x-range where bottom_z < z_wl)

# --- Step 3: submerged side-profile (X-Z) area & centroid ---
# For each X station, take a thin slice, find the local bottom_z, integrate
# depth(x) = max(0, z_wl - bottom_z(x)) over x (trapezoidal rule) for area,
# and integrate x*depth(x) for the first moment -> centroid_x = moment/area.

# --- Step 4: wetted surface area ---
# Build the submerged solid (hull ∩ box up to z_wl exactly), enumerate its
# Faces(), and sum the area of all faces EXCEPT the flat artificial cap face
# created by the cut (identified as the face whose bounding-box z-height ≈ 0).
```

Full working script is in the project chat history; the key trick is separating the
real hull skin faces from the flat "cap" face introduced by cutting the solid at the
waterline plane (cap has zero z-extent in its bounding box).

### 3.2 Results

| Quantity | Value | Source |
|---|---|---|
| Design waterline height (Z, relative to CAD origin) | −40.6 mm | [CAD] (25 kg, saltwater) |
| Hull bottom (Z) | −103.7 mm | [CAD] |
| Draft at design waterline | 63.1 mm | [CAD] |
| Waterline length (LWL) | 1.736 m | [CAD] |
| Beam at waterline | 0.406 m | [CAD] |
| Bow overhang above design waterline | ~0.264 m (~13% LOA) | [CAD] |
| Submerged hull side-profile area (no keel) | 0.0777 m² | [CAD] |
| Submerged hull side-profile centroid (from bow) | 1.153 m (57.6% LOA) | [CAD] |
| Wetted surface area below waterline (hull skin only) | 0.578 m² | [CAD] |

**Validation check [CALC]:** Hull-speed relation using CAD-derived LWL —

$$V_{hull} = 1.34\sqrt{LWL[ft]} = 1.34\sqrt{5.696} = 3.20 \text{ knots}$$

This matches the stated 3-knot design speed [PPTX] closely, suggesting the hull form and
target speed are self-consistent.

---

## 4. Assumed keel / ballast (placeholder — no keel CAD exists yet)

| Quantity | Value | Source |
|---|---|---|
| Keel planform area ($A_{keel}$) | 0.30 m² | [ASSUMED] mid-range of past CUSail keels (0.2–0.4 m²), scaled up |
| Keel span/depth | 1.0 m | [ASSUMED] typical past keel length |
| Keel centroid position (from bow) | 1.05 m (~52% LOA) | [ASSUMED] near-midship placement |
| Keel lift coefficient ($C_{l,keel}$) | 0.3 | [ASSUMED] modest angle of attack, symmetric foil |
| Keel moment arm below waterline ($r_{keel}$) | 0.55 m | [ASSUMED] ≈ half keel depth |
| Ballast mass ($m_{ballast}$) | 8 kg | [ASSUMED] scaled from past boats' 2.6–10 kg range |
| Ballast moment arm ($r_{ballast}$) | 1.0 m | [ASSUMED] ≈ hull draft + keel depth |

---

## 5. Mast position

### 5.1 Equations

Center of lateral resistance (area-weighted centroid of underwater profile):

$$x_{CLR} = \frac{A_{hull}\,x_{hull} + A_{keel}\,x_{keel}}{A_{hull}+A_{keel}}$$

Mast/CE lead ahead of CLR (5–10% of LWL; 5% used here per SP26 team precedent):

$$x_{mast} \approx x_{CE} \approx x_{CLR} - lead, \qquad lead = 0.05\times LWL$$

### 5.2 Calculation

$$x_{CLR} = \frac{(0.0777)(1.153) + (0.30)(1.05)}{0.0777+0.30} = 1.07\text{ m aft of bow} \quad \textbf{[CALC]}$$

$$lead = 0.05\times1.736 = 0.087\text{ m} \quad \textbf{[CALC]}$$

$$x_{mast} = 1.07 - 0.087 \approx \mathbf{0.98\text{ m aft of bow}\;(\approx49\%\;LOA)} \quad \textbf{[CALC]}$$

**Sensitivity note:** $A_{keel} \gg A_{hull}$ in this estimate, so $x_{CLR}$ is dominated by
the assumed keel position — this result should be treated as low-confidence until real
keel geometry replaces the placeholder.

---

## 6. Sail area — drag/hull-speed method

### 6.1 Equations

ITTC-1957 flat-plate friction line:

$$Re = \frac{V\cdot LWL}{\nu}, \qquad C_f = \frac{0.075}{(\log_{10}Re - 2)^2}$$

Friction resistance:

$$R_f = \tfrac12\rho_{water} V^2 S_{wetted}\, C_f$$

Required sail lift to overcome drag at wind speed $V$:

$$A_{sail} = \frac{2F}{\rho_{air}V^2 C_l}$$

### 6.2 Calculation

At hull speed $V=1.646$ m/s, $LWL=1.736$ m [CAD], $\nu=1.19\times10^{-6}$ m²/s:

$$Re = 2.40\times10^6, \qquad C_f = 0.0039 \quad \textbf{[CALC]}$$

$$R_f = \tfrac12(1025)(1.646)^2(0.578)(0.0039) \approx 3.1\text{ N (friction only)} \quad \textbf{[CALC, from CAD wetted area]}$$

**Caveat:** this is friction drag only. Near hull speed (SLR = 1.34) wave-making
(residuary) resistance is significant and not captured by a flat-plate estimate. Planning
range used below: 3.1 N (friction-only lower bound) to 9 N (≈3× margin for residuary
resistance) — **[ASSUMED margin, not derived]**. Replace with a proper resistance
prediction (Delft series regression, CFD, or tow-tank data) when available.

### 6.3 Results — sail area vs. wind speed ($C_l = 1$, $\rho_{air}=1.225$)

| Wind speed | Area for 3.1 N | Area for 9 N | Source |
|---|---|---|---|
| 2.5 m/s | 0.81 m² | 2.35 m² | [CALC] |
| 4.0 m/s | 0.32 m² | 0.92 m² | [CALC] |
| 6.0 m/s | 0.14 m² | 0.41 m² | [CALC] |

**Working estimate: $A_{sail} \approx 0.4$–$0.6\text{ m}^2$** to reach hull speed around
4–5 m/s true wind with margin. **[CALC, judgment call within the above range]**

---

## 7. Righting-moment / heel-angle check

### 7.1 Equation

$$v_{air} = \sqrt{\alpha\tan\theta}, \qquad
\alpha = \frac{m_{ballast}\,g\,r_{ballast}}{\dfrac{1}{200}C_{l,keel}\,\rho_{water}\,A_{keel}\,r_{keel} \;+\; \dfrac12 C_{l,sail}\,\rho_{air}\,A_{sail}\,r_{sail}}$$

(Source of equation form: Fall 2018 Mechanical Report, simplified moment balance about
heel axis.)

### 7.2 Inputs specific to this section

| Quantity | Value | Source |
|---|---|---|
| $A_{sail}$ | 0.5 m² | [CALC] (midpoint of §6.3 working estimate) |
| $r_{sail}$ | 0.77 m | [ASSUMED] freeboard (0.27 m [CAD]) + half sail height (0.5 m [ASSUMED]) |
| $C_{l,sail}$ | 1.0 | [ASSUMED] |

### 7.3 Calculation

$$\alpha = \frac{(8)(9.81)(1.0)}{\frac{1}{200}(0.3)(1025)(0.30)(0.55) + \frac12(1.0)(1.225)(0.5)(0.77)} \approx 160\ \text{m}^2/\text{s}^2 \quad \textbf{[CALC]}$$

| Wind speed | Heel angle | Source |
|---|---|---|
| 6 m/s | ~13° | [CALC] |
| 8 m/s | ~22° | [CALC] |
| 10 m/s | ~32° | [CALC] |

This progression looks reasonable for an unattended, stability-focused ocean-crossing
boat, **contingent on the §4 keel/ballast placeholders being close to the eventual real
design.**

---

## 8. Tail sail + servo sizing

### 8.1 Equations

Torque the tail sail must generate about the mast axis:

$$T = C_{l,tail}\cdot\tfrac12\rho_{air}V^2 A_{tail}\, r_{tail}$$

Required gear ratio given a servo's rated torque $T_{servo}$ and a safety factor $FS$:

$$GR \geq \frac{FS\cdot T}{T_{servo}}$$

### 8.2 Inputs

| Quantity | Value | Source |
|---|---|---|
| $A_{tail}$ | 0.12 m² | [ASSUMED] scaled up from past 0.10–0.11 m² tail sails |
| $r_{tail}$ | 0.5 m | [ASSUMED] scaled up from past 0.35–0.8 m crossmast arms |
| $C_{l,tail}$ | 1.0 | [ASSUMED] NACA 0018 near 10° AoA, consistent with past reports |
| Design gust speed | 10 m/s | [ASSUMED] worst-case, matches §7 upper heel-check bound |
| Safety factor | 1.5 | [ASSUMED] standard mobile-vehicle FS used in past reports |
| Reference servo torque (HS-785HB) | 1.07 N·m | [PAST DESIGN] historical CUSail servo spec |

### 8.3 Calculation

$$T = (1.0)\cdot\tfrac12(1.225)(10)^2(0.12)(0.5) \approx 3.7\text{ N·m} \quad \textbf{[CALC]}$$

$$T_{required,FS} = 1.5\times3.7 \approx 5.5\text{ N·m} \quad \textbf{[CALC]}$$

$$GR \geq \frac{5.5}{1.07} \approx \mathbf{5.1{:}1} \quad \textbf{[CALC]}$$

**Flag:** this is notably higher than the 3:1–4:1 ratios used in past years, which were
identified (Fall 2018, 2019 reports) as insufficient and a cause of course-holding
failures. Plan for either a higher gear ratio / stronger servo, or revisit
$A_{tail}$/$r_{tail}$ once real numbers replace the §8.2 placeholders.

---

## 9. Summary table

| Result | Value | Confidence |
|---|---|---|
| Mast position (aft of bow) | 0.98 m (~49% LOA) | Low — depends on assumed keel position |
| Working sail area | 0.4–0.6 m² | Medium — drag basis is real (CAD wetted area), residuary margin is assumed |
| Max heel at 10 m/s gust | ~32° | Low — depends on assumed ballast/keel |
| Tail sail area / arm | 0.12 m² / 0.5 m | Placeholder |
| Required servo gear ratio | ≥5.1:1 | Medium — depends on tail sail placeholders |

## 10. Next steps to de-risk this estimate

1. Model the keel (or provide target dimensions) and re-run §3 with a combined
   hull+keel STEP assembly to get a real $x_{CLR}$.
2. Pin down ballast mass from a full mass budget; re-run §7 with real values.
3. Replace the friction-only drag estimate (§6) with a residuary resistance prediction
   (Delft series or CFD) to tighten the sail area range.
4. Confirm tail sail geometry and re-check servo/gear selection against actual
   available hardware.
