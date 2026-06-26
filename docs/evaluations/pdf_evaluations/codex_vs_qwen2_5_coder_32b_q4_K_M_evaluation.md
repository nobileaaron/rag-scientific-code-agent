# Codex GPT-5.4 Reference vs Qwen2.5-Coder 32B Evaluation

Generated: 2026-06-19 12:39:05 UTC

## Goal

This report evaluates the saved Qwen2.5-Coder 32B RAG answer run in `docs/evaluations/answers/eval_v2_qwen2.5-32B-q4_K_M.json` against the Codex GPT-5.4 reference answers stored in `docs/evaluations/eval_answers_v2.json`. The format follows the older `codex_vs_local_llm_evaluation_20260423` report style, but the reference side here is the curated Codex V2 answer file rather than a new source-reading pass.

## Test Environment

### Codex Reference Side

- Model: `GPT-5.4` (Codex reference answers)
- Reference file: `docs/evaluations/eval_answers_v2.json`
- Question set: `docs/evaluations/eval_questions_v2.json`
- Evaluation basis: semantic comparison against the Codex reference answer for each question

### Local LLM Side

- Host: `merlin-g-100.psi.ch`
- Job / partition: `353388` on `gwendolen`
- Answer model: `qwen2.5-coder:32b-instruct-q4_K_M`
- Chunk explanation model: `qwen2.5-coder:32b`
- File / module / call-chain models: `qwen2.5-coder:32b-instruct-q4_K_M`, `qwen2.5-coder:32b-instruct-q4_K_M`, `qwen2.5-coder:32b-instruct-q4_K_M`
- Parser: `tree_sitter`
- Question count: `100`
- Answer prompt mode: `retrieval_answer_v2`
- Mean answer latency: `14.13s`
- Median answer latency: `13.52s`

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
| Correct | 55 |
| Partial | 23 |
| Incorrect | 22 |
| Average score (`Correct=1`, `Partial=0.5`, `Incorrect=0`) | 0.665 |

## Main Findings

- Strongest areas: Api Usage, Definition Location. These are mostly questions where the retrieved answer can be anchored to one well-described class, header, implementation file, or usage pattern.
- Weakest areas: Numerical Meaning, Build And Install. These questions require cross-file synthesis, precise implementation-location recovery, or careful numerical interpretation.
- The 32B run is the slowest of the Qwen2.5 q4_K_M runs evaluated so far, with mean latency `14.13s`, but it often gives the most detailed evidence lists.
- The remaining misses are mostly not formatting failures; they are retrieval or grounding failures where the answer cites plausible but wrong-neighborhood context.
- Compared with the smaller Qwen2.5 runs, the larger answer model tends to improve exact API/location recovery, but some numerical and build/configuration answers remain brittle.

## Category Breakdown

| Category | Questions | Correct | Partial | Incorrect | Avg score |
|---|---:|---:|---:|---:|---:|
| File Purpose | 13 | 6 | 5 | 2 | 0.654 |
| Definition Location | 15 | 12 | 0 | 3 | 0.800 |
| Class Responsibility | 13 | 9 | 2 | 2 | 0.769 |
| Algorithm | 12 | 4 | 5 | 3 | 0.542 |
| Data Flow | 9 | 6 | 2 | 1 | 0.778 |
| Api Usage | 12 | 9 | 2 | 1 | 0.833 |
| Parallelism And Kokkos | 9 | 2 | 5 | 2 | 0.500 |
| Boundary And Halo | 5 | 2 | 2 | 1 | 0.600 |
| Numerical Meaning | 3 | 1 | 0 | 2 | 0.333 |
| Build And Install | 5 | 2 | 0 | 3 | 0.400 |
| Testing And Workflow | 4 | 2 | 0 | 2 | 0.500 |

## Detailed Per-Question Evaluation

### File Purpose

#### file_001 - What does Ippl.h do?

- Verdict: **Correct**
- Codex reference answer: Declares the top-level IPPL runtime handles (`Comm`, `Env`, `Info`, `Warn`, `Error`) and the lifecycle wrappers `initialize`, `finalize`, `fence`, and `abort`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.53`
- Local answer excerpt: `Answer: Ippl.h serves as a central header file in the root module of IPPL, providing essential functions and variables for managing application initialization, termination, communication, and error handling. It includes key functions such as `ippl::abort`, ...`

#### file_002 - What is the purpose of Ippl.cpp?

- Verdict: **Partial**
- Codex reference answer: Implements runtime setup/teardown: command-line option parsing, MPI communicator/environment creation, logger setup, Kokkos init/finalize, and abort/fence helpers.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.33`
- Local answer excerpt: `Answer: The `Ippl.cpp` file contains essential utility functions for managing initialization, finalization, and error handling within the IPPL (Integrated Parallel Primitives Library) framework. It includes functions such as `abort`, `checkOption`, `getNume...`

#### file_003 - What does FFT.hpp implement?

- Verdict: **Correct**
- Codex reference answer: Implements `FFTBase` setup plus the FFT specialization family for complex/real, sine, cosine, and cosine-I transforms on IPPL fields via heFFTe.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.35`
- Local answer excerpt: `Answer: FFT.hpp defines the base class and several specializations for Fast Fourier Transform (FFT) operations within the `ippl` namespace. It supports various transform types, including real and complex field transformations. The file includes classes such...`

#### file_004 - What is BareField.h responsible for?

- Verdict: **Partial**
- Codex reference answer: Defines the core distributed field container: Kokkos-backed storage, owned/allocated domains, field layout access, halo exchange hooks, and expression-style assignment.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.30`
- Local answer excerpt: `Answer: The file `BareField.h` defines the `ippl::BareField` class, which is a fundamental abstraction for representing fields in scientific computations within the IPPL framework. It includes methods to access various properties of the field such as alloca...`

#### file_005 - What does Field.h add on top of BareField?

- Verdict: **Correct**
- Codex reference answer: Adds mesh awareness and boundary-condition management on top of `BareField`, plus volume integral/average helpers.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.61`
- Local answer excerpt: `Answer: The `ippl::Field` class adds functionality for boundary condition management, mesh representation, and higher-level operations such as deep copying, volume averaging, and integral calculations compared to `BareField`. It utilizes mesh abstractions l...`

#### file_006 - What role does HaloCells.h play in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: Defines the halo-exchange machinery for fields: pack/unpack, boundary exchange, and periodic handling for ghost cells.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.13`
- Local answer excerpt: `Answer: The `HaloCells` class and related structs within the IPPL library manage halo cells for field data, facilitating inter-process communication (IPC) in parallel computations. It includes classes like `ippl::detail::HaloCells`, which manages halo cell ...`

#### file_007 - What is the purpose of FieldLayout.h?

- Verdict: **Incorrect**
- Codex reference answer: Defines how a global `NDIndex` domain is partitioned across MPI ranks, including local subdomains, neighbors, and communication ranges.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.07`
- Local answer excerpt: `Answer: `FieldLayout.h` defines the `FieldLayout` class and related helper functions within the `ippl` namespace. This class manages field distribution and domain information. It includes methods like `getDomain` and `getDistribution` to access domain detai...`

#### file_008 - What does ParticleBase.h define?

- Verdict: **Partial**
- Codex reference answer: Defines the generic particle container base class with positions, optional IDs, registered attributes, and a particle layout that controls migration.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.31`
- Local answer excerpt: `Answer: The `ParticleBase` class serves as a foundational abstraction for managing particle data within the IPPL framework. It provides methods to handle attributes, layout, local/global particle counts, and boundary conditions. Key methods include `getAttr...`

#### file_009 - What is the purpose of ParticleSpatialLayout.h?

- Verdict: **Partial**
- Codex reference answer: Defines the spatial particle layout that decides ownership by region and migrates particles to the correct rank after motion.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The `ParticleSpatialLayout` class is designed to manage spatial layout and communication regions for particles within the IPPL (Integrated Particle Physics Library). It defines methods to configure, update, and retrieve spatial information necessary...`

