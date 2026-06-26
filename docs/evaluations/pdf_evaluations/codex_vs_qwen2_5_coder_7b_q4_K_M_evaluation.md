# Codex GPT-5.4 Reference vs Qwen2.5-Coder 7B Evaluation

Generated: 2026-06-19 12:29:14 UTC

## Goal

This report evaluates the saved Qwen2.5-Coder 7B RAG answer run in `docs/evaluations/answers/eval_v2_qwen2.5-7B-q4_K_M.json` against the Codex GPT-5.4 reference answers stored in `docs/evaluations/eval_answers_v2.json`. The format follows the older `codex_vs_local_llm_evaluation_20260423` report style, but the reference side here is the curated Codex V2 answer file rather than a new source-reading pass.

## Test Environment

### Codex Reference Side

- Model: `GPT-5.4` (Codex reference answers)
- Reference file: `docs/evaluations/eval_answers_v2.json`
- Question set: `docs/evaluations/eval_questions_v2.json`
- Evaluation basis: semantic comparison against the Codex reference answer for each question

### Local LLM Side

- Host: `merlin-g-100.psi.ch`
- Job / partition: `353389` on `gwendolen`
- Answer model: `qwen2.5-coder:7b-instruct-q4_K_M`
- Chunk explanation model: `qwen2.5-coder:32b`
- File / module / call-chain models: `qwen2.5-coder:32b-instruct-q4_K_M`, `qwen2.5-coder:32b-instruct-q4_K_M`, `qwen2.5-coder:32b-instruct-q4_K_M`
- Parser: `tree_sitter`
- Question count: `100`
- Answer prompt mode: `retrieval_answer_v2`
- Mean answer latency: `3.54s`
- Median answer latency: `3.37s`

### Retrieval Configuration Used by the Saved Run

- Candidate k: `20`
- Supplementary k: `3`
- Supplementary candidate k: `10`
- Vector store chunk count: `4441`
- Manifest embedding backend/model: `ollama` / `nomic-embed-text`

## Important Caveat

The per-question verdicts are a structured comparison against the Codex reference answers, not an independent re-reading of every IPPL source file. A question is marked Correct when the Qwen answer captures the central facts of the Codex reference; Partial when it contains relevant signal but misses important scope or implementation detail; and Incorrect when it abstains, points to the wrong subsystem, or omits the core reference answer.

Because the reference answers are intentionally concise, the grading emphasizes the main technical nouns, implementation locations, and algorithmic steps rather than exact wording. Ambiguous cases were treated conservatively as Partial rather than Correct.

## Overall Result

| Metric | Value |
|---|---:|
| Questions | 100 |
| Correct | 59 |
| Partial | 26 |
| Incorrect | 15 |
| Average score (`Correct=1`, `Partial=0.5`, `Incorrect=0`) | 0.720 |

## Main Findings

- Strongest areas: Class Responsibility, Data Flow. These are mostly questions where the retrieved answer can be anchored to one well-described class, header, implementation file, or usage pattern.
- Weakest areas: Build And Install, Numerical Meaning. These questions require cross-file synthesis, precise implementation-location recovery, or careful numerical interpretation, where the 7B answer model often latched onto nearby but incomplete context.
- The run is fast relative to larger models: mean latency is only a few seconds per answer, but speed comes with more retrieval-context misinterpretation.
- The most serious misses are wrong-neighborhood answers: for example, some questions about Field boundary conditions, MPI setup, or Maxwell/FDTD routines are answered from adjacent but incorrect subsystems.
- The 7B model often produces usable summaries for single-file or single-class questions, but it struggles to retain exact scope when the Codex reference requires multiple files, transform variants, or detailed algorithm steps.

## Category Breakdown

| Category | Questions | Correct | Partial | Incorrect | Avg score |
|---|---:|---:|---:|---:|---:|
| File Purpose | 13 | 6 | 5 | 2 | 0.654 |
| Definition Location | 15 | 10 | 2 | 3 | 0.733 |
| Class Responsibility | 13 | 9 | 4 | 0 | 0.846 |
| Algorithm | 12 | 5 | 6 | 1 | 0.667 |
| Data Flow | 9 | 7 | 1 | 1 | 0.833 |
| Api Usage | 12 | 10 | 0 | 2 | 0.833 |
| Parallelism And Kokkos | 9 | 4 | 3 | 2 | 0.611 |
| Boundary And Halo | 5 | 2 | 3 | 0 | 0.700 |
| Numerical Meaning | 3 | 1 | 1 | 1 | 0.500 |
| Build And Install | 5 | 2 | 1 | 2 | 0.500 |
| Testing And Workflow | 4 | 3 | 0 | 1 | 0.750 |

## Detailed Per-Question Evaluation

### File Purpose

#### file_001 - What does Ippl.h do?

- Verdict: **Correct**
- Codex reference answer: Declares the top-level IPPL runtime handles (`Comm`, `Env`, `Info`, `Warn`, `Error`) and the lifecycle wrappers `initialize`, `finalize`, `fence`, and `abort`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.29`
- Local answer excerpt: `**Answer:** The `Ippl.h` header file serves as a central header for managing application initialization, termination, communication, and error handling within the IPPL framework. It includes essential functions like `ippl::abort`, `ippl::initialize`, and `i...`

#### file_002 - What is the purpose of Ippl.cpp?

- Verdict: **Incorrect**
- Codex reference answer: Implements runtime setup/teardown: command-line option parsing, MPI communicator/environment creation, logger setup, Kokkos init/finalize, and abort/fence helpers.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.21`
- Local answer excerpt: `Answer: The `Ippl.cpp` file contains essential utility functions for managing initialization, finalization, and error handling within the IPPL (Integrated Parallel Primitives Library) framework. Key functions include `abort`, `checkOption`, `fence`, `finali...`

#### file_003 - What does FFT.hpp implement?

- Verdict: **Correct**
- Codex reference answer: Implements `FFTBase` setup plus the FFT specialization family for complex/real, sine, cosine, and cosine-I transforms on IPPL fields via heFFTe.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.35`
- Local answer excerpt: `**Answer:** The `FFT.hpp` file defines a base class (`FFTBase<Field, FFT, Backend, T>`) and several specializations (`RCTransform`, `CCTransform`, etc.) for Fast Fourier Transform (FFT) operations within the IPPL namespace. It includes methods such as `doma...`

#### file_004 - What is BareField.h responsible for?

- Verdict: **Partial**
- Codex reference answer: Defines the core distributed field container: Kokkos-backed storage, owned/allocated domains, field layout access, halo exchange hooks, and expression-style assignment.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.35`
- Local answer excerpt: `Answer: The `BareField.h` file defines the `ippl::BareField` class, which represents a fundamental abstraction for scientific fields within the IPPL framework. It includes methods to access properties such as allocation status, communicator, domain, halo, h...`

#### file_005 - What does Field.h add on top of BareField?

- Verdict: **Correct**
- Codex reference answer: Adds mesh awareness and boundary-condition management on top of `BareField`, plus volume integral/average helpers.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.44`
- Local answer excerpt: `Answer: The `ippl::Field` class extends the functionality provided by `BareField` by adding boundary conditions management and additional numerical operations. It provides methods for deep copying, volume averaging, and integral calculations over specified ...`

#### file_006 - What role does HaloCells.h play in IPPL?

