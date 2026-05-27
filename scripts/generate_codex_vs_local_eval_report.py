#!/usr/bin/env python3
"""Generate a source-backed Codex-vs-local-LLM evaluation report.

The report compares one saved evaluation JSON from docs/evaluations/answers
against a direct code-reading pass over data/raw/ippl. The goal is not to
re-run the RAG system, but to record a careful human-style grading pass with
source references and export it as both Markdown and PDF.
"""

from __future__ import annotations

import collections
import json
import statistics
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = REPO_ROOT / "docs" / "evaluations" / "eval_questions_v1.json"
ANSWERS_PATH = REPO_ROOT / "docs" / "evaluations" / "answers" / "eval_20260423T141904Z.json"
OUTPUT_MD = REPO_ROOT / "docs" / "evaluations" / "codex_vs_local_llm_evaluation_20260423.md"
OUTPUT_PDF = REPO_ROOT / "docs" / "evaluations" / "codex_vs_local_llm_evaluation_20260423.pdf"


VERDICT_SCORE = {"Correct": 1.0, "Partial": 0.5, "Incorrect": 0.0}

DEFAULT_NOTE = {
    "Correct": "The local answer matches the source-backed reading closely enough to be trusted.",
    "Partial": "The local answer contains real signal, but it misses an important scope boundary, file, or algorithm detail.",
    "Incorrect": "The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.",
}


@dataclass
class Evaluation:
    question_id: str
    verdict: str
    reference: str
    refs: str
    note: str


