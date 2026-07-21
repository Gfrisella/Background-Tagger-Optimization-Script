# Transverse Muon Background Detector Optimization

## Overview

This repository contains a simulation and optimization framework for designing a **transverse detector system** aimed at suppressing the combinatorial background produced by muons.

The central objective is to determine whether a system of detector layers installed along the decay vessel can:

1. Detect muons crossing the vessel aperture.
2. Reconstruct their trajectories.
3. Identify muons that would otherwise enter the downstream spectrometer or signal region.
4. Reject combinations of unrelated muons that mimic a displaced heavy neutral lepton (HNL) decay.
5. Minimize the detector cost while preserving sufficient tracking and rejection performance.

The optimization explores the trade-off between:

* Detector technology.
* Detector spatial and timing resolution.
* Detector efficiency.
* Detector geometry.
* Number and position of detector layers.
* Active detector area.
* Estimated channel cost.
* Track-reconstruction performance.
* Residual combinatorial background.

The ultimate design goal is to investigate whether the muon combinatorial background can be reduced to a negligible level, ideally approaching **zero surviving background candidates** within the simulated sample.

---

## Detector Concept

The detector consists of two components:

### 1. Fixed entrance trackers

Three tracking layers are placed immediately upstream of the vessel:

```text
z = 30.7 m
z = 30.8 m
z = 30.9 m
```

These layers provide an initial measurement of the incoming muon trajectory.

The current implementation uses:

```text
Technology: Straw tubes
```

with an active area of:

```text
x: ±1.8 m
y: ±1.35 m
```

The entrance trackers provide the initial direction and position information required to extrapolate muons through the vessel.

---

### 2. Optimized transverse detector layers

Additional detector layers are placed along the vessel between:

```text
31 m ≤ z ≤ 81 m
```

Their positions, technologies, and transverse margins are optimization parameters.

A detector layer is described by:

```python
{
    "z":          detector_position,
    "technology": detector_technology,
    "margin_x":   additional_x_margin,
    "margin_y":   additional_y_margin,
}
```

The detector geometry follows the expanding vessel aperture.

The transverse detector covers the region between the vessel boundary and an external margin:

```text
vessel aperture < detector aperture
```

This allows the detector to identify particles that leave the vessel and cross the surrounding transverse detector system.

---

## Input Data

The input file is:

```text
TRY6_UBT_to_T1_combined.pkl
```

The file contains information for two detector planes:

```text
Plane 0 → UBT
Plane 1 → T1
```

For each muon, the following quantities are used:

```text
px, py, pz
x, y, z
```

The UBT plane is used as the starting point of the simulation:

```text
z0 = 30.6 m
```

The T1 plane provides the reference position used to evaluate the final track extrapolation.

---

# Vessel Geometry

The vessel aperture is modeled as a linearly expanding tapered aperture.

The vessel begins at:

```text
z0 = 31 m
```

and has a length of:

```text
L = 50 m
```

The semi-apertures evolve from:

```text
x: 0.5 m → 2.0 m
y: 2.7 m → 6.0 m
```

The aperture is therefore:

```text
ax(z) = 0.5 + (2.0 - 0.5) × s/L

ay(z) = 2.7 + (6.0 - 2.7) × s/L
```

where:

```text
s = clip(z - 31, 0, 50)
```

This geometry is used to determine whether a particle remains inside the vessel or exits through the transverse aperture.

---

# Detector Acceptance

For a detector layer, a particle is accepted if it lies inside the active detector area:

```text
|x| ≤ ax_detector
|y| ≤ ay_detector
```

For the entrance trackers, this is the only acceptance requirement.

For lateral detectors, the particle must additionally be outside the vessel:

```text
|x| ≥ ax_vessel
OR
|y| ≥ ay_vessel
```

Therefore, lateral detector acceptance is:

```text
inside detector
AND
outside vessel
```

This corresponds to a detector surrounding the vessel and detecting muons that leave the decay volume.

---

# Detector Technologies

Three detector technologies are currently implemented.

## Technology A — Straw Tubes

```text
Name:        Straw
Relative cost/channel: 1.0
Pitch:       10 mm
Spatial resolution: 150 μm
Time resolution:    2 ns
Efficiency:         98%
```

This technology represents the low-cost baseline.

It provides relatively coarse spatial resolution but is attractive for large-area coverage.

---