- Verdict: **Partial**
- Codex reference answer: Defines the halo-exchange machinery for fields: pack/unpack, boundary exchange, and periodic handling for ghost cells.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.27`
- Local answer excerpt: `**Answer:** The `HaloCells` class and related structs within the IPPL library manage halo cells for field data, facilitating inter-process communication (IPC) in parallel computations. **Evidence:** - src/Field/HaloCells.h : HaloCells — manages ghost-region...`

#### file_007 - What is the purpose of FieldLayout.h?

- Verdict: **Incorrect**
- Codex reference answer: Defines how a global `NDIndex` domain is partitioned across MPI ranks, including local subdomains, neighbors, and communication ranges.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.07`
- Local answer excerpt: `**Answer:** The `FieldLayout.h` file defines the `FieldLayout<Dim>` class template and related helper functions within the `ippl` namespace. This class appears to manage field layouts and their associated domain decompositions in a scientific computing cont...`

#### file_008 - What does ParticleBase.h define?

- Verdict: **Partial**
- Codex reference answer: Defines the generic particle container base class with positions, optional IDs, registered attributes, and a particle layout that controls migration.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.38`
- Local answer excerpt: `**Answer:** The `ParticleBase.h` header file defines a foundational structure for managing particle data within the IPPL framework. It provides a class template `ParticleBase<PLayout, IP...>` that manages particles with specified layout and additional prope...`

#### file_009 - What is the purpose of ParticleSpatialLayout.h?

- Verdict: **Partial**
- Codex reference answer: Defines the spatial particle layout that decides ownership by region and migrates particles to the correct rank after motion.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The `ParticleSpatialLayout` class manages spatial layout and communication regions for particles within the IPPL library. It includes methods to configure, update, and retrieve spatial information necessary for particle distribution and neighbor int...`

#### file_010 - What does ParticleAttrib.h implement?

- Verdict: **Partial**
- Codex reference answer: Implements the `ParticleAttrib` storage object: a Kokkos-view-backed particle attribute with resize, serialization, and mirror/access helpers.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.11`
- Local answer excerpt: `**Answer:** The `ParticleAttrib.h` header file defines a class template `ippl::ParticleAttrib<T, Properties...>` for managing particle attributes in simulations. It provides methods for creating, destroying, manipulating, and communicating these attributes ...`

#### file_011 - What is UniformCartesian.h for?

- Verdict: **Correct**
- Codex reference answer: Defines the uniform Cartesian mesh class with spacing, origin, cell volume, total mesh volume, and vertex-position helpers.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.46`
- Local answer excerpt: `Answer: The `UniformCartesian.h` file defines the `UniformCartesian` class family within the `ippl::Meshes` namespace, specializing uniform Cartesian meshes. It provides methods for handling mesh properties such as vertex positions, cell volumes, and mesh s...`

#### file_012 - What does OrthogonalRecursiveBisection.h do?

- Verdict: **Correct**
- Codex reference answer: Declares the orthogonal recursive bisection domain-decomposition/load-balancing class and its cut/median/repartition helpers.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.47`
- Local answer excerpt: `Answer: The `OrthogonalRecursiveBisection.h` file defines a class named `ippl::OrthogonalRecursiveBisection` used for decomposing computational domains using an orthogonal recursive bisection algorithm. It includes methods like `cutDomain`, `findCutAxis`, `...`

#### file_013 - What is the purpose of CIC.h in the Interpolation subsystem?

- Verdict: **Correct**
- Codex reference answer: Declares the first-order cloud-in-cell interpolation helpers for scatter/gather between particles and grid fields.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.44`
- Local answer excerpt: `**Answer:** The file `CIC.h` defines function declarations within the `ippl::detail` namespace that handle interpolation operations, specifically for Cloud-in-Cell (CIC) methods. These functions include `scatterToField`, `scatterToPoint`, `gatherFromField`,...`

### Definition Location

#### loc_001 - Where is FFT initialization implemented in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: FFT initialization lives in `src/FFT/FFT.hpp`, especially `FFTBase` construction/setup and the transform-specific constructors that build the heFFTe plans.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.10`
- Local answer excerpt: `**Answer:** FFT initialization is not directly implemented in IPPL. The codebase does not include explicit support for FFTs. **Evidence:** - No chunks mention "FFT" or any related functions/classes. - The `initialize` function in `Ippl.cpp` handles general ...`

#### loc_002 - Where does IPPL set up the MPI environment?

- Verdict: **Partial**
- Codex reference answer: IPPL sets up MPI in `src/Ippl.cpp::initialize()` by constructing `mpi::Environment` and `mpi::Communicator`; the low-level `MPI_Init` check/call is in `src/Communicate/Environment.cpp`.
- Comparison: The answer names a relevant location but is thin or incomplete.
- Reference-token coverage: `0.19`
- Local answer excerpt: `Answer: IPPL sets up the MPI environment through the `setup` method of the `FFTBase` class. This is evident from the configuration and initialization steps within the constructor and setup method implementations found in `FFT.hpp`. Evidence: - data/raw/ippl...`

#### loc_003 - Where is Kokkos initialized and finalized inside IPPL?

- Verdict: **Correct**
- Codex reference answer: Kokkos is initialized and finalized directly in `src/Ippl.cpp` inside `ippl::initialize()` and `ippl::finalize()`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.67`
- Local answer excerpt: `**Answer:** Kokkos initialization occurs within `ippl::initialize` located in `Ippl.cpp`. The function `initialize` is responsible for setting up the Kokkos environment. Finalization of Kokkos happens in `ippl::finalize`, also defined in `Ippl.cpp`. **Evide...`

#### loc_004 - Where is the orthogonal recursive bisection load balancer implemented?

- Verdict: **Correct**
- Codex reference answer: The ORB load balancer is implemented in `src/Decomposition/OrthogonalRecursiveBisection.hpp` with declarations in the matching header.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.64`
- Local answer excerpt: `Answer: The orthogonal recursive bisection load balancer is implemented in the `OrthogonalRecursiveBisection` class within the `Decomposition` module. The implementation details are found in the `src/Decomposition/OrthogonalRecursiveBisection.h` file. Evide...`

#### loc_005 - Where are boundary conditions applied to a Field?

- Verdict: **Partial**
- Codex reference answer: Field BCs are attached in `Field::setFieldBC()` and actually applied through `BConds::apply()` and the concrete face classes in `BcTypes.hpp`.
- Comparison: The answer names a relevant location but is thin or incomplete.
- Reference-token coverage: `0.12`
- Local answer excerpt: `Answer: The second_order_mur_boundary_conditions struct is responsible for applying second-order Mur absorbing boundary conditions to all boundaries of a 3D computational domain. This struct uses Kokkos library constructs like Kokkos::parallel_for for paral...`

#### loc_006 - Where is the CIC (cloud-in-cell) scatter implemented?

