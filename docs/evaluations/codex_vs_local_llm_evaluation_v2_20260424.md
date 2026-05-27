# Codex GPT-5.4 vs Local LLM Evaluation (V2)

Generated: 2026-05-26 08:25:25 UTC

## Goal

This report compares the saved local-LLM V2 answer run in `docs/evaluations/answers/eval_v2_20260424T140027Z.json` against a direct source/doc reading pass over `data/raw/ippl`. The Codex side of the comparison reuses the same source-backed reference answers and verdicts established in the first evaluation round for the overlapping question IDs.

## Test Environment

### Codex Side

- Model: `GPT-5.4` (Codex)
- Method: direct source/doc reading of `data/raw/ippl`
- Question set: `docs/evaluations/eval_questions_v2.json`
- Retrieval used for grading: none; this was a source-backed comparison pass

### Local LLM Side

- Host: `merlin-g-100.psi.ch`
- Job / partition: `352660` on `gwendolen`
- Answer model: `qwen2.5-coder:32b-instruct-q4_K_M`
- Chunk explanation model: `qwen2.5-coder:14b`
- File / module / call-chain models: `qwen2.5-coder:32b-instruct-q4_K_M`, `qwen2.5-coder:32b-instruct-q4_K_M`, `qwen2.5-coder:32b-instruct-q4_K_M`
- Parser: `tree_sitter`
- Question count: `100`
- Answer prompt mode: `retrieval_answer_v2`
- Mean answer latency: `18.51s`
- Median answer latency: `17.16s`

### Retrieval Configuration Used by the Saved Run

- Candidate k: `20`
- Supplementary k: `3`
- Supplementary candidate k: `10`
- Vector store chunk count: `8013`

## Important Caveat

The saved answer file and embedded vector-store manifest are consistent enough that this report can be read as a straightforward evaluation of the saved V2 run.

## Overall Result

| Metric | Value |
|---|---:|
| Questions | 100 |
| Correct | 44 |
| Partial | 24 |
| Incorrect | 32 |
| Average score (`Correct=1`, `Partial=0.5`, `Incorrect=0`) | 0.560 |

## Main Findings

- Strongest areas: File Purpose, Class Responsibility. These questions were usually answerable from a single clear header, implementation file, or doc page.
- Weakest areas: Build And Install, Data Flow. These still tend to require cross-file synthesis, exact implementation location, or a sharper retrieval handoff between related subsystems.
- Compared with the first round, this V2 set removes test- and miniapp-dependent questions, so the remaining misses are a cleaner view of retrieval and answer quality over `src/` plus repository docs.
- The recurring failure mode is still undercoverage: when the right implementation file or doc page is not surfaced, the local answer either abstains or answers from a nearby but incomplete chunk.
- The strongest answers remain the structural ones: file purpose, class responsibility, and direct API usage tend to do well when one primary file dominates the evidence.

## Category Breakdown

| Category | Questions | Correct | Partial | Incorrect | Avg score |
|---|---:|---:|---:|---:|---:|
| File Purpose | 13 | 12 | 0 | 1 | 0.923 |
| Definition Location | 15 | 4 | 3 | 8 | 0.367 |
| Class Responsibility | 13 | 11 | 1 | 1 | 0.885 |
| Algorithm | 12 | 3 | 4 | 5 | 0.417 |
| Data Flow | 9 | 1 | 4 | 4 | 0.333 |
| Api Usage | 12 | 4 | 6 | 2 | 0.583 |
| Parallelism And Kokkos | 9 | 3 | 4 | 2 | 0.556 |
| Boundary And Halo | 5 | 2 | 1 | 2 | 0.500 |
| Numerical Meaning | 3 | 1 | 0 | 2 | 0.333 |
| Build And Install | 5 | 1 | 1 | 3 | 0.300 |
| Testing And Workflow | 4 | 2 | 0 | 2 | 0.500 |

## Detailed Per-Question Evaluation

### File Purpose

#### file_001 - What does Ippl.h do?

- Verdict: **Correct**
- Codex reference answer: Declares the top-level IPPL runtime handles (`Comm`, `Env`, `Info`, `Warn`, `Error`) and the lifecycle wrappers `initialize`, `finalize`, `fence`, and `abort`.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Ippl.h`
- Local answer excerpt: `Answer: Ippl.h serves as a central interface header file for the IPPL library. It includes several other headers necessary for its functionalities and defines essential communication objects such as `Comm` and `Env`, along with logging o...`

#### file_002 - What is the purpose of Ippl.cpp?

- Verdict: **Correct**
- Codex reference answer: Implements runtime setup/teardown: command-line option parsing, MPI communicator/environment creation, logger setup, Kokkos init/finalize, and abort/fence helpers.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Ippl.cpp`
- Local answer excerpt: `Answer: Ippl.cpp contains several utility and lifecycle management functions for the IPPL library, including initialization (`initialize`), option checking (`checkOption`), numerical option parsing (`getNumericalOption`), finalization (`...`

#### file_003 - What does FFT.hpp implement?

- Verdict: **Incorrect**
- Codex reference answer: Implements `FFTBase` setup plus the FFT specialization family for complex/real, sine, cosine, and cosine-I transforms on IPPL fields via heFFTe.
- Comparison: Narrowed the whole file to one `FFT<RCTransform, RealField>` path and missed the rest of the specialization family.
- Primary sources: `data/raw/ippl/src/FFT/FFT.hpp`
- Local answer excerpt: `Answer: FFT.hpp defines the base class template `FFTBase` and several specializations of the `FFT` class template for different types of transforms (e.g., `CCTransform`, `RCTransform`, `SiTransform`). It includes methods like `transform`...`

#### file_004 - What is BareField.h responsible for?

- Verdict: **Correct**
- Codex reference answer: Defines the core distributed field container: Kokkos-backed storage, owned/allocated domains, field layout access, halo exchange hooks, and expression-style assignment.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Field/BareField.h`
- Local answer excerpt: `Answer: `BareField.h` defines the `BareField` class, which represents a field managing memory and metadata for multi-dimensional data arrays. It includes methods like `getAllocated`, `getCommunicator`, `getDomain`, `getHalo`, `getHostMir...`

#### file_005 - What does Field.h add on top of BareField?

- Verdict: **Correct**
- Codex reference answer: Adds mesh awareness and boundary-condition management on top of `BareField`, plus volume integral/average helpers.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Field/Field.h`
- Local answer excerpt: `Answer: The `Field` class extends `BareField` by adding mesh and configurable boundary conditions. It includes methods such as `get_mesh`, `getFieldBC`, `setFieldBC`, `deepCopy`, `getVolumeAverage`, `getVolumeIntegral`, `initialize`, and...`

#### file_006 - What role does HaloCells.h play in IPPL?

- Verdict: **Correct**
- Codex reference answer: Defines the halo-exchange machinery for fields: pack/unpack, boundary exchange, and periodic handling for ghost cells.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Field/HaloCells.h; data/raw/ippl/src/Field/HaloCells.hpp`
- Local answer excerpt: `Answer: The `HaloCells.h` header file defines the `HaloCells` template class and associated structs (`assign`, `lhs_plus_assign`, `rhs_plus_assign`) to handle halo exchange operations in parallel computations. It facilitates data communi...`

#### file_007 - What is the purpose of FieldLayout.h?

- Verdict: **Correct**
- Codex reference answer: Defines how a global `NDIndex` domain is partitioned across MPI ranks, including local subdomains, neighbors, and communication ranges.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/FieldLayout/FieldLayout.h`
- Local answer excerpt: `Answer: FieldLayout.h defines the `FieldLayout` class template, which manages the distribution and properties of fields across parallel domains in simulations within the IPPL library. The file includes methods for handling dimensions, bo...`

#### file_008 - What does ParticleBase.h define?

- Verdict: **Correct**
- Codex reference answer: Defines the generic particle container base class with positions, optional IDs, registered attributes, and a particle layout that controls migration.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Particle/ParticleBase.h`
- Local answer excerpt: `Answer: `ParticleBase.h` defines `ParticleBase`, a base class for managing and storing particle data in IPPL. It includes methods like `getAttributeNum`, `getLayout`, `getLocalNum`, `getTotalNum` for accessing attributes, layout, local c...`

#### file_009 - What is the purpose of ParticleSpatialLayout.h?

- Verdict: **Correct**
- Codex reference answer: Defines the spatial particle layout that decides ownership by region and migrates particles to the correct rank after motion.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Particle/ParticleSpatialLayout.h; data/raw/ippl/src/Particle/ParticleSpatialLayout.hpp`
- Local answer excerpt: `Answer: The `ParticleSpatialLayout` class in `ParticleSpatialLayout.h` manages spatial layout configurations for particles within computational regions. It handles region layouts and neighbor communications, providing methods to retrieve...`

