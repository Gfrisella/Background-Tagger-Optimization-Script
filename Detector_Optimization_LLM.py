# %%
import pickle
import numpy as np

with open(
    "TRY6_UBT_to_T1_combined.pkl",
    "rb"
) as f:

    combined = pickle.load(f)
    
# %%
px = {}
py = {}
pz = {}
x = {}
y = {}
z = {}
# w = {}

for name in ["UBT", "T1"]:

    px[name] = combined[name]["px"]
    py[name] = combined[name]["py"]
    pz[name] = combined[name]["pz"]

    x[name] = combined[name]["x"]
    y[name] = combined[name]["y"]
    z[name] = combined[name]["z"]
    # w[name] = combined[name]["w"]

# %%
# Functions

def propagate_linear(x, y, px, py, pz, z0, z_new):
    """
    Linear transport of particles from z0 to z_new.

    Parameters
    ----------
    x, y : array-like
        Initial transverse positions.
    px, py, pz : array-like
        Momentum components.
    z0 : float
        Initial z position.
    z_new : float
        Target z position.

    Returns
    -------
    x_new, y_new : ndarray
        Transverse positions at z_new.
    """

    dz = z_new - z0

    # Avoid division problems for particles with pz ~ 0
    mask = np.abs(pz) > 0

    x_new = np.copy(x)
    y_new = np.copy(y)

    x_new[mask] += (px[mask] / pz[mask]) * dz
    y_new[mask] += (py[mask] / pz[mask]) * dz

    return x_new, y_new

def tapered_aperture(z):
    """
    Return the semi-apertures of the decay vessel.

    Parameters
    ----------
    z : float or ndarray
        Position along the beam line [m].

    Returns
    -------
    ax, ay : float or ndarray
        Semi-apertures in x and y [m].
    """

    z0 = 31          # vessel entrance [m]
    L = 50.0           # vessel length [m]

    z = np.asarray(z)

    # Relative coordinate along the vessel
    s = np.clip(z - z0, 0.0, L)

    ax = 0.5 + (2.0 - 0.5) * s / L
    ay = 2.7 + (6.0 - 2.7) * s / L

    return ax, ay

def detector_acceptance(x, y, z, layer):

    ax_det = layer["ax"]
    ay_det = layer["ay"]

    # Detector active area
    in_detector = (
        (np.abs(x) <= ax_det) &
        (np.abs(y) <= ay_det)
    )

    # Entrance tracker
    if layer["type"] == "entrance":
        return in_detector


    # Vessel aperture
    ax_vessel, ay_vessel = tapered_aperture(z)

    # Particle exits the vessel
    outside_vessel = (
        (np.abs(x) >= ax_vessel) |
        (np.abs(y) >= ay_vessel)
    )

    return in_detector & outside_vessel



# %%
# Detector Definition

DetectorTypes = {

    "A": {   # Straw tubes
        "name": "Straw",
        "cost_per_channel": 1.0,      # relative units
        "pitch": 0.010,               # 10 mm
        "sigma_x": 150e-6,            # 150 um
        "sigma_t": 2.0e-9,            # 2 ns
        "efficiency": 0.98,
    },

    "B": {   # Scintillating fibres
        "name": "Fiber",
        "cost_per_channel": 4.0,
        "pitch": 250e-6,              # 250 um
        "sigma_x": 70e-6,             # 70 um
        "sigma_t": 500e-12,           # 500 ps
        "efficiency": 0.995,
    },

    "C": {   # Silicon pixels
        "name": "Pixel",
        "cost_per_channel": 20.0,
        "pitch": 55e-6,               # 55 um
        "sigma_x": 10e-6,             # 10 um
        "sigma_t": 50e-12,            # 50 ps
        "efficiency": 0.999,
    }
}



# %%
# Function detector
def make_layout(lateral_layers):

    layout = []

    # -------------------------
    # Fixed entrance trackers
    # -------------------------

    for z in [30.7, 30.8, 30.9]:

        layout.append({
            "z": z,
            "technology": "A",
            "ax": 1.8,
            "ay": 1.35,
            "type": "entrance"
        })

    # -------------------------
    # Optimized lateral layers
    # -------------------------

    for layer in lateral_layers:

        z = layer["z"]

        vessel_ax, vessel_ay = tapered_aperture(z)

        margin_x = layer["margin_x"]
        margin_y = layer["margin_y"]

        layout.append({
            "z": z,
            "technology": layer["technology"],
            "dx": vessel_ax,
            "dy": vessel_ay,
            "ax": vessel_ax + margin_x,
            "ay": vessel_ay + margin_y,
            "type": "lateral"
        })

    return sorted(
        layout,
        key=lambda layer: layer["z"]
    )