#### file_010 - What does ParticleAttrib.h implement?

- Verdict: **Correct**
- Codex reference answer: Implements the `ParticleAttrib` storage object: a Kokkos-view-backed particle attribute with resize, serialization, and mirror/access helpers.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.44`
- Local answer excerpt: `Answer: The `ParticleAttrib.h` header file defines a class template `ippl::ParticleAttrib` within the `ippl` namespace. This class manages and manipulates attributes associated with particles in a simulation, providing methods for serialization, memory mana...`

#### file_011 - What is UniformCartesian.h for?

- Verdict: **Correct**
- Codex reference answer: Defines the uniform Cartesian mesh class with spacing, origin, cell volume, total mesh volume, and vertex-position helpers.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.62`
- Local answer excerpt: `Answer: `UniformCartesian.h` defines the `UniformCartesian` class family within the `ippl::Meshes` namespace. This class specializes uniform Cartesian meshes and includes methods for managing mesh properties such as `getDeltaVertex`, `getVertexPosition`, `g...`

#### file_012 - What does OrthogonalRecursiveBisection.h do?

- Verdict: **Correct**
- Codex reference answer: Declares the orthogonal recursive bisection domain-decomposition/load-balancing class and its cut/median/repartition helpers.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.47`
- Local answer excerpt: `Answer: The file `OrthogonalRecursiveBisection.h` defines the class `ippl::OrthogonalRecursiveBisection`, which is used for decomposing computational domains using an orthogonal recursive bisection algorithm. This class includes methods such as `cutDomain`,...`

#### file_013 - What is the purpose of CIC.h in the Interpolation subsystem?

- Verdict: **Partial**
- Codex reference answer: Declares the first-order cloud-in-cell interpolation helpers for scatter/gather between particles and grid fields.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The file `CIC.h` defines several function declarations within the `ippl::detail` namespace that handle interpolation operations, specifically for Cloud-in-Cell (CIC) methods. These functions include `scatterToField`, `scatterToPoint`, `gatherFromFie...`

### Definition Location

#### loc_001 - Where is FFT initialization implemented in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: FFT initialization lives in `src/FFT/FFT.hpp`, especially `FFTBase` construction/setup and the transform-specific constructors that build the heFFTe plans.
- Comparison: The answer cites a different implementation location than the Codex reference.
- Reference-token coverage: `0.35`
- Local answer excerpt: `Answer: The provided context does not mention any specific implementation of FFT initialization within the IPPL codebase. The chunks cover initialization functions for various components like MPI environment, communicators, command-line options, and field l...`

#### loc_002 - Where does IPPL set up the MPI environment?

- Verdict: **Incorrect**
- Codex reference answer: IPPL sets up MPI in `src/Ippl.cpp::initialize()` by constructing `mpi::Environment` and `mpi::Communicator`; the low-level `MPI_Init` check/call is in `src/Communicate/Environment.cpp`.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.19`
- Local answer excerpt: `Answer: The provided retrieved context does not explicitly mention where or how IPPL sets up the MPI environment. The chunks cover FFT setup, field allocation, and constructor definitions but do not address MPI initialization. Evidence: - src/FFT/FFT.h : se...`

#### loc_003 - Where is Kokkos initialized and finalized inside IPPL?

- Verdict: **Correct**
- Codex reference answer: Kokkos is initialized and finalized directly in `src/Ippl.cpp` inside `ippl::initialize()` and `ippl::finalize()`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.75`
- Local answer excerpt: `Answer: Kokkos is initialized and finalized within the `initialize` and `finalize` functions in the `Ippl.cpp` file. The `initialize` function calls `Kokkos::initialize(argc, argv)` to set up Kokkos, while the `finalize` function calls `Kokkos::finalize()` ...`

#### loc_004 - Where is the orthogonal recursive bisection load balancer implemented?

- Verdict: **Correct**
- Codex reference answer: The ORB load balancer is implemented in `src/Decomposition/OrthogonalRecursiveBisection.hpp` with declarations in the matching header.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.64`
- Local answer excerpt: `Answer: The orthogonal recursive bisection load balancer is implemented in the `OrthogonalRecursiveBisection.h` and `OrthogonalRecursiveBisection.hpp` files within the `Decomposition` module. The class `ippl::OrthogonalRecursiveBisection` defines the core l...`

#### loc_005 - Where are boundary conditions applied to a Field?

- Verdict: **Correct**
- Codex reference answer: Field BCs are attached in `Field::setFieldBC()` and actually applied through `BConds::apply()` and the concrete face classes in `BcTypes.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.44`
- Local answer excerpt: `Answer: Boundary conditions are applied to fields within the `FDTDSolverBase<EMField, SourceField, boundary_conditions>` class template through methods such as `applyBCs`, which uses `Field::getFieldBC` and involves dot product computations with `meta_dot::...`

#### loc_006 - Where is the CIC (cloud-in-cell) scatter implemented?

- Verdict: **Correct**
- Codex reference answer: CIC scatter is implemented in `src/Interpolation/CIC.hpp`, primarily `scatterToPoint()` and `scatterToField()`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.82`
- Local answer excerpt: `Answer: The CIC (Cloud-in-Cell) scatter implementation is primarily found in the `scatterToField` function declaration within the `CIC.h` file and its definition in `CIC.hpp`. The `scatterToField` function is part of the `ippl::detail` namespace and handles...`

#### loc_007 - Where is the CIC gather implemented?

- Verdict: **Correct**
- Codex reference answer: CIC gather is implemented in `src/Interpolation/CIC.hpp`, primarily `gatherFromPoint()` and `gatherFromField()`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.64`
- Local answer excerpt: `Answer: The CIC gather implementation is found in the `CIC.hpp` file within the `ippl::detail` namespace. The specific function responsible for gathering data from a field using Cloud-in-Cell (CIC) interpolation is `gatherFromField`. Evidence: - data/raw/ip...`

#### loc_008 - Where is halo exchange for BareField implemented?

- Verdict: **Correct**
- Codex reference answer: Halo exchange for `BareField` is surfaced in `src/Field/BareField.hpp` and actually performed in `src/Field/HaloCells.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.77`
- Local answer excerpt: `Answer: The halo exchange for `BareField` is implemented in methods within the `BareField` class, particularly in `accumulateHalo`, `fillHalo`, and related functions. These methods are defined in `BareField.hpp`. Evidence: - src/Field/BareField.hpp : ippl::...`

#### loc_009 - Where are the FFT-based open-boundary Poisson solver routines defined?

- Verdict: **Correct**
- Codex reference answer: The FFT open-boundary Poisson routines are defined in `src/PoissonSolvers/FFTOpenPoissonSolver.h` and `src/PoissonSolvers/FFTOpenPoissonSolver.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.83`
- Local answer excerpt: `Answer: The FFT-based open-boundary Poisson solver routines are defined in the `FFTOpenPoissonSolver` class within the files `FFTOpenPoissonSolver.h` and `FFTOpenPoissonSolver.hpp`. The class is designed to solve Poisson's equation using Fast Fourier Transf...`

