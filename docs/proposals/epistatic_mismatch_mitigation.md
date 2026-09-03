# RFC: Mitigation of Brain-Body Epistatic Mismatch in Flatland Simulation

> **Target File**: `proposals/epistatic_mismatch_mitigation.md`  
> **Status**: Architecture RFC / Technical Specification  
> **Author**: Phan Lê Hoàng Long  
> **Core Subsystems**: `agent_soa.py`, `neural_engine.py`, `morphology_engine.py`, `agent_pipeline.py`, `evolution.py`  
> **Reference Law Set**: `god-laws.md`

---

## 1. Problem Statement & Theoretical Context

In artificial life simulations featuring simultaneous morphology and controller evolution, **Epistatic Mismatch** (also known as the *neuromuscular disconnect* or *ontogenetic lag*) occurs when somatic morphology (the physical plant) drifts at a rate or trajectory that invalidates the neural controller (the brain).

In Flatland Simulation:
* **The Body**: Polygons defined by polar coordinates $(r_i, \phi_i)$ with $K \in [3, 24]$ vertices undergo morphological mutations (`vertex_mutation_std`, `topological_mutation_rate`). Body area $A$ dictates caloric storage and metabolic mass, while moment of inertia $I_{zz}$ dictates rotational resistance.
* **The Brain**: A fixed-topology Micro Elman RNN ($16 \to 12 \to 7$, 295 weights) maps sensory raycasts and vitals to locomotion actuators (`thrust`, `steer`).

### Failure Mode
When an individual undergoes a beneficial morphological mutation (e.g., elongating an acute vertex to $\theta < 20^\circ$ for high piercing damage[cite: 1]), its rotational moment of inertia $I_{zz}$ increases quadratically with distance from the centroid. If the inherited neural controller emits steering torque tuned for a low-$I_{zz}$ equilateral ancestor, the mutant experiences severe understeering or uncontrollable spin. Unable to navigate toward food before starving, the genetically superior body is eliminated—trapping the population in sub-optimal geometric local optima.

---

## 2. Four-Pillar Architectural Solution