def simulate_layer(layer, x, y, px, py, pz, z0):

    tech = DetectorTypes[layer["technology"]]

    x_hit, y_hit = propagate_linear(
        x, y,
        px, py, pz,
        z0,
        layer["z"]
    )

    accepted = detector_acceptance(
        x_hit,
        y_hit,
        layer['z'],
        layer
    )

    detected = accepted & (
        np.random.rand(len(x_hit))
        < tech["efficiency"]
    )

    sigma = tech["sigma_x"]

    x_hit[detected] += np.random.normal(
        0,
        sigma,
        detected.sum()
    )

    y_hit[detected] += np.random.normal(
        0,
        sigma,
        detected.sum()
    )

    return {
        "z": layer["z"],
        "technology": layer["technology"],
        "mask": detected,
        "x": x_hit,
        "y": y_hit,
    }

def simulate_detector_system(layout,
                      x, y,
                      px, py, pz,
                      z0):

    all_hits = []
    for layer_id, layer in enumerate(layout):

        hits = simulate_layer(
            layer,
            x, y,
            px, py, pz,
            z0
        )

        mask = hits["mask"]

        for i in np.where(mask)[0]:

            all_hits.append({
                "particle": i,
                "layer": layer_id,
                "z": hits["z"],
                "x": hits["x"][i],
                "y": hits["y"][i],
                "technology": hits["technology"]
            })

    return all_hits

def detector_layer_cost(layer):

    tech = DetectorTypes[layer["technology"]]

    ax_det = layer["ax"]
    ay_det = layer["ay"]
    
    # Entrance trackers: full active area
    if layer["type"] == "entrance":

        area = (
            ax_det *
            ay_det
        )

    # Lateral detectors: remove vessel area
    elif layer["type"] == "lateral":

        ax_vessel, ay_vessel = tapered_aperture(
            layer["z"]
        )

        area = (
            (ax_det - ax_vessel) *
            (ay_det - ay_vessel)
        )

    #Account for the 4 quadrant
    area *=4
    
    # number of channels
    if tech["name"] == "Pixel":

        n_channels = (
            area /
            tech["pitch"]**2
        )

    else:

        n_channels = (
            area /
            tech["pitch"]
        )


    cost = (
        n_channels *
        tech["cost_per_channel"]
    )


    return cost, area


def evaluate_detector_cost(layout):

    total = 0

    print("\nDetector cost breakdown")

    for i, layer in enumerate(layout):

        cost, area = detector_layer_cost(layer)

        total += cost

        print(
            f"Layer {i:02d} | "
            f"{DetectorTypes[layer['technology']]['name']:6s} | "
            rf"Aperture = {layer['ax']- (layer['dx'] if 'dx' in layer.keys() else 0):.2f} m × {layer['ay']- (layer['dy'] if 'dx' in layer.keys() else 0):.2f} m | "
            rf"Sensitive Area = {area:.2f} m$^2$ | "
            f"Cost = {cost:.2f}"
        )


    print("----------------------------")
    print(
        f"Total detector cost = {total}"
    )

    return total

# %%
# Fit Tracks

def fit_track(z, x, y, z_target=82.0):
    """
    Fit a straight track and extrapolate to z_target.

    Parameters
    ----------
    z, x, y : array
        Hit coordinates.

    Returns
    -------
    dict
    """

    if len(z) < 2:
        return None

    bx, ax = np.polyfit(z, x, 1)
    by, ay = np.polyfit(z, y, 1)

    return {

        "ax": ax,
        "bx": bx,

        "ay": ay,
        "by": by,

        "x_target": ax + bx*z_target,
        "y_target": ay + by*z_target,

        "n_hits": len(z)

    }

# %%
# DOCA + IP definition
def line_from_track(track):

    point = np.array([
        track["ax"],
        track["ay"],
        0.0
    ])

    direction = np.array([
        track["bx"],
        track["by"],
        1.0
    ])

    direction /= np.linalg.norm(direction)

    return point, direction

def track_track_doca(track1, track2):

    p1, v1 = line_from_track(track1)
    p2, v2 = line_from_track(track2)

    w0 = p1 - p2

    a = np.dot(v1, v1)
    b = np.dot(v1, v2)
    c = np.dot(v2, v2)
    d = np.dot(v1, w0)
    e = np.dot(v2, w0)

    denom = a*c - b*b

    if np.abs(denom) < 1e-12:
        return None

    s = (b*e - c*d)/denom
    t = (a*e - b*d)/denom

    c1 = p1 + s*v1
    c2 = p2 + t*v2

    vertex = 0.5*(c1 + c2)

    doca = np.linalg.norm(c1 - c2)

    return doca, vertex