- Verdict: **Correct**
- Codex reference answer: CIC scatter is implemented in `src/Interpolation/CIC.hpp`, primarily `scatterToPoint()` and `scatterToField()`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.73`
- Local answer excerpt: `Answer: The CIC (Cloud-in-Cell) scatter implementation is found in `ippl::detail::scatterToField` within the file `data/raw/ippl/src/Interpolation/CIC.hpp`. The function uses `ippl::mpi::Communicator::scatter` for distributing data from one process to multi...`

#### loc_007 - Where is the CIC gather implemented?

- Verdict: **Incorrect**
- Codex reference answer: CIC gather is implemented in `src/Interpolation/CIC.hpp`, primarily `gatherFromPoint()` and `gatherFromField()`.
- Comparison: The answer cites a different implementation location than the Codex reference.
- Reference-token coverage: `0.45`
- Local answer excerpt: `**Answer:** CIC gather is not explicitly implemented in the provided context. The closest related symbol mentioned is `gather`, which is a function defined within the `ParticleAttrib<T, Properties...>` class template in the IPPL codebase. However, its role ...`

#### loc_008 - Where is halo exchange for BareField implemented?

- Verdict: **Correct**
- Codex reference answer: Halo exchange for `BareField` is surfaced in `src/Field/BareField.hpp` and actually performed in `src/Field/HaloCells.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.69`
- Local answer excerpt: `Answer: Halo exchange for BareField is implemented in the `ippl::detail::HaloCells` class. This class manages and manipulates guard/ghost cells for fields in a computational domain, handling the communication of halo data between different parts of a decomp...`

#### loc_009 - Where are the FFT-based open-boundary Poisson solver routines defined?

- Verdict: **Correct**
- Codex reference answer: The FFT open-boundary Poisson routines are defined in `src/PoissonSolvers/FFTOpenPoissonSolver.h` and `src/PoissonSolvers/FFTOpenPoissonSolver.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.83`
- Local answer excerpt: `**Answer:** The FFT-based open-boundary Poisson solver routines are defined in the `FFTOpenPoissonSolver.hpp` file within the `ippl::FFTOpenPoissonSolver<FieldLHS, FieldRHS>` class template. This class provides methods for solving the Poisson equation using...`

#### loc_010 - Where is the conjugate gradient solver algorithm implemented?

- Verdict: **Correct**
- Codex reference answer: The CG/PCG algorithm implementation is in `src/LinearSolvers/PCG.h`; the Poisson wrapper that instantiates it is `src/PoissonSolvers/PoissonCG.h`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.67`
- Local answer excerpt: `Answer: The conjugate gradient solver algorithm is implemented in the `ippl::PoissonCG::solve` method within the `PoissonSolvers/PoissonCG.h` file. The class uses a PCG (Preconditioned Conjugate Gradient) solver, which is defined and used in the `LinearSolv...`

#### loc_011 - Where is the FEM Poisson solver implemented?

- Verdict: **Correct**
- Codex reference answer: The FEM Poisson solver is implemented in `src/PoissonSolvers/FEMPoissonSolver.h`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.83`
- Local answer excerpt: `Answer: The `FEMPoissonSolver` class implements a finite element method based solution to the Poisson equation. It is located in the file `data/raw/ippl/src/PoissonSolvers/FEMPoissonSolver.h`. Evidence: - data/raw/ippl/src/PoissonSolvers/FEMPoissonSolver.h ...`

#### loc_012 - Where is the FDTD Maxwell solver base class defined?

- Verdict: **Incorrect**
- Codex reference answer: The FDTD Maxwell solver base class is defined in `src/MaxwellSolvers/FDTDSolverBase.h` with implementation in `FDTDSolverBase.hpp`.
- Comparison: The answer cites a different implementation location than the Codex reference.
- Reference-token coverage: `0.60`
- Local answer excerpt: `Answer: The FDTD Maxwell solver base class is defined in `FieldSolverBase.h` within the `ippl::Manager` namespace. Evidence: - data/raw/ippl/src/Manager/FieldSolverBase.h : FieldSolverBase — abstract base class for field solvers providing common functionali...`

#### loc_013 - Where is the LagrangeSpace class defined?

- Verdict: **Correct**
- Codex reference answer: The `LagrangeSpace` class is defined in `src/FEM/LagrangeSpace.h` with methods implemented in `src/FEM/LagrangeSpace.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.78`
- Local answer excerpt: `Answer: The LagrangeSpace class is defined in the file `LagrangeSpace.h` within the `FEM` module of the IPPL codebase. It represents a Lagrange space for finite element methods on a structured grid. Evidence: - data/raw/ippl/src/FEM/LagrangeSpace.h : Lagran...`

#### loc_014 - Where is the particle update routine (that moves particles across ranks) implemented?

- Verdict: **Correct**
- Codex reference answer: Particle migration between ranks is implemented in `ParticleSpatialLayout::update()` in `src/Particle/ParticleSpatialLayout.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.70`
- Local answer excerpt: `Answer: The particle update routine that moves particles across ranks is primarily implemented in `data/raw/ippl/src/Particle/ParticleSpatialLayout.hpp`. Specifically, this functionality is encapsulated in the `update` method of the `ippl::ParticleSpatialLa...`

#### loc_015 - Where are IPPL timers defined?

- Verdict: **Correct**
- Codex reference answer: IPPL timers are defined by the singleton timing layer in `src/Utility/IpplTimings.h/.cpp`, not just the low-level `Timer` helper.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.44`
- Local answer excerpt: `Answer: IPPL timers are primarily defined and managed through several classes and functions. The `IpplTimerInfo` class is used to store individual timer information, including its name, wall time, and whether it is running. The `Timing` struct contains meth...`

### Class Responsibility

#### cls_001 - What is the main responsibility of the BareField class?

- Verdict: **Correct**
- Codex reference answer: `BareField` is the core distributed field storage class: it owns the data view, domain metadata, layout link, and halo operations.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.56`
- Local answer excerpt: `Answer: The `BareField` class is a fundamental abstraction for representing fields in scientific computations within the IPPL framework. It includes methods to access various properties of the field such as allocation status, communicator, domain, halo, hos...`

#### cls_002 - What is the main responsibility of the Field class compared to BareField?

- Verdict: **Correct**
- Codex reference answer: `Field` extends `BareField` with a mesh, boundary-condition container, and mesh-aware integral/average semantics.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.31`
- Local answer excerpt: `Answer: The `Field` class likely serves as a higher-level abstraction that builds on top of the lower-level `BareField`. It may provide additional functionalities such as boundary condition handling, field operations, and possibly more complex numerical alg...`

#### cls_003 - What does the FieldLayout class do and what are its main template parameters?

- Verdict: **Correct**
- Codex reference answer: `FieldLayout<Dim>` distributes a global `NDIndex<Dim>` over ranks and stores local domains, neighbors, and communication ranges; its only template parameter is `Dim`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.32`
- Local answer excerpt: `**Answer:** The `FieldLayout` class manages field distribution and domain details across computational domains. It is a template class `FieldLayout<Dim>`, where `Dim` represents the dimensionality of the field layout. **Evidence:** - `src/FieldLayout/FieldL...`

#### cls_004 - What is the purpose of the ParticleBase class and how is it meant to be used?

- Verdict: **Correct**
- Codex reference answer: `ParticleBase` is the user-extensible base container for particles; derived classes add attributes and register them so layout-driven migration can move them.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.30`
- Local answer excerpt: `**Answer:** The `ParticleBase` class serves as a foundational abstraction for managing particle data within the IPPL (Integrated Particle Physics Library) framework. It provides methods to handle attributes, layout, and local/global particle counts. The pri...`

#### cls_005 - What does the ParticleSpatialLayout class do?

- Verdict: **Correct**
- Codex reference answer: `ParticleSpatialLayout` decides which spatial region/rank owns each particle and performs the migration/update workflow after particles move.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.33`
- Local answer excerpt: `Answer: The `ParticleSpatialLayout` class manages spatial layout and communication regions for particles within the IPPL (Integrated Particle Physics Library). It defines methods to configure, update, and retrieve spatial information necessary for particle ...`

#### cls_006 - What is the responsibility of UniformCartesian?