#### loc_010 - Where is the conjugate gradient solver algorithm implemented?

- Verdict: **Correct**
- Codex reference answer: The CG/PCG algorithm implementation is in `src/LinearSolvers/PCG.h`; the Poisson wrapper that instantiates it is `src/PoissonSolvers/PoissonCG.h`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.58`
- Local answer excerpt: `Answer: The conjugate gradient solver algorithm is implemented in the `PoissonCG` class within the file `PoissonCG.h`. The key method that executes the CG method is `ippl::PoissonCG::solve`, which sets up and solves the Poisson equation using the Conjugate ...`

#### loc_011 - Where is the FEM Poisson solver implemented?

- Verdict: **Correct**
- Codex reference answer: The FEM Poisson solver is implemented in `src/PoissonSolvers/FEMPoissonSolver.h`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `1.00`
- Local answer excerpt: `Answer: The FEM Poisson solver is implemented in the `FEMPoissonSolver` class within the file `FEMPoissonSolver.h`. This class inherits from the `Poisson<FieldLHS, FieldRHS>` base class and uses finite element methods combined with the Conjugate Gradient al...`

#### loc_012 - Where is the FDTD Maxwell solver base class defined?

- Verdict: **Incorrect**
- Codex reference answer: The FDTD Maxwell solver base class is defined in `src/MaxwellSolvers/FDTDSolverBase.h` with implementation in `FDTDSolverBase.hpp`.
- Comparison: The answer cites a different implementation location than the Codex reference.
- Reference-token coverage: `0.70`
- Local answer excerpt: `Answer: The provided context does not contain information about the specific definition of an FDTD Maxwell solver base class within the IPPL codebase. The chunks cover topics related to `FieldSolverBase`, a general field solver base class, and classes like ...`

#### loc_013 - Where is the LagrangeSpace class defined?

- Verdict: **Correct**
- Codex reference answer: The `LagrangeSpace` class is defined in `src/FEM/LagrangeSpace.h` with methods implemented in `src/FEM/LagrangeSpace.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.78`
- Local answer excerpt: `Answer: The `LagrangeSpace` class is defined in the file `LagrangeSpace.h` within the `ippl` namespace. It is a class representing a Lagrange space for finite element methods on a structured grid and inherits from `FiniteElementSpace`. Evidence: - data/raw/...`

#### loc_014 - Where is the particle update routine (that moves particles across ranks) implemented?

- Verdict: **Correct**
- Codex reference answer: Particle migration between ranks is implemented in `ParticleSpatialLayout::update()` in `src/Particle/ParticleSpatialLayout.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.80`
- Local answer excerpt: `Answer: The particle update routine that moves particles across ranks is implemented in the `update` method of the `ParticleSpatialLayout<T, Dim, Mesh, Properties...>` class template. This method handles boundary conditions, determines which particles need ...`

#### loc_015 - Where are IPPL timers defined?

- Verdict: **Correct**
- Codex reference answer: IPPL timers are defined by the singleton timing layer in `src/Utility/IpplTimings.h/.cpp`, not just the low-level `Timer` helper.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.44`
- Local answer excerpt: `Answer: IPPL timers are defined within the `IpplTimings.h` file. The primary class responsible for managing timer information is `IpplTimerInfo`. Additionally, the `Timing::startTimer` function in `IpplTimings.cpp` handles starting a specific timer using a ...`

### Class Responsibility

#### cls_001 - What is the main responsibility of the BareField class?

- Verdict: **Correct**
- Codex reference answer: `BareField` is the core distributed field storage class: it owns the data view, domain metadata, layout link, and halo operations.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.50`
- Local answer excerpt: `Answer: The `BareField` class is a fundamental abstraction for representing fields in scientific computations within the IPPL framework. It includes methods to access various properties of the field such as allocation status, communicator, domain, halo, hos...`

#### cls_002 - What is the main responsibility of the Field class compared to BareField?

- Verdict: **Partial**
- Codex reference answer: `Field` extends `BareField` with a mesh, boundary-condition container, and mesh-aware integral/average semantics.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.19`
- Local answer excerpt: `Answer: The provided context does not mention a `Field` class distinct from `BareField`. The main responsibilities discussed are those of `BareField`, which includes managing memory and access patterns for multidimensional fields, handling ghost cells, and ...`

#### cls_003 - What does the FieldLayout class do and what are its main template parameters?

- Verdict: **Correct**
- Codex reference answer: `FieldLayout<Dim>` distributes a global `NDIndex<Dim>` over ranks and stores local domains, neighbors, and communication ranges; its only template parameter is `Dim`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.47`
- Local answer excerpt: `Answer: The `FieldLayout` class manages field distribution, domain information, and neighbor relationships for scientific computations. It is designed to distribute a multi-dimensional index space (domain) among MPI ranks, allowing certain dimensions to be ...`

#### cls_004 - What is the purpose of the ParticleBase class and how is it meant to be used?

- Verdict: **Correct**
- Codex reference answer: `ParticleBase` is the user-extensible base container for particles; derived classes add attributes and register them so layout-driven migration can move them.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.45`
- Local answer excerpt: `Answer: The `ParticleBase` class serves as a foundational abstraction for managing particle data within the IPPL framework. It provides methods to handle attributes, layout, and local/global particle counts. Users define derived classes from `ParticleBase` ...`

#### cls_005 - What does the ParticleSpatialLayout class do?

- Verdict: **Correct**
- Codex reference answer: `ParticleSpatialLayout` decides which spatial region/rank owns each particle and performs the migration/update workflow after particles move.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.39`
- Local answer excerpt: `Answer: The `ParticleSpatialLayout` class is designed to manage spatial layout and communication regions for particles within the IPPL (Integrated Particle Physics Library). It defines methods to configure, update, and retrieve spatial information necessary...`

#### cls_006 - What is the responsibility of UniformCartesian?

- Verdict: **Correct**
- Codex reference answer: `UniformCartesian` represents a uniform Cartesian mesh and exposes spacing/origin/volume and vertex-position geometry queries.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.62`
- Local answer excerpt: `Answer: The `UniformCartesian` class represents uniform-spacing Cartesian meshes and provides functionality for initializing and manipulating such meshes. It includes methods like `getDeltaVertex`, `getVertexPosition`, `getCellVolume`, `getMeshSpacing`, `ge...`

#### cls_007 - What does the Mesh base class define?

- Verdict: **Partial**
- Codex reference answer: `Mesh` is the abstract base interface for meshes: origin, grid size, spacing, vertex positions, and volume queries.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.20`
- Local answer excerpt: `Answer: The provided context does not mention a `Mesh` base class or its specific definitions within the IPPL codebase. Evidence: - data/raw/ippl/src/Types/Variant.h : _Variant_base — core struct for managing variant types with constructors and assignment o...`

#### cls_008 - What is the responsibility of the Communicator class in ippl::mpi?

