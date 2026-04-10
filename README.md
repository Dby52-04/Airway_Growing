# Airway Generation Source Code

Source code for generating complete lung airway trees from patient-specific imaging data, based on the algorithm described in Tawhai et al. 2004 (J Appl Physiol). These files are adapted from the [Chaste](https://chaste.cs.ox.ac.uk/) lung module.

## Files

### Core Classes


| File                               | Description                                                                                                                                                                                                                                                                          |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `AirwayGeneration.hpp/cpp`         | Defines the `Apex` (growth apex) and `AirwayGeneration` (a collection of apices for one generation level) data structures used during tree growing                                                                                                                                   |
| `AirwayGenerator.hpp/cpp`          | Single-lobe airway growing algorithm. Fills a lobe volume with seed points, then iteratively grows branches via bifurcation from initial apices toward point cloud centers                                                                                                           |
| `MultiLobeAirwayGenerator.hpp/cpp` | Wraps `AirwayGenerator` to handle all 5 lung lobes (RUL, RML, RLL, LUL, LLL) together. Assigns growth apices from major airways to the correct lobes, distributes seed points proportionally by lobe volume, generates each lobe's tree, and merges the results into a single output |
| `AirwayRemesher.hpp/cpp`           | Rebalances airway tree meshes to improve condition number for downstream flow simulations                                                                                                                                                                                            |


### Batch Runner


| File       | Description                                                                                                                                 |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `batch.py` | Python script that auto-discovers patient samples, generates Chaste C++ test files for each, then builds and runs them via cmake/make/ctest |


## Dependencies

- **Chaste** framework (lung module)
- **VTK** >= 5.6 (for mesh I/O, STL reading, point cloud operations)
- **PETSc** (Chaste runtime dependency)

## Algorithm Overview

1. Load patient-specific major airways mesh (`.vtu`) with radius and terminal marker data
2. Load 5 lung lobe surfaces (`.stl`) — right upper/middle/lower, left upper/lower
3. Assign terminal nodes of the major airways as growth apices in the corresponding lobes
4. Generate seed point clouds within each lobe, distributed proportionally by volume
5. Grow airway branches iteratively: each apex bifurcates toward the center of its local point cloud, splitting the cloud and creating child apices
6. Compute Horsfield ordering and branch radii
7. Merge all lobe trees with the major airways and output as `.vtu`, Triangle/TetGen, and CMGUI formats

