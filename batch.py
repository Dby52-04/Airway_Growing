"""
Batch Chaste Airway Generation
Run Chaste airway generation for multiple samples
"""

import os
import subprocess
import glob
import sys

# ============================================================
# Configuration
# ============================================================
CHASTE_SOURCE = "/home/newton/Project/2026/Chaste"
CHASTE_BUILD = "/home/newton/Chaste_build"
PROJECT_NAME = "MyAirwayProject"
DATA_DIR = "/home/newton/Project/2026/Airway_Growing/data/generations"
TEST_DIR = os.path.join(CHASTE_SOURCE, f"projects/{PROJECT_NAME}/test")
OUTPUT_BASE = "/home/newton/Project/2026/Airway_Growing/output"

LOBES = ["rul", "rml", "rll", "lul", "lll"]
JOBS = os.cpu_count() or 4


def to_camel(name):
    return name.replace("_", " ").title().replace(" ", "")


# Auto-discover all samples from the data directory (based on VTU files)
vtu_files = sorted(glob.glob(os.path.join(DATA_DIR, "*_major_airways.vtu")))
SAMPLES = [os.path.basename(f).replace("_major_airways.vtu", "") for f in vtu_files]

print(f"Found {len(SAMPLES)} samples: {SAMPLES}")

# ============================================================
# Generate hpp files for each sample
# ============================================================
HPP_TEMPLATE = '''#ifndef TEST{upper}_AIRWAYGENERATION_HPP_
#define TEST{upper}_AIRWAYGENERATION_HPP_

#ifdef CHASTE_VTK
#define _BACKWARD_BACKWARD_WARNING_H 1
#include "vtkSmartPointer.h"
#include "vtkPolyData.h"
#include "vtkSTLReader.h"
#endif

#include <cxxtest/TestSuite.h>
#include "MultiLobeAirwayGenerator.hpp"
#include "PetscSetupAndFinalize.hpp"

class Test{camel}AirwayGeneration : public CxxTest::TestSuite
{{
public:
    void TestGenerateAirways()
    {{
#if defined(CHASTE_VTK) && ((VTK_MAJOR_VERSION>=5 && VTK_MINOR_VERSION>=6) || VTK_MAJOR_VERSION>=6)
        EXIT_IF_PARALLEL;

        TetrahedralMesh<1,3> airways_mesh;
        VtkMeshReader<1,3> airways_mesh_reader(
            "{data_dir}/{name}_major_airways.vtu");
        airways_mesh.ConstructFromMeshReader(airways_mesh_reader);

        std::vector<double> node_radii;
        airways_mesh_reader.GetPointData("radius", node_radii);
        std::vector<double> terminal_marker;
        airways_mesh_reader.GetPointData("start_id", terminal_marker);

        for (TetrahedralMesh<1,3>::NodeIterator
             iter = airways_mesh.GetNodeIteratorBegin();
             iter != airways_mesh.GetNodeIteratorEnd(); ++iter)
        {{
            iter->AddNodeAttribute(node_radii[iter->GetIndex()]);
            iter->AddNodeAttribute(fmod(terminal_marker[iter->GetIndex()], 2));
        }}

        MultiLobeAirwayGenerator generator(airways_mesh);
        generator.SetNumberOfPointsPerLung(15000);
        generator.SetBranchingFraction(0.4);
        generator.SetDiameterRatio(1.15);
        generator.SetMinimumBranchLength(0.00001);
        generator.SetPointLimit(1);
        generator.SetAngleLimit(180.0);

        vtkSmartPointer<vtkSTLReader> lll_reader = vtkSmartPointer<vtkSTLReader>::New();
        lll_reader->SetFileName("{data_dir}/{name}_lll.stl");
        lll_reader->Update();
        generator.AddLobe(lll_reader->GetOutput(), LEFT);

        vtkSmartPointer<vtkSTLReader> lul_reader = vtkSmartPointer<vtkSTLReader>::New();
        lul_reader->SetFileName("{data_dir}/{name}_lul.stl");
        lul_reader->Update();
        generator.AddLobe(lul_reader->GetOutput(), LEFT);

        vtkSmartPointer<vtkSTLReader> rll_reader = vtkSmartPointer<vtkSTLReader>::New();
        rll_reader->SetFileName("{data_dir}/{name}_rll.stl");
        rll_reader->Update();
        generator.AddLobe(rll_reader->GetOutput(), RIGHT);

        vtkSmartPointer<vtkSTLReader> rml_reader = vtkSmartPointer<vtkSTLReader>::New();
        rml_reader->SetFileName("{data_dir}/{name}_rml.stl");
        rml_reader->Update();
        generator.AddLobe(rml_reader->GetOutput(), RIGHT);

        vtkSmartPointer<vtkSTLReader> rul_reader = vtkSmartPointer<vtkSTLReader>::New();
        rul_reader->SetFileName("{data_dir}/{name}_rul.stl");
        rul_reader->Update();
        generator.AddLobe(rul_reader->GetOutput(), RIGHT);

        generator.AssignGrowthApices();
        generator.DistributePoints();
        generator.Generate("{name}_airway_generation", "{name}_complete_airway_tree");

#endif
    }}
}};

#endif
'''