- Verdict: **Correct**
- Codex reference answer: `ippl::mpi::Communicator` wraps MPI point-to-point, collectives, tag handling, and managed communication buffers.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.46`
- Local answer excerpt: `Answer: The `Communicator` class in `ippl::mpi` manages MPI communicators and their associated operations, providing methods for managing MPI communications such as barriers, rank retrieval, size determination, and communication splitting. It also handles b...`

#### cls_009 - What is the role of the Environment class in ippl::mpi?

- Verdict: **Correct**
- Codex reference answer: `ippl::mpi::Environment` manages MPI environment lifetime checks/teardown and provides an abort hook.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.50`
- Local answer excerpt: `Answer: The `ippl::mpi::Environment` class manages MPI (Message Passing Interface) environment setup and teardown within the IPPL codebase. It includes constructors for initializing MPI and destructors for finalizing MPI, along with utility functions like `...`

#### cls_010 - What does the Archive class do in the Communicate module?

- Verdict: **Incorrect**
- Codex reference answer: `Archive` serializes and deserializes Kokkos views and vector-valued views into raw byte buffers for MPI transfer.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.08`
- Local answer excerpt: `Answer: The provided context does not contain any information about an `Archive` class within the `Communicate` module of IPPL. The chunks cover modules like `Partition`, `Types`, and `Utility`, but do not mention the `Archive` class or its functionality. E...`

#### cls_011 - What is the role of the BConds class?

- Verdict: **Correct**
- Codex reference answer: `BConds` is the container of boundary-condition faces and orchestrates neighbor discovery, BC application, and ghost-to-physical assignment.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The `BConds` class is responsible for handling boundary conditions in fields within the IPPL library. It encapsulates various operations related to boundary conditions and includes methods such as `apply`, `assignGhostToPhysical`, and `findBCNeighbo...`

#### cls_012 - What is the role of the BaseManager class?

- Verdict: **Correct**
- Codex reference answer: `BaseManager` provides the simulation loop skeleton: `pre_run`, `pre_step`, `advance`, `post_step`, and `run(nt)`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.87`
- Local answer excerpt: `Answer: The `BaseManager` class serves as a foundational abstract class within the `ippl` namespace. It provides essential methods such as `run`, `pre_run`, `post_step`, and `pre_step`, which are crucial for managing simulation or computational workflows. T...`

#### cls_013 - What does the Index class represent and what operations does it support?

- Verdict: **Incorrect**
- Codex reference answer: `Index` represents a regular strided integer range/slice and supports range-style arithmetic and comparison operations used in domain descriptions.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.06`
- Local answer excerpt: `Answer: The provided retrieved context does not contain any information about an `Index` class within the IPPL codebase. The chunks cover various other classes and structs such as `Tuple`, `_Build_FUN`, `Verifier`, `_Uninitialized`, `Min`, but there is no m...`

### Algorithm

#### alg_001 - How does the FFT-based open-boundary Poisson solver compute the electrostatic potential?

- Verdict: **Incorrect**
- Codex reference answer: The FFT open-boundary solver embeds/extends the RHS onto larger domains, FFTs both the density and a precomputed Green's function, multiplies in Fourier space, inverse transforms, and optionally computes gradients/Hessians.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.19`
- Local answer excerpt: `Answer: The `FFTOpenPoissonSolver` class template is responsible for solving the Poisson equation using FFT techniques. It involves initializing fields, setting right-hand sides, and performing the solve operation. The solver uses methods like `initializeFi...`

#### alg_002 - How does the FFT-based periodic Poisson solver work in IPPL?

- Verdict: **Correct**
- Codex reference answer: The periodic FFT solver FFTs the charge density, divides each Fourier mode by `|k|^2` (with the zero mode handled separately), then inverse transforms; gradients are computed by multiplying by `ik/|k|^2` before the inverse FFT.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.45`
- Local answer excerpt: `Answer: The FFT-based periodic Poisson solver in IPPL is implemented by the `FFTTruncatedGreenPeriodicPoissonSolver` class. It solves the periodic Poisson problem using Fourier transforms and a truncated Green's function. The solver performs an FFT on the c...`

#### alg_003 - How does the truncated Green periodic Poisson solver differ from the standard periodic one?

- Verdict: **Correct**
- Codex reference answer: The truncated-Green periodic solver replaces the simple `1/|k|^2` kernel with the FFT of a truncated/erf-smoothed Green's function `forceConstant * erf(alpha r) / r`, then follows the same transform-multiply-inverse pattern.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.42`
- Local answer excerpt: `Answer: The `FFTTruncatedGreenPeriodicPoissonSolver` differs from the `FFTPeriodicPoissonSolver` by incorporating a truncated Green's function to handle long-range interactions. Specifically, `FFTTruncatedGreenPeriodicPoissonSolver` uses a convolution with ...`

#### alg_004 - How does IPPL's CG solver iterate in the PCG.h implementation?

- Verdict: **Incorrect**
- Codex reference answer: In `PCG.h`, the CG iteration forms residual/direction fields, applies the operator, computes `alpha` and `beta` from inner products, updates the solution/residual/direction, and stops on tolerance or iteration count; the preconditioned variant inserts `M^{-1}` applications on the residual.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.23`
- Local answer excerpt: `Answer: The provided retrieved context does not specify the exact iteration process of IPPL's CG solver within the `PCG.h` implementation. The chunks cover setup and configuration aspects but do not delve into the detailed iterative logic. Evidence: - src/L...`

#### alg_005 - How is cloud-in-cell interpolation performed in IPPL (both scatter and gather directions)?

- Verdict: **Incorrect**
- Codex reference answer: CIC computes lower/upper weights per axis, scatters with atomic adds to the `2^Dim` neighboring grid points, and gathers by summing the same weighted stencil back to particles.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.22`
- Local answer excerpt: `Answer: In IPPL, Cloud-in-Cell (CIC) interpolation for scattering particle attributes onto a field is handled by the `scatter` method within the `ParticleAttrib<T, Properties...>` class template. This method uses parallel execution via Kokkos to map each pa...`

#### alg_006 - How does the standard FDTD solver advance the electromagnetic field in time?

- Verdict: **Partial**
- Codex reference answer: The standard FDTD solver advances the source-like field with a second-order finite-difference update using the previous and current time levels plus neighboring cells and source terms, then fills halos and reapplies BCs.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The `StandardFDTDSolver` class advances the electromagnetic field in time through its `step()` method. This method uses a leapfrog scheme to update the electric and magnetic fields iteratively while considering boundary conditions and source terms. ...`

#### alg_007 - How does the LagrangeSpace class evaluate degrees of freedom per element?

- Verdict: **Correct**
- Codex reference answer: `LagrangeSpace` evaluates element DOFs by mapping local element indices to global DOF indices, then evaluates order-1 reference-element shape functions and gradients on those local DOFs.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.32`
- Local answer excerpt: `Answer: The `LagrangeSpace` class evaluates degrees of freedom per element using a template parameter that specifies the dimension and order of the Lagrangian elements. This is done by inheriting from `FiniteElementSpace` with a third template argument calc...`

#### alg_008 - How is Gauss-Jacobi quadrature implemented and used in IPPL FEM?

- Verdict: **Correct**
- Codex reference answer: Gauss-Jacobi quadrature computes nodes/weights by Newton iteration on Jacobi polynomial roots, starting from Chebyshev or LehrFEM-style guesses, and uses the resulting rule on reference elements in FEM.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.62`
- Local answer excerpt: `Answer: The `GaussJacobiQuadrature` class represents a Gauss-Jacobi quadrature rule in IPPL, inheriting from the base `Quadrature` class. It computes integration nodes and weights using Newton iterations based on Chebyshev nodes as initial guesses, followin...`

