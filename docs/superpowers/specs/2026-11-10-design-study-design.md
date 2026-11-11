# Design study mode for the sail notebook

Date: 2026-11-10. Status: draft for approval.

## Intent

`notebooks/notebook.py` currently evaluates one design. It has a few one-off sweeps (sail area × aspect ratio speed, mast sizing) that nothing reads. The goal is to turn it towards a **design study**: requirements and modelling choices are inputs, and designs and their performance are outputs. The main use is seeing **trends** as design parameters change, so the user can choose parameters and see which requirement is binding where. It is not a black-box optimiser.

The existing Inputs section, widgets and single-design cells stay, so a specific design can still be tested.

## Design variables (what gets swept)

- Sail area and aspect ratio.
- Mast step position: x, plus the deck-to-sail-foot gap. Mast length = sail span + gap, with the mast top flush with the sail top. Mast length is therefore derived, not free. (The gap may map onto the existing `step_dz_in`. To be confirmed in the code.)
- Mast tube outer diameter (OD) and inner diameter (ID), as **free inputs**. Today the wall is solved by the structural calculation. In study mode strength and deflection become pass/fail margins on a given tube.

## Inputs to the study

The existing `requirements`, `assumptions`, `estimates` and `constants` groups. The study reads them, so changing a wind speed, the distance or `taper_in` redraws everything.

## Objectives (maximise margin, shown as shading and margin lines)

- **Survivability:** survival heeling moment against righting moment (with the rig), tip deflection, mast strength.
- **Stability:** heel limit against usable stability range, GM, downflooding angle.

## Thresholds (pass or fail, not optimised)

- Speed: at least the required speed (1.04 kn) at the relevant winds. Faster is secondary.
- Total mass: at most a cap. Lighter is secondary.
- **Manufacturing limits:**
  - wall thickness (OD − ID)/2 at least a minimum
  - OD at most the drivetrain mount limit
  - mast length at most a maximum
  - sail area at most a maximum
  - rig mass at most 25 kg (existing)
- **Standard tube sizes:** OD and ID snap to a stock list.

## Graded manufacturing score

Sail **bulk**, shown as a shaded quantity or margin line. Chord drives bulk faster than span, so at fixed area a higher aspect ratio is easier to build. This trades against structural and induced-drag costs that the maps already show.

## How results are shown

A combination of two views, always marking the current design and shading the infeasible side:

- **Maps:** colour is a margin (survival or stability), contours are the binding thresholds. Used for the pair that interacts most, sail area × aspect ratio.
- **Margin lines:** one panel per group of related variables, with a line per constraint margin (0 = limit), so the lowest line is the one that binds. Groups: mast tube (OD, ID), mast step (x, gap).

## Structure (builder's call, to confirm in the code)

One function takes a design, requirements and assumptions, and returns performance numbers and a margin for each of the 14 existing Design Summary checks, plus the new manufacturing limits. The sweeps call it, and the existing single-design cells keep their widgets. This needs the evaluation (now spread over about 20 cells that read widget values) to be callable with explicit parameters. The cost of one evaluation limits how large a sweep can be, and needs measuring first.

## Goals

- Trends in survivability and stability across the design variables.
- Visible binding constraints, and where the design is most constrained.
- Existing single-design evaluation still works.

## Non-goals

- Automatic optimisation, or a single "best design" answer.
- New physics. Model-fidelity items in `TODO.md` are unchanged.

## Anti-goals

- Hard-coded defaults or magic numbers in the sweep: new limits are `Param` entries in the right group, per the project conventions.
- A sweep that silently disagrees with the single-design evaluation.

## Builder's calls (flagged, not agreed)

- Placeholder limits for minimum wall, drivetrain OD, maximum mast length, maximum sail area and mass cap: new `Param` entries in `requirements`, clearly marked placeholders.
- Stock tubes: a common carbon tube range as a placeholder list in `assumptions`, since no list was given.
- Bulk metric: chord² × thickness, or similar, to be chosen when built.
- Which margins appear on which plot.

## Open questions

- Cost of one evaluation, and so the practical sweep resolution.
- How the all-up mass correction (one-way) interacts with sweeping rig mass. It may need to move upstream when sail size varies.
- Whether the gap maps onto `step_dz_in`.

## Housekeeping

Changes go through a live marimo session with `/marimo-pair`, per `CLAUDE.md`. Update `NOTEBOOK_OVERVIEW.md` and `TODO.md` when the change lands.
