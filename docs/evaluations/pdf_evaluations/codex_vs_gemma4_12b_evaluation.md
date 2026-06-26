# Codex GPT-5.4 Reference vs Gemma4 12B Evaluation

Generated: 2026-06-19 12:56:08 UTC

## Goal

This report evaluates the saved Gemma4 12B RAG answer run in `docs/evaluations/answers/eval_v2_gemma4-12B.json` against the Codex GPT-5.4 reference answers stored in `docs/evaluations/eval_answers_v2.json`. The format follows the older `codex_vs_local_llm_evaluation_20260423` report style, but the reference side here is the curated Codex V2 answer file rather than a new source-reading pass.

## Test Environment

### Codex Reference Side

- Model: `GPT-5.4` (Codex reference answers)
- Reference file: `docs/evaluations/eval_answers_v2.json`
- Question set: `docs/evaluations/eval_questions_v2.json`
- Evaluation basis: semantic comparison against the Codex reference answer for each question

### Local LLM Side

- Host: `merlin-g-100.psi.ch`
- Job / partition: `353458` on `gwendolen`
- Answer model: `gemma4:12b`
- Chunk explanation model: `qwen2.5-coder:32b`
- File / module / call-chain models: `qwen2.5-coder:32b-instruct-q4_K_M`, `qwen2.5-coder:32b-instruct-q4_K_M`, `qwen2.5-coder:32b-instruct-q4_K_M`
- Parser: `tree_sitter`
- Question count: `100`
- Answer prompt mode: `retrieval_answer_v2`
- Mean answer latency: `38.72s`
- Median answer latency: `34.97s`

### Retrieval Configuration Used by the Saved Run

- Candidate k: `20`
- Supplementary k: `3`
- Supplementary candidate k: `10`
- Vector store chunk count: `4441`
- Manifest embedding backend/model: `ollama` / `nomic-embed-text`

## Important Caveat

The per-question verdicts are a structured comparison against the Codex reference answers, not an independent re-reading of every IPPL source file. A question is marked Correct when the local answer captures the central facts of the Codex reference; Partial when it contains relevant signal but misses important scope or implementation detail; and Incorrect when it abstains, points to the wrong subsystem, or omits the core reference answer.

Because the reference answers are intentionally concise, the grading emphasizes the main technical nouns, implementation locations, and algorithmic steps rather than exact wording. Ambiguous cases were treated conservatively as Partial rather than Correct.

## Overall Result

| Metric | Value |
|---|---:|
| Questions | 100 |
| Correct | 56 |
| Partial | 23 |
| Incorrect | 21 |
| Average score (`Correct=1`, `Partial=0.5`, `Incorrect=0`) | 0.675 |
| Answers with leaked self-correction/planning text | 0 |

## Main Findings

- Strongest areas: Api Usage, Definition Location. These are mostly questions where the retrieved answer can be anchored to one well-described class, header, implementation file, or usage pattern.
- Weakest areas: Build And Install, Testing And Workflow. These questions require cross-file synthesis, precise implementation-location recovery, or careful numerical interpretation.
- Gemma4 12B is relatively slow in this run, with mean latency `38.72s`, and its answers tend to be detailed but not always tightly scoped to the Codex reference.
- The remaining misses are mostly retrieval/grounding failures: plausible evidence from adjacent IPPL components can still displace the exact implementation or numerical detail asked for.
- Compared with the Qwen-family reports, this run should be read as another local-model baseline under the same RAG artifacts and rubric, not as a different retrieval setup.

## Category Breakdown

| Category | Questions | Correct | Partial | Incorrect | Avg score |
|---|---:|---:|---:|---:|---:|
| File Purpose | 13 | 8 | 3 | 2 | 0.731 |
| Definition Location | 15 | 11 | 0 | 4 | 0.733 |
| Class Responsibility | 13 | 9 | 1 | 3 | 0.731 |
| Algorithm | 12 | 4 | 7 | 1 | 0.625 |
| Data Flow | 9 | 5 | 2 | 2 | 0.667 |
| Api Usage | 12 | 10 | 2 | 0 | 0.917 |
| Parallelism And Kokkos | 9 | 3 | 4 | 2 | 0.556 |
| Boundary And Halo | 5 | 2 | 3 | 0 | 0.700 |
| Numerical Meaning | 3 | 2 | 0 | 1 | 0.667 |
| Build And Install | 5 | 0 | 1 | 4 | 0.100 |
| Testing And Workflow | 4 | 2 | 0 | 2 | 0.500 |

## Detailed Per-Question Evaluation

### File Purpose

#### file_001 - What does Ippl.h do?