#### alg_009 - How does the orthogonal recursive bisection decide where to cut the domain?

- Verdict: **Partial**
- Codex reference answer: ORB chooses a cut axis from the domain geometry and then finds a weight-balanced cut/median so recursive splits distribute load more evenly.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.37`
- Local answer excerpt: `Answer: The orthogonal recursive bisection decides where to cut the domain by identifying the longest axis of the current domain and finding the median along that axis. This is done through the `findCutAxis` method, which determines the axis with the maximu...`

#### alg_010 - How does inverse transform sampling generate particles from a given distribution in IPPL?

- Verdict: **Partial**
- Codex reference answer: Inverse transform sampling maps uniform random values in CDF space to samples by estimating the inverse and refining it with Newton-Raphson, dimension by dimension.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.41`
- Local answer excerpt: `Answer: Inverse transform sampling in IPPL is implemented within the `InverseTransformSampling` class. The `generate` method of this class fills a provided view with random samples generated from a specified target distribution using uniformly distributed r...`

#### alg_011 - How does the FFT class interface with heFFTe to perform complex-to-complex and real-to-complex transforms?

- Verdict: **Partial**
- Codex reference answer: The FFT layer builds heFFTe boxes/plans in `setup()`, copies IPPL field data into the required views/subviews, calls heFFTe forward/backward transforms, and copies results back for CC/RC/DST/DCT variants.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.23`
- Local answer excerpt: `Answer: The `FFT` class interfaces with Heffte through its constructor and setup method. The constructor configures the FFT operations by converting domain information into Heffte-compatible bounds and then calls the `setup` method. The `setup` method likel...`

#### alg_012 - How does IPPL's preconditioned CG use the preconditioner defined in Preconditioner.h?

- Verdict: **Partial**
- Codex reference answer: PCG applies a chosen preconditioner from `Preconditioner.h` to the residual, uses the preconditioned residual in its inner products and direction updates, and iterates until tolerance/max iterations.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.22`
- Local answer excerpt: `Answer: IPPL's preconditioned Conjugate Gradient (CG) method uses the preconditioners defined in `Preconditioner.h` by setting them through the `setPreconditioner` method of the `ippl::CG` class. This method is called within the solver configuration process...`

### Data Flow

#### flow_001 - How does charge density flow from particles to the grid in a typical PIC step in IPPL?

- Verdict: **Correct**
- Codex reference answer: In the PIC workflow, particle charges and positions are deposited onto the grid with CIC (`scatter`) or FEM assembly (`assemble_rhs_from_particles`), accumulated into `rho`, and then normalized/background-shifted in the manager before solving.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.31`
- Local answer excerpt: `Answer: The function `assemble_rhs_from_particles` in the file `data/raw/ippl/src/FEM/FEMInterpolate.hpp` is responsible for depositing charge density from particles to the grid. It iterates over each particle, locates its position on the mesh using shape f...`

#### flow_002 - How does the electric field flow from the grid back to particles after a Poisson solve?

- Verdict: **Partial**
- Codex reference answer: After the field solve, the manager gathers the electric field back to particles with CIC `gather(...)` or FEM `interpolate_grad_to_diracs(...)`, storing particle-local `E` values for the push step.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.22`
- Local answer excerpt: `Answer: The electric field is computed as the gradient of the potential on the grid. In `FFTOpenPoissonSolver`, if the output type includes gradients (`SOL_AND_GRAD`), the method computes the gradient in Fourier space and then transforms it back to physical...`

#### flow_003 - How are halo cells exchanged between neighboring MPI ranks for a BareField?

- Verdict: **Incorrect**
- Codex reference answer: Halo exchange uses `FieldLayout` neighbor/range metadata to pack field subviews, send/receive them with MPI, unpack into ghost or physical regions, and handle serial-periodic dimensions locally.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.15`
- Local answer excerpt: `Answer: Halo cells are exchanged between neighboring MPI ranks using the `accumulateHalo` method of the `ippl::BareField<T, Dim, ViewArgs...>` class template. This method is responsible for managing halo region data exchange efficiently. Evidence: - src/Fie...`

#### flow_004 - How are particles migrated between MPI ranks by ParticleSpatialLayout?

- Verdict: **Correct**
- Codex reference answer: `ParticleSpatialLayout::update()` applies particle BCs, locates destination ranks, advertises receive counts with RMA, sends all registered attributes, destroys invalid local particles, and receives the incoming ones.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.27`
- Local answer excerpt: `Answer: The `ParticleSpatialLayout` class manages spatial layout and communication regions for particles. It includes methods like `locateParticles`, `positionInRegion`, and `update` which are likely involved in determining particle positions and managing t...`

#### flow_005 - How does FieldLayout decide which index ranges live on which rank?

- Verdict: **Correct**
- Codex reference answer: `FieldLayout` uses the partitioner and the requested parallel/serial decomposition flags to assign each rank a local `NDIndex`, plus neighbor and communication range tables.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.33`
- Local answer excerpt: `Answer: FieldLayout decides which index ranges live on which rank through methods like `addNeighbors`, `findNeighbors`, and `findPeriodicNeighbors`. These methods manage neighbor relationships, including intersections of domains between ranks and the number...`

#### flow_006 - How is a ParameterList used to configure the FFT and solver classes?

- Verdict: **Correct**
- Codex reference answer: `ParameterList` is merged into FFT and solver objects, then consumed by `setup()/initialize()/solve()` for communication mode, pencil/reorder flags, transform direction, solver type, tolerances, preconditioner settings, and output type.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.28`
- Local answer excerpt: `Answer: A `ParameterList` is used to configure the FFT and solver classes by passing it as an argument during initialization. For the FFT class, the constructor takes a `ParameterList` which contains necessary parameters for setting up the FFT operations. S...`

#### flow_007 - How does data flow through the BaseManager's pre_step / advance / post_step hooks during a simulation?

- Verdict: **Correct**
- Codex reference answer: `BaseManager::run()` executes `pre_step()`, `advance()`, and `post_step()` for each timestep; derived managers use those hooks for deposit/solve/gather, time updates, and output.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.52`
- Local answer excerpt: `Answer: The `BaseManager` class provides essential methods such as `pre_step`, `advance`, and `post_step` for managing the simulation workflow. During a simulation, these methods are likely called in sequence to handle pre-step operations, advance the simul...`

#### flow_008 - How does the FEM solver move data between fields and FEMVector representations?

- Verdict: **Correct**
- Codex reference answer: FEM solvers move data by assembling field data into FEM load/stiffness representations (`evaluateLoadVector`, `evaluateAx`, `FEMVector`) and then interpolating the solved field quantities back where needed.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.25`
- Local answer excerpt: `Answer: The FEM solver uses `FEMVector` to manage distributed field data with halo cells for parallel computations. The `accumulateHalo` method in `FEMVector.hpp` handles halo exchange operations using MPI communication. Data is packed into a buffer and sen...`

#### flow_009 - How does OrthogonalRecursiveBisection redistribute particles after rebalancing?