## Technology B — Scintillating Fibres

```text
Name:        Fiber
Relative cost/channel: 4.0
Pitch:       250 μm
Spatial resolution: 70 μm
Time resolution:    500 ps
Efficiency:         99.5%
```

This technology provides improved spatial and timing resolution at a higher channel cost.

It is potentially useful for layers where improved track resolution significantly reduces background candidates.

---

## Technology C — Silicon Pixels

```text
Name:        Pixel
Relative cost/channel: 20.0
Pitch:       55 μm
Spatial resolution: 10 μm
Time resolution:    50 ps
Efficiency:         99.9%
```

Silicon pixels provide the highest precision but are significantly more expensive.

They are therefore particularly relevant for optimization studies investigating whether a small number of high-precision layers can replace a larger number of lower-cost detectors.

---

# Particle Propagation

The current simulation uses linear transport.

For a particle starting at:

```text
(x, y, z0)
```

with momentum:

```text
(px, py, pz)
```

the position at a new longitudinal coordinate is:

```text
x_new = x + px/pz × (z_new - z0)

y_new = y + py/pz × (z_new - z0)
```

This approximation assumes straight-line propagation between detector layers.

Magnetic fields, energy loss, multiple scattering, and other transport effects are not currently included in this implementation.

---

# Detector Simulation

For every detector layer:

1. The particle is propagated to the detector position.
2. The detector acceptance is evaluated.
3. A random detection efficiency is applied.
4. A spatial measurement error is generated.
5. The resulting hit is stored.

The detector efficiency is sampled according to:

```python
random() < detector_efficiency
```

For detected hits, Gaussian spatial smearing is applied:

```text
x_measured = x_true + Gaussian(0, σx)

y_measured = y_true + Gaussian(0, σy)
```

The simulation stores:

```text
particle ID
layer ID
z position
x position
y position
detector technology
```

---

# Track Reconstruction

A particle must have at least three detector hits to be reconstructed.

The trajectory is fitted independently in the x-z and y-z planes:

```text
x(z) = ax + bx × z

y(z) = ay + by × z
```

The reconstructed track is extrapolated to:

```text
z = 82 m
```

The extrapolated position is:

```text
x_target = ax + bx × 82

y_target = ay + by × 82
```

The track is classified according to whether it enters the T1 acceptance:

```text
|x_target| ≤ 2 m
|y_target| ≤ 3 m
```

Tracks inside this region are classified as:

```text
accepted tracks
```

Tracks outside this region are classified as:

```text
rejected tracks
```

The rejected tracks are the primary source of potential combinatorial background candidates.

---

# Combinatorial Background Study

The rejected tracks are used to construct all possible track pairs:

```python
combinations(rejected_tracks, 2)
```

Only tracks satisfying:

```text
p > 1 GeV/c
```

are included in the current study.

For each pair, the distance of closest approach (DOCA) is calculated.

The two tracks are represented as 3D lines:

```text
r1(s) = p1 + s × v1

r2(t) = p2 + t × v2
```

The DOCA is:

```text
DOCA = |r1(s) - r2(t)|
```

The midpoint between the two closest points is used as the reconstructed vertex.

A pair is considered a potential HNL-like candidate if:

```text
DOCA < 2 cm
```

For such candidates, the HNL direction is approximated as:

```text
direction = direction_1 + direction_2
```

The impact parameter relative to the production point is then calculated.

The current implementation uses:

```text
origin = (0, 0, 0)
```

and computes the distance between the reconstructed HNL flight line and the production point.

---

# Optimization Parameters

The detector layout is controlled by the parameter set:

```python
theta = [
    {
        "z": z_position,
        "technology": detector_type,
        "margin_x": x_margin,
        "margin_y": y_margin,
    },
    ...
]
```

The optimization can therefore vary:

## Detector position

```text
z
```

subject to:

```text
31 m ≤ z ≤ 81 m
```

All detector layer positions must be unique.

---

## Detector technology

The technology can be selected from:

```text
A → Straw tubes
B → Scintillating fibres
C → Silicon pixels
```

---

## Transverse detector margin

The detector aperture is defined as:

```text
ax_detector = ax_vessel + margin_x

ay_detector = ay_vessel + margin_y
```

The margins control the detector coverage outside the vessel.

Larger margins increase the probability of detecting particles that leave the vessel but also increase the detector area and cost.

---

# Detector Cost Model