- Verdict: **Correct**
- Codex reference answer: `UniformCartesian` represents a uniform Cartesian mesh and exposes spacing/origin/volume and vertex-position geometry queries.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The `UniformCartesian` class defines a uniform Cartesian mesh for simulations, providing functionalities such as initializing the mesh, setting and retrieving mesh spacing, calculating cell volumes, and determining vertex positions. Evidence: - src/...`

#### cls_007 - What does the Mesh base class define?

- Verdict: **Partial**
- Codex reference answer: `Mesh` is the abstract base interface for meshes: origin, grid size, spacing, vertex positions, and volume queries.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.20`
- Local answer excerpt: `Answer: The Mesh base class defines a framework for representing mesh-based quantities in particle simulations. It includes functionality for defining the spatial domain, managing grid points, and handling boundary conditions. Evidence: - src/Field/BareFiel...`

#### cls_008 - What is the responsibility of the Communicator class in ippl::mpi?

- Verdict: **Partial**
- Codex reference answer: `ippl::mpi::Communicator` wraps MPI point-to-point, collectives, tag handling, and managed communication buffers.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.23`
- Local answer excerpt: `Answer: The Communicator class in ippl::mpi manages MPI-based communication within the IPPL library. It provides methods for managing MPI communicators such as barriers, rank retrieval, and size determination. Evidence: - data/raw/ippl/src/Communicate/Commu...`

#### cls_009 - What is the role of the Environment class in ippl::mpi?

- Verdict: **Correct**
- Codex reference answer: `ippl::mpi::Environment` manages MPI environment lifetime checks/teardown and provides an abort hook.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.30`
- Local answer excerpt: `Answer: The `Environment` class in `ippl::mpi` manages MPI environments within the IPPL library. It includes constructors, destructors, and utility functions like `initialized` and `finalized`. Evidence: - data/raw/ippl/src/Communicate/Environment.cpp : Env...`

#### cls_010 - What does the Archive class do in the Communicate module?

- Verdict: **Partial**
- Codex reference answer: `Archive` serializes and deserializes Kokkos views and vector-valued views into raw byte buffers for MPI transfer.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.08`
- Local answer excerpt: `Answer: The `Archive` class in the `Communicate` module is likely used for managing and serializing data to be exchanged between different processes or nodes during parallel simulations. It probably includes methods for packing and unpacking data structures...`

#### cls_011 - What is the role of the BConds class?

- Verdict: **Correct**
- Codex reference answer: `BConds` is the container of boundary-condition faces and orchestrates neighbor discovery, BC application, and ghost-to-physical assignment.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.44`
- Local answer excerpt: `Answer: The `BConds` class defines boundary condition objects and manages their application to fields within the IPPL (Integrated Plasma Physics Library). It includes methods for finding neighbors subject to boundary conditions, applying these conditions, a...`

#### cls_012 - What is the role of the BaseManager class?

- Verdict: **Correct**
- Codex reference answer: `BaseManager` provides the simulation loop skeleton: `pre_run`, `pre_step`, `advance`, `post_step`, and `run(nt)`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.73`
- Local answer excerpt: `**Answer:** The `BaseManager` class defines essential lifecycle methods such as `run`, `pre_run`, `post_step`, and `pre_step`. It acts as a base class for managing simulation workflows within IPPL. **Evidence:** - src/Manager/BaseManager.h : BaseManager — c...`

#### cls_013 - What does the Index class represent and what operations does it support?

- Verdict: **Partial**
- Codex reference answer: `Index` represents a regular strided integer range/slice and supports range-style arithmetic and comparison operations used in domain descriptions.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.24`
- Local answer excerpt: `**Answer:** The Index class represents a data structure used for indexing purposes in scientific computing simulations. It supports operations such as creating, accessing, and manipulating indices to efficiently manage data structures. **Evidence:** - src/F...`

### Algorithm

#### alg_001 - How does the FFT-based open-boundary Poisson solver compute the electrostatic potential?

- Verdict: **Partial**
- Codex reference answer: The FFT open-boundary solver embeds/extends the RHS onto larger domains, FFTs both the density and a precomputed Green's function, multiplies in Fourier space, inverse transforms, and optionally computes gradients/Hessians.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.41`
- Local answer excerpt: `**Answer:** The FFT-based open-boundary Poisson solver computes the electrostatic potential by solving the Poisson equation using Fast Fourier Transform (FFT) techniques. It involves initializing fields, setting right-hand sides, and performing the solve op...`

#### alg_002 - How does the FFT-based periodic Poisson solver work in IPPL?

- Verdict: **Correct**
- Codex reference answer: The periodic FFT solver FFTs the charge density, divides each Fourier mode by `|k|^2` (with the zero mode handled separately), then inverse transforms; gradients are computed by multiplying by `ik/|k|^2` before the inverse FFT.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.45`
- Local answer excerpt: `Answer: The FFT-based periodic Poisson solver in IPPL solves the periodic Poisson problem using Fast Fourier Transforms (FFTs). It computes the solution to the equation \( \nabla^2 \phi = -\rho \) where \(\phi\) is the electrostatic potential and \(\rho\) i...`

#### alg_003 - How does the truncated Green periodic Poisson solver differ from the standard periodic one?

- Verdict: **Correct**
- Codex reference answer: The truncated-Green periodic solver replaces the simple `1/|k|^2` kernel with the FFT of a truncated/erf-smoothed Green's function `forceConstant * erf(alpha r) / r`, then follows the same transform-multiply-inverse pattern.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.42`
- Local answer excerpt: `### Answer: The truncated Green periodic Poisson solver differs from the standard periodic one by incorporating a truncated Green's function to handle long-range interactions more efficiently. The standard approach likely solves the Poisson equation directl...`

#### alg_004 - How does IPPL's CG solver iterate in the PCG.h implementation?

- Verdict: **Partial**
- Codex reference answer: In `PCG.h`, the CG iteration forms residual/direction fields, applies the operator, computes `alpha` and `beta` from inner products, updates the solution/residual/direction, and stops on tolerance or iteration count; the preconditioned variant inserts `M^{-1}` applications on the residual.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.23`
- Local answer excerpt: `Answer: The `PCG.h` file implements the Conjugate Gradient (CG) solver within the `ippl::PCG` class. The CG method iteratively improves an approximate solution to a linear system of equations \(-\nabla^2 u = f\) until it converges to a sufficiently accurate...`

#### alg_005 - How is cloud-in-cell interpolation performed in IPPL (both scatter and gather directions)?

- Verdict: **Partial**
- Codex reference answer: CIC computes lower/upper weights per axis, scatters with atomic adds to the `2^Dim` neighboring grid points, and gathers by summing the same weighted stencil back to particles.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.26`
- Local answer excerpt: `Answer: Cloud-in-cell (CIC) interpolation in IPPL is used for distributing particle attributes onto a computational grid or collecting data from a field into particles. This process involves mapping physical positions of particles to nearest grid points and...`

#### alg_006 - How does the standard FDTD solver advance the electromagnetic field in time?

- Verdict: **Correct**
- Codex reference answer: The standard FDTD solver advances the source-like field with a second-order finite-difference update using the previous and current time levels plus neighboring cells and source terms, then fills halos and reapplies BCs.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.42`
- Local answer excerpt: `Answer: The standard FDTD solver advances the electromagnetic field by updating the electric (`E`) and magnetic (`B`) fields over time using a finite-difference method. The `step()` method is overridden in derived classes to implement the specific update sc...`

#### alg_007 - How does the LagrangeSpace class evaluate degrees of freedom per element?

- Verdict: **Incorrect**
- Codex reference answer: `LagrangeSpace` evaluates element DOFs by mapping local element indices to global DOF indices, then evaluates order-1 reference-element shape functions and gradients on those local DOFs.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.32`
- Local answer excerpt: `Answer: The `LagrangeSpace` class evaluates degrees of freedom per element through its method `getLagrangeNumElementDOFs`. This method calculates the number of degrees of freedom for a given polynomial order and spatial dimension using template parameters. ...`