def impact_parameter(vertex, direction, origin=np.array([0., 0., 0.])):
    """
    Compute the impact parameter (IP) of a reconstructed HNL.

    Parameters
    ----------
    vertex : array-like, shape (3,)
        Reconstructed decay vertex.

    direction : array-like, shape (3,)
        Reconstructed HNL flight direction.
        (Does not need to be normalized.)

    origin : array-like, shape (3,), optional
        Production point (default = (0,0,0)).

    Returns
    -------
    ip : float
        Distance of closest approach between the HNL flight line
        and the production point.
    """

    direction = np.asarray(direction, dtype=float)
    direction /= np.linalg.norm(direction)

    vertex = np.asarray(vertex, dtype=float)
    origin = np.asarray(origin, dtype=float)

    return np.linalg.norm(
        np.cross(origin - vertex, direction)
    )

# %%
# Main
from itertools import combinations

def theta_to_layers(theta):

    layers = []

    for i in range(len(theta["z"])):

        layers.append({
            "z": theta["z"][i],
            "technology": theta["technology"][i],
            "margin_x": theta["margin_x"][i],
            "margin_y": theta["margin_y"][i],
        })

    return layers

def objective(result):

    efficiency = (
        result["n_accepted"]
        / result["n_tracks"]
    )

    candidate_rate = (
        result["n_doca_candidates"]
        / result["n_rejected"]
        if result["n_rejected"] > 0
        else 0
    )

    score = (
        5.0 * efficiency
        - 1.0 * candidate_rate
        - 10.0 * result["min_ip"]
        - 0.1 * result["cost"] / 1e6
        - 1.0 * result["sigma_x"] / 1e-3
        - 1.0 * result["sigma_y"] / 1e-3
    )

    return score

def evaluate_theta(theta,x0,
        y0,
        px0,
        py0,
        pz0,
        z0,
        x_true,
        y_true,
        p_true):

    z_values = [layer["z"] for layer in theta]

    # z must be ordered
    if len(set(z_values)) != len(z_values):
        return None

    if any(z < 31 or z > 81 for z in z_values):
        return None

    # Create detector
    layout = make_layout(theta)

    # Run physics simulation
    result = main(
        x0,
        y0,
        px0,
        py0,
        pz0,
        z0,
        x_true,
        y_true,
        p_true,
        layout
    )

    score = objective(result)

    return {
        "theta": theta,
        "score": score,
        "result": result,
    }