The cost model is based on the sensitive detector area and the number of detector channels.

The current cost is expressed in relative units.

For entrance trackers:

```text
area = detector area
```

For lateral detectors:

```text
area =
detector area
-
vessel area
```

The full detector area includes all four quadrants:

```text
total area = 4 × quadrant area
```

---

## Channel estimation

For pixel detectors:

```text
N_channels = area / pitch²
```

For straw and fibre detectors:

```text
N_channels = area / pitch
```

The detector cost is then:

```text
cost =
N_channels × relative_cost_per_channel
```

The total detector cost is:

```text
total_cost =
Σ cost_layer
```

The optimization can therefore directly compare detector layouts with different technologies and geometries.

---

# Optimization Objective

The current objective function combines physics performance and cost:

```python
score =
    5.0 × efficiency
    - 1.0 × candidate_rate
    - 10.0 × min_ip
    - 0.1 × cost / 1e6
    - 1.0 × sigma_x / 1e-3
    - 1.0 × sigma_y / 1e-3
```

where:

### Tracking efficiency

```text
efficiency =
number of accepted tracks
/
total reconstructed tracks
```

---

### Candidate rate

```text
candidate_rate =
number of DOCA candidates
/
number of rejected tracks
```

A smaller candidate rate is preferred.

The long-term goal is to minimize:

```text
N_doca_candidates
```

and ideally obtain:

```text
N_doca_candidates = 0
```

within the simulated sample.

---

### Impact parameter

The minimum impact parameter among candidate pairs is included in the objective.

The current implementation uses:

```text
min_ip
```

as a background-discrimination variable.

---

### Track resolution

The track residuals at the T1 reference plane are calculated as:

```text
residual_x =
x_reconstructed - x_true

residual_y =
y_reconstructed - y_true
```

The corresponding widths are:

```text
sigma_x
sigma_y
```

Better detector resolution should improve the reconstructed track quality and potentially reduce fake close-approach combinations.

---

### Cost penalty

The total detector cost is penalized through:

```text
-0.1 × cost / 1e6
```

This prevents the optimizer from simply selecting arbitrarily large and expensive detector systems.

---

# Example Layout

The current example layout contains five optimized transverse detector layers:

```text
z = 40 m  → Straw
z = 50 m  → Straw
z = 60 m  → Straw
z = 70 m  → Fibre
z = 78 m  → Straw
```

with:

```text
margin_x = 0.7 m
margin_y = 0.7 m
```

Together with the three fixed entrance trackers, this gives:

```text
8 detector layers total
```

The detector layout can be evaluated with:

```python
evaluate_theta(
    theta,
    x0,
    y0,
    px0,
    py0,
    pz0,
    z0,
    x_true,
    y_true,
    p_true
)
```

---

# Analysis Workflow

The complete workflow is:

```text
Input muon samples
        │
        ▼
Load UBT and T1 data
        │
        ▼
Define detector layout
        │
        ▼
Propagate muons through detector layers
        │
        ▼
Apply detector acceptance
        │
        ▼
Apply detector efficiency
        │
        ▼
Smear detector hits
        │
        ▼
Reconstruct tracks
        │
        ▼
Extrapolate tracks to T1
        │
        ▼
Classify accepted/rejected tracks
        │
        ▼
Build rejected-track combinations
        │
        ▼
Calculate DOCA
        │
        ▼
Select close-approach candidates
        │
        ▼
Calculate reconstructed IP
        │
        ▼
Evaluate tracking performance
        │
        ▼
Calculate detector cost
        │
        ▼
Compute optimization score
```

---

# Optimization Strategy

The framework is designed to support a multi-parameter detector optimization.

The optimization variables are:

```text
N_layers
z_i
technology_i
margin_x_i
margin_y_i
```

Possible optimization strategies include:

* Grid scans.
* Random sampling.
* Bayesian optimization.
* Genetic algorithms.
* Differential evolution.
* Simulated annealing.
* Multi-objective optimization.

A layout should be evaluated using a common simulated sample to ensure that different detector configurations can be compared consistently.

---

# Recommended Optimization Targets

The optimization should not rely only on the scalar score.

The most important physics quantities to monitor are:

```text
Number of reconstructed tracks
Number of accepted tracks
Number of rejected tracks
Number of DOCA candidates
Minimum DOCA
Minimum IP
Track resolution
Detector cost
```