- Verdict: **Correct**
- Codex reference answer: Declares the top-level IPPL runtime handles (`Comm`, `Env`, `Info`, `Warn`, `Error`) and the lifecycle wrappers `initialize`, `finalize`, `fence`, and `abort`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.41`
- Local answer excerpt: `Answer: Ippl.h serves as a central header file in the root module of the IPPL library. It provides essential functions and variables for managing application initialization (`ippl::initialize`), termination (`ippl::finalize`), synchronization (`ippl::fence`...`

#### file_002 - What is the purpose of Ippl.cpp?

- Verdict: **Partial**
- Codex reference answer: Implements runtime setup/teardown: command-line option parsing, MPI communicator/environment creation, logger setup, Kokkos init/finalize, and abort/fence helpers.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.42`
- Local answer excerpt: `Answer: The `Ippl.cpp` file contains essential utility functions for managing initialization, finalization, and error handling within the IPPL framework. It is responsible for configuring and managing the library's runtime environment, which includes functi...`

#### file_003 - What does FFT.hpp implement?

- Verdict: **Correct**
- Codex reference answer: Implements `FFTBase` setup plus the FFT specialization family for complex/real, sine, cosine, and cosine-I transforms on IPPL fields via heFFTe.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.29`
- Local answer excerpt: `Answer: The file `FFT.hpp` defines the base class `FFTBase<Field, FFT, Backend, T>` and several specializations for Fast Fourier Transform (FFT) operations within the `ippl` namespace. It supports various transform types, including real and complex field tr...`

#### file_004 - What is BareField.h responsible for?

- Verdict: **Incorrect**
- Codex reference answer: Defines the core distributed field container: Kokkos-backed storage, owned/allocated domains, field layout access, halo exchange hooks, and expression-style assignment.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.22`
- Local answer excerpt: `Answer: The `BareField.h` file defines the `ippl::BareField` class, which serves as a fundamental abstraction for representing fields in scientific computations within the IPPL framework. This class includes methods to access various properties of the field...`

#### file_005 - What does Field.h add on top of BareField?

- Verdict: **Correct**
- Codex reference answer: Adds mesh awareness and boundary-condition management on top of `BareField`, plus volume integral/average helpers.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.61`
- Local answer excerpt: `Answer: `Field.h` adds higher-level capabilities to the basic foundation provided by `BareField`. Specifically, it introduces boundary condition (BC) management through the methods `getFieldBC` and `setFieldBC`, integration with mesh representations like `U...`

#### file_006 - What role does HaloCells.h play in IPPL?

- Verdict: **Partial**
- Codex reference answer: Defines the halo-exchange machinery for fields: pack/unpack, boundary exchange, and periodic handling for ghost cells.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.40`
- Local answer excerpt: `Answer: The `HaloCells.h` file defines the `ippl::detail::HaloCells` class and related structures including `FieldBufferData`, `assign`, `lhs_plus_assign`, and `rhs_plus_assign`. Its primary role is to manage guard/ghost cells for field data, facilitating i...`

#### file_007 - What is the purpose of FieldLayout.h?

- Verdict: **Incorrect**
- Codex reference answer: Defines how a global `NDIndex` domain is partitioned across MPI ranks, including local subdomains, neighbors, and communication ranges.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.14`
- Local answer excerpt: `Answer: FieldLayout.h defines the FieldLayout class and related helper functions within the ippl namespace to manage field distribution, domain information, and layout configurations for scientific computations. It includes a bound_type struct to represent ...`

#### file_008 - What does ParticleBase.h define?

- Verdict: **Partial**
- Codex reference answer: Defines the generic particle container base class with positions, optional IDs, registered attributes, and a particle layout that controls migration.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.31`
- Local answer excerpt: `Answer: The `ParticleBase.h` file defines the `ippl::ParticleBase` class, which serves as a foundational abstraction for managing particle data within the IPPL framework, including attributes, layout, and local/global particle counts. It also defines the `i...`

#### file_009 - What is the purpose of ParticleSpatialLayout.h?

- Verdict: **Correct**
- Codex reference answer: Defines the spatial particle layout that decides ownership by region and migrates particles to the correct rank after motion.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.46`
- Local answer excerpt: `Answer: The `ParticleSpatialLayout` class is designed to manage the spatial layout and communication regions for particles within the IPPL library. It ensures that particles are distributed across processors based on their positions relative to a fixed grid...`

#### file_010 - What does ParticleAttrib.h implement?

- Verdict: **Correct**
- Codex reference answer: Implements the `ParticleAttrib` storage object: a Kokkos-view-backed particle attribute with resize, serialization, and mirror/access helpers.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.50`
- Local answer excerpt: `Answer: The header file `ParticleAttrib.h` defines a class template, `ippl::ParticleAttrib`, within the `ippl` namespace. This class is used to manage and manipulate attributes associated with particles in a simulation (such as position or velocity). It pro...`

#### file_011 - What is UniformCartesian.h for?

- Verdict: **Correct**
- Codex reference answer: Defines the uniform Cartesian mesh class with spacing, origin, cell volume, total mesh volume, and vertex-position helpers.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.62`
- Local answer excerpt: `Answer: The file `UniformCartesian.h` defines the `UniformCartesian` class family in the `ippl::Meshes` namespace, which specializes uniform Cartesian meshes used in computational physics and numerical simulations involving structured grids. It provides met...`

#### file_012 - What does OrthogonalRecursiveBisection.h do?

- Verdict: **Correct**
- Codex reference answer: Declares the orthogonal recursive bisection domain-decomposition/load-balancing class and its cut/median/repartition helpers.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.60`
- Local answer excerpt: `Answer: The file `OrthogonalRecursiveBisection.h` defines the class `ippl::OrthogonalRecursiveBisection`, which implements an orthogonal recursive bisection algorithm for decomposing computational domains. This method is used in parallel computing to divide...`

#### file_013 - What is the purpose of CIC.h in the Interpolation subsystem?

- Verdict: **Correct**
- Codex reference answer: Declares the first-order cloud-in-cell interpolation helpers for scatter/gather between particles and grid fields.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.50`
- Local answer excerpt: `Answer: The file `CIC.h` defines several function declarations within the `ippl::detail` namespace that handle interpolation operations specifically for Cloud-in-Cell (CIC) methods. These functions are used to distribute particles' properties onto a grid an...`

### Definition Location

#### loc_001 - Where is FFT initialization implemented in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: FFT initialization lives in `src/FFT/FFT.hpp`, especially `FFTBase` construction/setup and the transform-specific constructors that build the heFFTe plans.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.30`
- Local answer excerpt: `Answer: The provided context does not contain information regarding FFT initialization. The available chunks cover MPI environment and command-line parsing in `Ippl.cpp`, field layout configuration in `FieldLayout.h`, FEM vector construction in `FEMVector.h...`

#### loc_002 - Where does IPPL set up the MPI environment?

- Verdict: **Incorrect**
- Codex reference answer: IPPL sets up MPI in `src/Ippl.cpp::initialize()` by constructing `mpi::Environment` and `mpi::Communicator`; the low-level `MPI_Init` check/call is in `src/Communicate/Environment.cpp`.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.05`
- Local answer excerpt: `Answer: The provided context is insufficient to answer this question. The retrieved chunks cover Fourier Transform configuration and plan initialization using the HeFFTe library (e.g., `ippl::FFTBase::setup`), field memory allocation and sizing in `BareFiel...`

#### loc_003 - Where is Kokkos initialized and finalized inside IPPL?

- Verdict: **Correct**
- Codex reference answer: Kokkos is initialized and finalized directly in `src/Ippl.cpp` inside `ippl::initialize()` and `ippl::finalize()`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.67`
- Local answer excerpt: `Answer: Kokkos is initialized within the `ippl::initialize` function in `Ippl.cpp` using the call `Kokkos::initialize(argc, argv)` with the remaining command-line arguments. The `ippl::finalize` function, also located in `Ippl.cpp`, handles the cleanup of r...`

#### loc_004 - Where is the orthogonal recursive bisection load balancer implemented?

- Verdict: **Correct**
- Codex reference answer: The ORB load balancer is implemented in `src/Decomposition/OrthogonalRecursiveBisection.hpp` with declarations in the matching header.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.71`
- Local answer excerpt: `Answer: The orthogonal recursive bisection load balancer is implemented via the `ippl::OrthogonalRecursiveBisection` class (and its template version `ippl::OrthogonalRecursiveBisection<Field, Tp>`) located in the `Decomposition` module. The implementation r...`

#### loc_005 - Where are boundary conditions applied to a Field?

- Verdict: **Correct**
- Codex reference answer: Field BCs are attached in `Field::setFieldBC()` and actually applied through `BConds::apply()` and the concrete face classes in `BcTypes.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: Boundary conditions for an `ippl::Field` are stored as a member variable `bc_m` of type `BConds_t` and configured via the `setFieldBC` method in `Field.h`. These conditions are applied within the `MaxwellSolvers` module during simulation; specifical...`

#### loc_006 - Where is the CIC (cloud-in-cell) scatter implemented?

- Verdict: **Correct**
- Codex reference answer: CIC scatter is implemented in `src/Interpolation/CIC.hpp`, primarily `scatterToPoint()` and `scatterToField()`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.91`
- Local answer excerpt: `Answer: The core CIC (cloud-in-cell) scatter logic is implemented in the `ippl::detail` namespace within `data/raw/ippl/src/Interpolation/CIC.hpp`. This is primarily handled by the `scatterToField` function, which uses a fold expression to call `scatterToPo...`

#### loc_007 - Where is the CIC gather implemented?

- Verdict: **Correct**
- Codex reference answer: CIC gather is implemented in `src/Interpolation/CIC.hpp`, primarily `gatherFromPoint()` and `gatherFromField()`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.82`
- Local answer excerpt: `Answer: The CIC gather operations are implemented as the `gatherFromField` and `gatherFromPoint` methods within the `ippl::detail` namespace. These methods are defined in `data/raw/ippl/src/Interpolation/CIC.hpp` (and declared in `data/raw/ippl/src/Interpol...`

#### loc_008 - Where is halo exchange for BareField implemented?

- Verdict: **Correct**
- Codex reference answer: Halo exchange for `BareField` is surfaced in `src/Field/BareField.hpp` and actually performed in `src/Field/HaloCells.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.54`
- Local answer excerpt: `Answer: The halo exchange for `BareField` is implemented through the `ippl::detail::HaloCells` class. The `BareField` class uses `detail::HaloCells` as its internal `halo_type` to manage ghost cells and support parallel computations. Specifically, the `Halo...`

#### loc_009 - Where are the FFT-based open-boundary Poisson solver routines defined?

- Verdict: **Correct**
- Codex reference answer: The FFT open-boundary Poisson routines are defined in `src/PoissonSolvers/FFTOpenPoissonSolver.h` and `src/PoissonSolvers/FFTOpenPoissonSolver.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.83`
- Local answer excerpt: `Answer: The FFT-based open-boundary Poisson solver is implemented via the `FFTOpenPoissonSolver` class template (specifically `ippl::FFTOpenPoissonSolver<FieldLHS, FieldRHS>`), which inherits from `Poisson<FieldLHS, FieldRHS>`. The primary routines are loca...`

#### loc_010 - Where is the conjugate gradient solver algorithm implemented?

- Verdict: **Correct**
- Codex reference answer: The CG/PCG algorithm implementation is in `src/LinearSolvers/PCG.h`; the Poisson wrapper that instantiates it is `src/PoissonSolvers/PoissonCG.h`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.67`
- Local answer excerpt: `Answer: The core conjugate gradient algorithm is implemented in the `ippl::CG` class template found in `src/LinearSolvers/PCG.h`. This class manages the execution of the CG method, including configuration of operators and preconditioners for solving linear ...`

#### loc_011 - Where is the FEM Poisson solver implemented?

- Verdict: **Correct**
- Codex reference answer: The FEM Poisson solver is implemented in `src/PoissonSolvers/FEMPoissonSolver.h`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.83`
- Local answer excerpt: `Answer: The FEM Poisson solver is implemented as the `FEMPoissonSolver` class in the file `data/raw/ippl/src/PoissonSolvers/FEMPoissonSolver.h`. This class inherits from `Poisson<FieldLHS, FieldRHS>` and solves the Poisson equation using finite element meth...`

#### loc_012 - Where is the FDTD Maxwell solver base class defined?

- Verdict: **Incorrect**
- Codex reference answer: The FDTD Maxwell solver base class is defined in `src/MaxwellSolvers/FDTDSolverBase.h` with implementation in `FDTDSolverBase.hpp`.
- Comparison: The answer cites a different implementation location than the Codex reference.
- Reference-token coverage: `0.40`
- Local answer excerpt: `Answer: The `FieldSolverBase` class is defined in `src/Manager/FieldSolverBase.h` within the `ippl::Manager` namespace. It serves as an abstract base class for field solvers, providing common functionality and enforcing a specific interface including method...`

#### loc_013 - Where is the LagrangeSpace class defined?

- Verdict: **Correct**
- Codex reference answer: The `LagrangeSpace` class is defined in `src/FEM/LagrangeSpace.h` with methods implemented in `src/FEM/LagrangeSpace.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.56`
- Local answer excerpt: `Answer: The `ippl::LagrangeSpace` class is defined in the file `data/raw/ippl/src/FEM/LagrangeSpace.h`. This class, which inherits from `FiniteElementSpace`, represents a Lagrange space for finite element methods (FEM) on a structured grid and provides func...`

#### loc_014 - Where is the particle update routine (that moves particles across ranks) implemented?

- Verdict: **Correct**
- Codex reference answer: Particle migration between ranks is implemented in `ParticleSpatialLayout::update()` in `src/Particle/ParticleSpatialLayout.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.70`
- Local answer excerpt: `Answer: The particle update routines that move particles across ranks are implemented in two different classes depending on the layout used: 1. **ippl::ParticleSpatialLayout<T, Dim, Mesh, Properties...>::update**: Located in `data/raw/ippl/src/Particle/Part...`

#### loc_015 - Where are IPPL timers defined?

- Verdict: **Incorrect**
- Codex reference answer: IPPL timers are defined by the singleton timing layer in `src/Utility/IpplTimings.h/.cpp`, not just the low-level `Timer` helper.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.25`
- Local answer excerpt: `Answer: The provided context does not specify where IPPL timers are defined. The retrieved chunks cover the initialization of the IPPL system (including timer settings and `Timer::enableFences` in `Ippl.cpp`), buffer management logic, and the definition of ...`

### Class Responsibility

#### cls_001 - What is the main responsibility of the BareField class?

- Verdict: **Correct**
- Codex reference answer: `BareField` is the core distributed field storage class: it owns the data view, domain metadata, layout link, and halo operations.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.44`
- Local answer excerpt: `Answer: The `ippl::BareField` class serves as a fundamental abstraction for representing fields in scientific computations within the IPPL framework. Its primary responsibilities include managing memory and access patterns for multidimensional fields while ...`

#### cls_002 - What is the main responsibility of the Field class compared to BareField?

- Verdict: **Incorrect**
- Codex reference answer: `Field` extends `BareField` with a mesh, boundary-condition container, and mesh-aware integral/average semantics.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.19`
- Local answer excerpt: `Answer: The provided context is insufficient to answer the question because it does not mention a 'Field' class or provide any comparison between a 'Field' and 'BareField'. The retrieved chunks cover the `ippl::BareField` class, which manages multidimension...`

#### cls_003 - What does the FieldLayout class do and what are its main template parameters?

- Verdict: **Correct**
- Codex reference answer: `FieldLayout<Dim>` distributes a global `NDIndex<Dim>` over ranks and stores local domains, neighbors, and communication ranges; its only template parameter is `Dim`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.58`
- Local answer excerpt: `Answer: The `ippl::FieldLayout` class manages the distribution of a multi-dimensional index space (domain) across MPI ranks. It handles partitioning the domain among different ranks while allowing specific dimensions to be marked as non-partitioned ('SERIAL...`

#### cls_004 - What is the purpose of the ParticleBase class and how is it meant to be used?

- Verdict: **Correct**
- Codex reference answer: `ParticleBase` is the user-extensible base container for particles; derived classes add attributes and register them so layout-driven migration can move them.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.40`
- Local answer excerpt: `Answer: The `ParticleBase` class serves as a foundational abstraction for managing particle data within the IPPL framework. It functions as both a container and manager for sets of particles, providing methods to handle attributes (represented as instances ...`

#### cls_005 - What does the ParticleSpatialLayout class do?

- Verdict: **Correct**
- Codex reference answer: `ParticleSpatialLayout` decides which spatial region/rank owns each particle and performs the migration/update workflow after particles move.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.56`
- Local answer excerpt: `Answer: The `ippl::ParticleSpatialLayout` class manages the spatial distribution of particles across processors based on their positions relative to a fixed grid. It is a specialized version of `detail::ParticleLayout` designed to ensure that particles are ...`

#### cls_006 - What is the responsibility of UniformCartesian?

- Verdict: **Correct**
- Codex reference answer: `UniformCartesian` represents a uniform Cartesian mesh and exposes spacing/origin/volume and vertex-position geometry queries.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.62`
- Local answer excerpt: `Answer: The `UniformCartesian` class in the `ippl::Meshes` namespace (inheriting from `Mesh<T, Dim>`) is responsible for representing uniform-spacing Cartesian meshes used in numerical simulations. It provides functionality to initialize and manipulate thes...`

#### cls_007 - What does the Mesh base class define?

- Verdict: **Incorrect**
- Codex reference answer: `Mesh` is the abstract base interface for meshes: origin, grid size, spacing, vertex positions, and volume queries.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.20`
- Local answer excerpt: `Answer: The provided context does not contain information regarding what the Mesh base class defines. Evidence: - data/raw/ippl/src/Meshes/CartesianCentering.h : CartesianCentering — handles logic and reporting for centering operations on Cartesian grids. -...`

#### cls_008 - What is the responsibility of the Communicator class in ippl::mpi?

- Verdict: **Correct**
- Codex reference answer: `ippl::mpi::Communicator` wraps MPI point-to-point, collectives, tag handling, and managed communication buffers.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The `ippl::mpi::Communicator` class is responsible for encapsulating MPI communication functionalities, including managing barriers, rank retrieval, and size determination. It facilitates inter-process communication to enable efficient data exchange...`

#### cls_009 - What is the role of the Environment class in ippl::mpi?

- Verdict: **Correct**
- Codex reference answer: `ippl::mpi::Environment` manages MPI environment lifetime checks/teardown and provides an abort hook.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.50`
- Local answer excerpt: `Answer: The `ippl::mpi::Environment` class manages Message Passing Interface (MPI) environment setup and teardown within the IPPL library. It provides functionality for initializing and finalizing the MPI environment, including member functions such as `ini...`

#### cls_010 - What does the Archive class do in the Communicate module?

- Verdict: **Partial**
- Codex reference answer: `Archive` serializes and deserializes Kokkos views and vector-valued views into raw byte buffers for MPI transfer.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.23`
- Local answer excerpt: `Answer: The `Archive` class family in the Communicate module provides functionality for managing data buffers and performing serialization and deserialization operations, particularly within communication or serialization contexts. Specifically, the `ippl::...`

#### cls_011 - What is the role of the BConds class?

- Verdict: **Correct**
- Codex reference answer: `BConds` is the container of boundary-condition faces and orchestrates neighbor discovery, BC application, and ghost-to-physical assignment.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.44`
- Local answer excerpt: `Answer: The `ippl::BConds` class serves as a container for boundary condition (BC) objects associated with fields. It manages and applies these conditions by interacting with specific BC classes (which inherit from `detail::BCondBase<Field>`). The class pro...`

#### cls_012 - What is the role of the BaseManager class?

- Verdict: **Correct**
- Codex reference answer: `BaseManager` provides the simulation loop skeleton: `pre_run`, `pre_step`, `advance`, `post_step`, and `run(nt)`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.87`
- Local answer excerpt: `Answer: The `BaseManager` class is an abstract base class within the `ippl` namespace that provides a structured and standardized framework for managing simulation lifecycles, including setup, execution, and cleanup phases. It utilizes the Template Method p...`

#### cls_013 - What does the Index class represent and what operations does it support?

- Verdict: **Incorrect**
- Codex reference answer: `Index` represents a regular strided integer range/slice and supports range-style arithmetic and comparison operations used in domain descriptions.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.12`
- Local answer excerpt: `Answer: The provided context is insufficient to answer what the `Index` class represents; however, the retrieved chunks cover a variant type system including an `index()` member function for determining active types, a `Tuple` structure that utilizes index-...`

### Algorithm

#### alg_001 - How does the FFT-based open-boundary Poisson solver compute the electrostatic potential?

- Verdict: **Partial**
- Codex reference answer: The FFT open-boundary solver embeds/extends the RHS onto larger domains, FFTs both the density and a precomputed Green's function, multiplies in Fourier space, inverse transforms, and optionally computes gradients/Hessians.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.30`
- Local answer excerpt: `Answer: The `FFTOpenPoissonSolver` class template solves the Poisson equation using Fast Fourier Transform (FFT) techniques. To handle open boundaries specifically, it utilizes Vico-Greengard's Green's function via methods such as `green_function` and `grn_...`

#### alg_002 - How does the FFT-based periodic Poisson solver work in IPPL?

- Verdict: **Correct**
- Codex reference answer: The periodic FFT solver FFTs the charge density, divides each Fourier mode by `|k|^2` (with the zero mode handled separately), then inverse transforms; gradients are computed by multiplying by `ik/|k|^2` before the inverse FFT.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.55`
- Local answer excerpt: `Answer: The FFT-based periodic Poisson solver, specifically implemented in classes such as `FFTTruncatedGreenPeriodicPoissonSolver`, solves the equation $\nabla^2 \phi = -\rho$ and calculates the electric field $E = -\nabla \phi$ by utilizing Fast Fourier T...`

#### alg_003 - How does the truncated Green periodic Poisson solver differ from the standard periodic one?

- Verdict: **Correct**
- Codex reference answer: The truncated-Green periodic solver replaces the simple `1/|k|^2` kernel with the FFT of a truncated/erf-smoothed Green's function `forceConstant * erf(alpha r) / r`, then follows the same transform-multiply-inverse pattern.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.25`
- Local answer excerpt: `Answer: The `FFTTruncatedGreenPeriodicPoissonSolver` differs from the standard periodic solver (such as the `FFTPeriodicPoissonSolver`) by utilizing a **truncated Green's function** to handle periodic boundary conditions effectively. While both solvers util...`

#### alg_004 - How does IPPL's CG solver iterate in the PCG.h implementation?

- Verdict: **Incorrect**
- Codex reference answer: In `PCG.h`, the CG iteration forms residual/direction fields, applies the operator, computes `alpha` and `beta` from inner products, updates the solution/residual/direction, and stops on tolerance or iteration count; the preconditioned variant inserts `M^{-1}` applications on the residual.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.27`
- Local answer excerpt: `Answer: The provided context does not contain specific details regarding the internal iteration logic or calculation steps used by the conjugate gradient method in `PCG.h`. The available documentation covers the configuration of operators and preconditioner...`

#### alg_005 - How is cloud-in-cell interpolation performed in IPPL (both scatter and gather directions)?

- Verdict: **Partial**
- Codex reference answer: CIC computes lower/upper weights per axis, scatters with atomic adds to the `2^Dim` neighboring grid points, and gathers by summing the same weighted stencil back to particles.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.26`
- Local answer excerpt: `Answer: Cloud-in-cell (CIC) interpolation is performed in both directions using a consistent coordinate transformation where particle positions are mapped to grid units $l$ via `(pp_view - origin) * invdx + 0.5`. In the **scatter** direction, the method `Pa...`

#### alg_006 - How does the standard FDTD solver advance the electromagnetic field in time?

- Verdict: **Partial**
- Codex reference answer: The standard FDTD solver advances the source-like field with a second-order finite-difference update using the previous and current time levels plus neighboring cells and source terms, then fills halos and reapplies BCs.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The standard FDTD solver, implemented in the `StandardFDTDSolver` class, advances the electromagnetic field (`EMField`) by one time step using a leapfrog scheme. This method calculates several coefficients ($a_1$, $a_2$, $a_4$, $a_6$, and $a_8$) bas...`

#### alg_007 - How does the LagrangeSpace class evaluate degrees of freedom per element?

- Verdict: **Correct**
- Codex reference answer: `LagrangeSpace` evaluates element DOFs by mapping local element indices to global DOF indices, then evaluates order-1 reference-element shape functions and gradients on those local DOFs.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.32`
- Local answer excerpt: `Answer: The `LagrangeSpace` class determines the number of degrees of freedom (DOFs) per element using the `getLagrangeNumElementDOFs(Dim, Order)` function. This value is determined based on the polynomial order and spatial dimension of the mesh. The calcul...`

#### alg_008 - How is Gauss-Jacobi quadrature implemented and used in IPPL FEM?

- Verdict: **Correct**
- Codex reference answer: Gauss-Jacobi quadrature computes nodes/weights by Newton iteration on Jacobi polynomial roots, starting from Chebyshev or LehrFEM-style guesses, and uses the resulting rule on reference elements in FEM.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.54`
- Local answer excerpt: `Answer: Gauss-Jacobi quadrature is implemented through the `ippl::GaussJacobiQuadrature` class, which inherits from the `ippl::Quadrature` base class. The implementation uses a combination of Chebyshev nodes as initial guesses and Newton iterations to compu...`

#### alg_009 - How does the orthogonal recursive bisection decide where to cut the domain?

- Verdict: **Partial**
- Codex reference answer: ORB chooses a cut axis from the domain geometry and then finds a weight-balanced cut/median so recursive splits distribute load more evenly.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.37`
- Local answer excerpt: `Answer: The orthogonal recursive bisection determines the cut location by first identifying the "longest axis" of the multi-dimensional domain using the `findCutAxis` method, which selects the dimension with the maximum length within an `NDIndex`. Once the ...`

#### alg_010 - How does inverse transform sampling generate particles from a given distribution in IPPL?

- Verdict: **Partial**
- Codex reference answer: Inverse transform sampling maps uniform random values in CDF space to samples by estimating the inverse and refining it with Newton-Raphson, dimension by dimension.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.41`
- Local answer excerpt: `Answer: Inverse transform sampling is implemented in the `ippl::random::InverseTransformSampling` class. This process utilizes a `Distribution` object, which encapsulates the probability density function (PDF), cumulative distribution function (CDF), and an...`

#### alg_011 - How does the FFT class interface with heFFTe to perform complex-to-complex and real-to-complex transforms?

- Verdict: **Partial**
- Codex reference answer: The FFT layer builds heFFTe boxes/plans in `setup()`, copies IPPL field data into the required views/subviews, calls heFFTe forward/backward transforms, and copies results back for CC/RC/DST/DCT variants.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.27`
- Local answer excerpt: `Answer: The `FFT` class utilizes a family of specialized classes parameterized by various transform types, including `CCTransform`, `Cos1Transform`, and `RCTransform`, to handle different transformation modes. To interface with heFFTe, the class converts in...`

#### alg_012 - How does IPPL's preconditioned CG use the preconditioner defined in Preconditioner.h?

- Verdict: **Partial**
- Codex reference answer: PCG applies a chosen preconditioner from `Preconditioner.h` to the residual, uses the preconditioned residual in its inner products and direction updates, and iterates until tolerance/max iterations.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.22`
- Local answer excerpt: `Answer: The preconditioned Conjugate Gradient (CG) solver, implemented via the `ippl::CG` class in `PCG.h`, uses the `setPreconditioner` method to select and configure a preconditioner from those defined in `Preconditioner.h`. The `preconditioner` struct se...`

### Data Flow

#### flow_001 - How does charge density flow from particles to the grid in a typical PIC step in IPPL?

- Verdict: **Correct**
- Codex reference answer: In the PIC workflow, particle charges and positions are deposited onto the grid with CIC (`scatter`) or FEM assembly (`assemble_rhs_from_particles`), accumulated into `rho`, and then normalized/background-shifted in the manager before solving.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.42`
- Local answer excerpt: `Answer: In a typical PIC step, charge density is transferred from particles to the grid using the `assemble_rhs_from_particles` function. This process involves depositing weighted values from particle attributes (such as charge) into a field $f$ based on th...`

#### flow_002 - How does the electric field flow from the grid back to particles after a Poisson solve?

- Verdict: **Incorrect**
- Codex reference answer: After the field solve, the manager gathers the electric field back to particles with CIC `gather(...)` or FEM `interpolate_grad_to_diracs(...)`, storing particle-local `E` values for the push step.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.35`
- Local answer excerpt: `Answer: The retrieved context does not provide information on how the electric field flows from the grid back to particles; however, it covers the calculation of electric fields on a mesh using finite differences or Fourier-space convolution with a Green's ...`

#### flow_003 - How are halo cells exchanged between neighboring MPI ranks for a BareField?

- Verdict: **Partial**
- Codex reference answer: Halo exchange uses `FieldLayout` neighbor/range metadata to pack field subviews, send/receive them with MPI, unpack into ghost or physical regions, and handle serial-periodic dimensions locally.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.22`
- Local answer excerpt: `Answer: The exchange of halo cells for a `BareField` is managed by the `ippl::detail::HaloCells` class, which facilitates inter-process communication (IPC) of boundary data between different parts of a decomposed field in a distributed-memory setting. While...`

#### flow_004 - How are particles migrated between MPI ranks by ParticleSpatialLayout?

- Verdict: **Correct**
- Codex reference answer: `ParticleSpatialLayout::update()` applies particle BCs, locates destination ranks, advertises receive counts with RMA, sends all registered attributes, destroys invalid local particles, and receives the incoming ones.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.27`
- Local answer excerpt: `Answer: The `ParticleSpatialLayout` class manages particle movement between processors through the `update` routine, which is called when changes affect the global layout. Migration involves the `locateParticles` method, which determines the target rank for...`

#### flow_005 - How does FieldLayout decide which index ranges live on which rank?

- Verdict: **Correct**
- Codex reference answer: `FieldLayout` uses the partitioner and the requested parallel/serial decomposition flags to assign each rank a local `NDIndex`, plus neighbor and communication range tables.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.29`
- Local answer excerpt: `Answer: The `FieldLayout<Dim>` class manages domain information and field distribution by utilizing multi-dimensional index spaces of type `NDIndex_t` to define spatial regions. It employs methods such as `getBounds`, `getLocalNDIndex`, and `getHostLocalDom...`

#### flow_006 - How is a ParameterList used to configure the FFT and solver classes?

- Verdict: **Correct**
- Codex reference answer: `ParameterList` is merged into FFT and solver objects, then consumed by `setup()/initialize()/solve()` for communication mode, pencil/reorder flags, transform direction, solver type, tolerances, preconditioner settings, and output type.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.28`
- Local answer excerpt: `Answer: The `ParameterList` class manages a collection of named parameters (supporting types such as `double`, `float`, and `bool`) to define configurations like "tolerance in case of iterative solvers." In the `FFT` class, a `ParameterList` is passed into ...`

#### flow_007 - How does data flow through the BaseManager's pre_step / advance / post_step hooks during a simulation?

- Verdict: **Partial**
- Codex reference answer: `BaseManager::run()` executes `pre_step()`, `advance()`, and `post_step()` for each timestep; derived managers use those hooks for deposit/solve/gather, time updates, and output.
- Comparison: The answer has some relevant signal but undercuts itself with uncertainty or abstention.
- Reference-token coverage: `0.52`
- Local answer excerpt: `Answer: The provided context is insufficient to describe how data flows through the `pre_step`, `advance`, and `post_step` hooks. The retrieved chunks cover: - The definition of `BaseManager` methods (`run`, `pre_run`, `pre_step`, `post_step`, and `advance`...`

#### flow_008 - How does the FEM solver move data between fields and FEMVector representations?

- Verdict: **Correct**
- Codex reference answer: FEM solvers move data by assembling field data into FEM load/stiffness representations (`evaluateLoadVector`, `evaluateAx`, `FEMVector`) and then interpolating the solved field quantities back where needed.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.35`
- Local answer excerpt: `Answer: The provided context does not describe how the FEM solver moves data between fields and FEMVector representations; however, it details how `FEMVector` handles internal data movement across distributed domains and notes that fields are used as inputs...`

#### flow_009 - How does OrthogonalRecursiveBisection redistribute particles after rebalancing?

- Verdict: **Incorrect**
- Codex reference answer: After ORB recomputes the decomposition, particle ownership changes are realized by updating the layout/regions and then migrating particles with the usual particle update path.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.11`
- Local answer excerpt: `Answer: The `OrthogonalRecursiveBisection::binaryRepartition` method manages particle distribution across different ranks by performing a binary recursive bisection of the computational domain. If it is not the first iteration of the process (where analytic...`

### Api Usage

#### api_001 - How do I create a 3D Field of doubles in IPPL?

- Verdict: **Partial**
- Codex reference answer: A typical 3D field is `Field<double, 3, UniformCartesian<double, 3>, Cell>` constructed from a `UniformCartesian` mesh and a `FieldLayout<3>`.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.29`
- Local answer excerpt: `Answer: To create a 3D field of doubles, use the `ippl::Field` class, which inherits from `BareField<T, Dim, ViewArgs...>`. In this context, $T$ represents the data type (e.g., double) and $Dim$ represents the dimensionality (e.g., 3). The field can be inst...`

#### api_002 - How do I construct a UniformCartesian mesh with custom spacing and origin?

- Verdict: **Correct**
- Codex reference answer: Construct the mesh as `UniformCartesian<double, Dim> mesh(domain, hx, origin);` where `hx` is the spacing vector and `origin` is the mesh origin.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.69`
- Local answer excerpt: `Answer: To construct a `UniformCartesian` mesh with specific spacing and origin, use the `ippl::UniformCartesian` constructor located in `src/Meshes/UniformCartesian.h`. This constructor accepts three parameters for initialization: an `NDIndex<Dim>` (repres...`

#### api_003 - How do I attach a boundary condition (e.g. periodic) to a Field?

- Verdict: **Partial**
- Codex reference answer: Create a `BConds<FieldT, Dim>`, assign per-face BC objects such as `PeriodicFace<FieldT>`, then call `field.setFieldBC(bc)`.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: To attach a boundary condition to a field, you use the `setFieldBC()` method on the field object. Specifically, for periodic boundary conditions, the `setPeriodicBoundaryConditions` method in the `FDTDSolverBase` class template creates a vector of s...`

#### api_004 - How do I define a custom particle class that adds mass and velocity attributes on top of ParticleBase?

- Verdict: **Correct**
- Codex reference answer: Define a class derived from `ParticleBase<ParticleSpatialLayout<...>>`, add `mass` and `velocity` attributes as members, and register them with `addAttribute()` in the constructor.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.47`
- Local answer excerpt: `Answer: To include additional properties in the particle data structure, you can utilize the `addAttribute` method within the `ParticleBase<PLayout, IP...>` template. This method takes a reference to an object of type `detail::ParticleAttribBase<MemorySpace...`

#### api_005 - How do I call ippl::initialize and ippl::finalize in a main program?

- Verdict: **Correct**
- Codex reference answer: Call the free namespace functions `ippl::initialize(argc, argv);` and `ippl::finalize();` from `main`, as shown in the docs/examples.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.53`
- Local answer excerpt: `Answer: To call `ippl::initialize` in a main program, you must provide three parameters: an integer reference to the argument count (`int& argc`), a command-line argument array (`char* argv[]`), and an MPI communicator (`MPI_Comm comm`). This function is de...`

#### api_006 - How do I set up and run a forward FFT on an IPPL Field?

- Verdict: **Correct**
- Codex reference answer: Set up the relevant layouts/fields/parameters, build an `FFT<CCTransform, ...>` or `FFT<RCTransform, ...>` object, and call `transform(FORWARD, ...)` on the field(s).
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.47`
- Local answer excerpt: `Answer: To set up and run an FFT on a field, you instantiate an `iqppl::FFT` class template (such as `iqppl::FFT<RCTransform, RealField>` or `iqppl::FFT<CCTransform, ComplexField>`). The setup is performed during construction by providing input and output `...`

#### api_007 - How do I construct an FFTPeriodicPoissonSolver and solve for the potential?

- Verdict: **Correct**
- Codex reference answer: Construct `FFTPeriodicPoissonSolver(lhs, rhs)` (or default construct then set fields/params), ensure the RHS is attached, and call `solve()` to write the potential/gradient outputs.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.57`
- Local answer excerpt: `Answer: To construct an `ippl::FFTPeriodicPoissonSolver`, instantiate the class defined in `FFTPeriodicPoissonSolver.h` or `FFTPeriodicPoissonSolver.hpp`. The constructor for this class automatically initializes the base class and invokes the `setDefaultPar...`

#### api_008 - How do I invoke the conjugate gradient Poisson solver on a Field?

- Verdict: **Correct**
- Codex reference answer: Use `PoissonCG<FieldT>` (or the Alpine `FieldSolver` wrapper around it), set its fields/parameters, and call `solve()` so the internal CG/PCG object iterates on the field.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.35`
- Local answer excerpt: `Answer: To invoke the conjugate gradient Poisson solver on a Field, use the `ippl::PoissonCG` class. This class can be instantiated through a constructor that accepts left-hand side (`lhs_type& lhs`) and right-hand side (`rhs_type& rhs`) fields (representin...`

#### api_009 - How do I sample particles from a normal distribution using IPPL Random utilities?

- Verdict: **Correct**
- Codex reference answer: For Gaussian draws, IPPL exposes both `randn` convenience generation and the more general `InverseTransformSampling` + `NormalDistribution` path.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.39`
- Local answer excerpt: `Answer: To sample from a normal distribution, use the `ippl::random::NormalDistribution` class. This class is specifically designed for sampling from a normal distribution on a bounded domain using inverse transform sampling and inherits from the `ippl::ran...`

#### api_010 - How do I register particle attributes with ParticleBase so that they are communicated on migration?

- Verdict: **Correct**
- Codex reference answer: Register each particle attribute with `addAttribute(...)`; migration then serializes and transfers all registered attributes automatically.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.62`
- Local answer excerpt: `Answer: To register particle attributes with `ParticleBase` so that they are managed and communicated during migration, you must define a custom class derived from `ippl::ParticleBase` (found in `ParticleBase.h`). Each attribute within this derived class mu...`

#### api_011 - How do I access the MPI rank and size through the IPPL Communicator?

- Verdict: **Correct**
- Codex reference answer: Access rank and size with `ippl::Comm->rank()` and `ippl::Comm->size()` (or the same methods on a `Communicator` object).
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.40`
- Local answer excerpt: `Answer: To access the rank and size of the current MPI communicator, use the `rank()` and `size()` member functions of the `ippl::mpi::Communicator` class. The `size()` method specifically retrieves the number of processes (or rank count) within the current...`

#### api_012 - How do I use IpplTimings to measure a region of code?

- Verdict: **Correct**
- Codex reference answer: Get a timer handle with `IpplTimings::getTimer("name")`, surround the code with `startTimer()` / `stopTimer()`, and print with `IpplTimings::print()`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.86`
- Local answer excerpt: `Answer: To measure a region of code using the `IpplTimings` class (located in `data/raw/ippl/src/Utility/IpplTimings.h`), follow these steps: 1. Create or retrieve a timer reference for your specific code section by calling `IpplTimings::getTimer("timer nam...`

### Parallelism And Kokkos

#### par_001 - How does IPPL achieve performance portability across CPUs and GPUs?

- Verdict: **Partial**
- Codex reference answer: IPPL gets performance portability by combining Kokkos execution/memory abstractions with MPI and heFFTe, so the same code paths can target CPUs and GPUs.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.41`
- Local answer excerpt: `Answer: IPPL achieves performance portability by utilizing the **Kokkos** library, which provides abstraction layers for multiple execution spaces. Specifically, it uses **Kokkos views** (`Kokos::View`) to manage data across different execution spaces (such...`

#### par_002 - Why does IPPL use Kokkos::View for field storage?

- Verdict: **Partial**
- Codex reference answer: IPPL uses `Kokkos::View` because fields need execution-space-aware storage, subviews, mirrors, and portable kernels across host/device memory spaces.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.23`
- Local answer excerpt: `Answer: IPPL utilizes `Kokkos::View` through the `view_type` defined within the `BareField` class to represent the actual storage for field data, which leverages Kokkos for memory management. Evidence: - data/raw/ippl/src/Field/BareField.h : BareField — The...`

#### par_003 - How does IPPL parallelize loops over field indices using Kokkos RangePolicy?

- Verdict: **Correct**
- Codex reference answer: Loops are parallelized through `ippl::getRangePolicy` / `createRangePolicy` and the `ippl::parallel_for` wrapper over Kokkos `RangePolicy`/`MDRangePolicy`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.67`
- Local answer excerpt: `Answer: IPPL uses a `RangePolicy` struct defined in the `ParallelDispatch.h` file to manage multi-dimensional range indices for parallel execution. This struct provides a `policy_type` that wraps Kokkos' `MDRangePolicy`, which utilizes `Kokkos::Rank<Dim>` t...`

#### par_004 - How does IPPL support mixed precision (float vs double) for fields?

- Verdict: **Partial**
- Codex reference answer: Precision is chosen by the field value type (`Field<float,...>` vs `Field<double,...>`), and the codebase also contains mixed-precision examples where fields/particles deliberately use different precisions.
- Comparison: The answer has some relevant signal but undercuts itself with uncertainty or abstention.
- Reference-token coverage: `0.35`
- Local answer excerpt: `Answer: The provided context does not contain information regarding how IPPL specifically supports mixed precision (float vs double) for fields. The retrieved chunks cover: system initialization and configuration options (`Ippl.h`, `Ippl.cpp`), multi-type p...`

#### par_005 - How does IPPL handle multiple execution spaces like OpenMP and CUDA in the same build?

- Verdict: **Incorrect**
- Codex reference answer: Multiple execution spaces are enabled at build time through `IPPL_PLATFORMS` and Kokkos/HeFFTe backend flags; IPPL also has container helpers for multi-space data.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.33`
- Local answer excerpt: `Answer: The retrieved context is insufficient to answer how IPPL handles multiple execution spaces like OpenMP and CUDA in the same build. The chunks cover the initialization of MPI environments, Inform objects for logging, and Kokkos; first-order grid inte...`

#### par_006 - What is the purpose of ParallelDispatch.h and what helpers does it expose?

- Verdict: **Correct**
- Codex reference answer: `ParallelDispatch.h` wraps Kokkos policies and functors, exposing `RangePolicy`, `getRangePolicy`, `createRangePolicy`, `parallel_for`, and `parallel_reduce`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.72`
- Local answer excerpt: `Answer: The purpose of `ParallelDispatch.h` is to provide abstractions and utilities for parallel execution within the IPPL framework, specifically facilitating the dispatching and management of parallel tasks. It exposes several helpers including: - **ippl...`

#### par_007 - How does the Archive class serialize/deserialize Kokkos views for MPI transfer?

- Verdict: **Partial**
- Codex reference answer: `Archive` serializes Kokkos views into one-dimensional byte buffers with Kokkos kernels and `memcpy`, then deserializes them back into views on receive.
- Comparison: The answer has some relevant signal but undercuts itself with uncertainty or abstention.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The retrieved context is insufficient to answer how the Archive class serializes or deserializes Kokkos views for MPI transfer; the provided snippets cover communicator logging, environment settings, request handling, memory buffers, and collective ...`

#### par_008 - How are MPI tags managed in IPPL to avoid collisions across subsystems?

- Verdict: **Correct**
- Codex reference answer: MPI tags are managed with fixed base tags in `Tags.h` and the cyclic tag allocator in `TagMaker`, which `Communicator` inherits.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.29`
- Local answer excerpt: `Answer: MPI tags are managed through a `Tag` enumeration within the `ippl::mpi::tag` namespace, which defines a set of integer constants used to differentiate between types of messages in the MPI framework. This tagging system allows for efficient message h...`

#### par_009 - What does Kokkos::fence do, and when does IPPL call the wrapper ippl::fence?

- Verdict: **Incorrect**
- Codex reference answer: `Kokkos::fence()` waits for outstanding kernels; IPPL exposes `ippl::fence()` as a runtime wrapper in `Ippl.cpp` and also fences internally after many kernel/data-movement steps.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.24`
- Local answer excerpt: `Answer: The retrieved context is insufficient to answer the question because it does not provide information on what `Kokkos::fence` specifically does. The chunks cover the role of `ippl::fence` as a synchronization point or barrier used during data packing...`

### Boundary And Halo

#### bc_001 - What boundary condition types are provided in BcTypes.h?

- Verdict: **Correct**
- Codex reference answer: `BcTypes.h` provides periodic, constant, zero, extrapolating, and no-BC face classes.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.70`
- Local answer excerpt: `Answer: The `BcTypes.h` file defines a family of boundary condition classes based on the abstract base class `ippl::detail::BCondBase`. The specific types provided are `ippl::PeriodicFace`, `ippl::ZeroFace`, `ippl::ConstantFace`, `ippl::NoBcFace` (the defau...`

#### bc_002 - How does a periodic boundary condition differ from a Neumann boundary condition in IPPL Fields?

- Verdict: **Partial**
- Codex reference answer: Periodic BCs wrap values from the opposite side of the domain; there is no explicit `NeumannFace` class in this codebase, so the closest non-periodic behavior is constant/extrapolating face treatment.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.29`
- Local answer excerpt: `Answer: The retrieved context does not mention or define Neumann boundary conditions. The provided chunks cover periodic boundary conditions (implemented via `PeriodicFace` and `PeriodicBC`) and non-periodic options such as `second_order_mur_boundary_condit...`

#### bc_003 - How are ghost cells populated during a halo exchange?

- Verdict: **Partial**
- Codex reference answer: Ghost cells are populated mainly by `fillHalo()` / `PeriodicFace::apply()`: source slabs are packed, exchanged, and unpacked into ghost regions; `accumulateHalo_noghost()` is a different operation.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.27`
- Local answer excerpt: `Answer: Ghost cells are populated during a halo exchange via the `exchangeBoundaries` method in the `HaloCells` class. This process involves several steps: first, the specific data ranges for each neighbor are identified using `FieldLayout::getNeighborsSend...`

#### bc_004 - How are physical-cell values copied into ghost cells for periodic boundary conditions?

- Verdict: **Correct**
- Codex reference answer: Periodic ghost cells are filled from opposite-side physical cells in `applyPeriodicSerialDim()` and the multi-rank `PeriodicFace::apply()` path.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.26`
- Local answer excerpt: `Answer: For electromagnetic fields such as `A_n`, `A_nm1`, and `A_np1`, the `applyBCs` method in `FDTDSolverBase` handles periodic boundary conditions by calling `getFieldBC().apply()` on each field when the `boundary_conditions` type is set to periodic. Th...`

#### bc_005 - How does the absorbing boundary condition in the MaxwellSolvers module damp outgoing waves?

- Verdict: **Partial**
- Codex reference answer: The absorbing Maxwell BC uses second-order Mur-style formulas with precomputed weights and previous/current/next boundary values plus tangential neighbors to damp outgoing waves.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The absorbing boundary condition in the MaxwellSolvers module is implemented using "second-order Mur absorbing boundary conditions" (ABC) to minimize reflections for electromagnetic field solvers. These are managed by the `second_order_mur_boundary_...`

### Numerical Meaning

#### num_001 - What does the FFT-based Poisson solver physically compute in terms of Coulomb's law?

- Verdict: **Correct**
- Codex reference answer: The FFT Poisson solvers compute electrostatic potential (and optionally field/gradient) from charge density, i.e. the discretized Coulomb potential corresponding to `-Δφ = ρ`.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.69`
- Local answer excerpt: `Answer: The FFT-based Poisson solvers, including `ippl::FFTOpenPoissonSolver`, `ippl::FFTPeriodicPoissonSolver`, and `ippl::FFTTruncatedGreenPeriodicPoissonSolver`, compute the electrostatic potential (and optionally its gradient and Hessian) based on a cha...`

#### num_002 - What is the physical meaning of the fields advanced by the FDTD solver?

- Verdict: **Correct**
- Codex reference answer: The Maxwell solvers evolve electromagnetic field data: electric and magnetic fields (`E`, `B`) driven by a source/four-current field.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.57`
- Local answer excerpt: `Answer: The FDTD solver advances **electromagnetic fields** (represented by the `EMField` type), which include **electric (E)** and **magnetic (B)** components. The solver also incorporates a **source term** (`SourceField`), which represents the **current d...`

#### num_007 - What are the numerical tradeoffs between the FFT and CG Poisson solvers in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: FFT Poisson is fast and direct on structured uniform grids with compatible BCs but less flexible; CG/PCG is iterative and may be slower/convergence-limited, but it is more flexible for alternative discretizations, BCs, and preconditioning.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.17`
- Local answer excerpt: `Answer: The retrieved context is insufficient to answer the question regarding numerical trade-offs between FFT and CG Poisson solvers. The provided chunks cover the implementation details of the Conjugate Gradient (CG) method for sparse systems and the mul...`

### Build And Install

#### build_001 - Which third-party libraries does IPPL depend on, and what are they used for?

- Verdict: **Incorrect**
- Codex reference answer: Core third-party dependencies are MPI for distributed communication, Kokkos for performance portability, heFFTe for FFT backends/plans, FFTW/CuFFT as optional FFT backends, and GoogleTest for tests.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.12`
- Local answer excerpt: `Answer: IPPL depends on **MPI** to initialize its environment and communicators (specifically the `mpi::Environment` and `mpi::Communicator` types). It also relies on **Kokkos** via the `Kokkos_Core.hpp` header to manage the runtime environment necessary fo...`

#### build_002 - What C++ standard does IPPL require, and why?

- Verdict: **Incorrect**
- Codex reference answer: IPPL requires C++20, as stated in the README badge and the installation examples/configuration flags.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.20`
- Local answer excerpt: `Answer: The provided context does not specify which C++ standard IPPL requires. Evidence: - data/raw/ippl/src/Ippl.cpp : initialize — describes the initialization of MPI environments, log levels, and timer settings. - data/raw/ippl/src/Manager/PicManager.h ...`

#### build_003 - How is IPPL configured with CMake to enable a GPU build?

- Verdict: **Incorrect**
- Codex reference answer: GPU builds are enabled through CMake options like `IPPL_PLATFORMS=CUDA` or `IPPL_PLATFORMS="HIP;OPENMP"` plus matching Kokkos/architecture/backend flags (`Kokkos_ARCH_*`, `CMAKE_CUDA_ARCHITECTURES`, `Kokkos_ENABLE_HIP`, `Heffte_ENABLE_ROCM`, etc.).
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.13`
- Local answer excerpt: `Answer: The retrieved context does not contain information regarding CMake configurations for enabling a GPU build. The available content covers the `ippl::initialize` function for system initialization, the `FFTBase` class and various Fourier transform imp...`

#### build_004 - What options does INSTALLATION.md describe for configuring Kokkos for IPPL?

- Verdict: **Partial**
- Codex reference answer: `INSTALLATION.md` describes Kokkos version selection plus backend/architecture options used with IPPL builds, including CUDA and HIP/OpenMP examples and `IPPL_PLATFORMS` combinations.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.24`
- Local answer excerpt: `Answer: The `INSTALLATION.md` file specifies the `Kokkos_VERSION` option for configuring Kokkos, which has a default value of `4.5.00`. It describes that this variable can be overridden by setting it to any git tag or SHA (for example, `git.4.7.01`) to sele...`

#### build_005 - How do I install IPPL on the EULER cluster according to the documentation?

- Verdict: **Incorrect**
- Codex reference answer: The EULER install guide says to connect with VPN/SSH, switch to the new software stack, purge modules, load GCC/CMake/CUDA/OpenMPI, clone the repo, configure a build, compile, and test on an interactive node.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.10`
- Local answer excerpt: `Answer: The provided context is insufficient to answer how to install IPPL on the EULER cluster. The retrieved chunks cover internal library components including system initialization (`ippl::initialize`), finite element data structures and types (`Element`...`

### Testing And Workflow

#### test_002 - What naming conventions does WORKFLOW.md require for variables, constants, and member variables?

- Verdict: **Correct**
- Codex reference answer: `WORKFLOW.md` requires camelCase variables, CAPITAL_CASE compile-time constants, and member names suffixed with `_m`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.69`
- Local answer excerpt: `Answer: WORKFLOW.md specifies that variables must use camel casing (e.g., `myVariable`), compile-time constants should use capital casing (e.g., `MY_CONSTANT`), and member variables must be suffixed with `_m` (e.g., `memberVar_m`). Evidence: - data/raw/ippl...`

#### test_003 - When should code use Kokkos::sqrt versus std::sqrt according to WORKFLOW.md?

- Verdict: **Correct**
- Codex reference answer: Use `std::sqrt` in host-only code, and `Kokkos::sqrt` in device-capable code such as `KOKKOS_INLINE_FUNCTION` kernels.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.75`
- Local answer excerpt: `Answer: Code should use `std::sqrt` for host-only code. It should use `Kokkos::sqrt` for device-code or any code that might be run on a device, such as functions marked with `KOKKOS_INLINE_FUNCTION`, to ensure performance and portability on GPUs. Evidence: ...`

#### test_004 - How does IPPL profile MPI calls using mpiP?

- Verdict: **Incorrect**
- Codex reference answer: IPPL profiles MPI calls with mpiP by preloading `libmpiP.so`, optionally setting `MPIP` flags, then parsing the produced `.mpiP` output with the bundled `scripts/mpiP.py`.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.19`
- Local answer excerpt: `Answer: The provided context does not contain information regarding how IPPL profiles MPI calls using mpiP. The retrieved chunks cover core utility functions like initialization and error handling (Ippl.cpp, Ippl.h), communication management classes such as...`

#### test_005 - What does the SLURM job template for Gwendolen in the README look like?

- Verdict: **Incorrect**
- Codex reference answer: The README does include a Gwendolen SLURM template showing the `gmerlin6` cluster, `gwendolen` partition, GPU count, and `srun ./<your_executable> <args> --kokkos-map-device-id-by=mpi_rank`.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.21`
- Local answer excerpt: `Answer: The provided context does not contain information regarding a SLURM job template for Gwendolen. The retrieved chunks cover example SLURM scripts available for the PSI computing cluster, the logic and Python-based architecture used to process test re...`