#### file_010 - What does ParticleAttrib.h implement?

- Verdict: **Correct**
- Codex reference answer: Implements the `ParticleAttrib` storage object: a Kokkos-view-backed particle attribute with resize, serialization, and mirror/access helpers.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Particle/ParticleAttrib.h`
- Local answer excerpt: `Answer: The `ParticleAttrib` class template is responsible for managing attributes associated with particles in simulations. It provides methods for serialization (`deserialize`), printing (`print`), memory management (`realloc`, `resize...`

#### file_011 - What is UniformCartesian.h for?

- Verdict: **Correct**
- Codex reference answer: Defines the uniform Cartesian mesh class with spacing, origin, cell volume, total mesh volume, and vertex-position helpers.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Meshes/UniformCartesian.h`
- Local answer excerpt: `Answer: UniformCartesian.h defines the `UniformCartesian` class template, which represents a uniform Cartesian mesh derived from `Mesh<T, Dim>`. This class provides methods for calculating vertex positions (`getVertexPosition`), cell vol...`

#### file_012 - What does OrthogonalRecursiveBisection.h do?

- Verdict: **Correct**
- Codex reference answer: Declares the orthogonal recursive bisection domain-decomposition/load-balancing class and its cut/median/repartition helpers.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Decomposition/OrthogonalRecursiveBisection.h`
- Local answer excerpt: `Answer: The `OrthogonalRecursiveBisection` class in `OrthogonalRecursiveBisection.h` is designed to handle domain decomposition through orthogonal recursive bisection. This method divides a computational domain into smaller subdomains ef...`

#### file_013 - What is the purpose of CIC.h in the Interpolation subsystem?

- Verdict: **Correct**
- Codex reference answer: Declares the first-order cloud-in-cell interpolation helpers for scatter/gather between particles and grid fields.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Interpolation/CIC.h`
- Local answer excerpt: `Answer: The file `CIC.h` in the Interpolation subsystem defines essential interfaces and operations related to Cloud-in-Cell (CIC) interpolation. It declares template functions that compute weights, indices, and perform scattering of par...`

### Definition Location

#### loc_001 - Where is FFT initialization implemented in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: FFT initialization lives in `src/FFT/FFT.hpp`, especially `FFTBase` construction/setup and the transform-specific constructors that build the heFFTe plans.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/FFT/FFT.hpp`
- Local answer excerpt: `Answer: FFT initialization in IPPL is implemented in the `FFT<RCTransform, RealField>` constructor within the `FFT.hpp` file. This constructor sets up the FFT operation using the Heffte library by configuring input and output layouts thr...`

#### loc_002 - Where does IPPL set up the MPI environment?

- Verdict: **Partial**
- Codex reference answer: IPPL sets up MPI in `src/Ippl.cpp::initialize()` by constructing `mpi::Environment` and `mpi::Communicator`; the low-level `MPI_Init` check/call is in `src/Communicate/Environment.cpp`.
- Comparison: The local answer found the low-level MPI constructor, but missed that the IPPL entry point is `ippl::initialize()` in `Ippl.cpp`.
- Primary sources: `data/raw/ippl/src/Ippl.cpp; data/raw/ippl/src/Communicate/Environment.cpp`
- Local answer error: `NameError: name 'exact_symbols' is not defined`

#### loc_003 - Where is Kokkos initialized and finalized inside IPPL?

- Verdict: **Incorrect**
- Codex reference answer: Kokkos is initialized and finalized directly in `src/Ippl.cpp` inside `ippl::initialize()` and `ippl::finalize()`.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/Ippl.cpp`
- Local answer error: `NameError: name 'exact_symbols' is not defined`

#### loc_004 - Where is the orthogonal recursive bisection load balancer implemented?

- Verdict: **Correct**
- Codex reference answer: The ORB load balancer is implemented in `src/Decomposition/OrthogonalRecursiveBisection.hpp` with declarations in the matching header.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Decomposition/OrthogonalRecursiveBisection.hpp`
- Local answer excerpt: `Answer: The orthogonal recursive bisection load balancer is implemented in the `OrthogonalRecursiveBisection.h` and `OrthogonalRecursiveBisection.hpp` files. The primary class template definition for this functionality is found in `Ortho...`

#### loc_005 - Where are boundary conditions applied to a Field?

- Verdict: **Partial**
- Codex reference answer: Field BCs are attached in `Field::setFieldBC()` and actually applied through `BConds::apply()` and the concrete face classes in `BcTypes.hpp`.
- Comparison: The local answer contains real signal, but it misses an important scope boundary, file, or algorithm detail.
- Primary sources: `data/raw/ippl/src/Field/Field.h; data/raw/ippl/src/Field/BConds.hpp; data/raw/ippl/src/Field/BcTypes.hpp`
- Local answer excerpt: `Answer: Boundary conditions are applied to a `Field` through the `BConds` class, which contains and manages various boundary condition objects (`BCondBase`). The `apply` method of these boundary condition objects is called on a `Field& f...`

#### loc_006 - Where is the CIC (cloud-in-cell) scatter implemented?

- Verdict: **Incorrect**
- Codex reference answer: CIC scatter is implemented in `src/Interpolation/CIC.hpp`, primarily `scatterToPoint()` and `scatterToField()`.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/Interpolation/CIC.hpp`
- Local answer excerpt: `Answer: The CIC (cloud-in-cell) scatter implementation is found in the `CIC.h` and `CIC.hpp` files within the Interpolation module. Specifically, the `scatterToPoint` and `scatterToField` functions are declared in `CIC.h`, and their defi...`

#### loc_007 - Where is the CIC gather implemented?

- Verdict: **Incorrect**
- Codex reference answer: CIC gather is implemented in `src/Interpolation/CIC.hpp`, primarily `gatherFromPoint()` and `gatherFromField()`.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/Interpolation/CIC.hpp`
- Local answer excerpt: `Answer: The CIC gather implementation is not explicitly detailed in the provided chunks. The chunks discuss methods related to CIC interpolation and gathering but do not provide a specific implementation of the CIC gather operation. They...`

#### loc_008 - Where is halo exchange for BareField implemented?

- Verdict: **Partial**
- Codex reference answer: Halo exchange for `BareField` is surfaced in `src/Field/BareField.hpp` and actually performed in `src/Field/HaloCells.hpp`.
- Comparison: The local answer found the right concept, but not the exact implementation split across the wrapper and helper file.
- Primary sources: `data/raw/ippl/src/Field/BareField.hpp; data/raw/ippl/src/Field/HaloCells.hpp`
- Local answer excerpt: `Answer: Halo exchange for `BareField` is implemented in the `accumulateHalo` method defined within the `BareField.hpp` file. The `accumulateHalo` method likely utilizes the `HaloCells` class from `HaloCells.h` to manage halo cell exchang...`

#### loc_009 - Where are the FFT-based open-boundary Poisson solver routines defined?

- Verdict: **Incorrect**
- Codex reference answer: The FFT open-boundary Poisson routines are defined in `src/PoissonSolvers/FFTOpenPoissonSolver.h` and `src/PoissonSolvers/FFTOpenPoissonSolver.hpp`.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/PoissonSolvers/FFTOpenPoissonSolver.h; data/raw/ippl/src/PoissonSolvers/FFTOpenPoissonSolver.hpp`
- Local answer excerpt: `Answer: The FFT-based open-boundary Poisson solver routines are defined in the `FFTOpenPoissonSolver.hpp` and `FFTOpenPoissonSolver.h` files. The `FFTOpenPoissonSolver` class template is responsible for solving Poisson equations using FF...`

#### loc_010 - Where is the conjugate gradient solver algorithm implemented?

- Verdict: **Incorrect**
- Codex reference answer: The CG/PCG algorithm implementation is in `src/LinearSolvers/PCG.h`; the Poisson wrapper that instantiates it is `src/PoissonSolvers/PoissonCG.h`.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/LinearSolvers/PCG.h; data/raw/ippl/src/PoissonSolvers/PoissonCG.h`
- Local answer excerpt: `Answer: The conjugate gradient solver algorithm is implemented in the `PCG` class within the file `LinearSolvers/PCG.h`. The `PoissonCG` class in `PoissonSolvers/PoissonCG.h` utilizes this implementation through its `solve` method, which...`

#### loc_011 - Where is the FEM Poisson solver implemented?

- Verdict: **Correct**
- Codex reference answer: The FEM Poisson solver is implemented in `src/PoissonSolvers/FEMPoissonSolver.h`.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/PoissonSolvers/FEMPoissonSolver.h`
- Local answer excerpt: `Answer: The FEM Poisson solver is implemented in the `FEMPoissonSolver` class, defined in the file `FEMPoissonSolver.h` located under the path `data/raw/ippl/src/PoissonSolvers`. This class inherits from `Poisson<FieldLHS, FieldRHS>` and...`

#### loc_012 - Where is the FDTD Maxwell solver base class defined?

- Verdict: **Incorrect**
- Codex reference answer: The FDTD Maxwell solver base class is defined in `src/MaxwellSolvers/FDTDSolverBase.h` with implementation in `FDTDSolverBase.hpp`.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/MaxwellSolvers/FDTDSolverBase.h; data/raw/ippl/src/MaxwellSolvers/FDTDSolverBase.hpp`
- Local answer excerpt: `Answer: The FDTD Maxwell solver base class is not explicitly mentioned or defined in the provided retrieved context. The context discusses a `Maxwell` base class for solvers of Maxwell's equations but does not specify it as an FDTD-speci...`

#### loc_013 - Where is the LagrangeSpace class defined?

- Verdict: **Correct**
- Codex reference answer: The `LagrangeSpace` class is defined in `src/FEM/LagrangeSpace.h` with methods implemented in `src/FEM/LagrangeSpace.hpp`.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/FEM/LagrangeSpace.h; data/raw/ippl/src/FEM/LagrangeSpace.hpp`
- Local answer excerpt: `Answer: The `LagrangeSpace` class template is defined in the file `data/raw/ippl/src/FEM/LagrangeSpace.h`. This header file includes key abstractions such as `DeviceStruct` and provides essential methods for handling Lagrangian finite el...`

#### loc_014 - Where is the particle update routine (that moves particles across ranks) implemented?

- Verdict: **Correct**
- Codex reference answer: Particle migration between ranks is implemented in `ParticleSpatialLayout::update()` in `src/Particle/ParticleSpatialLayout.hpp`.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Particle/ParticleSpatialLayout.hpp`
- Local answer excerpt: `Answer: The particle update routine that moves particles across ranks is primarily implemented in the `update` method of the `ParticleSpatialLayout<T, Dim, Mesh, Properties...>` class template in the `ParticleSpatialLayout.hpp` file. Thi...`

#### loc_015 - Where are IPPL timers defined?

- Verdict: **Incorrect**
- Codex reference answer: IPPL timers are defined by the singleton timing layer in `src/Utility/IpplTimings.h/.cpp`, not just the low-level `Timer` helper.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/Utility/IpplTimings.h; data/raw/ippl/src/Utility/IpplTimings.cpp`
- Local answer excerpt: `Answer: IPPL timers are primarily defined in `Timer.h` and managed within the `IpplTimings` class. The `Timer` class provides functionality for timing operations, while `IpplTimings` manages and reports timing information using instances...`

### Class Responsibility

#### cls_001 - What is the main responsibility of the BareField class?

- Verdict: **Correct**
- Codex reference answer: `BareField` is the core distributed field storage class: it owns the data view, domain metadata, layout link, and halo operations.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Field/BareField.h`
- Local answer excerpt: `Answer: The `BareField` class represents a field, managing memory and metadata for multi-dimensional data arrays, and provides methods to initialize, access, and perform operations on the field data. It supports communication mechanisms ...`

#### cls_002 - What is the main responsibility of the Field class compared to BareField?

- Verdict: **Incorrect**
- Codex reference answer: `Field` extends `BareField` with a mesh, boundary-condition container, and mesh-aware integral/average semantics.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/Field/Field.h`
- Local answer excerpt: `Answer: The provided context does not specify the exact implementation details or the full scope of `Field`'s functionality beyond its role as a template class representing numerical fields on a mesh. However, it suggests that the `Field...`

#### cls_003 - What does the FieldLayout class do and what are its main template parameters?

- Verdict: **Partial**
- Codex reference answer: `FieldLayout<Dim>` distributes a global `NDIndex<Dim>` over ranks and stores local domains, neighbors, and communication ranges; its only template parameter is `Dim`.
- Comparison: The local answer got the role right but blurred the distinction between template parameters and constructor/runtime inputs.
- Primary sources: `data/raw/ippl/src/FieldLayout/FieldLayout.h`
- Local answer excerpt: `Answer: The `FieldLayout` class manages the distribution and properties of fields across parallel domains. It describes how an index space (represented by an `NDIndex` object) is distributed among MPI ranks, handles initial partitioning,...`

#### cls_004 - What is the purpose of the ParticleBase class and how is it meant to be used?

- Verdict: **Correct**
- Codex reference answer: `ParticleBase` is the user-extensible base container for particles; derived classes add attributes and register them so layout-driven migration can move them.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Particle/ParticleBase.h`
- Local answer excerpt: `Answer: The `ParticleBase` class serves as a base class for managing and storing particle data in simulations. It provides methods for accessing and updating particle attributes, layout, local counts, and total counts. Users are expected...`

#### cls_005 - What does the ParticleSpatialLayout class do?

- Verdict: **Correct**
- Codex reference answer: `ParticleSpatialLayout` decides which spatial region/rank owns each particle and performs the migration/update workflow after particles move.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Particle/ParticleSpatialLayout.h; data/raw/ippl/src/Particle/ParticleSpatialLayout.hpp`
- Local answer excerpt: `Answer: The `ParticleSpatialLayout` class manages spatial layout configurations for particles within computational regions. It handles region layouts and neighbor communications, providing methods to retrieve region layouts, fill hash st...`

#### cls_006 - What is the responsibility of UniformCartesian?

- Verdict: **Correct**
- Codex reference answer: `UniformCartesian` represents a uniform Cartesian mesh and exposes spacing/origin/volume and vertex-position geometry queries.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Meshes/UniformCartesian.h`
- Local answer excerpt: `Answer: The `UniformCartesian` class template represents a uniform Cartesian mesh and provides methods for initializing, setting/getting mesh spacing, calculating cell volumes, and retrieving vertex positions and spacings. It inherits fr...`

#### cls_007 - What does the Mesh base class define?

- Verdict: **Correct**
- Codex reference answer: `Mesh` is the abstract base interface for meshes: origin, grid size, spacing, vertex positions, and volume queries.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Meshes/Mesh.h`
- Local answer excerpt: `Answer: The retrieved context does not provide any information about a `Mesh` base class. The chunks cover FFTBase, Status, IpplInfo, _Variant_base, and other classes but do not mention a Mesh base class. Evidence: - data/raw/ippl/src/FF...`

#### cls_008 - What is the responsibility of the Communicator class in ippl::mpi?

- Verdict: **Correct**
- Codex reference answer: `ippl::mpi::Communicator` wraps MPI point-to-point, collectives, tag handling, and managed communication buffers.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Communicate/Communicator.h`
- Local answer excerpt: `Answer: The Communicator class in `ippl::mpi` does not appear to be explicitly mentioned or detailed in the provided context. The closest related information is about the `Environment` class in `src/Communicate/Environment.h`, which mana...`

#### cls_009 - What is the role of the Environment class in ippl::mpi?

- Verdict: **Correct**
- Codex reference answer: `ippl::mpi::Environment` manages MPI environment lifetime checks/teardown and provides an abort hook.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Communicate/Environment.h; data/raw/ippl/src/Communicate/Environment.cpp`
- Local answer excerpt: `Answer: The `Environment` class manages MPI environment settings within IPPL, encapsulating initialization, finalization, and error handling functionalities. It takes command-line arguments (`argc`, `argv`) and an optional MPI communicat...`

#### cls_010 - What does the Archive class do in the Communicate module?

- Verdict: **Correct**
- Codex reference answer: `Archive` serializes and deserializes Kokkos views and vector-valued views into raw byte buffers for MPI transfer.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Communicate/Archive.h; data/raw/ippl/src/Communicate/Archive.hpp`
- Local answer excerpt: `Answer: The `Archive` class in the `Communicate` module serves as a central component for data serialization and deserialization within the IPPL codebase. It manages data buffers and provides methods such as `getBuffer`, `getBufferSize`,...`

#### cls_011 - What is the role of the BConds class?

- Verdict: **Correct**
- Codex reference answer: `BConds` is the container of boundary-condition faces and orchestrates neighbor discovery, BC application, and ghost-to-physical assignment.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Field/BConds.h; data/raw/ippl/src/Field/BConds.hpp`
- Local answer excerpt: `Answer: The `BConds` class serves as a container for boundary conditions (BCs) in the field domain within the IPPL scientific C++ codebase. It manages and applies boundary conditions to fields by calling methods like `findBCNeighbors` an...`

#### cls_012 - What is the role of the BaseManager class?

- Verdict: **Correct**
- Codex reference answer: `BaseManager` provides the simulation loop skeleton: `pre_run`, `pre_step`, `advance`, `post_step`, and `run(nt)`.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Manager/BaseManager.h`
- Local answer excerpt: `Answer: The `BaseManager` class in IPPL serves as an abstract manager responsible for orchestrating key simulation steps, including setup, execution, and teardown operations. It defines methods such as `run`, `pre_run`, `pre_step`, `post...`

#### cls_013 - What does the Index class represent and what operations does it support?

- Verdict: **Correct**
- Codex reference answer: `Index` represents a regular strided integer range/slice and supports range-style arithmetic and comparison operations used in domain descriptions.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Index/Index.h; data/raw/ippl/src/Index/Index.hpp`
- Local answer excerpt: `Answer: The retrieved context does not contain any information about an `Index` class or its operations within the IPPL codebase. Evidence: - data/raw/ippl/src/Communicate/Status.h : Status — a communication status handle for non-blockin...`

### Algorithm

#### alg_001 - How does the FFT-based open-boundary Poisson solver compute the electrostatic potential?

- Verdict: **Incorrect**
- Codex reference answer: The FFT open-boundary solver embeds/extends the RHS onto larger domains, FFTs both the density and a precomputed Green's function, multiplies in Fourier space, inverse transforms, and optionally computes gradients/Hessians.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/PoissonSolvers/FFTOpenPoissonSolver.h; data/raw/ippl/src/PoissonSolvers/FFTOpenPoissonSolver.hpp`
- Local answer excerpt: `Answer: The FFT-based open-boundary Poisson solver computes the electrostatic potential by transforming the charge density field from real to Fourier space using FFT. It then multiplies this transformed field with a precomputed Green's f...`

#### alg_002 - How does the FFT-based periodic Poisson solver work in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: The periodic FFT solver FFTs the charge density, divides each Fourier mode by `|k|^2` (with the zero mode handled separately), then inverse transforms; gradients are computed by multiplying by `ik/|k|^2` before the inverse FFT.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/PoissonSolvers/FFTPeriodicPoissonSolver.hpp`
- Local answer excerpt: `Answer: The `FFTPeriodicPoissonSolver` class is designed to solve periodic Poisson equations using Fast Fourier Transform (FFT) techniques within the IPPL scientific C++ codebase. It encapsulates the FFT-based solution process, including...`

#### alg_003 - How does the truncated Green periodic Poisson solver differ from the standard periodic one?

- Verdict: **Incorrect**
- Codex reference answer: The truncated-Green periodic solver replaces the simple `1/|k|^2` kernel with the FFT of a truncated/erf-smoothed Green's function `forceConstant * erf(alpha r) / r`, then follows the same transform-multiply-inverse pattern.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/PoissonSolvers/FFTTruncatedGreenPeriodicPoissonSolver.h; data/raw/ippl/src/PoissonSolvers/FFTTruncatedGreenPeriodicPoissonSolver.hpp`
- Local answer excerpt: `Answer: The truncated Green periodic Poisson solver differs from the standard periodic Poisson solver by including a step to compute and regularize a truncated Green's function. This is done through the `greensFunction` method, which is ...`

#### alg_004 - How does IPPL's CG solver iterate in the PCG.h implementation?

- Verdict: **Partial**
- Codex reference answer: In `PCG.h`, the CG iteration forms residual/direction fields, applies the operator, computes `alpha` and `beta` from inner products, updates the solution/residual/direction, and stops on tolerance or iteration count; the preconditioned variant inserts `M^{-1}` applications on the residual.
- Comparison: The local answer captured the plain CG loop but did not clearly separate it from the preconditioned path.
- Primary sources: `data/raw/ippl/src/LinearSolvers/PCG.h`
- Local answer excerpt: `Answer: IPPL's CG solver iterates through a method that is not explicitly detailed in the provided chunks. However, based on the information given, the `PCG` class inherits from `CG`, and both classes have methods like `initializeFields`...`

#### alg_005 - How is cloud-in-cell interpolation performed in IPPL (both scatter and gather directions)?

- Verdict: **Correct**
- Codex reference answer: CIC computes lower/upper weights per axis, scatters with atomic adds to the `2^Dim` neighboring grid points, and gathers by summing the same weighted stencil back to particles.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Interpolation/CIC.h; data/raw/ippl/src/Interpolation/CIC.hpp`
- Local answer excerpt: `Answer: Cloud-in-Cell (CIC) interpolation in IPPL involves specific functions for both scatter and gather operations. The `scatterToPoint` function in `CIC.hpp` handles the distribution of particle data to grid points using atomic operat...`

#### alg_006 - How does the standard FDTD solver advance the electromagnetic field in time?

- Verdict: **Incorrect**
- Codex reference answer: The standard FDTD solver advances the source-like field with a second-order finite-difference update using the previous and current time levels plus neighboring cells and source terms, then fills halos and reapplies BCs.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/MaxwellSolvers/StandardFDTDSolver.hpp`
- Local answer excerpt: `Answer: The `StandardFDTDSolver` class advances the electromagnetic field in time by overriding the `step()` method from its base class `FDTDSolverBase`. The `step()` method is part of the FDTD simulation loop and is responsible for upda...`

#### alg_007 - How does the LagrangeSpace class evaluate degrees of freedom per element?

- Verdict: **Partial**
- Codex reference answer: `LagrangeSpace` evaluates element DOFs by mapping local element indices to global DOF indices, then evaluates order-1 reference-element shape functions and gradients on those local DOFs.
- Comparison: The local answer focused on the compile-time DOF count and missed most of the actual element-DOF evaluation logic.
- Primary sources: `data/raw/ippl/src/FEM/LagrangeSpace.h; data/raw/ippl/src/FEM/LagrangeSpace.hpp`
- Local answer excerpt: `Answer: The `LagrangeSpace` class uses the `numElementDOFs` parameter to specify the number of degrees of freedom (DOFs) per element. This parameter is passed during the instantiation of the `LagrangeSpace` template class and represents ...`

#### alg_008 - How is Gauss-Jacobi quadrature implemented and used in IPPL FEM?

- Verdict: **Correct**
- Codex reference answer: Gauss-Jacobi quadrature computes nodes/weights by Newton iteration on Jacobi polynomial roots, starting from Chebyshev or LehrFEM-style guesses, and uses the resulting rule on reference elements in FEM.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/FEM/Quadrature/GaussJacobiQuadrature.h; data/raw/ippl/src/FEM/Quadrature/GaussJacobiQuadrature.hpp`
- Local answer excerpt: `Answer: The Gauss-Jacobi quadrature is implemented through the `GaussJacobiQuadrature` class template defined in `GaussJacobiQuadrature.hpp`. This class inherits from a base `Quadrature` class and is responsible for computing quadrature ...`

#### alg_009 - How does the orthogonal recursive bisection decide where to cut the domain?

- Verdict: **Partial**
- Codex reference answer: ORB chooses a cut axis from the domain geometry and then finds a weight-balanced cut/median so recursive splits distribute load more evenly.
- Comparison: The local answer captured the cut-axis choice but did not clearly state that the cut location is chosen from the particle-weight distribution.
- Primary sources: `data/raw/ippl/src/Decomposition/OrthogonalRecursiveBisection.h; data/raw/ippl/src/Decomposition/OrthogonalRecursiveBisection.hpp`
- Local answer excerpt: `Answer: The orthogonal recursive bisection decides where to cut the domain by determining the longest axis of the domain and selecting it for the next cut. This is achieved through the `findCutAxis` method, which finds the axis with the ...`

#### alg_010 - How does inverse transform sampling generate particles from a given distribution in IPPL?

- Verdict: **Correct**
- Codex reference answer: Inverse transform sampling maps uniform random values in CDF space to samples by estimating the inverse and refining it with Newton-Raphson, dimension by dimension.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Random/InverseTransformSampling.h`
- Local answer excerpt: `Answer: The `InverseTransformSampling` class in IPPL generates random samples from a given distribution function by using the inverse of its cumulative distribution function (CDF). The method involves generating uniform random variates a...`

#### alg_011 - How does the FFT class interface with heFFTe to perform complex-to-complex and real-to-complex transforms?

- Verdict: **Incorrect**
- Codex reference answer: The FFT layer builds heFFTe boxes/plans in `setup()`, copies IPPL field data into the required views/subviews, calls heFFTe forward/backward transforms, and copies results back for CC/RC/DST/DCT variants.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/FFT/FFT.hpp`
- Local answer excerpt: `Answer: The FFT class interfaces with HeFFTe to perform complex-to-complex and real-to-complex transforms through specific methods like `transform`. The `FFT<CCTransform, ComplexField>::transform` method performs an in-place FFT on a com...`

#### alg_012 - How does IPPL's preconditioned CG use the preconditioner defined in Preconditioner.h?

- Verdict: **Partial**
- Codex reference answer: PCG applies a chosen preconditioner from `Preconditioner.h` to the residual, uses the preconditioned residual in its inner products and direction updates, and iterates until tolerance/max iterations.
- Comparison: The local answer recognized the preconditioner family but stayed generic instead of tying it to the actual PCG update flow.
- Primary sources: `data/raw/ippl/src/LinearSolvers/Preconditioner.h; data/raw/ippl/src/LinearSolvers/PCG.h`
- Local answer excerpt: `Answer: IPPL's preconditioned Conjugate Gradient (PCG) solver uses the preconditioners defined in `Preconditioner.h` through the `setPreconditioner` method. This method sets up different preconditioners like Jacobi, Polynomial Newton, Po...`

### Data Flow

#### flow_001 - How does charge density flow from particles to the grid in a typical PIC step in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: In the PIC workflow, particle charges and positions are deposited onto the grid with CIC (`scatter`) or FEM assembly (`assemble_rhs_from_particles`), accumulated into `rho`, and then normalized/background-shifted in the manager before solving.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/alpine/AlpineManager.h; data/raw/ippl/src/Interpolation/CIC.hpp`
- Local answer excerpt: `Answer: In IPPL, charge density flows from particles to the grid through a process involving interpolation and scattering operations. The `gather` method in the `ParticleAttrib` class is responsible for transferring charge density values...`

#### flow_002 - How does the electric field flow from the grid back to particles after a Poisson solve?

- Verdict: **Incorrect**
- Codex reference answer: After the field solve, the manager gathers the electric field back to particles with CIC `gather(...)` or FEM `interpolate_grad_to_diracs(...)`, storing particle-local `E` values for the push step.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/alpine/AlpineManager.h`
- Local answer excerpt: `Answer: After solving the Poisson equation to compute the electrostatic potential on the grid, the electric field is computed as the gradient of this potential. This electric field is then transferred back to the particles using interpol...`

#### flow_003 - How are halo cells exchanged between neighboring MPI ranks for a BareField?

- Verdict: **Partial**
- Codex reference answer: Halo exchange uses `FieldLayout` neighbor/range metadata to pack field subviews, send/receive them with MPI, unpack into ghost or physical regions, and handle serial-periodic dimensions locally.
- Comparison: The local answer contains real signal, but it misses an important scope boundary, file, or algorithm detail.
- Primary sources: `data/raw/ippl/src/Field/HaloCells.hpp; data/raw/ippl/src/Field/BareField.hpp`
- Local answer excerpt: `Answer: Halo cells are exchanged between neighboring MPI ranks using the `accumulateHalo` method of the `BareField` class. This method checks if there is more than one process involved (`layout_m->comm.size() > 1`) and, if so, calls `hal...`

#### flow_004 - How are particles migrated between MPI ranks by ParticleSpatialLayout?

- Verdict: **Partial**
- Codex reference answer: `ParticleSpatialLayout::update()` applies particle BCs, locates destination ranks, advertises receive counts with RMA, sends all registered attributes, destroys invalid local particles, and receives the incoming ones.
- Comparison: The local answer found the owning routine but skipped most of the send/destroy/receive sequence.
- Primary sources: `data/raw/ippl/src/Particle/ParticleSpatialLayout.hpp`
- Local answer excerpt: `Answer: Particles are migrated between MPI ranks by `ParticleSpatialLayout` through a combination of methods that manage spatial layouts and communications. The `update` method triggers particle redistribution based on their new position...`

#### flow_005 - How does FieldLayout decide which index ranges live on which rank?

- Verdict: **Partial**
- Codex reference answer: `FieldLayout` uses the partitioner and the requested parallel/serial decomposition flags to assign each rank a local `NDIndex`, plus neighbor and communication range tables.
- Comparison: The local answer contains real signal, but it misses an important scope boundary, file, or algorithm detail.
- Primary sources: `data/raw/ippl/src/FieldLayout/FieldLayout.h; data/raw/ippl/src/Partition/Partitioner.h`
- Local answer excerpt: `Answer: FieldLayout decides which index ranges live on which rank through a combination of methods that calculate domain boundaries and add neighbor information. The `findNeighbors` method determines neighboring ranks based on the field ...`

#### flow_006 - How is a ParameterList used to configure the FFT and solver classes?

- Verdict: **Incorrect**
- Codex reference answer: `ParameterList` is merged into FFT and solver objects, then consumed by `setup()/initialize()/solve()` for communication mode, pencil/reorder flags, transform direction, solver type, tolerances, preconditioner settings, and output type.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/FFT/FFT.hpp; data/raw/ippl/src/PoissonSolvers/FFTPeriodicPoissonSolver.h; data/raw/ippl/src/PoissonSolvers/PoissonCG.h`
- Local answer excerpt: `Answer: In the IPPL codebase, `ParameterList` is used to manage and pass configuration parameters for FFT operations. Specifically, a `ParameterList` is passed as an argument during the construction of FFT objects (e.g., `FFT<RCTransform...`

#### flow_007 - How does data flow through the BaseManager's pre_step / advance / post_step hooks during a simulation?

- Verdict: **Correct**
- Codex reference answer: `BaseManager::run()` executes `pre_step()`, `advance()`, and `post_step()` for each timestep; derived managers use those hooks for deposit/solve/gather, time updates, and output.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Manager/BaseManager.h; data/raw/ippl/alpine/AlpineManager.h`
- Local answer excerpt: `Answer: The `BaseManager` class defines the `pre_step`, `advance`, and `post_step` methods as virtual functions intended to be overridden by derived classes. These methods are part of the simulation lifecycle management, where `pre_step`...`

#### flow_008 - How does the FEM solver move data between fields and FEMVector representations?

- Verdict: **Incorrect**
- Codex reference answer: FEM solvers move data by assembling field data into FEM load/stiffness representations (`evaluateLoadVector`, `evaluateAx`, `FEMVector`) and then interpolating the solved field quantities back where needed.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/FEM/LagrangeSpace.h; data/raw/ippl/src/FEM/LagrangeSpace.hpp; data/raw/ippl/src/FEM/FEMVector.h`
- Local answer excerpt: `Answer: The FEM solver uses `FEMVector` to manage vector operations and halo exchanges. Specifically, methods like `accumulateHalo`, `fillHalo`, and `deepCopy` are used for data movement between fields and `FEMVector` representations. `a...`

#### flow_009 - How does OrthogonalRecursiveBisection redistribute particles after rebalancing?

- Verdict: **Partial**
- Codex reference answer: After ORB recomputes the decomposition, particle ownership changes are realized by updating the layout/regions and then migrating particles with the usual particle update path.
- Comparison: The local answer contains real signal, but it misses an important scope boundary, file, or algorithm detail.
- Primary sources: `data/raw/ippl/src/Decomposition/OrthogonalRecursiveBisection.hpp; data/raw/ippl/src/Particle/ParticleSpatialLayout.hpp`
- Local answer excerpt: `Answer: After rebalancing, `OrthogonalRecursiveBisection` redistributes particles by performing a binary repartitioning operation. This involves scattering particles (`scatterR`), recursively bisecting domains based on load balancing cri...`

### Api Usage

#### api_001 - How do I create a 3D Field of doubles in IPPL?

- Verdict: **Partial**
- Codex reference answer: A typical 3D field is `Field<double, 3, UniformCartesian<double, 3>, Cell>` constructed from a `UniformCartesian` mesh and a `FieldLayout<3>`.
- Comparison: The local answer had the right shape but stayed abstract instead of grounding it in the concrete mesh/layout construction IPPL expects.
- Primary sources: `data/raw/ippl/src/Field/Field.h; data/raw/ippl/src/Meshes/UniformCartesian.h; data/raw/ippl/doc/examples/BasicsFields.hpp`
- Local answer excerpt: `Answer: To create a 3D field of doubles in IPPL, you would use the `Field` class template with appropriate parameters. Based on the provided context, the `Field` class is defined in `Field.h` and `Field.hpp`. The type for double precisio...`

#### api_002 - How do I construct a UniformCartesian mesh with custom spacing and origin?

- Verdict: **Partial**
- Codex reference answer: Construct the mesh as `UniformCartesian<double, Dim> mesh(domain, hx, origin);` where `hx` is the spacing vector and `origin` is the mesh origin.
- Comparison: The local answer contains real signal, but it misses an important scope boundary, file, or algorithm detail.
- Primary sources: `data/raw/ippl/src/Meshes/UniformCartesian.h; data/raw/ippl/doc/examples/BasicsMesh.hpp`
- Local answer excerpt: `Answer: To construct a `UniformCartesian` mesh with custom spacing and origin, use its constructor defined in `UniformCartesian.hpp`. The constructor takes parameters for dimensions (`NDIndex<Dim>& ndi`), mesh spacing (`vector_type& hx`)...`

#### api_003 - How do I attach a boundary condition (e.g. periodic) to a Field?

- Verdict: **Partial**
- Codex reference answer: Create a `BConds<FieldT, Dim>`, assign per-face BC objects such as `PeriodicFace<FieldT>`, then call `field.setFieldBC(bc)`.
- Comparison: The local answer contains real signal, but it misses an important scope boundary, file, or algorithm detail.
- Primary sources: `data/raw/ippl/src/Field/Field.h; data/raw/ippl/src/Field/BConds.h; data/raw/ippl/src/Field/BcTypes.h`
- Local answer excerpt: `Answer: To attach a periodic boundary condition to a `Field`, you can use the `setPeriodicBoundaryConditions` method provided by classes like `FDTDSolverBase`. This method sets up periodic boundary conditions for fields by creating and a...`

#### api_004 - How do I define a custom particle class that adds mass and velocity attributes on top of ParticleBase?

- Verdict: **Correct**
- Codex reference answer: Define a class derived from `ParticleBase<ParticleSpatialLayout<...>>`, add `mass` and `velocity` attributes as members, and register them with `addAttribute()` in the constructor.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Particle/ParticleBase.h`
- Local answer excerpt: `Answer: To define a custom particle class with mass and velocity attributes on top of `ParticleBase`, you need to derive from `ParticleBase` and add `ParticleAttribute` instances for mass and velocity. You should also use the constructor...`

#### api_005 - How do I call ippl::initialize and ippl::finalize in a main program?

- Verdict: **Incorrect**
- Codex reference answer: Call the free namespace functions `ippl::initialize(argc, argv);` and `ippl::finalize();` from `main`, as shown in the docs/examples.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/Ippl.h; data/raw/ippl/doc/examples/HelloWorld.hpp`
- Local answer error: `NameError: name 'exact_symbols' is not defined`

#### api_006 - How do I set up and run a forward FFT on an IPPL Field?

- Verdict: **Partial**
- Codex reference answer: Set up the relevant layouts/fields/parameters, build an `FFT<CCTransform, ...>` or `FFT<RCTransform, ...>` object, and call `transform(FORWARD, ...)` on the field(s).
- Comparison: The local answer contains real signal, but it misses an important scope boundary, file, or algorithm detail.
- Primary sources: `data/raw/ippl/src/FFT/FFT.h; data/raw/ippl/src/FFT/FFT.hpp; data/raw/ippl/doc/examples/BasicsFFT.hpp`
- Local answer error: `NameError: name 'exact_symbols' is not defined`

#### api_007 - How do I construct an FFTPeriodicPoissonSolver and solve for the potential?

- Verdict: **Partial**
- Codex reference answer: Construct `FFTPeriodicPoissonSolver(lhs, rhs)` (or default construct then set fields/params), ensure the RHS is attached, and call `solve()` to write the potential/gradient outputs.
- Comparison: The local answer contains real signal, but it misses an important scope boundary, file, or algorithm detail.
- Primary sources: `data/raw/ippl/src/PoissonSolvers/FFTPeriodicPoissonSolver.h; data/raw/ippl/src/PoissonSolvers/FFTPeriodicPoissonSolver.hpp`
- Local answer excerpt: `Answer: To construct an `FFTPeriodicPoissonSolver` and solve for the potential, follow these steps: 1. Create instances of `FieldLHS` and `FieldRHS` representing the left-hand side (solution field) and right-hand side (source term) of th...`

#### api_008 - How do I invoke the conjugate gradient Poisson solver on a Field?

- Verdict: **Incorrect**
- Codex reference answer: Use `PoissonCG<FieldT>` (or the Alpine `FieldSolver` wrapper around it), set its fields/parameters, and call `solve()` so the internal CG/PCG object iterates on the field.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/PoissonSolvers/PoissonCG.h`
- Local answer excerpt: `Answer: To invoke the Conjugate Gradient Poisson solver on a Field, you need to create an instance of `PoissonCG`, set the left-hand side field (the solution field), and call the `solve` method. Here's how: 1. Create an instance of `Pois...`

#### api_009 - How do I sample particles from a normal distribution using IPPL Random utilities?

- Verdict: **Partial**
- Codex reference answer: For Gaussian draws, IPPL exposes both `randn` convenience generation and the more general `InverseTransformSampling` + `NormalDistribution` path.
- Comparison: The local answer contains real signal, but it misses an important scope boundary, file, or algorithm detail.
- Primary sources: `data/raw/ippl/src/Random/Randn.h; data/raw/ippl/src/Random/NormalDistribution.h; data/raw/ippl/src/Random/InverseTransformSampling.h`
- Local answer excerpt: `Answer: The `InverseTransformSampling` class can be used to generate samples from a specified distribution, including a normal distribution. This class utilizes inverse transform sampling and supports both domain decomposition and non-do...`

#### api_010 - How do I register particle attributes with ParticleBase so that they are communicated on migration?

- Verdict: **Correct**
- Codex reference answer: Register each particle attribute with `addAttribute(...)`; migration then serializes and transfers all registered attributes automatically.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Particle/ParticleBase.h; data/raw/ippl/src/Particle/ParticleSpatialLayout.hpp`
- Local answer excerpt: `Answer: To register particle attributes with `ParticleBase` so that they are communicated on migration, you must define a derived class from `ParticleBase` and use the `addAttribute` method to add each attribute. This ensures that the at...`

#### api_011 - How do I access the MPI rank and size through the IPPL Communicator?

- Verdict: **Correct**
- Codex reference answer: Access rank and size with `ippl::Comm->rank()` and `ippl::Comm->size()` (or the same methods on a `Communicator` object).
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Communicate/Communicator.h`
- Local answer excerpt: `Answer: To access the MPI rank and size through the IPPL Communicator, you can use the methods `rank` and `size` respectively. The `rank` method returns the rank of the current process in the MPI communicator, while the `size` method ret...`

#### api_012 - How do I use IpplTimings to measure a region of code?

- Verdict: **Correct**
- Codex reference answer: Get a timer handle with `IpplTimings::getTimer("name")`, surround the code with `startTimer()` / `stopTimer()`, and print with `IpplTimings::print()`.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Utility/IpplTimings.h`
- Local answer excerpt: `Answer: To measure a region of code using `IpplTimings`, follow these steps: 1. Create a timer by calling `IpplTimings::getTimer("timer name")`. This will return a reference to an existing timer or create a new one if it does not exist. ...`

### Parallelism And Kokkos

#### par_001 - How does IPPL achieve performance portability across CPUs and GPUs?

- Verdict: **Correct**
- Codex reference answer: IPPL gets performance portability by combining Kokkos execution/memory abstractions with MPI and heFFTe, so the same code paths can target CPUs and GPUs.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/README.md; data/raw/ippl/src/Utility/ParallelDispatch.h`
- Local answer excerpt: `Answer: IPPL achieves performance portability across CPUs and GPUs by leveraging Kokkos for parallelism, which provides a programming model that abstracts hardware specifics. The `ReflectiveBC::operator()` method is an example of how Kok...`

#### par_002 - Why does IPPL use Kokkos::View for field storage?

- Verdict: **Partial**
- Codex reference answer: IPPL uses `Kokkos::View` because fields need execution-space-aware storage, subviews, mirrors, and portable kernels across host/device memory spaces.
- Comparison: The local answer did not really explain the motivation; it mostly restated that Views exist.
- Primary sources: `data/raw/ippl/src/Field/BareField.h; data/raw/ippl/src/Communicate/Archive.h`
- Local answer excerpt: `Answer: The retrieved context does not provide a specific explanation for why IPPL uses `Kokkos::View` for field storage. The chunks cover various aspects of IPPL's functionality and structure but do not explicitly state the reason for c...`

#### par_003 - How does IPPL parallelize loops over field indices using Kokkos RangePolicy?

- Verdict: **Partial**
- Codex reference answer: Loops are parallelized through `ippl::getRangePolicy` / `createRangePolicy` and the `ippl::parallel_for` wrapper over Kokkos `RangePolicy`/`MDRangePolicy`.
- Comparison: The local answer contains real signal, but it misses an important scope boundary, file, or algorithm detail.
- Primary sources: `data/raw/ippl/src/Utility/ParallelDispatch.h`
- Local answer excerpt: `Answer: IPPL uses `RangePolicy` from the `ParallelDispatch.h` file to define policies for parallel execution of loops over field indices. Specifically, `RangePolicy` is a struct that defines multidimensional range policies using Kokkos's...`

#### par_004 - How does IPPL support mixed precision (float vs double) for fields?

- Verdict: **Incorrect**
- Codex reference answer: Precision is chosen by the field value type (`Field<float,...>` vs `Field<double,...>`), and the codebase also contains mixed-precision examples where fields/particles deliberately use different precisions.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/Field/Field.h; data/raw/ippl/alpine/ExamplesWithoutPicManager/LandauDampingMixedPrecision.cpp`
- Local answer excerpt: `Answer: IPPL supports mixed precision through its unit tests, which include configurations that test components using single (`float`) and double (`double`) precision. This is evident from the `UNIT_TESTS.md` documentation, which lists d...`

#### par_005 - How does IPPL handle multiple execution spaces like OpenMP and CUDA in the same build?

- Verdict: **Partial**
- Codex reference answer: Multiple execution spaces are enabled at build time through `IPPL_PLATFORMS` and Kokkos/HeFFTe backend flags; IPPL also has container helpers for multi-space data.
- Comparison: The local answer contains real signal, but it misses an important scope boundary, file, or algorithm detail.
- Primary sources: `data/raw/ippl/INSTALLATION.md; data/raw/ippl/src/Utility/TypeUtils.h`
- Local answer excerpt: `Answer: IPPL handles multiple execution spaces like OpenMP and CUDA through the use of Kokkos, which abstracts away the specifics of different backends. The `MultispaceContainer` class in `TypeUtils.h` manages elements across different m...`

#### par_006 - What is the purpose of ParallelDispatch.h and what helpers does it expose?

- Verdict: **Correct**
- Codex reference answer: `ParallelDispatch.h` wraps Kokkos policies and functors, exposing `RangePolicy`, `getRangePolicy`, `createRangePolicy`, `parallel_for`, and `parallel_reduce`.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Utility/ParallelDispatch.h`
- Local answer excerpt: `Answer: The `ParallelDispatch.h` file defines abstractions and utilities for parallel execution in the IPPL library, specifically tailored to integrate with Kokkos for handling parallel loops and reductions. It exposes several helpers in...`

#### par_007 - How does the Archive class serialize/deserialize Kokkos views for MPI transfer?

- Verdict: **Correct**
- Codex reference answer: `Archive` serializes Kokkos views into one-dimensional byte buffers with Kokkos kernels and `memcpy`, then deserializes them back into views on receive.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Communicate/Archive.h; data/raw/ippl/src/Communicate/Archive.hpp`
- Local answer excerpt: `Answer: The `Archive` class serializes and deserializes Kokkos views by wrapping one-dimensional Kokkos views of type `char`. Serialization involves copying data from a Kokkos view into this char-based buffer using `Kokkos::deep_copy`, w...`

#### par_008 - How are MPI tags managed in IPPL to avoid collisions across subsystems?

- Verdict: **Incorrect**
- Codex reference answer: MPI tags are managed with fixed base tags in `Tags.h` and the cyclic tag allocator in `TagMaker`, which `Communicator` inherits.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/Communicate/Tags.h; data/raw/ippl/src/Communicate/TagMaker.h; data/raw/ippl/src/Communicate/Communicator.h`
- Local answer excerpt: `Answer: IPPL uses a `TagMaker` class in the `Communicate` module to manage MPI tags and avoid collisions across subsystems. The `TagMaker` class provides methods like `next_tag`, `create_base_tag`, and `current_tag` to generate, create, ...`

#### par_009 - What does Kokkos::fence do, and when does IPPL call the wrapper ippl::fence?

- Verdict: **Partial**
- Codex reference answer: `Kokkos::fence()` waits for outstanding kernels; IPPL exposes `ippl::fence()` as a runtime wrapper in `Ippl.cpp` and also fences internally after many kernel/data-movement steps.
- Comparison: The local answer contains real signal, but it misses an important scope boundary, file, or algorithm detail.
- Primary sources: `data/raw/ippl/src/Ippl.cpp; data/raw/ippl/src/Field/HaloCells.hpp; data/raw/ippl/src/Communicate/Archive.hpp`
- Local answer excerpt: `Answer: Kokkos::fence is used to enforce a synchronization barrier, ensuring that all preceding operations are completed before any subsequent operations proceed. In IPPL, ippl::fence acts as a wrapper around Kokkos::fence and is called ...`

### Boundary And Halo

#### bc_001 - What boundary condition types are provided in BcTypes.h?

- Verdict: **Correct**
- Codex reference answer: `BcTypes.h` provides periodic, constant, zero, extrapolating, and no-BC face classes.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/Field/BcTypes.h`
- Local answer excerpt: `Answer: The `BcTypes.h` file defines several derived classes representing different boundary condition types: `ConstantFace`, `ExtrapolateFace`, `NoBcFace`, `PeriodicFace`, and `ZeroFace`. Evidence: - data/raw/ippl/src/Field/BcTypes.h : ...`

#### bc_002 - How does a periodic boundary condition differ from a Neumann boundary condition in IPPL Fields?

- Verdict: **Partial**
- Codex reference answer: Periodic BCs wrap values from the opposite side of the domain; there is no explicit `NeumannFace` class in this codebase, so the closest non-periodic behavior is constant/extrapolating face treatment.
- Comparison: The local answer's abstention was understandable because the question names a BC type that is not literally implemented, but it still missed the useful source-backed clarification.
- Primary sources: `data/raw/ippl/src/Field/BcTypes.h; data/raw/ippl/src/Field/BcTypes.hpp`
- Local answer excerpt: `Answer: The provided retrieved context does not explicitly describe the differences between periodic and Neumann boundary conditions in IPPL fields. The context only mentions that `setPeriodicBoundaryConditions` is a method used to set u...`

#### bc_003 - How are ghost cells populated during a halo exchange?

- Verdict: **Incorrect**
- Codex reference answer: Ghost cells are populated mainly by `fillHalo()` / `PeriodicFace::apply()`: source slabs are packed, exchanged, and unpacked into ghost regions; `accumulateHalo_noghost()` is a different operation.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/Field/HaloCells.hpp; data/raw/ippl/src/Field/BcTypes.hpp`
- Local answer excerpt: `Answer: Ghost cells are populated during a halo exchange by calling `HaloCells<T, Dim, ViewArgs...>::accumulateHalo_noghost`. This method uses `exchangeBoundaries` with an operation (`lhs_plus_assign`) to transfer data from halo cells to...`

#### bc_004 - How are physical-cell values copied into ghost cells for periodic boundary conditions?

- Verdict: **Incorrect**
- Codex reference answer: Periodic ghost cells are filled from opposite-side physical cells in `applyPeriodicSerialDim()` and the multi-rank `PeriodicFace::apply()` path.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/Field/HaloCells.hpp; data/raw/ippl/src/Field/BcTypes.hpp`
- Local answer excerpt: `Answer: The `assignGhostToPhysical` method within the `PeriodicFace<Field>` class is responsible for copying physical-cell values into ghost cells for periodic boundary conditions. This method calculates appropriate shifts for coordinate...`

#### bc_005 - How does the absorbing boundary condition in the MaxwellSolvers module damp outgoing waves?

- Verdict: **Correct**
- Codex reference answer: The absorbing Maxwell BC uses second-order Mur-style formulas with precomputed weights and previous/current/next boundary values plus tangential neighbors to damp outgoing waves.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/MaxwellSolvers/AbsorbingBC.h`
- Local answer excerpt: `Answer: The `second_order_mur_boundary_conditions` struct applies second-order Mur absorbing boundary conditions to all boundaries of a 3D computational domain. It uses precomputed weights based on mesh spacing and time step to adjust fi...`

### Numerical Meaning

#### num_001 - What does the FFT-based Poisson solver physically compute in terms of Coulomb's law?

- Verdict: **Correct**
- Codex reference answer: The FFT Poisson solvers compute electrostatic potential (and optionally field/gradient) from charge density, i.e. the discretized Coulomb potential corresponding to `-Δφ = ρ`.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/src/PoissonSolvers/FFTOpenPoissonSolver.h; data/raw/ippl/src/PoissonSolvers/FFTPeriodicPoissonSolver.h`
- Local answer excerpt: `Answer: The retrieved context does not provide specific information about an FFT-based Poisson solver or its relationship to Coulomb's law. The chunks cover various solvers and their methods but do not mention any FFT-based solver that e...`

#### num_002 - What is the physical meaning of the fields advanced by the FDTD solver?

- Verdict: **Incorrect**
- Codex reference answer: The Maxwell solvers evolve electromagnetic field data: electric and magnetic fields (`E`, `B`) driven by a source/four-current field.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/MaxwellSolvers/Maxwell.h; data/raw/ippl/src/MaxwellSolvers/FDTDSolverBase.h`
- Local answer excerpt: `Answer: The FDTD solver advances the electric (`E`) and magnetic (`B`) fields over time. These fields represent electromagnetic wave propagation according to Maxwell's equations. Evidence: - data/raw/ippl/src/MaxwellSolvers/FDTDSolverBas...`

#### num_007 - What are the numerical tradeoffs between the FFT and CG Poisson solvers in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: FFT Poisson is fast and direct on structured uniform grids with compatible BCs but less flexible; CG/PCG is iterative and may be slower/convergence-limited, but it is more flexible for alternative discretizations, BCs, and preconditioning.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/src/PoissonSolvers/FFTPeriodicPoissonSolver.h; data/raw/ippl/src/PoissonSolvers/PoissonCG.h; data/raw/ippl/src/PoissonSolvers/FEMPoissonSolver.h`
- Local answer excerpt: `Answer: The FFTPeriodicPoissonSolver in IPPL leverages FFT algorithms for solving periodic Poisson equations, which can be highly efficient due to its parallel nature and low computational complexity. It uses transformations between spat...`

### Build And Install

#### build_001 - Which third-party libraries does IPPL depend on, and what are they used for?

- Verdict: **Incorrect**
- Codex reference answer: Core third-party dependencies are MPI for distributed communication, Kokkos for performance portability, heFFTe for FFT backends/plans, FFTW/CuFFT as optional FFT backends, and GoogleTest for tests.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/README.md; data/raw/ippl/INSTALLATION.md; data/raw/ippl/unit_tests/CMakeLists.txt`
- Local answer excerpt: `Answer: IPPL depends on Kokkos for portable parallelism across CPU/GPU. Specifically, it includes `Kokkos_Core.hpp`. There is no mention of heFFTe or MPI in the retrieved context. Evidence: - src/Ippl.cpp : Ippl — contains several utilit...`

#### build_002 - What C++ standard does IPPL require, and why?

- Verdict: **Incorrect**
- Codex reference answer: IPPL requires C++20, as stated in the README badge and the installation examples/configuration flags.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/README.md; data/raw/ippl/INSTALLATION.md`
- Local answer excerpt: `Answer: The retrieved context does not specify which C++ standard IPPL requires or provide any reason for that requirement. Evidence: - data/raw/ippl/src/Ippl.cpp : abort — The entity is a function named `abort` defined in the file `Ippl...`

#### build_003 - How is IPPL configured with CMake to enable a GPU build?

- Verdict: **Incorrect**
- Codex reference answer: GPU builds are enabled through CMake options like `IPPL_PLATFORMS=CUDA` or `IPPL_PLATFORMS="HIP;OPENMP"` plus matching Kokkos/architecture/backend flags (`Kokkos_ARCH_*`, `CMAKE_CUDA_ARCHITECTURES`, `Kokkos_ENABLE_HIP`, `Heffte_ENABLE_ROCM`, etc.).
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/INSTALLATION.md`
- Local answer excerpt: `Answer: The provided retrieved context does not contain any specific information about configuring IPPL for a GPU build. The documentation and code excerpts focus on general setup, including installation, testing, and compilation options...`

#### build_004 - What options does INSTALLATION.md describe for configuring Kokkos for IPPL?

- Verdict: **Partial**
- Codex reference answer: `INSTALLATION.md` describes Kokkos version selection plus backend/architecture options used with IPPL builds, including CUDA and HIP/OpenMP examples and `IPPL_PLATFORMS` combinations.
- Comparison: The local answer contains real signal, but it misses an important scope boundary, file, or algorithm detail.
- Primary sources: `data/raw/ippl/INSTALLATION.md`
- Local answer excerpt: `Answer: INSTALLATION.md describes several CMake options related to Kokkos configuration for IPPL. The relevant option is `IPPL_PLATFORMS`, which can be set to one of `SERIAL, OPENMP, CUDA, "OPENMP;CUDA"`, with a default value of `SERIAL`...`

#### build_005 - How do I install IPPL on the EULER cluster according to the documentation?

- Verdict: **Correct**
- Codex reference answer: The EULER install guide says to connect with VPN/SSH, switch to the new software stack, purge modules, load GCC/CMake/CUDA/OpenMPI, clone the repo, configure a build, compile, and test on an interactive node.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/doc/extras/IPPLonEULER.md`
- Local answer excerpt: `Answer: To install IPPL on the EULER cluster, follow these steps: 1. Connect to the cluster using SSH and ensure you are connected via the ETH-VPN. 2. Load the new software stack, clean your environment, and load required modules: ``` en...`

### Testing And Workflow

#### test_002 - What naming conventions does WORKFLOW.md require for variables, constants, and member variables?

- Verdict: **Correct**
- Codex reference answer: `WORKFLOW.md` requires camelCase variables, CAPITAL_CASE compile-time constants, and member names suffixed with `_m`.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/WORKFLOW.md`
- Local answer excerpt: `Answer: The naming conventions specified in `WORKFLOW.md` are as follows: - Variables should use camel case. - Compile-time constants should be in capital letters. - Member variables should end with an underscore followed by 'm'. Evidenc...`

#### test_003 - When should code use Kokkos::sqrt versus std::sqrt according to WORKFLOW.md?

- Verdict: **Correct**
- Codex reference answer: Use `std::sqrt` in host-only code, and `Kokkos::sqrt` in device-capable code such as `KOKKOS_INLINE_FUNCTION` kernels.
- Comparison: The local answer matches the source-backed reading closely enough to be trusted.
- Primary sources: `data/raw/ippl/WORKFLOW.md`
- Local answer excerpt: `Answer: According to WORKFLOW.md, any instance of a mathematical function in host-only code should use symbols from the standard library, e.g., `std::sqrt`. Any instances occurring in device-code or code that might be run on a device (su...`

#### test_004 - How does IPPL profile MPI calls using mpiP?

- Verdict: **Incorrect**
- Codex reference answer: IPPL profiles MPI calls with mpiP by preloading `libmpiP.so`, optionally setting `MPIP` flags, then parsing the produced `.mpiP` output with the bundled `scripts/mpiP.py`.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/README.md; data/raw/ippl/scripts/mpiP.py`
- Local answer excerpt: `Answer: The provided context does not mention IPPL profiling MPI calls with mpiP. The chunks cover initialization, configuration, synchronization, and error handling functions in `Ippl.cpp`, declarations of utility classes and inline poi...`

#### test_005 - What does the SLURM job template for Gwendolen in the README look like?

- Verdict: **Incorrect**
- Codex reference answer: The README does include a Gwendolen SLURM template showing the `gmerlin6` cluster, `gwendolen` partition, GPU count, and `srun ./<your_executable> <args> --kokkos-map-device-id-by=mpi_rank`.
- Comparison: The local answer either missed the relevant source-backed answer or contradicted the code/docs materially.
- Primary sources: `data/raw/ippl/README.md`
- Local answer excerpt: `Answer: The provided context does not contain a specific SLURM job template for Gwendolen. The README.md mentions example job scripts for running on the local PSI computing cluster but does not provide a detailed template for Gwendolen. ...`

## Conclusion

This V2 run is a cleaner measurement than the first round because the questions are now restricted to what should be answerable from `src/` and repository documentation. The local system is clearly useful on structural questions, but it still loses ground when the answer depends on retrieving the right implementation file or synthesizing across a few related source files.

The best next step is still retrieval quality: make it more likely to surface the exact solver, particle, interpolation, or documentation files that match the query intent, then keep the final prompt focused instead of letting one nearby file dominate the context.