A promising detector configuration should satisfy:

```text
N_doca_candidates → 0
```

while maintaining:

```text
high track reconstruction efficiency
```

and:

```text
acceptable detector cost
```

A useful final optimization criterion is therefore:

```text
minimize:

    background candidates
    detector cost

subject to:

    sufficient tracking efficiency
    sufficient spatial resolution
    sufficient detector acceptance
```

---

# Important Current Limitations

The present implementation is a first optimization framework and contains several approximations.

## 1. Straight-line propagation

The transport model currently neglects:

* Magnetic fields.
* Multiple scattering.
* Energy loss.
* Detector material interactions.

These effects should be included in a more realistic detector performance study.

---

## 2. Simplified detector geometry

The detector area is estimated using idealized rectangular geometries.

The real detector implementation may require:

* Module segmentation.
* Support structures.
* Dead regions.
* Overlap regions.
* Services.
* Electronics.
* Mechanical constraints.

These effects are not currently included in the cost model.

---

## 3. Simplified cost model

The cost is currently based only on:

```text
number of channels
×
relative cost per channel
```

A realistic cost model should also include:

* Front-end electronics.
* Readout boards.
* Power systems.
* Cooling.
* Mechanical support.
* Cabling.
* Installation.
* Maintenance.
* Detector material.
* Timing infrastructure.

---

## 4. Track fitting

The current track fit is an unweighted linear least-squares fit.

The fit does not currently use:

* Hit uncertainties.
* Different detector resolutions.
* Timing information.
* Multiple-scattering covariance.
* Outlier rejection.

A weighted track fit would provide a more realistic estimate of the detector performance.

---

## 5. Timing information is not currently used

The detector technology definitions include timing resolutions:

```text
sigma_t
```

but timing is not yet used in:

* Hit association.
* Track reconstruction.
* Muon identification.
* Combinatorial background rejection.

Timing information could provide an important additional handle against accidental combinations.

---

## 6. Random detector efficiency

The detector efficiency is currently sampled randomly for every particle and detector layer.

For reproducible optimization studies, the random seed should be controlled.

Alternatively, common random numbers can be used so that different detector configurations are compared using the same underlying stochastic detector response.

---

## 7. Statistical interpretation

A result with:

```text
0 candidates
```

in a finite simulated sample does not automatically prove that the physical background is exactly zero.

The final background estimate should account for:

* The simulated exposure.
* The number of generated events.
* The event weights.
* The detector efficiency.
* The statistical upper limit associated with zero observed candidates.

The optimization should therefore distinguish between:

```text
zero candidates in the simulation
```

and:

```text
demonstrated negligible physical background
```

---

# Future Improvements

The following developments are recommended.

### Detector optimization

* Optimize the number of layers.
* Optimize detector positions.
* Optimize technology assignment per layer.
* Optimize x and y margins independently.
* Add detector cost constraints.
* Perform Pareto optimization between cost and background rejection.

### Reconstruction

* Implement weighted least-squares fitting.
* Include timing information.
* Add hit association.
* Add outlier rejection.
* Include multiple scattering.
* Include magnetic-field transport.

### Background rejection

* Optimize DOCA thresholds.
* Optimize impact-parameter requirements.
* Include timing coincidence requirements.
* Study three-dimensional vertex reconstruction.
* Evaluate accidental combinations using event mixing.

### Cost model

* Replace relative channel cost with engineering cost estimates.
* Include electronics and services.
* Include detector support structures.
* Include installation and maintenance costs.

### Statistical analysis

* Propagate event weights.
* Calculate background rates.
* Determine confidence intervals.
* Quantify the upper limit for zero observed candidates.

---

# Summary

This framework provides a first simulation-based approach to optimize a transverse detector system designed to suppress muon combinatorial backgrounds.

The optimization combines:

```text
detector geometry
+
detector technology
+
spatial resolution
+
efficiency
+
track reconstruction
+
DOCA-based background identification
+
impact-parameter reconstruction
+
detector cost
```

The central design question is:

> Can a cost-effective system of transverse detector layers reconstruct and reject the relevant muon trajectories well enough to reduce the combinatorial background to zero surviving candidates?

The current framework provides the basic tools required to answer this question through systematic detector-layout optimization.

The next major step is to perform a broad scan of detector configurations and construct a cost-versus-background-rejection Pareto frontier.