def main(x, y, px, py, pz, z0, x_true, y_true, p_true, layout):

    # -----------------------------
    # 1. Create detector layout
    # -----------------------------
    detector_cost = evaluate_detector_cost(layout)
    # print("Detector layout:")
    # for layer in layout:
    #     print(layer)


    # -----------------------------
    # 2. Simulate detector hits
    # -----------------------------
    all_hits = []

    all_hits =simulate_detector_system(layout,
                      x, y,
                      px, py, pz,
                      z0)
    print("\nTotal hits:", len(all_hits))

    # -----------------------------
    # 3. Collect hits per particle
    # -----------------------------
    particle_hits = {}

    for hit in all_hits:

        pid = hit["particle"]

        if pid not in particle_hits:
            particle_hits[pid] = []

        particle_hits[pid].append(hit)
        
    # -----------------------------
    # 4. Fit tracks
    # -----------------------------
    accepted_tracks = {}
    rejected_tracks = {}

    for pid, hits in particle_hits.items():

        if len(hits) < 3:
            continue

        z_hits = np.array(
            [h["z"] for h in hits]
        )

        x_hits = np.array(
            [h["x"] for h in hits]
        )

        y_hits = np.array(
            [h["y"] for h in hits]
        )

        
        track = fit_track(
            z_hits,
            x_hits,
            y_hits,
            z_target=82.0
        )
        inside_T1 = (
            (np.abs(track["x_target"]) <= 2) &
            (np.abs(track["y_target"]) <= 3)
        )

        if not inside_T1:
            rejected_tracks[pid] = track
            continue
        else:
            accepted_tracks[pid] = track

    print("\nTotal tracks:", len(rejected_tracks) + len(accepted_tracks) )
    print("Accepted tracks:", len(accepted_tracks))
    print("Rejected tracks:", len(rejected_tracks))

    # Keep only rejected tracks with true momentum > 1 GeV/c
    tracks_list = [
        track
        for pid, track in rejected_tracks.items()
        if p_true[pid] > 1
    ]

    print("Rejected tracks with p > 1 GeV/c:", len(tracks_list))

    rejected_doca = []
    doca_candidates = []
    ip_values = []

    for t1, t2 in combinations(tracks_list, 2):

        result = track_track_doca(t1, t2)

        if result is None:
            continue

        doca, vertex = result

        # Statistics for ALL pairs
        rejected_doca.append(doca)

        # Only keep good HNL candidates
        if doca > 0.02:
            continue

        doca_candidates.append(doca)

        _, v1 = line_from_track(t1)
        _, v2 = line_from_track(t2)

        hnl_dir = v1 + v2
        hnl_dir /= np.linalg.norm(hnl_dir)

        ip = impact_parameter(vertex, hnl_dir)

        ip_values.append(ip)

    rejected_doca = np.asarray(rejected_doca)
    doca_candidates = np.asarray(doca_candidates)
    ip_values = np.asarray(ip_values)



    if len(rejected_doca):

        print("\nAll rejected-track pairs")
        print(f"Pairs       : {len(rejected_doca)}")
        print(f"Min DOCA    : {np.min(rejected_doca)*100:.2f} cm")
        print(f"Mean DOCA   : {np.mean(rejected_doca)*100:.2f} cm")
        print(f"Median DOCA : {np.median(rejected_doca)*100:.2f} cm")
        print(f"RMS DOCA    : {np.std(rejected_doca)*100:.2f} cm")

    if len(doca_candidates):

        print("\nDOCA < 2 cm candidates")
        print(f"Candidates  : {len(doca_candidates)}")
        print(f"Mean DOCA   : {np.mean(doca_candidates)*100:.2f} cm")
        print(f"Median DOCA : {np.median(doca_candidates)*100:.2f} cm")
        print(f"RMS DOCA    : {np.std(doca_candidates)*100:.2f} cm")

        print(f"Mean IP     : {np.mean(ip_values)*100:.2f} cm")
        print(f"Median IP   : {np.median(ip_values)*100:.2f} cm")
        print(f"Best IP     : {np.min(ip_values)*100:.2f} cm")


    # -----------------------------
    # 5. Compare with truth at z=82
    # -----------------------------
    residual_x = []
    residual_y = []

    for pid, track in accepted_tracks.items():

        residual_x.append(
            track["x_target"] - x_true[pid]
        )

        residual_y.append(
            track["y_target"] - y_true[pid]
        )

    residual_x = np.asarray(residual_x)
    residual_y = np.asarray(residual_y)    

    if len(residual_x):

        print("\nTrack performance:")
        print(f"sigma x = {np.std(residual_x)*10**2:.4f} cm")
        print(f"sigma y = {np.std(residual_y)*10**2:.4f} cm")

    # return {
    #     "layout": layout,
    #     "cost": detector_cost,
    #     "hits": all_hits,
    #     "tracks": tracks,
    #     "accepted_tracks": accepted_tracks,
    #     "rejected_tracks": rejected_tracks,
    #     "residual_x": residual_x,
    #     "residual_y": residual_y
    # }
    return {
        "cost": detector_cost,

        "n_tracks": len(accepted_tracks) + len(rejected_tracks),

        "n_accepted": len(accepted_tracks),

        "n_rejected": len(rejected_tracks),

        "n_doca_candidates": len(doca_candidates),

        "min_ip": np.min(ip_values)*100
            if len(ip_values) else np.inf,

        "sigma_x": np.std(residual_x)*100
            if len(residual_x) else np.inf,

        "sigma_y": np.std(residual_y)*100
            if len(residual_y) else np.inf,
    }

# %%
x0 = np.asarray(x["UBT"])
y0 = np.asarray(y["UBT"])

px0 = np.asarray(px["UBT"])
py0 = np.asarray(py["UBT"])
pz0 = np.asarray(pz["UBT"])

x_true, y_true = np.asarray(x["T1"]), np.asarray(y["T1"])
p_true = np.asarray(np.sqrt(px["T1"]**2+py["T1"]**2+pz["T1"]**2))
z0 = 30.6


theta = [
    {
        "z": 40.0,
        "technology": "A",
        "margin_x": 0.7,
        "margin_y": 0.7,
    },
    {
        "z": 50.0,
        "technology": "A",
        "margin_x": 0.7,
        "margin_y": 0.7,
    },
    {
        "z": 60.0,
        "technology": "A",
        "margin_x": 0.7,
        "margin_y": 0.7,
    },
    {
        "z": 70.0,
        "technology": "B",
        "margin_x": 0.7,
        "margin_y": 0.7,
    },
    {
        "z": 78.0,
        "technology": "A",
        "margin_x": 0.7,
        "margin_y": 0.7,
    },
]

print(evaluate_theta(theta,x0, y0, px0, py0, pz0, z0, x_true, y_true, p_true))



# %%


# %%