#### alg_008 - How is Gauss-Jacobi quadrature implemented and used in IPPL FEM?

- Verdict: **Correct**
- Codex reference answer: Gauss-Jacobi quadrature computes nodes/weights by Newton iteration on Jacobi polynomial roots, starting from Chebyshev or LehrFEM-style guesses, and uses the resulting rule on reference elements in FEM.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.50`
- Local answer excerpt: `**Answer:** Gauss-Jacobi quadrature in IPPL FEM is implemented through the `GaussJacobiQuadrature` class, which inherits from the base `Quadrature` class. This class computes quadrature nodes and weights specifically tailored for Gauss-Jacobi polynomials. T...`

#### alg_009 - How does the orthogonal recursive bisection decide where to cut the domain?

- Verdict: **Partial**
- Codex reference answer: ORB chooses a cut axis from the domain geometry and then finds a weight-balanced cut/median so recursive splits distribute load more evenly.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.32`
- Local answer excerpt: `**Answer:** The orthogonal recursive bisection decides where to cut the domain by finding the axis along which to perform the next cut. This is done by identifying the longest axis of the field layout. The method `findCutAxis` uses iterators and index opera...`

#### alg_010 - How does inverse transform sampling generate particles from a given distribution in IPPL?

- Verdict: **Partial**
- Codex reference answer: Inverse transform sampling maps uniform random values in CDF space to samples by estimating the inverse and refining it with Newton-Raphson, dimension by dimension.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.35`
- Local answer excerpt: `**Answer:** Inverse transform sampling in IPPL generates particles by mapping uniformly distributed random numbers to samples that follow a specified target probability distribution. The `Distribution` class encapsulates the PDF, CDF, and estimate function ...`

#### alg_011 - How does the FFT class interface with heFFTe to perform complex-to-complex and real-to-complex transforms?

- Verdict: **Partial**
- Codex reference answer: The FFT layer builds heFFTe boxes/plans in `setup()`, copies IPPL field data into the required views/subviews, calls heFFTe forward/backward transforms, and copies results back for CC/RC/DST/DCT variants.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.23`
- Local answer excerpt: `### Answer: The `FFT` class interfaces with `heFFTe` through its constructor and member functions to set up and perform Fast Fourier Transforms (FFTs). The `FFT` class is parameterized with specific transform types (`Cos1Transform`, `CosTransform`, etc.) an...`

#### alg_012 - How does IPPL's preconditioned CG use the preconditioner defined in Preconditioner.h?

- Verdict: **Correct**
- Codex reference answer: PCG applies a chosen preconditioner from `Preconditioner.h` to the residual, uses the preconditioned residual in its inner products and direction updates, and iterates until tolerance/max iterations.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.28`
- Local answer excerpt: `Answer: IPPL's preconditioned CG uses a user-defined preconditioner, which is defined in `Preconditioner.h`. The solver sets up and applies this preconditioner during each iteration of the Conjugate Gradient algorithm. Specifically, the `CG::setPrecondition...`

### Data Flow

#### flow_001 - How does charge density flow from particles to the grid in a typical PIC step in IPPL?

- Verdict: **Correct**
- Codex reference answer: In the PIC workflow, particle charges and positions are deposited onto the grid with CIC (`scatter`) or FEM assembly (`assemble_rhs_from_particles`), accumulated into `rho`, and then normalized/background-shifted in the manager before solving.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.35`
- Local answer excerpt: `**Answer:** The process of charge density flowing from particles to the grid involves several key steps. It starts with the `mble_rhs_from_particles` function, which assembles the right-hand side (RHS) for a system using particle data by depositing weighted...`

#### flow_002 - How does the electric field flow from the grid back to particles after a Poisson solve?

- Verdict: **Correct**
- Codex reference answer: After the field solve, the manager gathers the electric field back to particles with CIC `gather(...)` or FEM `interpolate_grad_to_diracs(...)`, storing particle-local `E` values for the push step.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.39`
- Local answer excerpt: `Answer: The electric field flows from the grid back to particles through an additional step after the Poisson solver has computed the electrostatic potential. This involves computing the gradient of the potential to obtain the electric field \( E = -\nabla ...`

#### flow_003 - How are halo cells exchanged between neighboring MPI ranks for a BareField?

- Verdict: **Incorrect**
- Codex reference answer: Halo exchange uses `FieldLayout` neighbor/range metadata to pack field subviews, send/receive them with MPI, unpack into ghost or physical regions, and handle serial-periodic dimensions locally.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.19`
- Local answer excerpt: `**Answer:** The exchange of halo cells between neighboring MPI ranks for a `BareField` is managed through the `ippl::detail::HaloCells` class. This class provides methods such as `exchangeBoundaries`, which facilitates the communication and synchronization ...`

#### flow_004 - How are particles migrated between MPI ranks by ParticleSpatialLayout?

- Verdict: **Correct**
- Codex reference answer: `ParticleSpatialLayout::update()` applies particle BCs, locates destination ranks, advertises receive counts with RMA, sends all registered attributes, destroys invalid local particles, and receives the incoming ones.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.27`
- Local answer excerpt: `**Answer:** The `ParticleSpatialLayout` class is responsible for managing spatial layout and communication regions for particles across different MPI ranks. It provides methods like `locateParticles`, `numberOfSends`, and `updateLayout` to determine particl...`

#### flow_005 - How does FieldLayout decide which index ranges live on which rank?

- Verdict: **Correct**
- Codex reference answer: `FieldLayout` uses the partitioner and the requested parallel/serial decomposition flags to assign each rank a local `NDIndex`, plus neighbor and communication range tables.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.33`
- Local answer excerpt: `Answer: FieldLayout manages how index ranges are distributed across ranks through methods like `addNeighbors`, `calcWidths`, and `findNeighbors`. These methods help in identifying and setting up neighboring relationships between different computational doma...`

#### flow_006 - How is a ParameterList used to configure the FFT and solver classes?

- Verdict: **Correct**
- Codex reference answer: `ParameterList` is merged into FFT and solver objects, then consumed by `setup()/initialize()/solve()` for communication mode, pencil/reorder flags, transform direction, solver type, tolerances, preconditioner settings, and output type.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.36`
- Local answer excerpt: `Answer: A `ParameterList` object is used to configure both FFT and solver classes by passing it as an argument during their construction or initialization. This allows for setting up specific parameters such as tolerance levels, domain sizes, or other simul...`

#### flow_007 - How does data flow through the BaseManager's pre_step / advance / post_step hooks during a simulation?

- Verdict: **Correct**
- Codex reference answer: `BaseManager::run()` executes `pre_step()`, `advance()`, and `post_step()` for each timestep; derived managers use those hooks for deposit/solve/gather, time updates, and output.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.48`
- Local answer excerpt: `**Answer:** The `BaseManager` class in IPPL manages the lifecycle of simulations by providing hooks such as `pre_step`, `advance`, and `post_step`. The data flow through these hooks during a simulation follows this sequence: 1. **Pre-Step Hook**: Before eac...`

#### flow_008 - How does the FEM solver move data between fields and FEMVector representations?

- Verdict: **Correct**
- Codex reference answer: FEM solvers move data by assembling field data into FEM load/stiffness representations (`evaluateLoadVector`, `evaluateAx`, `FEMVector`) and then interpolating the solved field quantities back where needed.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.25`
- Local answer excerpt: `Answer: The FEM solver moves data between fields and FEMVector representations through the use of the `accumulateHalo` method within the `FEMVector<T>` class. This method handles halo exchange operations using MPI for inter-process communication, ensuring t...`