- Verdict: **Partial**
- Codex reference answer: After ORB recomputes the decomposition, particle ownership changes are realized by updating the layout/regions and then migrating particles with the usual particle update path.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.22`
- Local answer excerpt: `Answer: The `OrthogonalRecursiveBisection` class handles particle redistribution through its `binaryRepartition` method. This method performs a recursive bisection of the computational domain and updates the field layout to reflect the new subdomains. Durin...`

### Api Usage

#### api_001 - How do I create a 3D Field of doubles in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: A typical 3D field is `Field<double, 3, UniformCartesian<double, 3>, Cell>` constructed from a `UniformCartesian` mesh and a `FieldLayout<3>`.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.07`
- Local answer excerpt: `Answer: The provided context does not include specific information on how to create a 3D Field of doubles in IPPL. The retrieved chunks cover initialization functions, utility files, and variant type implementations but do not address field creation. Eviden...`

#### api_002 - How do I construct a UniformCartesian mesh with custom spacing and origin?

- Verdict: **Correct**
- Codex reference answer: Construct the mesh as `UniformCartesian<double, Dim> mesh(domain, hx, origin);` where `hx` is the spacing vector and `origin` is the mesh origin.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.85`
- Local answer excerpt: `Answer: To construct a `UniformCartesian` mesh with custom spacing and origin, you use its constructor by providing an `NDIndex<Dim>` object for dimensions, a `vector_type` for spacing (`hx`), and another `vector_type` for the origin. The constructor is def...`

#### api_003 - How do I attach a boundary condition (e.g. periodic) to a Field?

- Verdict: **Partial**
- Codex reference answer: Create a `BConds<FieldT, Dim>`, assign per-face BC objects such as `PeriodicFace<FieldT>`, then call `field.setFieldBC(bc)`.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.31`
- Local answer excerpt: `Answer: To attach a periodic boundary condition to a Field in IPPL, you can use the `setPeriodicBoundaryConditions` method defined within the `FDTDSolverBase` class template. This method sets up periodic boundary conditions for the fields `A_n`, `A_np1`, an...`

#### api_004 - How do I define a custom particle class that adds mass and velocity attributes on top of ParticleBase?

- Verdict: **Correct**
- Codex reference answer: Define a class derived from `ParticleBase<ParticleSpatialLayout<...>>`, add `mass` and `velocity` attributes as members, and register them with `addAttribute()` in the constructor.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.59`
- Local answer excerpt: `Answer: To define a custom particle class with additional `mass` and `velocity` attributes on top of `ParticleBase`, you need to create a derived class that inherits from `ippl::ParticleBase`. In this derived class, use the `addAttribute` method provided by...`

#### api_005 - How do I call ippl::initialize and ippl::finalize in a main program?

- Verdict: **Correct**
- Codex reference answer: Call the free namespace functions `ippl::initialize(argc, argv);` and `ippl::finalize();` from `main`, as shown in the docs/examples.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.60`
- Local answer excerpt: `Answer: To call `ippl::initialize` and `ippl::finalize` in a main program, you need to include `Ippl.h` and then invoke these functions with appropriate arguments. Specifically, `ippl::initialize` requires references to the command-line argument count (`arg...`

#### api_006 - How do I set up and run a forward FFT on an IPPL Field?

- Verdict: **Correct**
- Codex reference answer: Set up the relevant layouts/fields/parameters, build an `FFT<CCTransform, ...>` or `FFT<RCTransform, ...>` object, and call `transform(FORWARD, ...)` on the field(s).
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.67`
- Local answer excerpt: `Answer: To set up and run a forward FFT on an IPPL Field, you need to create an instance of the `FFT` class with appropriate layouts and parameters. First, define input and output layouts for your field data. Then, instantiate the `FFT` object using these l...`

#### api_007 - How do I construct an FFTPeriodicPoissonSolver and solve for the potential?

- Verdict: **Correct**
- Codex reference answer: Construct `FFTPeriodicPoissonSolver(lhs, rhs)` (or default construct then set fields/params), ensure the RHS is attached, and call `solve()` to write the potential/gradient outputs.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.52`
- Local answer excerpt: `Answer: To construct an `FFTPeriodicPoissonSolver` and solve for the potential, follow these steps: 1. Create an instance of `FFTPeriodicPoissonSolver`. This involves calling its constructor, which initializes default parameters. 2. Use the `setRhs` method ...`

#### api_008 - How do I invoke the conjugate gradient Poisson solver on a Field?

- Verdict: **Partial**
- Codex reference answer: Use `PoissonCG<FieldT>` (or the Alpine `FieldSolver` wrapper around it), set its fields/parameters, and call `solve()` so the internal CG/PCG object iterates on the field.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.40`
- Local answer excerpt: `Answer: To invoke the conjugate gradient Poisson solver on a `Field`, instantiate the `PoissonCG` class with left-hand side (`lhs`) and right-hand side (`rhs`) fields. Configure the solver using methods like `setDefaultParameters` and `setSolver`, then call...`

#### api_009 - How do I sample particles from a normal distribution using IPPL Random utilities?

- Verdict: **Correct**
- Codex reference answer: For Gaussian draws, IPPL exposes both `randn` convenience generation and the more general `InverseTransformSampling` + `NormalDistribution` path.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.33`
- Local answer excerpt: `Answer: To sample particles from a normal distribution using IPPL's random utilities, you can use the `InverseTransformSampling` class with a `Distribution` object configured to represent a normal distribution. Specifically, you would define a `normal_pdf`,...`

#### api_010 - How do I register particle attributes with ParticleBase so that they are communicated on migration?

- Verdict: **Correct**
- Codex reference answer: Register each particle attribute with `addAttribute(...)`; migration then serializes and transfers all registered attributes automatically.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.62`
- Local answer excerpt: `Answer: To register particle attributes with `ParticleBase` for communication during migration, you must define a class derived from `ParticleBase`, declare your custom attributes as instances of `ParticleAttribute<T>`, and use the `addAttribute` method wit...`

#### api_011 - How do I access the MPI rank and size through the IPPL Communicator?

- Verdict: **Correct**
- Codex reference answer: Access rank and size with `ippl::Comm->rank()` and `ippl::Comm->size()` (or the same methods on a `Communicator` object).
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.50`
- Local answer excerpt: `Answer: To access the MPI rank and size through the IPPL Communicator, you can use the methods `ippl::mpi::Communicator::rank` and `ippl::mpi::Communicator::size`, respectively. These methods are part of the `Communicator` class in the `ippl::mpi` namespace...`

#### api_012 - How do I use IpplTimings to measure a region of code?

- Verdict: **Correct**
- Codex reference answer: Get a timer handle with `IpplTimings::getTimer("name")`, surround the code with `startTimer()` / `stopTimer()`, and print with `IpplTimings::print()`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.86`
- Local answer excerpt: `Answer: To measure a region of code using `IpplTimings`, follow these steps: 1. Create a timer by calling `IpplTimings::getTimer("timer name")`. This will either create a new timer or return a reference to an existing one with the specified name. 2. Start t...`

### Parallelism And Kokkos

#### par_001 - How does IPPL achieve performance portability across CPUs and GPUs?

- Verdict: **Partial**
- Codex reference answer: IPPL gets performance portability by combining Kokkos execution/memory abstractions with MPI and heFFTe, so the same code paths can target CPUs and GPUs.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.41`
- Local answer excerpt: `Answer: IPPL achieves performance portability across CPUs and GPUs primarily through its use of Kokkos. The `initialize` function in Ippl.cpp initializes Kokkos with command-line arguments, which is crucial for setting up Kokkos to manage parallel execution...`

#### par_002 - Why does IPPL use Kokkos::View for field storage?