ready_samples = []

for name in SAMPLES:
    # Check all required files exist
    required = [f"{name}_major_airways.vtu"] + [f"{name}_{l}.stl" for l in LOBES]
    missing = [f for f in required if not os.path.exists(os.path.join(DATA_DIR, f))]
    if missing:
        print(f"WARNING: {name}: missing files {missing}, skipping")
        continue

    camel = to_camel(name)
    upper = camel.upper()

    hpp_content = HPP_TEMPLATE.format(
        upper=upper, camel=camel, name=name, project=PROJECT_NAME, data_dir=DATA_DIR
    )

    hpp_filename = f"Test{camel}AirwayGeneration.hpp"
    hpp_path = os.path.join(TEST_DIR, hpp_filename)

    with open(hpp_path, 'w') as f:
        f.write(hpp_content)

    ready_samples.append(name)
    print(f"OK: {name} -> {hpp_filename}")

# Write ContinuousTestPack.txt
pack_path = os.path.join(TEST_DIR, "ContinuousTestPack.txt")
with open(pack_path, 'w') as f:
    f.write('\n'.join(f"Test{to_camel(n)}AirwayGeneration.hpp" for n in ready_samples) + '\n')
print(f"\nUpdated ContinuousTestPack.txt ({len(ready_samples)} tests)")

if not ready_samples:
    print("No valid samples, exiting.")
    sys.exit(0)

# ============================================================
# Build and Run
# ============================================================
print("\n" + "="*60)
print("Starting build and run")
print("="*60)

# Run cmake
print("\n[1/3] Running cmake...")
ret = subprocess.run(
    ["cmake", f"-DChaste_ENABLE_project_{PROJECT_NAME}=ON", CHASTE_SOURCE],
    cwd=CHASTE_BUILD, capture_output=True, text=True
)
if ret.returncode != 0:
    print(f"cmake failed:\n{ret.stderr}")
    sys.exit(1)

# Build and run all tests
total = len(ready_samples)
for i, name in enumerate(ready_samples, 1):
    camel = to_camel(name)
    target = f"Test{camel}AirwayGeneration"

    print(f"\n[{i}/{total}] Building {target}...")
    ret = subprocess.run(
        ["make", f"-j{JOBS}", target],
        cwd=CHASTE_BUILD, capture_output=True, text=True
    )
    if ret.returncode != 0:
        print(f"  FAIL: build failed:\n{ret.stderr[-500:]}")
        continue

    print(f"[{i}/{total}] Running {target}...")
    ret = subprocess.run(
        ["ctest", "-V", "-R", target],
        cwd=CHASTE_BUILD, capture_output=True, text=True,
        env={**os.environ, "CHASTE_TEST_OUTPUT": OUTPUT_BASE}
    )
    if ret.returncode == 0:
        output_dir = os.path.join(OUTPUT_BASE, f"{name}_airway_generation")
        print(f"  OK: success! Output: {output_dir}/")
    else:
        print(f"  FAIL: run failed:\n{ret.stdout[-500:]}")

# ============================================================
# Summary
# ============================================================
print("\n" + "="*60)
print("Done! Output directories:")
for name in ready_samples:
    output_dir = os.path.join(OUTPUT_BASE, f"{name}_airway_generation")
    if os.path.exists(output_dir):
        files = os.listdir(output_dir)
        print(f"  OK: {name}: {output_dir}/ ({len(files)} files)")
    else:
        print(f"  FAIL: {name}: not generated")