#### flow_009 - How does OrthogonalRecursiveBisection redistribute particles after rebalancing?

- Verdict: **Partial**
- Codex reference answer: After ORB recomputes the decomposition, particle ownership changes are realized by updating the layout/regions and then migrating particles with the usual particle update path.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.22`
- Local answer excerpt: `**Answer:** The `OrthogonalRecursiveBisection` class uses an orthogonal recursive bisection algorithm to redistribute particles after rebalancing. It splits computational domains into subdomains along specified axes and updates the processor assignments acc...`

### Api Usage

#### api_001 - How do I create a 3D Field of doubles in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: A typical 3D field is `Field<double, 3, UniformCartesian<double, 3>, Cell>` constructed from a `UniformCartesian` mesh and a `FieldLayout<3>`.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.21`
- Local answer excerpt: `Answer: To create a 3D Field of doubles in IPPL, you would typically use the `Field` module. The `BareField` class is used to define distributed field data structures, and you can specify the type as `double` for the field elements. Evidence: - src/Field/Ba...`

#### api_002 - How do I construct a UniformCartesian mesh with custom spacing and origin?

- Verdict: **Correct**
- Codex reference answer: Construct the mesh as `UniformCartesian<double, Dim> mesh(domain, hx, origin);` where `hx` is the spacing vector and `origin` is the mesh origin.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.69`
- Local answer excerpt: `Answer: To construct a `UniformCartesian` mesh with custom spacing and origin, you need to instantiate the `UniformCartesian` class from the IPPL library using the provided dimensions (`NDIndex<Dim>`), spacing vector (`vector_type hx`), and origin vector (`...`

#### api_003 - How do I attach a boundary condition (e.g. periodic) to a Field?

- Verdict: **Incorrect**
- Codex reference answer: Create a `BConds<FieldT, Dim>`, assign per-face BC objects such as `PeriodicFace<FieldT>`, then call `field.setFieldBC(bc)`.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.19`
- Local answer excerpt: `Answer: To attach a periodic boundary condition to a `Field` in IPPL, you can use the `setPeriodicBoundaryConditions` method of the `FDTDSolverBase` class template. This method configures the boundary conditions for the fields (`A_n`, `A_nm1`, and `A_np1`) ...`

#### api_004 - How do I define a custom particle class that adds mass and velocity attributes on top of ParticleBase?

- Verdict: **Correct**
- Codex reference answer: Define a class derived from `ParticleBase<ParticleSpatialLayout<...>>`, add `mass` and `velocity` attributes as members, and register them with `addAttribute()` in the constructor.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.41`
- Local answer excerpt: `Answer: To define a custom particle class that adds mass and velocity attributes on top of `ParticleBase`, you need to create a new class derived from `ParticleBase` and add these additional attributes. Evidence: - src/Particle/ParticleBase.hpp : ParticleBa...`

#### api_005 - How do I call ippl::initialize and ippl::finalize in a main program?

- Verdict: **Correct**
- Codex reference answer: Call the free namespace functions `ippl::initialize(argc, argv);` and `ippl::finalize();` from `main`, as shown in the docs/examples.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.60`
- Local answer excerpt: `**Answer:** To call `ippl::initialize` and `ippl::finalize` in a main program, you should include the `Ippl.h` header file. Then, you can call these functions at the beginning and end of your `main` function, respectively. ```cpp #include <Ippl.h> int main(...`

#### api_006 - How do I set up and run a forward FFT on an IPPL Field?

- Verdict: **Correct**
- Codex reference answer: Set up the relevant layouts/fields/parameters, build an `FFT<CCTransform, ...>` or `FFT<RCTransform, ...>` object, and call `transform(FORWARD, ...)` on the field(s).
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.67`
- Local answer excerpt: `Answer: To set up and run a forward FFT on an IPPL `Field`, you need to follow these steps: 1. **Initialize FFT Object**: Create an instance of the `FFT` class template with the appropriate transform type (e.g., `RCTransform`) and field type (e.g., `RealFie...`

#### api_007 - How do I construct an FFTPeriodicPoissonSolver and solve for the potential?

- Verdict: **Correct**
- Codex reference answer: Construct `FFTPeriodicPoissonSolver(lhs, rhs)` (or default construct then set fields/params), ensure the RHS is attached, and call `solve()` to write the potential/gradient outputs.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.57`
- Local answer excerpt: `**Answer:** To construct an `FFTPeriodicPoissonSolver` and solve for the potential, you need to create an instance of the solver class and then call its methods in a specific order. Here's how: 1. **Include Necessary Headers**: Ensure that you include the h...`

#### api_008 - How do I invoke the conjugate gradient Poisson solver on a Field?

- Verdict: **Correct**
- Codex reference answer: Use `PoissonCG<FieldT>` (or the Alpine `FieldSolver` wrapper around it), set its fields/parameters, and call `solve()` so the internal CG/PCG object iterates on the field.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.40`
- Local answer excerpt: `**Answer:** To invoke the conjugate gradient Poisson solver on a Field in IPPL, you need to create an instance of the `PoissonCG` class and use its methods to set up and solve the equation. Here is a step-by-step guide based on the retrieved context: 1. **I...`

#### api_009 - How do I sample particles from a normal distribution using IPPL Random utilities?

- Verdict: **Correct**
- Codex reference answer: For Gaussian draws, IPPL exposes both `randn` convenience generation and the more general `InverseTransformSampling` + `NormalDistribution` path.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.33`
- Local answer excerpt: `Answer: To sample particles from a normal distribution using IPPL Random utilities, you can use the `normal_estimate` struct and the `InverseTransformSampling` class. Here's an example of how to do it: 1. Define a `Distribution` object with the desired mean...`

#### api_010 - How do I register particle attributes with ParticleBase so that they are communicated on migration?

- Verdict: **Correct**
- Codex reference answer: Register each particle attribute with `addAttribute(...)`; migration then serializes and transfers all registered attributes automatically.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.69`
- Local answer excerpt: `Answer: To register particle attributes with `ParticleBase` so that they are communicated on migration, you should define a derived class from `ParticleBase` and use the `addAttribute` method to include your custom attributes. These attributes will then be ...`

#### api_011 - How do I access the MPI rank and size through the IPPL Communicator?

- Verdict: **Correct**
- Codex reference answer: Access rank and size with `ippl::Comm->rank()` and `ippl::Comm->size()` (or the same methods on a `Communicator` object).
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.50`
- Local answer excerpt: `Answer: The IPPL Communicator provides methods to access the MPI rank and size. Specifically: - To get the MPI rank of the current process, use `ippl::mpi::Communicator::rank`. - To get the total number of processes (MPI size), use `ippl::mpi::Communicator:...`

#### api_012 - How do I use IpplTimings to measure a region of code?

- Verdict: **Correct**
- Codex reference answer: Get a timer handle with `IpplTimings::getTimer("name")`, surround the code with `startTimer()` / `stopTimer()`, and print with `IpplTimings::print()`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.79`
- Local answer excerpt: `Answer: To use `IpplTimings` to measure a region of code, follow these steps: 1. **Create a Timer**: Use `IpplTimings::getTimer("timer name")` to create or retrieve a timer object by providing a unique name for your timer. 2. **Start the Timer**: Call `Ippl...`

### Parallelism And Kokkos

#### par_001 - How does IPPL achieve performance portability across CPUs and GPUs?

- Verdict: **Partial**
- Codex reference answer: IPPL gets performance portability by combining Kokkos execution/memory abstractions with MPI and heFFTe, so the same code paths can target CPUs and GPUs.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.35`
- Local answer excerpt: `**Answer:** IPPL achieves performance portability across CPUs and GPUs through its integration with Kokkos. Kokkos is designed to provide a single API for writing kernels that can run on both CPU and GPU hardware, enabling developers to write code once and ...`

#### par_002 - Why does IPPL use Kokkos::View for field storage?

- Verdict: **Correct**
- Codex reference answer: IPPL uses `Kokkos::View` because fields need execution-space-aware storage, subviews, mirrors, and portable kernels across host/device memory spaces.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.36`
- Local answer excerpt: `Answer: IPPL uses Kokkos::View for field storage to provide a unified and flexible memory management system that can operate on both CPU and GPU devices. This allows for efficient parallel access and computation across different hardware architectures. Evid...`

#### par_003 - How does IPPL parallelize loops over field indices using Kokkos RangePolicy?

- Verdict: **Correct**
- Codex reference answer: Loops are parallelized through `ippl::getRangePolicy` / `createRangePolicy` and the `ippl::parallel_for` wrapper over Kokkos `RangePolicy`/`MDRangePolicy`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.67`
- Local answer excerpt: `Answer: IPPL utilizes Kokkos' RangePolicy to parallelize loops over field indices. Specifically, it uses `createRangePolicy` from `Utility/ParallelDispatch.h` to define a policy based on begin and end indices for multi-dimensional spaces. This policy is the...`

#### par_004 - How does IPPL support mixed precision (float vs double) for fields?

- Verdict: **Partial**
- Codex reference answer: Precision is chosen by the field value type (`Field<float,...>` vs `Field<double,...>`), and the codebase also contains mixed-precision examples where fields/particles deliberately use different precisions.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.25`
- Local answer excerpt: `**Answer:** IPPL supports mixed precision (float vs double) for fields through its configuration options and numerical methods, allowing users to specify the desired precision level during initialization. **Evidence:** - `Ippl.h : ippl::detail::getNumerical...`

#### par_005 - How does IPPL handle multiple execution spaces like OpenMP and CUDA in the same build?

- Verdict: **Correct**
- Codex reference answer: Multiple execution spaces are enabled at build time through `IPPL_PLATFORMS` and Kokkos/HeFFTe backend flags; IPPL also has container helpers for multi-space data.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.44`
- Local answer excerpt: `**Answer:** IPPL handles multiple execution spaces like OpenMP and CUDA within the same build by utilizing Kokkos's polymorphic memory and execution space abstractions. The `TypeForAllSpaces` struct defines variant types for both memory (`unique_memory_spac...`

#### par_006 - What is the purpose of ParallelDispatch.h and what helpers does it expose?

- Verdict: **Correct**
- Codex reference answer: `ParallelDispatch.h` wraps Kokkos policies and functors, exposing `RangePolicy`, `getRangePolicy`, `createRangePolicy`, `parallel_for`, and `parallel_reduce`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.50`
- Local answer excerpt: `### Answer: The `ParallelDispatch.h` file provides abstractions and utilities for parallel execution within the IPPL framework. It includes structs and functions that facilitate dispatching and management of parallel tasks. ### Evidence: - `src/Utility/Para...`

#### par_007 - How does the Archive class serialize/deserialize Kokkos views for MPI transfer?

- Verdict: **Incorrect**
- Codex reference answer: `Archive` serializes Kokkos views into one-dimensional byte buffers with Kokkos kernels and `memcpy`, then deserializes them back into views on receive.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.31`
- Local answer excerpt: `Answer: The provided context does not contain any information about the Archive class or how it serializes/deserializes Kokkos views for MPI transfer. Evidence: - No specific chunks cover the mentioned topic.`

#### par_008 - How are MPI tags managed in IPPL to avoid collisions across subsystems?

- Verdict: **Incorrect**
- Codex reference answer: MPI tags are managed with fixed base tags in `Tags.h` and the cyclic tag allocator in `TagMaker`, which `Communicator` inherits.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.29`
- Local answer excerpt: `Answer: IPPL does not explicitly manage MPI tags within the provided context. The focus of IPPL appears to be on providing foundational utilities and structures for parallel particle-in-cell simulations rather than managing MPI communication details. Eviden...`

#### par_009 - What does Kokkos::fence do, and when does IPPL call the wrapper ippl::fence?

- Verdict: **Partial**
- Codex reference answer: `Kokkos::fence()` waits for outstanding kernels; IPPL exposes `ippl::fence()` as a runtime wrapper in `Ippl.cpp` and also fences internally after many kernel/data-movement steps.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.14`
- Local answer excerpt: `Answer: `ippl::fence` is a synchronization method used to ensure that all previous operations on a window are completed before any subsequent operations begin. It plays a role during the serialization and deserialization processes of data. Evidence: - ippl/...`

### Boundary And Halo

#### bc_001 - What boundary condition types are provided in BcTypes.h?

- Verdict: **Correct**
- Codex reference answer: `BcTypes.h` provides periodic, constant, zero, extrapolating, and no-BC face classes.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.70`
- Local answer excerpt: `Answer: The `BcTypes.h` file defines several boundary condition classes including `ConstantFace`, `ExtrapolateFace`, `NoBcFace`, `PeriodicFace`, and `ZeroFace`. These classes are used to handle different types of boundary conditions in field operations. Evi...`

#### bc_002 - How does a periodic boundary condition differ from a Neumann boundary condition in IPPL Fields?

- Verdict: **Partial**
- Codex reference answer: Periodic BCs wrap values from the opposite side of the domain; there is no explicit `NeumannFace` class in this codebase, so the closest non-periodic behavior is constant/extrapolating face treatment.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.29`
- Local answer excerpt: `Answer: A periodic boundary condition sets the field values at the boundaries such that the solution appears to repeat itself. In contrast, a Neumann boundary condition specifies the normal derivative of the field at the boundaries. Evidence: - src/MaxwellS...`

#### bc_003 - How are ghost cells populated during a halo exchange?

- Verdict: **Partial**
- Codex reference answer: Ghost cells are populated mainly by `fillHalo()` / `PeriodicFace::apply()`: source slabs are packed, exchanged, and unpacked into ghost regions; `accumulateHalo_noghost()` is a different operation.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.36`
- Local answer excerpt: `**Answer:** The `accumulateHalo_noghost` method is responsible for accumulating halo cells without ghost data during a halo exchange. It calls `exchangeBoundaries` to facilitate the exchange of boundary data related to halo cells. **Evidence:** - `data/raw/...`

#### bc_004 - How are physical-cell values copied into ghost cells for periodic boundary conditions?

- Verdict: **Partial**
- Codex reference answer: Periodic ghost cells are filled from opposite-side physical cells in `applyPeriodicSerialDim()` and the multi-rank `PeriodicFace::apply()` path.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.21`
- Local answer excerpt: `**Answer:** The `applyBCs` method in the `FDTDSolverBase<EMField, SourceField, boundary_conditions>` class template applies periodic boundary conditions to the electromagnetic fields by invoking the `getFieldBC().apply()` method on each field (`A_n`, `A_nm1...`

#### bc_005 - How does the absorbing boundary condition in the MaxwellSolvers module damp outgoing waves?

- Verdict: **Correct**
- Codex reference answer: The absorbing Maxwell BC uses second-order Mur-style formulas with precomputed weights and previous/current/next boundary values plus tangential neighbors to damp outgoing waves.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.46`
- Local answer excerpt: `Answer: The absorbing boundary condition in the MaxwellSolvers module damp outgoing waves through second-order absorbing boundary conditions (ABC). The `AbsorbingBC.h` header file defines structs like `second_order_abc_corner`, `second_order_abc_edge`, and ...`

### Numerical Meaning

#### num_001 - What does the FFT-based Poisson solver physically compute in terms of Coulomb's law?

- Verdict: **Partial**
- Codex reference answer: The FFT Poisson solvers compute electrostatic potential (and optionally field/gradient) from charge density, i.e. the discretized Coulomb potential corresponding to `-Δφ = ρ`.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The FFT-based Poisson solver numerically solves Laplace's equation with boundary conditions to determine the electric potential. This is physically equivalent to solving Coulomb's law, which describes the electrostatic interactions between point cha...`

#### num_002 - What is the physical meaning of the fields advanced by the FDTD solver?

- Verdict: **Correct**
- Codex reference answer: The Maxwell solvers evolve electromagnetic field data: electric and magnetic fields (`E`, `B`) driven by a source/four-current field.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.36`
- Local answer excerpt: `**Answer:** The electromagnetic fields `A_np1` are updated by the `step` method within the `NonStandardFDTDSolver<EMField, SourceField, boundary_conditions>` class template. This method advances the solution of Maxwell's equations by one time step using a n...`

#### num_007 - What are the numerical tradeoffs between the FFT and CG Poisson solvers in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: FFT Poisson is fast and direct on structured uniform grids with compatible BCs but less flexible; CG/PCG is iterative and may be slower/convergence-limited, but it is more flexible for alternative discretizations, BCs, and preconditioning.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.21`
- Local answer excerpt: `**Answer:** The Conjugate Gradient (CG) method implemented in the `ippl::CG` class template is an iterative solver that efficiently solves linear systems \( Ax = b \). It minimizes a quadratic function associated with the linear system and is particularly e...`

### Build And Install

#### build_001 - Which third-party libraries does IPPL depend on, and what are they used for?

- Verdict: **Partial**
- Codex reference answer: Core third-party dependencies are MPI for distributed communication, Kokkos for performance portability, heFFTe for FFT backends/plans, FFTW/CuFFT as optional FFT backends, and GoogleTest for tests.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.25`
- Local answer excerpt: `Answer: IPPL depends on MPI, Kokkos, and heFFTe. MPI is used for parallel processing across distributed systems, Kokkos provides a performance-portable C++ programming model, and heFFTe is utilized for performing distributed Fast Fourier Transforms. Evidenc...`

#### build_002 - What C++ standard does IPPL require, and why?

- Verdict: **Incorrect**
- Codex reference answer: IPPL requires C++20, as stated in the README badge and the installation examples/configuration flags.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.10`
- Local answer excerpt: `Answer: IPPL requires a C++14 standard. This is because it uses features introduced in C++14, such as variadic templates, type traits, and range-based for loops. Evidence: - data/raw/ippl/src/Types/Variant.h : get — The use of `std::__find_uniq_type_in_pack...`

#### build_003 - How is IPPL configured with CMake to enable a GPU build?

- Verdict: **Incorrect**
- Codex reference answer: GPU builds are enabled through CMake options like `IPPL_PLATFORMS=CUDA` or `IPPL_PLATFORMS="HIP;OPENMP"` plus matching Kokkos/architecture/backend flags (`Kokkos_ARCH_*`, `CMAKE_CUDA_ARCHITECTURES`, `Kokkos_ENABLE_HIP`, `Heffte_ENABLE_ROCM`, etc.).
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.23`
- Local answer excerpt: `Answer: IPPL's CMake configuration for enabling a GPU build involves specifying the appropriate Kokkos backend. The relevant chunk indicates that the `initialize` function parses command-line options and sets up the necessary infrastructure, but does not pr...`

#### build_004 - What options does INSTALLATION.md describe for configuring Kokkos for IPPL?

- Verdict: **Correct**
- Codex reference answer: `INSTALLATION.md` describes Kokkos version selection plus backend/architecture options used with IPPL builds, including CUDA and HIP/OpenMP examples and `IPPL_PLATFORMS` combinations.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.33`
- Local answer excerpt: `**Answer:** The `INSTALLATION.md` file describes several CMake options for configuring Kokkos within IPPL. These include setting the platform (`SERIAL`, `OPENMP`, `CUDA`, or a combination), specifying the version of Kokkos and Heffte, controlling whether ce...`

#### build_005 - How do I install IPPL on the EULER cluster according to the documentation?

- Verdict: **Correct**
- Codex reference answer: The EULER install guide says to connect with VPN/SSH, switch to the new software stack, purge modules, load GCC/CMake/CUDA/OpenMPI, clone the repo, configure a build, compile, and test on an interactive node.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.60`
- Local answer excerpt: `Answer: To install IPPL on the EULER cluster, follow these steps: 1. Connect to the EULER cluster via SSH with `ssh -Y <username>@euler.ethz.ch`. 2. Load the New Software Stack: `env2lmod` 3. Clean the Environment: `module purge` 4. Load Dependencies: `modu...`

### Testing And Workflow

#### test_002 - What naming conventions does WORKFLOW.md require for variables, constants, and member variables?

- Verdict: **Correct**
- Codex reference answer: `WORKFLOW.md` requires camelCase variables, CAPITAL_CASE compile-time constants, and member names suffixed with `_m`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.75`
- Local answer excerpt: `**Answer:** WORKFLOW.md requires that variables use camel casing (`myVariable`), compile-time constants use capital casing (`MY_CONSTANT`), and member variables should be suffixed with `_m` (`memberVar_m`). **Evidence:** - src/Utility/WORKFLOW.md : Naming C...`

#### test_003 - When should code use Kokkos::sqrt versus std::sqrt according to WORKFLOW.md?

- Verdict: **Correct**
- Codex reference answer: Use `std::sqrt` in host-only code, and `Kokkos::sqrt` in device-capable code such as `KOKKOS_INLINE_FUNCTION` kernels.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.75`
- Local answer excerpt: `Answer: In IPPL code, `Kokkos::sqrt` should be used when dealing with mathematical functions that might be executed on device-code or potentially run on a device (such as those marked with `KOKKOS_INLINE_FUNCTION`). For host-only code, it is recommended to ...`

#### test_004 - How does IPPL profile MPI calls using mpiP?

- Verdict: **Correct**
- Codex reference answer: IPPL profiles MPI calls with mpiP by preloading `libmpiP.so`, optionally setting `MPIP` flags, then parsing the produced `.mpiP` output with the bundled `scripts/mpiP.py`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.31`
- Local answer excerpt: `**Answer:** IPPL profiles MPI calls using mpiP by integrating it with the MPI communication functions used within IPPL. This allows for detailed performance analysis and optimization of parallel computing tasks. **Evidence:** - `data/raw/ippl/src/Ippl.cpp :...`

#### test_005 - What does the SLURM job template for Gwendolen in the README look like?

- Verdict: **Incorrect**
- Codex reference answer: The README does include a Gwendolen SLURM template showing the `gmerlin6` cluster, `gwendolen` partition, GPU count, and `srun ./<your_executable> <args> --kokkos-map-device-id-by=mpi_rank`.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.17`
- Local answer excerpt: `**Answer:** The README.md file does not contain any information about a specific SLURM job template for Gwendolen. However, it provides an overview of CI/CD and includes links to related documentation such as "SLURM Job scripts." **Evidence:** - `README.md`...`