- Verdict: **Incorrect**
- Codex reference answer: IPPL uses `Kokkos::View` because fields need execution-space-aware storage, subviews, mirrors, and portable kernels across host/device memory spaces.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.27`
- Local answer excerpt: `Answer: The provided context does not specify why IPPL uses `Kokkos::View` for field storage. The chunks cover initialization of the IPPL environment, command-line parsing, and some utility functions, but do not discuss the use of `Kokkos::View`. Evidence: ...`

#### par_003 - How does IPPL parallelize loops over field indices using Kokkos RangePolicy?

- Verdict: **Correct**
- Codex reference answer: Loops are parallelized through `ippl::getRangePolicy` / `createRangePolicy` and the `ippl::parallel_for` wrapper over Kokkos `RangePolicy`/`MDRangePolicy`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.60`
- Local answer excerpt: `Answer: IPPL uses `createRangePolicy` from `ParallelDispatch.h` to construct range policies for parallel execution of loops over field indices. This method takes begin and end arrays as parameters, which define the index ranges for each dimension. Depending...`

#### par_004 - How does IPPL support mixed precision (float vs double) for fields?

- Verdict: **Partial**
- Codex reference answer: Precision is chosen by the field value type (`Field<float,...>` vs `Field<double,...>`), and the codebase also contains mixed-precision examples where fields/particles deliberately use different precisions.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.30`
- Local answer excerpt: `Answer: Based on the provided retrieved context, there is no explicit mention of how IPPL supports mixed precision (float vs double) for fields. The context covers utility functions, initialization, finalization, communication, and error handling but does n...`

#### par_005 - How does IPPL handle multiple execution spaces like OpenMP and CUDA in the same build?

- Verdict: **Partial**
- Codex reference answer: Multiple execution spaces are enabled at build time through `IPPL_PLATFORMS` and Kokkos/HeFFTe backend flags; IPPL also has container helpers for multi-space data.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.33`
- Local answer excerpt: `Answer: IPPL handles multiple execution spaces such as OpenMP and CUDA through conditional compilation within the `TypeForAllSpaces` struct defined in `Utility/TypeUtils.h`. This struct aggregates various memory and execution space types into variant types ...`

#### par_006 - What is the purpose of ParallelDispatch.h and what helpers does it expose?

- Verdict: **Correct**
- Codex reference answer: `ParallelDispatch.h` wraps Kokkos policies and functors, exposing `RangePolicy`, `getRangePolicy`, `createRangePolicy`, `parallel_for`, and `parallel_reduce`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.56`
- Local answer excerpt: `Answer: The file `ParallelDispatch.h` provides abstractions and utilities for parallel execution within the IPPL framework. It includes structs like `Coords`, `ExtractRank`, `ExtractReducerReturnType`, `FunctorWrapper`, and `RangePolicy`. Additionally, it e...`

#### par_007 - How does the Archive class serialize/deserialize Kokkos views for MPI transfer?

- Verdict: **Partial**
- Codex reference answer: `Archive` serializes Kokkos views into one-dimensional byte buffers with Kokkos kernels and `memcpy`, then deserializes them back into views on receive.
- Comparison: The answer has some relevant signal but undercuts itself with uncertainty or abstention.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: Insufficient information is provided to describe how the Archive class serializes/deserializes Kokkos views for MPI transfer. The retrieved chunks cover various parts of the MPI communication infrastructure but do not mention the Archive class or it...`

#### par_008 - How are MPI tags managed in IPPL to avoid collisions across subsystems?

- Verdict: **Partial**
- Codex reference answer: MPI tags are managed with fixed base tags in `Tags.h` and the cyclic tag allocator in `TagMaker`, which `Communicator` inherits.
- Comparison: The answer has some relevant signal but undercuts itself with uncertainty or abstention.
- Reference-token coverage: `0.50`
- Local answer excerpt: `Answer: The provided retrieved context does not contain specific information on how MPI tags are managed within IPPL to avoid collisions across subsystems. The context covers various modules and files but does not delve into details of MPI tag management or...`

#### par_009 - What does Kokkos::fence do, and when does IPPL call the wrapper ippl::fence?

- Verdict: **Incorrect**
- Codex reference answer: `Kokkos::fence()` waits for outstanding kernels; IPPL exposes `ippl::fence()` as a runtime wrapper in `Ippl.cpp` and also fences internally after many kernel/data-movement steps.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.14`
- Local answer excerpt: `Answer: The wrapper `ippl::fence` is not explicitly detailed in the provided context. However, based on the information given about `Window::fence`, it likely serves as a synchronization point for remote memory access (RMA) operations using MPI_Win_fence. T...`

### Boundary And Halo

#### bc_001 - What boundary condition types are provided in BcTypes.h?

- Verdict: **Correct**
- Codex reference answer: `BcTypes.h` provides periodic, constant, zero, extrapolating, and no-BC face classes.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.80`
- Local answer excerpt: `Answer: BcTypes.h defines several boundary condition classes within IPPL, including `ippl::ConstantFace` for applying constant value boundary conditions, `ippl::ExtrapolateFace` for extrapolating values at the boundaries, `ippl::NoBcFace` which does nothing...`

#### bc_002 - How does a periodic boundary condition differ from a Neumann boundary condition in IPPL Fields?

- Verdict: **Incorrect**
- Codex reference answer: Periodic BCs wrap values from the opposite side of the domain; there is no explicit `NeumannFace` class in this codebase, so the closest non-periodic behavior is constant/extrapolating face treatment.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.29`
- Local answer excerpt: `Answer: The provided context does not specify how a periodic boundary condition differs from a Neumann boundary condition in IPPL Fields. The context discusses the setup of periodic boundary conditions through methods like `setPeriodicBoundaryConditions` bu...`

#### bc_003 - How are ghost cells populated during a halo exchange?

- Verdict: **Partial**
- Codex reference answer: Ghost cells are populated mainly by `fillHalo()` / `PeriodicFace::apply()`: source slabs are packed, exchanged, and unpacked into ghost regions; `accumulateHalo_noghost()` is a different operation.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.32`
- Local answer excerpt: `Answer: Ghost cells are populated during a halo exchange by methods like `exchangeBoundaries` within the `HaloCells<T, Dim, ViewArgs...>` class. This method is called by other functions such as `accumulateHalo_noghost`, which prepares and triggers the bound...`

#### bc_004 - How are physical-cell values copied into ghost cells for periodic boundary conditions?

- Verdict: **Correct**
- Codex reference answer: Periodic ghost cells are filled from opposite-side physical cells in `applyPeriodicSerialDim()` and the multi-rank `PeriodicFace::apply()` path.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.32`
- Local answer excerpt: `Answer: The `setPeriodicBoundaryConditions` method configures periodic boundary conditions on fields by creating a vector of shared pointers to `PeriodicFace` objects for each face of the simulation grid. The `applyBCs` method then applies these boundary co...`

#### bc_005 - How does the absorbing boundary condition in the MaxwellSolvers module damp outgoing waves?

- Verdict: **Partial**
- Codex reference answer: The absorbing Maxwell BC uses second-order Mur-style formulas with precomputed weights and previous/current/next boundary values plus tangential neighbors to damp outgoing waves.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.42`
- Local answer excerpt: `Answer: The absorbing boundary condition in the `MaxwellSolvers` module is implemented through structs like `second_order_abc_corner`, `second_order_abc_edge`, and `second_order_abc_face` defined in `AbsorbingBC.h`. These structs likely contain methods that...`

### Numerical Meaning

#### num_001 - What does the FFT-based Poisson solver physically compute in terms of Coulomb's law?