RAW_EVALUATIONS = r"""
file_001	Correct	Declares the top-level IPPL runtime handles (`Comm`, `Env`, `Info`, `Warn`, `Error`) and the lifecycle wrappers `initialize`, `finalize`, `fence`, and `abort`.	data/raw/ippl/src/Ippl.h	
file_002	Correct	Implements runtime setup/teardown: command-line option parsing, MPI communicator/environment creation, logger setup, Kokkos init/finalize, and abort/fence helpers.	data/raw/ippl/src/Ippl.cpp	
file_003	Incorrect	Implements `FFTBase` setup plus the FFT specialization family for complex/real, sine, cosine, and cosine-I transforms on IPPL fields via heFFTe.	data/raw/ippl/src/FFT/FFT.hpp	Narrowed the whole file to one `FFT<RCTransform, RealField>` path and missed the rest of the specialization family.
file_004	Correct	Defines the core distributed field container: Kokkos-backed storage, owned/allocated domains, field layout access, halo exchange hooks, and expression-style assignment.	data/raw/ippl/src/Field/BareField.h	
file_005	Correct	Adds mesh awareness and boundary-condition management on top of `BareField`, plus volume integral/average helpers.	data/raw/ippl/src/Field/Field.h	
file_006	Correct	Defines the halo-exchange machinery for fields: pack/unpack, boundary exchange, and periodic handling for ghost cells.	data/raw/ippl/src/Field/HaloCells.h; data/raw/ippl/src/Field/HaloCells.hpp	
file_007	Correct	Defines how a global `NDIndex` domain is partitioned across MPI ranks, including local subdomains, neighbors, and communication ranges.	data/raw/ippl/src/FieldLayout/FieldLayout.h	
file_008	Correct	Defines the generic particle container base class with positions, optional IDs, registered attributes, and a particle layout that controls migration.	data/raw/ippl/src/Particle/ParticleBase.h	
file_009	Correct	Defines the spatial particle layout that decides ownership by region and migrates particles to the correct rank after motion.	data/raw/ippl/src/Particle/ParticleSpatialLayout.h; data/raw/ippl/src/Particle/ParticleSpatialLayout.hpp	
file_010	Correct	Implements the `ParticleAttrib` storage object: a Kokkos-view-backed particle attribute with resize, serialization, and mirror/access helpers.	data/raw/ippl/src/Particle/ParticleAttrib.h	
file_011	Correct	Defines the uniform Cartesian mesh class with spacing, origin, cell volume, total mesh volume, and vertex-position helpers.	data/raw/ippl/src/Meshes/UniformCartesian.h	
file_012	Correct	Declares the orthogonal recursive bisection domain-decomposition/load-balancing class and its cut/median/repartition helpers.	data/raw/ippl/src/Decomposition/OrthogonalRecursiveBisection.h	
file_013	Correct	Declares the first-order cloud-in-cell interpolation helpers for scatter/gather between particles and grid fields.	data/raw/ippl/src/Interpolation/CIC.h	

loc_001	Incorrect	FFT initialization lives in `src/FFT/FFT.hpp`, especially `FFTBase` construction/setup and the transform-specific constructors that build the heFFTe plans.	data/raw/ippl/src/FFT/FFT.hpp	
loc_002	Partial	IPPL sets up MPI in `src/Ippl.cpp::initialize()` by constructing `mpi::Environment` and `mpi::Communicator`; the low-level `MPI_Init` check/call is in `src/Communicate/Environment.cpp`.	data/raw/ippl/src/Ippl.cpp; data/raw/ippl/src/Communicate/Environment.cpp	The local answer found the low-level MPI constructor, but missed that the IPPL entry point is `ippl::initialize()` in `Ippl.cpp`.
loc_003	Incorrect	Kokkos is initialized and finalized directly in `src/Ippl.cpp` inside `ippl::initialize()` and `ippl::finalize()`.	data/raw/ippl/src/Ippl.cpp	
loc_004	Correct	The ORB load balancer is implemented in `src/Decomposition/OrthogonalRecursiveBisection.hpp` with declarations in the matching header.	data/raw/ippl/src/Decomposition/OrthogonalRecursiveBisection.hpp	
loc_005	Partial	Field BCs are attached in `Field::setFieldBC()` and actually applied through `BConds::apply()` and the concrete face classes in `BcTypes.hpp`.	data/raw/ippl/src/Field/Field.h; data/raw/ippl/src/Field/BConds.hpp; data/raw/ippl/src/Field/BcTypes.hpp	
loc_006	Incorrect	CIC scatter is implemented in `src/Interpolation/CIC.hpp`, primarily `scatterToPoint()` and `scatterToField()`.	data/raw/ippl/src/Interpolation/CIC.hpp	
loc_007	Incorrect	CIC gather is implemented in `src/Interpolation/CIC.hpp`, primarily `gatherFromPoint()` and `gatherFromField()`.	data/raw/ippl/src/Interpolation/CIC.hpp	
loc_008	Partial	Halo exchange for `BareField` is surfaced in `src/Field/BareField.hpp` and actually performed in `src/Field/HaloCells.hpp`.	data/raw/ippl/src/Field/BareField.hpp; data/raw/ippl/src/Field/HaloCells.hpp	The local answer found the right concept, but not the exact implementation split across the wrapper and helper file.
loc_009	Incorrect	The FFT open-boundary Poisson routines are defined in `src/PoissonSolvers/FFTOpenPoissonSolver.h` and `src/PoissonSolvers/FFTOpenPoissonSolver.hpp`.	data/raw/ippl/src/PoissonSolvers/FFTOpenPoissonSolver.h; data/raw/ippl/src/PoissonSolvers/FFTOpenPoissonSolver.hpp	
loc_010	Incorrect	The CG/PCG algorithm implementation is in `src/LinearSolvers/PCG.h`; the Poisson wrapper that instantiates it is `src/PoissonSolvers/PoissonCG.h`.	data/raw/ippl/src/LinearSolvers/PCG.h; data/raw/ippl/src/PoissonSolvers/PoissonCG.h	
loc_011	Correct	The FEM Poisson solver is implemented in `src/PoissonSolvers/FEMPoissonSolver.h`.	data/raw/ippl/src/PoissonSolvers/FEMPoissonSolver.h	
loc_012	Incorrect	The FDTD Maxwell solver base class is defined in `src/MaxwellSolvers/FDTDSolverBase.h` with implementation in `FDTDSolverBase.hpp`.	data/raw/ippl/src/MaxwellSolvers/FDTDSolverBase.h; data/raw/ippl/src/MaxwellSolvers/FDTDSolverBase.hpp	
loc_013	Correct	The `LagrangeSpace` class is defined in `src/FEM/LagrangeSpace.h` with methods implemented in `src/FEM/LagrangeSpace.hpp`.	data/raw/ippl/src/FEM/LagrangeSpace.h; data/raw/ippl/src/FEM/LagrangeSpace.hpp	
loc_014	Correct	Particle migration between ranks is implemented in `ParticleSpatialLayout::update()` in `src/Particle/ParticleSpatialLayout.hpp`.	data/raw/ippl/src/Particle/ParticleSpatialLayout.hpp	
loc_015	Incorrect	IPPL timers are defined by the singleton timing layer in `src/Utility/IpplTimings.h/.cpp`, not just the low-level `Timer` helper.	data/raw/ippl/src/Utility/IpplTimings.h; data/raw/ippl/src/Utility/IpplTimings.cpp	

cls_001	Correct	`BareField` is the core distributed field storage class: it owns the data view, domain metadata, layout link, and halo operations.	data/raw/ippl/src/Field/BareField.h	
cls_002	Incorrect	`Field` extends `BareField` with a mesh, boundary-condition container, and mesh-aware integral/average semantics.	data/raw/ippl/src/Field/Field.h	
cls_003	Partial	`FieldLayout<Dim>` distributes a global `NDIndex<Dim>` over ranks and stores local domains, neighbors, and communication ranges; its only template parameter is `Dim`.	data/raw/ippl/src/FieldLayout/FieldLayout.h	The local answer got the role right but blurred the distinction between template parameters and constructor/runtime inputs.
cls_004	Correct	`ParticleBase` is the user-extensible base container for particles; derived classes add attributes and register them so layout-driven migration can move them.	data/raw/ippl/src/Particle/ParticleBase.h	
cls_005	Correct	`ParticleSpatialLayout` decides which spatial region/rank owns each particle and performs the migration/update workflow after particles move.	data/raw/ippl/src/Particle/ParticleSpatialLayout.h; data/raw/ippl/src/Particle/ParticleSpatialLayout.hpp	
cls_006	Correct	`UniformCartesian` represents a uniform Cartesian mesh and exposes spacing/origin/volume and vertex-position geometry queries.	data/raw/ippl/src/Meshes/UniformCartesian.h	
cls_007	Correct	`Mesh` is the abstract base interface for meshes: origin, grid size, spacing, vertex positions, and volume queries.	data/raw/ippl/src/Meshes/Mesh.h	
cls_008	Correct	`ippl::mpi::Communicator` wraps MPI point-to-point, collectives, tag handling, and managed communication buffers.	data/raw/ippl/src/Communicate/Communicator.h	
cls_009	Correct	`ippl::mpi::Environment` manages MPI environment lifetime checks/teardown and provides an abort hook.	data/raw/ippl/src/Communicate/Environment.h; data/raw/ippl/src/Communicate/Environment.cpp	
cls_010	Correct	`Archive` serializes and deserializes Kokkos views and vector-valued views into raw byte buffers for MPI transfer.	data/raw/ippl/src/Communicate/Archive.h; data/raw/ippl/src/Communicate/Archive.hpp	
cls_011	Correct	`BConds` is the container of boundary-condition faces and orchestrates neighbor discovery, BC application, and ghost-to-physical assignment.	data/raw/ippl/src/Field/BConds.h; data/raw/ippl/src/Field/BConds.hpp	
cls_012	Correct	`BaseManager` provides the simulation loop skeleton: `pre_run`, `pre_step`, `advance`, `post_step`, and `run(nt)`.	data/raw/ippl/src/Manager/BaseManager.h	
cls_013	Correct	`Index` represents a regular strided integer range/slice and supports range-style arithmetic and comparison operations used in domain descriptions.	data/raw/ippl/src/Index/Index.h; data/raw/ippl/src/Index/Index.hpp	

alg_001	Incorrect	The FFT open-boundary solver embeds/extends the RHS onto larger domains, FFTs both the density and a precomputed Green's function, multiplies in Fourier space, inverse transforms, and optionally computes gradients/Hessians.	data/raw/ippl/src/PoissonSolvers/FFTOpenPoissonSolver.h; data/raw/ippl/src/PoissonSolvers/FFTOpenPoissonSolver.hpp	
alg_002	Incorrect	The periodic FFT solver FFTs the charge density, divides each Fourier mode by `|k|^2` (with the zero mode handled separately), then inverse transforms; gradients are computed by multiplying by `ik/|k|^2` before the inverse FFT.	data/raw/ippl/src/PoissonSolvers/FFTPeriodicPoissonSolver.hpp	
alg_003	Incorrect	The truncated-Green periodic solver replaces the simple `1/|k|^2` kernel with the FFT of a truncated/erf-smoothed Green's function `forceConstant * erf(alpha r) / r`, then follows the same transform-multiply-inverse pattern.	data/raw/ippl/src/PoissonSolvers/FFTTruncatedGreenPeriodicPoissonSolver.h; data/raw/ippl/src/PoissonSolvers/FFTTruncatedGreenPeriodicPoissonSolver.hpp	
alg_004	Partial	In `PCG.h`, the CG iteration forms residual/direction fields, applies the operator, computes `alpha` and `beta` from inner products, updates the solution/residual/direction, and stops on tolerance or iteration count; the preconditioned variant inserts `M^{-1}` applications on the residual.	data/raw/ippl/src/LinearSolvers/PCG.h	The local answer captured the plain CG loop but did not clearly separate it from the preconditioned path.
alg_005	Correct	CIC computes lower/upper weights per axis, scatters with atomic adds to the `2^Dim` neighboring grid points, and gathers by summing the same weighted stencil back to particles.	data/raw/ippl/src/Interpolation/CIC.h; data/raw/ippl/src/Interpolation/CIC.hpp	
alg_006	Incorrect	The standard FDTD solver advances the source-like field with a second-order finite-difference update using the previous and current time levels plus neighboring cells and source terms, then fills halos and reapplies BCs.	data/raw/ippl/src/MaxwellSolvers/StandardFDTDSolver.hpp	
alg_007	Partial	`LagrangeSpace` evaluates element DOFs by mapping local element indices to global DOF indices, then evaluates order-1 reference-element shape functions and gradients on those local DOFs.	data/raw/ippl/src/FEM/LagrangeSpace.h; data/raw/ippl/src/FEM/LagrangeSpace.hpp	The local answer focused on the compile-time DOF count and missed most of the actual element-DOF evaluation logic.
alg_008	Correct	Gauss-Jacobi quadrature computes nodes/weights by Newton iteration on Jacobi polynomial roots, starting from Chebyshev or LehrFEM-style guesses, and uses the resulting rule on reference elements in FEM.	data/raw/ippl/src/FEM/Quadrature/GaussJacobiQuadrature.h; data/raw/ippl/src/FEM/Quadrature/GaussJacobiQuadrature.hpp	
alg_009	Partial	ORB chooses a cut axis from the domain geometry and then finds a weight-balanced cut/median so recursive splits distribute load more evenly.	data/raw/ippl/src/Decomposition/OrthogonalRecursiveBisection.h; data/raw/ippl/src/Decomposition/OrthogonalRecursiveBisection.hpp	The local answer captured the cut-axis choice but did not clearly state that the cut location is chosen from the particle-weight distribution.
alg_010	Correct	Inverse transform sampling maps uniform random values in CDF space to samples by estimating the inverse and refining it with Newton-Raphson, dimension by dimension.	data/raw/ippl/src/Random/InverseTransformSampling.h	
alg_011	Incorrect	The FFT layer builds heFFTe boxes/plans in `setup()`, copies IPPL field data into the required views/subviews, calls heFFTe forward/backward transforms, and copies results back for CC/RC/DST/DCT variants.	data/raw/ippl/src/FFT/FFT.hpp	
alg_012	Partial	PCG applies a chosen preconditioner from `Preconditioner.h` to the residual, uses the preconditioned residual in its inner products and direction updates, and iterates until tolerance/max iterations.	data/raw/ippl/src/LinearSolvers/Preconditioner.h; data/raw/ippl/src/LinearSolvers/PCG.h	The local answer recognized the preconditioner family but stayed generic instead of tying it to the actual PCG update flow.

flow_001	Incorrect	In the PIC workflow, particle charges and positions are deposited onto the grid with CIC (`scatter`) or FEM assembly (`assemble_rhs_from_particles`), accumulated into `rho`, and then normalized/background-shifted in the manager before solving.	data/raw/ippl/alpine/AlpineManager.h; data/raw/ippl/src/Interpolation/CIC.hpp	
flow_002	Incorrect	After the field solve, the manager gathers the electric field back to particles with CIC `gather(...)` or FEM `interpolate_grad_to_diracs(...)`, storing particle-local `E` values for the push step.	data/raw/ippl/alpine/AlpineManager.h	
flow_003	Partial	Halo exchange uses `FieldLayout` neighbor/range metadata to pack field subviews, send/receive them with MPI, unpack into ghost or physical regions, and handle serial-periodic dimensions locally.	data/raw/ippl/src/Field/HaloCells.hpp; data/raw/ippl/src/Field/BareField.hpp	
flow_004	Partial	`ParticleSpatialLayout::update()` applies particle BCs, locates destination ranks, advertises receive counts with RMA, sends all registered attributes, destroys invalid local particles, and receives the incoming ones.	data/raw/ippl/src/Particle/ParticleSpatialLayout.hpp	The local answer found the owning routine but skipped most of the send/destroy/receive sequence.
flow_005	Partial	`FieldLayout` uses the partitioner and the requested parallel/serial decomposition flags to assign each rank a local `NDIndex`, plus neighbor and communication range tables.	data/raw/ippl/src/FieldLayout/FieldLayout.h; data/raw/ippl/src/Partition/Partitioner.h	
flow_006	Incorrect	`ParameterList` is merged into FFT and solver objects, then consumed by `setup()/initialize()/solve()` for communication mode, pencil/reorder flags, transform direction, solver type, tolerances, preconditioner settings, and output type.	data/raw/ippl/src/FFT/FFT.hpp; data/raw/ippl/src/PoissonSolvers/FFTPeriodicPoissonSolver.h; data/raw/ippl/src/PoissonSolvers/PoissonCG.h	
flow_007	Correct	`BaseManager::run()` executes `pre_step()`, `advance()`, and `post_step()` for each timestep; derived managers use those hooks for deposit/solve/gather, time updates, and output.	data/raw/ippl/src/Manager/BaseManager.h; data/raw/ippl/alpine/AlpineManager.h	
flow_008	Incorrect	FEM solvers move data by assembling field data into FEM load/stiffness representations (`evaluateLoadVector`, `evaluateAx`, `FEMVector`) and then interpolating the solved field quantities back where needed.	data/raw/ippl/src/FEM/LagrangeSpace.h; data/raw/ippl/src/FEM/LagrangeSpace.hpp; data/raw/ippl/src/FEM/FEMVector.h	
flow_009	Partial	After ORB recomputes the decomposition, particle ownership changes are realized by updating the layout/regions and then migrating particles with the usual particle update path.	data/raw/ippl/src/Decomposition/OrthogonalRecursiveBisection.hpp; data/raw/ippl/src/Particle/ParticleSpatialLayout.hpp	

api_001	Partial	A typical 3D field is `Field<double, 3, UniformCartesian<double, 3>, Cell>` constructed from a `UniformCartesian` mesh and a `FieldLayout<3>`.	data/raw/ippl/src/Field/Field.h; data/raw/ippl/src/Meshes/UniformCartesian.h; data/raw/ippl/doc/examples/BasicsFields.hpp	The local answer had the right shape but stayed abstract instead of grounding it in the concrete mesh/layout construction IPPL expects.
api_002	Partial	Construct the mesh as `UniformCartesian<double, Dim> mesh(domain, hx, origin);` where `hx` is the spacing vector and `origin` is the mesh origin.	data/raw/ippl/src/Meshes/UniformCartesian.h; data/raw/ippl/doc/examples/BasicsMesh.hpp	
api_003	Partial	Create a `BConds<FieldT, Dim>`, assign per-face BC objects such as `PeriodicFace<FieldT>`, then call `field.setFieldBC(bc)`.	data/raw/ippl/src/Field/Field.h; data/raw/ippl/src/Field/BConds.h; data/raw/ippl/src/Field/BcTypes.h	
api_004	Correct	Define a class derived from `ParticleBase<ParticleSpatialLayout<...>>`, add `mass` and `velocity` attributes as members, and register them with `addAttribute()` in the constructor.	data/raw/ippl/src/Particle/ParticleBase.h	
api_005	Incorrect	Call the free namespace functions `ippl::initialize(argc, argv);` and `ippl::finalize();` from `main`, as shown in the docs/examples.	data/raw/ippl/src/Ippl.h; data/raw/ippl/doc/examples/HelloWorld.hpp	
api_006	Partial	Set up the relevant layouts/fields/parameters, build an `FFT<CCTransform, ...>` or `FFT<RCTransform, ...>` object, and call `transform(FORWARD, ...)` on the field(s).	data/raw/ippl/src/FFT/FFT.h; data/raw/ippl/src/FFT/FFT.hpp; data/raw/ippl/doc/examples/BasicsFFT.hpp	
api_007	Partial	Construct `FFTPeriodicPoissonSolver(lhs, rhs)` (or default construct then set fields/params), ensure the RHS is attached, and call `solve()` to write the potential/gradient outputs.	data/raw/ippl/src/PoissonSolvers/FFTPeriodicPoissonSolver.h; data/raw/ippl/src/PoissonSolvers/FFTPeriodicPoissonSolver.hpp	
api_008	Incorrect	Use `PoissonCG<FieldT>` (or the Alpine `FieldSolver` wrapper around it), set its fields/parameters, and call `solve()` so the internal CG/PCG object iterates on the field.	data/raw/ippl/src/PoissonSolvers/PoissonCG.h	
api_009	Partial	For Gaussian draws, IPPL exposes both `randn` convenience generation and the more general `InverseTransformSampling` + `NormalDistribution` path.	data/raw/ippl/src/Random/Randn.h; data/raw/ippl/src/Random/NormalDistribution.h; data/raw/ippl/src/Random/InverseTransformSampling.h	
api_010	Correct	Register each particle attribute with `addAttribute(...)`; migration then serializes and transfers all registered attributes automatically.	data/raw/ippl/src/Particle/ParticleBase.h; data/raw/ippl/src/Particle/ParticleSpatialLayout.hpp	
api_011	Correct	Access rank and size with `ippl::Comm->rank()` and `ippl::Comm->size()` (or the same methods on a `Communicator` object).	data/raw/ippl/src/Communicate/Communicator.h	
api_012	Correct	Get a timer handle with `IpplTimings::getTimer("name")`, surround the code with `startTimer()` / `stopTimer()`, and print with `IpplTimings::print()`.	data/raw/ippl/src/Utility/IpplTimings.h	

par_001	Correct	IPPL gets performance portability by combining Kokkos execution/memory abstractions with MPI and heFFTe, so the same code paths can target CPUs and GPUs.	data/raw/ippl/README.md; data/raw/ippl/src/Utility/ParallelDispatch.h	
par_002	Partial	IPPL uses `Kokkos::View` because fields need execution-space-aware storage, subviews, mirrors, and portable kernels across host/device memory spaces.	data/raw/ippl/src/Field/BareField.h; data/raw/ippl/src/Communicate/Archive.h	The local answer did not really explain the motivation; it mostly restated that Views exist.
par_003	Partial	Loops are parallelized through `ippl::getRangePolicy` / `createRangePolicy` and the `ippl::parallel_for` wrapper over Kokkos `RangePolicy`/`MDRangePolicy`.	data/raw/ippl/src/Utility/ParallelDispatch.h	
par_004	Incorrect	Precision is chosen by the field value type (`Field<float,...>` vs `Field<double,...>`), and the codebase also contains mixed-precision examples where fields/particles deliberately use different precisions.	data/raw/ippl/src/Field/Field.h; data/raw/ippl/alpine/ExamplesWithoutPicManager/LandauDampingMixedPrecision.cpp	
par_005	Partial	Multiple execution spaces are enabled at build time through `IPPL_PLATFORMS` and Kokkos/HeFFTe backend flags; IPPL also has container helpers for multi-space data.	data/raw/ippl/INSTALLATION.md; data/raw/ippl/src/Utility/TypeUtils.h	
par_006	Correct	`ParallelDispatch.h` wraps Kokkos policies and functors, exposing `RangePolicy`, `getRangePolicy`, `createRangePolicy`, `parallel_for`, and `parallel_reduce`.	data/raw/ippl/src/Utility/ParallelDispatch.h	
par_007	Correct	`Archive` serializes Kokkos views into one-dimensional byte buffers with Kokkos kernels and `memcpy`, then deserializes them back into views on receive.	data/raw/ippl/src/Communicate/Archive.h; data/raw/ippl/src/Communicate/Archive.hpp	
par_008	Incorrect	MPI tags are managed with fixed base tags in `Tags.h` and the cyclic tag allocator in `TagMaker`, which `Communicator` inherits.	data/raw/ippl/src/Communicate/Tags.h; data/raw/ippl/src/Communicate/TagMaker.h; data/raw/ippl/src/Communicate/Communicator.h	
par_009	Partial	`Kokkos::fence()` waits for outstanding kernels; IPPL exposes `ippl::fence()` as a runtime wrapper in `Ippl.cpp` and also fences internally after many kernel/data-movement steps.	data/raw/ippl/src/Ippl.cpp; data/raw/ippl/src/Field/HaloCells.hpp; data/raw/ippl/src/Communicate/Archive.hpp	

bc_001	Correct	`BcTypes.h` provides periodic, constant, zero, extrapolating, and no-BC face classes.	data/raw/ippl/src/Field/BcTypes.h	
bc_002	Partial	Periodic BCs wrap values from the opposite side of the domain; there is no explicit `NeumannFace` class in this codebase, so the closest non-periodic behavior is constant/extrapolating face treatment.	data/raw/ippl/src/Field/BcTypes.h; data/raw/ippl/src/Field/BcTypes.hpp	The local answer's abstention was understandable because the question names a BC type that is not literally implemented, but it still missed the useful source-backed clarification.
bc_003	Incorrect	Ghost cells are populated mainly by `fillHalo()` / `PeriodicFace::apply()`: source slabs are packed, exchanged, and unpacked into ghost regions; `accumulateHalo_noghost()` is a different operation.	data/raw/ippl/src/Field/HaloCells.hpp; data/raw/ippl/src/Field/BcTypes.hpp	
bc_004	Incorrect	Periodic ghost cells are filled from opposite-side physical cells in `applyPeriodicSerialDim()` and the multi-rank `PeriodicFace::apply()` path.	data/raw/ippl/src/Field/HaloCells.hpp; data/raw/ippl/src/Field/BcTypes.hpp	
bc_005	Correct	The absorbing Maxwell BC uses second-order Mur-style formulas with precomputed weights and previous/current/next boundary values plus tangential neighbors to damp outgoing waves.	data/raw/ippl/src/MaxwellSolvers/AbsorbingBC.h	

num_001	Correct	The FFT Poisson solvers compute electrostatic potential (and optionally field/gradient) from charge density, i.e. the discretized Coulomb potential corresponding to `-Δφ = ρ`.	data/raw/ippl/src/PoissonSolvers/FFTOpenPoissonSolver.h; data/raw/ippl/src/PoissonSolvers/FFTPeriodicPoissonSolver.h	
num_002	Incorrect	The Maxwell solvers evolve electromagnetic field data: electric and magnetic fields (`E`, `B`) driven by a source/four-current field.	data/raw/ippl/src/MaxwellSolvers/Maxwell.h; data/raw/ippl/src/MaxwellSolvers/FDTDSolverBase.h	
num_003	Incorrect	The Landau damping mini-app models collisionless electrostatic plasma wave damping by phase mixing of particles against a sinusoidally perturbed distribution.	data/raw/ippl/alpine/LandauDamping.cpp; data/raw/ippl/alpine/LandauDampingManager.h; data/raw/ippl/doc/examples/LandauDampingEx.hpp	
num_004	Incorrect	The bump-on-tail example models a beam-on-background velocity distribution that drives an electrostatic instability (growth of Langmuir-like waves).	data/raw/ippl/alpine/BumponTailInstabilityManager.h; data/raw/ippl/alpine/BumponTailInstability.cpp	
num_005	Incorrect	The PenningTrap example simulates charged particles confined by a magnetic field and an external quadrupole electric potential, together with the self-consistent field from the particle charge density.	data/raw/ippl/alpine/PenningTrap.cpp; data/raw/ippl/alpine/PenningTrapManager.h	
num_006	Incorrect	The StructureFormation mini-app models the gravitational growth of cosmic structure from initial density fluctuations using particle dynamics.	data/raw/ippl/cosmology/StructureFormation.cpp	
num_007	Incorrect	FFT Poisson is fast and direct on structured uniform grids with compatible BCs but less flexible; CG/PCG is iterative and may be slower/convergence-limited, but it is more flexible for alternative discretizations, BCs, and preconditioning.	data/raw/ippl/src/PoissonSolvers/FFTPeriodicPoissonSolver.h; data/raw/ippl/src/PoissonSolvers/PoissonCG.h; data/raw/ippl/src/PoissonSolvers/FEMPoissonSolver.h	
num_008	Incorrect	`lbthres` is the tolerated load imbalance; once the imbalance exceeds roughly `lbthres * 100` percent, the mini-app triggers load balancing/repartitioning.	data/raw/ippl/alpine/LandauDamping.cpp; data/raw/ippl/alpine/PenningTrap.cpp; data/raw/ippl/alpine/BumponTailInstability.cpp	

ex_001	Incorrect	The LandauDamping mini-app is built from `alpine/LandauDamping.cpp` plus its manager and shared Alpine components such as `LandauDampingManager.h`, `AlpineManager.h`, `FieldContainer.hpp`, `FieldSolver.hpp`, `LoadBalancer.hpp`, and `ParticleContainer.hpp`.	data/raw/ippl/alpine/LandauDamping.cpp; data/raw/ippl/alpine/LandauDampingManager.h; data/raw/ippl/alpine/AlpineManager.h	
ex_002	Incorrect	`AlpineManager.h` supplies the shared PIC-manager logic for the alpine mini-apps: particle-to-grid, grid-to-particle, FEM/CIC switch, charge conservation checks, and common run-step hooks.	data/raw/ippl/alpine/AlpineManager.h	
ex_003	Incorrect	`LandauDamping.cpp` is the main double-precision Alpine mini-app using the manager-based stack; `LandauDampingMixedPrecision.cpp` is a mixed-precision variant that keeps some quantities in double and others in single precision for memory savings.	data/raw/ippl/alpine/LandauDamping.cpp; data/raw/ippl/alpine/ExamplesWithoutPicManager/LandauDampingMixedPrecision.cpp	
ex_004	Incorrect	`LandauDampingCorrectness.cpp` loads the generated CSV and the reference CSV, compares row counts and selected columns (`time`, `Ex_field_energy`, optionally `Ex_max_norm`) against a tolerance, and exits with pass/fail codes.	data/raw/ippl/alpine/validation/LandauDampingCorrectness.cpp; data/raw/ippl/alpine/validation/FieldLandau_valid_result.csv	
ex_005	Incorrect	The PenningTrap example configures a field container, particle container, and field solver in `pre_run()`, initializes particles from normal distributions, performs a warmup solve, then alternates deposit/solve/gather in the time integrator.	data/raw/ippl/alpine/PenningTrapManager.h; data/raw/ippl/alpine/PenningTrap.cpp	
ex_006	Incorrect	The BumponTailInstability executable accepts grid sizes, particle count, timestep count, solver type, load-balance threshold, timestep method, and the usual `--overallocate` / `--info` runtime options.	data/raw/ippl/alpine/BumponTailInstability.cpp	
ex_007	Incorrect	Those example files live under `doc/examples/`: `HelloWorld.hpp`, `BasicsFields.hpp`, `BasicsParticles.hpp`, and `BasicsFFT.hpp`.	data/raw/ippl/doc/examples/HelloWorld.hpp; data/raw/ippl/doc/examples/BasicsFields.hpp; data/raw/ippl/doc/examples/BasicsParticles.hpp; data/raw/ippl/doc/examples/BasicsFFT.hpp	

build_001	Incorrect	Core third-party dependencies are MPI for distributed communication, Kokkos for performance portability, heFFTe for FFT backends/plans, FFTW/CuFFT as optional FFT backends, and GoogleTest for tests.	data/raw/ippl/README.md; data/raw/ippl/INSTALLATION.md; data/raw/ippl/unit_tests/CMakeLists.txt	
build_002	Incorrect	IPPL requires C++20, as stated in the README badge and the installation examples/configuration flags.	data/raw/ippl/README.md; data/raw/ippl/INSTALLATION.md	
build_003	Incorrect	GPU builds are enabled through CMake options like `IPPL_PLATFORMS=CUDA` or `IPPL_PLATFORMS="HIP;OPENMP"` plus matching Kokkos/architecture/backend flags (`Kokkos_ARCH_*`, `CMAKE_CUDA_ARCHITECTURES`, `Kokkos_ENABLE_HIP`, `Heffte_ENABLE_ROCM`, etc.).	data/raw/ippl/INSTALLATION.md	
build_004	Partial	`INSTALLATION.md` describes Kokkos version selection plus backend/architecture options used with IPPL builds, including CUDA and HIP/OpenMP examples and `IPPL_PLATFORMS` combinations.	data/raw/ippl/INSTALLATION.md	
build_005	Correct	The EULER install guide says to connect with VPN/SSH, switch to the new software stack, purge modules, load GCC/CMake/CUDA/OpenMPI, clone the repo, configure a build, compile, and test on an interactive node.	data/raw/ippl/doc/extras/IPPLonEULER.md	

test_001	Correct	Unit tests are organized under `unit_tests/` by subsystem and are parameterized over precision, dimensionality, and available execution-space combinations, as described in `UNIT_TESTS.md`.	data/raw/ippl/unit_tests/CMakeLists.txt; data/raw/ippl/UNIT_TESTS.md	
test_002	Correct	`WORKFLOW.md` requires camelCase variables, CAPITAL_CASE compile-time constants, and member names suffixed with `_m`.	data/raw/ippl/WORKFLOW.md	
test_003	Correct	Use `std::sqrt` in host-only code, and `Kokkos::sqrt` in device-capable code such as `KOKKOS_INLINE_FUNCTION` kernels.	data/raw/ippl/WORKFLOW.md	
test_004	Incorrect	IPPL profiles MPI calls with mpiP by preloading `libmpiP.so`, optionally setting `MPIP` flags, then parsing the produced `.mpiP` output with the bundled `scripts/mpiP.py`.	data/raw/ippl/README.md; data/raw/ippl/scripts/mpiP.py	
test_005	Incorrect	The README does include a Gwendolen SLURM template showing the `gmerlin6` cluster, `gwendolen` partition, GPU count, and `srun ./<your_executable> <args> --kokkos-map-device-id-by=mpi_rank`.	data/raw/ippl/README.md	
"""


def parse_evaluations() -> dict[str, Evaluation]:
    out: dict[str, Evaluation] = {}
    for raw in RAW_EVALUATIONS.strip().splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) == 4:
            parts.append("")
        if len(parts) != 5:
            raise ValueError(f"Malformed evaluation row: {raw!r}")
        question_id, verdict, reference, refs, note = parts
        out[question_id] = Evaluation(question_id, verdict, reference, refs, note.strip())
    return out


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_answer_excerpt(answer: str, max_len: int = 240) -> str:
    collapsed = " ".join(answer.split())
    return collapsed if len(collapsed) <= max_len else collapsed[: max_len - 3] + "..."


def format_answer_result(answer: dict) -> str:
    error = answer.get("error")
    if error:
        error_type = error.get("type", "Error")
        message = error.get("message", "")
        return f"- Local answer error: `{error_type}: {message}`"
    return f"- Local answer excerpt: `{normalize_answer_excerpt(answer['answer'])}`"


def category_display_name(raw: str) -> str:
    return raw.replace("_", " ").title()


def build_markdown(
    questions_doc: dict,
    answers_doc: dict,
    evaluations: dict[str, Evaluation],
) -> str:
    question_map = {q["id"]: q for q in questions_doc["questions"]}
    answers = answers_doc["answers"]

    if set(question_map) != set(evaluations):
        missing = sorted(set(question_map) - set(evaluations))
        extra = sorted(set(evaluations) - set(question_map))
        raise SystemExit(f"Evaluation coverage mismatch. Missing={missing} Extra={extra}")

    scored_rows = []
    by_category = collections.defaultdict(list)
    for answer in answers:
        ev = evaluations[answer["id"]]
        score = VERDICT_SCORE[ev.verdict]
        scored_rows.append((answer, ev, score))
        by_category[answer["category"]].append((answer, ev, score))

    total_questions = len(scored_rows)
    correct = sum(1 for _, ev, _ in scored_rows if ev.verdict == "Correct")
    partial = sum(1 for _, ev, _ in scored_rows if ev.verdict == "Partial")
    incorrect = sum(1 for _, ev, _ in scored_rows if ev.verdict == "Incorrect")
    overall_score = sum(score for _, _, score in scored_rows) / total_questions

    latencies = [a["latency_seconds"] for a, _, _ in scored_rows]
    mean_latency = statistics.mean(latencies)
    median_latency = statistics.median(latencies)

    settings_snapshot = answers_doc["settings_snapshot"]
    vector_manifest = answers_doc["vector_store_manifest"]
    run_metadata = answers_doc["run_metadata"]
    models = answers_doc["models"]

    lines: list[str] = []
    lines.append("# Codex GPT-5.4 vs Local LLM Evaluation")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")
    lines.append("## Goal")
    lines.append("")
    lines.append(
        "This report compares the saved local-LLM answer run in "
        f"`{ANSWERS_PATH.relative_to(REPO_ROOT)}` against a direct source-reading pass over "
        "`data/raw/ippl`. The Codex side of the comparison was done by reading the IPPL codebase "
        "and docs directly rather than querying the local RAG system again."
    )
    lines.append("")
    lines.append("## Test Environment")
    lines.append("")
    lines.append("### Codex Side")
    lines.append("")
    lines.append("- Model: `GPT-5.4` (Codex)")
    lines.append("- Method: direct source/doc reading of `data/raw/ippl`")
    lines.append("- Retrieval used for grading: none; this was a manual code-reading comparison")
    lines.append("")
    lines.append("### Local LLM Side")
    lines.append("")
    lines.append(f"- Host: `{run_metadata['hostname']}`")
    lines.append(f"- Job / partition: `{run_metadata['slurm_job_id']}` on `{run_metadata['slurm_partition']}`")
    lines.append(f"- Answer model: `{models['answer_model']['raw']}`")
    lines.append(f"- Chunk explanation model: `{models['chunk_explanation_model']['raw']}`")
    lines.append(f"- File / module / call-chain models: `{models['file_level_model']['raw']}`, `{models['module_level_model']['raw']}`, `{models['call_chain_model']['raw']}`")
    lines.append(f"- Parser: `{run_metadata['parser_type']}`")
    lines.append(f"- Question count: `{run_metadata['answer_count']}`")
    lines.append(f"- Answer prompt mode: `{run_metadata['answer_prompt_mode']}`")
    lines.append(f"- Mean answer latency: `{mean_latency:.2f}s`")
    lines.append(f"- Median answer latency: `{median_latency:.2f}s`")
    lines.append("")
    lines.append("### Retrieval Configuration Used by the Saved Run")
    lines.append("")
    lines.append(f"- Candidate k: `{settings_snapshot['retrieval']['candidate_k']}`")
    lines.append(f"- Supplementary k: `{settings_snapshot['retrieval']['supplementary_k']}`")
    lines.append(f"- Supplementary candidate k: `{settings_snapshot['retrieval']['supplementary_candidate_k']}`")
    lines.append(f"- Vector store chunk count: `{run_metadata['vector_store_chunk_count']}`")
    lines.append("")
    lines.append("## Important Caveat")
    lines.append("")
    lines.append(
        "The saved answer file says the runtime settings had `BAAI/bge-code-v1` configured as the "
        "sentence-transformer model, but the persisted vector-store manifest embedded in the same "
        "answer file still shows `embedding_backend = ollama` and `embedding_model = nomic-embed-text`."
    )
    lines.append("")
    lines.append(
        "That means this evaluated answer run was produced with the 32B answer model on top of an "
        "older persisted `nomic-embed-text` vector store, not on top of a rebuilt `bge-code-v1` store. "
        "This matters because several of the misses in algorithm/example/build questions are consistent "
        "with retrieval undercoverage rather than answer-model weakness alone."
    )
    lines.append("")
    lines.append("## Overall Result")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Questions | {total_questions} |")
    lines.append(f"| Correct | {correct} |")
    lines.append(f"| Partial | {partial} |")
    lines.append(f"| Incorrect | {incorrect} |")
    lines.append(f"| Average score (`Correct=1`, `Partial=0.5`, `Incorrect=0`) | {overall_score:.3f} |")
    lines.append("")
    lines.append("## Main Findings")
    lines.append("")
    lines.append("- Strongest area: file-purpose and class-responsibility questions. When the answer could be recovered from a single well-described header, the local model was often solid.")
    lines.append("- Weakest area: algorithm, examples/mini-apps, numerical meaning, and build/configuration questions. Those require cross-file synthesis or specific docs/examples that the retrieved context often did not surface.")
    lines.append("- Recurrent failure mode: false abstention. Many wrong answers were not hallucinations so much as 'the retrieved context does not contain this', even when the codebase clearly did.")
    lines.append("- Another recurrent failure mode: overspecialization. The `FFT.hpp` answer is the clearest example: the model latched onto one specialization and treated it as the whole file.")
    lines.append("- The workflow/build docs were underused. README / INSTALLATION / example comments contain direct answers for several questions that the local run still missed.")
    lines.append("")
    lines.append("## Category Breakdown")
    lines.append("")
    lines.append("| Category | Questions | Correct | Partial | Incorrect | Avg score |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for category in [q["category"] for q in questions_doc["questions"]]:
        if category not in by_category:
            continue
        rows = by_category.pop(category)
        c = sum(1 for _, ev, _ in rows if ev.verdict == "Correct")
        p = sum(1 for _, ev, _ in rows if ev.verdict == "Partial")
        i = sum(1 for _, ev, _ in rows if ev.verdict == "Incorrect")
        avg = sum(score for _, _, score in rows) / len(rows)
        lines.append(
            f"| {category_display_name(category)} | {len(rows)} | {c} | {p} | {i} | {avg:.3f} |"
        )
    lines.append("")
    lines.append("## Detailed Per-Question Evaluation")
    lines.append("")

    ordered_categories = []
    seen = set()
    for q in questions_doc["questions"]:
        if q["category"] not in seen:
            ordered_categories.append(q["category"])
            seen.add(q["category"])

    answers_by_id = {a["id"]: a for a in answers_doc["answers"]}

    for category in ordered_categories:
        lines.append(f"### {category_display_name(category)}")
        lines.append("")
        for q in [q for q in questions_doc["questions"] if q["category"] == category]:
            answer = answers_by_id[q["id"]]
            ev = evaluations[q["id"]]
            note = ev.note or DEFAULT_NOTE[ev.verdict]
            lines.append(f"#### {q['id']} - {q['question']}")
            lines.append("")
            lines.append(f"- Verdict: **{ev.verdict}**")
            lines.append(f"- Codex reference answer: {ev.reference}")
            lines.append(f"- Comparison: {note}")
            lines.append(f"- Primary sources: `{ev.refs}`")
            lines.append(format_answer_result(answer))
            lines.append("")

    lines.append("## Conclusion")
    lines.append("")
    lines.append(
        "The local 32B run was plainly useful, but its quality was uneven. It did reasonably well on "
        "single-file structural questions, and it often answered in a measured tone rather than "
        "hallucinating wildly. The bigger problem was coverage: once the answer depended on the right "
        "example file, the right solver implementation, or a cross-file algorithm story, it often "
        "fell back to abstention or to whichever nearby chunk looked most similar."
    )
    lines.append("")
    lines.append(
        "The most actionable next step is not only to swap answer models. It is to rebuild the vector "
        "store with the intended embedder, keep the file/module summaries precise, and make retrieval "
        "more likely to surface examples, solver implementations, and doc pages when the question "
        "obviously targets those assets."
    )
    lines.append("")

    return "\n".join(lines)


def markdown_to_plaintext(markdown_text: str) -> str:
    lines = []
    for raw in markdown_text.splitlines():
        line = raw
        if line.startswith("#"):
            line = line.lstrip("#").strip().upper()
        line = line.replace("**", "")
        line = line.replace("`", "")
        if line.startswith("|") and line.endswith("|"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            line = " | ".join(parts)
        lines.append(line)
    return "\n".join(lines)


class SimplePDF:
    def __init__(self, title: str):
        self.title = title
        self.pages: list[list[str]] = []

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def add_wrapped_text(self, text: str, width: int = 100, lines_per_page: int = 62) -> None:
        current: list[str] = []
        for raw in text.splitlines():
            if not raw.strip():
                wrapped = [""]
            else:
                wrapped = textwrap.wrap(
                    raw,
                    width=width,
                    break_long_words=False,
                    replace_whitespace=False,
                    drop_whitespace=False,
                )
            for line in wrapped:
                if len(current) >= lines_per_page:
                    self.pages.append(current)
                    current = []
                current.append(line)
        if current:
            self.pages.append(current)

    def write(self, path: Path) -> None:
        objects: list[bytes] = []

        def add_object(data: bytes) -> int:
            objects.append(data)
            return len(objects)

        font_obj = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

        page_objs = []
        content_objs = []

        for page_index, page_lines in enumerate(self.pages, start=1):
            stream_lines = ["BT", "/F1 9 Tf", "50 800 Td", "11 TL"]
            header = f"{self.title}  |  page {page_index}/{len(self.pages)}"
            stream_lines.append(f"({self._escape(header)}) Tj")
            stream_lines.append("T*")
            stream_lines.append("T*")
            for line in page_lines:
                stream_lines.append(f"({self._escape(line)}) Tj")
                stream_lines.append("T*")
            stream_lines.append("ET")
            stream = "\n".join(stream_lines).encode("latin-1", "replace")
            content_obj = add_object(
                b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
            )
            content_objs.append(content_obj)
            page_objs.append(
                add_object(
                    (
                        f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 595 842] "
                        f"/Resources << /Font << /F1 {font_obj} 0 R >> >> "
                        f"/Contents {content_obj} 0 R >>"
                    ).encode("ascii")
                )
            )

        kids = " ".join(f"{obj} 0 R" for obj in page_objs)
        pages_obj = add_object(f"<< /Type /Pages /Kids [ {kids} ] /Count {len(page_objs)} >>".encode("ascii"))

        # Replace parent placeholder in pages.
        for idx, objnum in enumerate(page_objs):
            objects[objnum - 1] = objects[objnum - 1].replace(b"/Parent 0 0 R", f"/Parent {pages_obj} 0 R".encode("ascii"))

        catalog_obj = add_object(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode("ascii"))

        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for i, obj in enumerate(objects, start=1):
            offsets.append(len(output))
            output.extend(f"{i} 0 obj\n".encode("ascii"))
            output.extend(obj)
            output.extend(b"\nendobj\n")

        xref_offset = len(output)
        output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        output.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            output.extend(f"{off:010d} 00000 n \n".encode("ascii"))
        output.extend(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF\n"
            ).encode("ascii")
        )
        path.write_bytes(output)


def main() -> None:
    questions_doc = load_json(QUESTIONS_PATH)
    answers_doc = load_json(ANSWERS_PATH)
    evaluations = parse_evaluations()

    markdown_report = build_markdown(questions_doc, answers_doc, evaluations)
    OUTPUT_MD.write_text(markdown_report, encoding="utf-8")

    pdf = SimplePDF("Codex GPT-5.4 vs Local LLM Evaluation")
    pdf.add_wrapped_text(markdown_to_plaintext(markdown_report))
    pdf.write(OUTPUT_PDF)

    print(f"Wrote {OUTPUT_MD}")
    print(f"Wrote {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