- Verdict: **Incorrect**
- Codex reference answer: The FFT Poisson solvers compute electrostatic potential (and optionally field/gradient) from charge density, i.e. the discretized Coulomb potential corresponding to `-Δφ = ρ`.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.31`
- Local answer excerpt: `Answer: The retrieved context does not specify that IPPL includes an FFT-based Poisson solver. The context only mentions the `ippl::Poisson` class for solving Poisson's equation and a Conjugate Gradient method solver (`PoissonCG`). There is no information p...`

#### num_002 - What is the physical meaning of the fields advanced by the FDTD solver?

- Verdict: **Correct**
- Codex reference answer: The Maxwell solvers evolve electromagnetic field data: electric and magnetic fields (`E`, `B`) driven by a source/four-current field.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.43`
- Local answer excerpt: `Answer: The FDTD solver advances the electromagnetic field `A_np1` using data from previous and current fields (`A_nm1`, `A_n`) and a source term. The fields represent the vector potential of the electromagnetic field at different time steps. The solver use...`

#### num_007 - What are the numerical tradeoffs between the FFT and CG Poisson solvers in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: FFT Poisson is fast and direct on structured uniform grids with compatible BCs but less flexible; CG/PCG is iterative and may be slower/convergence-limited, but it is more flexible for alternative discretizations, BCs, and preconditioning.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.17`
- Local answer excerpt: `Answer: The retrieved context does not provide specific information about the numerical tradeoffs between the FFT and CG Poisson solvers in IPPL. However, it does describe the roles and some implementation details of both solvers. Evidence: - src/LinearSolv...`

### Build And Install

#### build_001 - Which third-party libraries does IPPL depend on, and what are they used for?

- Verdict: **Incorrect**
- Codex reference answer: Core third-party dependencies are MPI for distributed communication, Kokkos for performance portability, heFFTe for FFT backends/plans, FFTW/CuFFT as optional FFT backends, and GoogleTest for tests.
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.21`
- Local answer excerpt: `Answer: IPPL depends on Kokkos and MPI. Kokkos is used for portable parallelism across CPUs and GPUs, while MPI is used for distributed communication. Evidence: - data/raw/ippl/src/Ippl.cpp : ippl::initialize — Initialize Kokkos with the remaining command-l...`

#### build_002 - What C++ standard does IPPL require, and why?

- Verdict: **Incorrect**
- Codex reference answer: IPPL requires C++20, as stated in the README badge and the installation examples/configuration flags.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.10`
- Local answer excerpt: `Answer: The required C++ standard for IPPL is not explicitly stated in the provided context. Evidence: - data/raw/ippl/src/Ippl.cpp : initialize — Explanation of `ippl::initialize` Function does not mention the C++ standard. - data/raw/ippl/src/Ippl.h : Ipp...`

#### build_003 - How is IPPL configured with CMake to enable a GPU build?

- Verdict: **Incorrect**
- Codex reference answer: GPU builds are enabled through CMake options like `IPPL_PLATFORMS=CUDA` or `IPPL_PLATFORMS="HIP;OPENMP"` plus matching Kokkos/architecture/backend flags (`Kokkos_ARCH_*`, `CMAKE_CUDA_ARCHITECTURES`, `Kokkos_ENABLE_HIP`, `Heffte_ENABLE_ROCM`, etc.).
- Comparison: The answer misses the main Codex reference answer or points to the wrong subsystem.
- Reference-token coverage: `0.17`
- Local answer excerpt: `Answer: The provided retrieved context does not discuss how IPPL is configured with CMake to enable a GPU build. The context covers various aspects of the IPPL codebase including initialization functions, variant type implementations, and error handling but...`

#### build_004 - What options does INSTALLATION.md describe for configuring Kokkos for IPPL?

- Verdict: **Correct**
- Codex reference answer: `INSTALLATION.md` describes Kokkos version selection plus backend/architecture options used with IPPL builds, including CUDA and HIP/OpenMP examples and `IPPL_PLATFORMS` combinations.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.43`
- Local answer excerpt: `Answer: INSTALLATION.md describes the `IPPL_PLATFORMS` option for configuring Kokkos. This option can be set to `SERIAL`, `OPENMP`, `CUDA`, or `"OPENMP;CUDA"`, with a default of `SERIAL`. Evidence: - data/raw/ippl/INSTALLATION.md : IPPL_PLATFORMS — can be o...`

#### build_005 - How do I install IPPL on the EULER cluster according to the documentation?

- Verdict: **Correct**
- Codex reference answer: The EULER install guide says to connect with VPN/SSH, switch to the new software stack, purge modules, load GCC/CMake/CUDA/OpenMPI, clone the repo, configure a build, compile, and test on an interactive node.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.67`
- Local answer excerpt: `Answer: To install IPPL on the EULER cluster, follow these steps: 1. Connect to the cluster using SSH with trusted X11 forwarding enabled: `ssh -Y <username>@euler.ethz.ch`. 2. Transition to the new software stack and clean the environment: ``` env2lmod mod...`

### Testing And Workflow

#### test_002 - What naming conventions does WORKFLOW.md require for variables, constants, and member variables?

- Verdict: **Correct**
- Codex reference answer: `WORKFLOW.md` requires camelCase variables, CAPITAL_CASE compile-time constants, and member names suffixed with `_m`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.69`
- Local answer excerpt: `Answer: WORKFLOW.md requires the following naming conventions: - Variables should use camel casing (`myVariable`). - Compile time constants should use capital casing (`MY_CONSTANT`). - Member variables should be suffixed with `_m` (`memberVar_m`). Evidence:...`

#### test_003 - When should code use Kokkos::sqrt versus std::sqrt according to WORKFLOW.md?

- Verdict: **Correct**
- Codex reference answer: Use `std::sqrt` in host-only code, and `Kokkos::sqrt` in device-capable code such as `KOKKOS_INLINE_FUNCTION` kernels.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.75`
- Local answer excerpt: `Answer: According to WORKFLOW.md, for host-only code, standard library symbols (e.g., `std::sqrt`) should be used. For device-code or potentially device-executed code (such as those marked with `KOKKOS_INLINE_FUNCTION`), Kokkos symbols (e.g., `Kokkos::sqrt`...`

#### test_004 - How does IPPL profile MPI calls using mpiP?

- Verdict: **Incorrect**
- Codex reference answer: IPPL profiles MPI calls with mpiP by preloading `libmpiP.so`, optionally setting `MPIP` flags, then parsing the produced `.mpiP` output with the bundled `scripts/mpiP.py`.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.19`
- Local answer excerpt: `Answer: The retrieved context does not provide specific information on how IPPL profiles MPI calls using mpiP. The provided chunks cover initialization and management of MPI communication within IPPL but do not mention profiling tools like mpiP. Evidence: -...`

#### test_005 - What does the SLURM job template for Gwendolen in the README look like?

- Verdict: **Incorrect**
- Codex reference answer: The README does include a Gwendolen SLURM template showing the `gmerlin6` cluster, `gwendolen` partition, GPU count, and `srun ./<your_executable> <args> --kokkos-map-device-id-by=mpi_rank`.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.17`
- Local answer excerpt: `Answer: The provided retrieved context does not contain a specific SLURM job template for Gwendolen. The README.md file lists "SLURM Job scripts" under the table of contents but does not provide any actual templates or examples. Evidence: - src/README.md : ...`
