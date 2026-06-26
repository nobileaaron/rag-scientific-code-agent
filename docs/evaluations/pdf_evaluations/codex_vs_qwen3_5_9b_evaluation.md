# Codex GPT-5.4 Reference vs Qwen3.5 9B Evaluation

Generated: 2026-06-19 12:48:20 UTC

## Goal

This report evaluates the saved Qwen3.5 9B RAG answer run in `docs/evaluations/answers/eval_v2_qwen3.5-9B.json` against the Codex GPT-5.4 reference answers stored in `docs/evaluations/eval_answers_v2.json`. The format follows the older `codex_vs_local_llm_evaluation_20260423` report style, but the reference side here is the curated Codex V2 answer file rather than a new source-reading pass.

## Test Environment

### Codex Reference Side

- Model: `GPT-5.4` (Codex reference answers)
- Reference file: `docs/evaluations/eval_answers_v2.json`
- Question set: `docs/evaluations/eval_questions_v2.json`
- Evaluation basis: semantic comparison against the Codex reference answer for each question

### Local LLM Side

- Host: `merlin-g-100.psi.ch`
- Job / partition: `353461` on `gwendolen`
- Answer model: `qwen3.5:9b`
- Chunk explanation model: `qwen2.5-coder:32b`
- File / module / call-chain models: `qwen2.5-coder:32b-instruct-q4_K_M`, `qwen2.5-coder:32b-instruct-q4_K_M`, `qwen2.5-coder:32b-instruct-q4_K_M`
- Parser: `tree_sitter`
- Question count: `100`
- Answer prompt mode: `retrieval_answer_v2`
- Mean answer latency: `18.14s`
- Median answer latency: `11.45s`

### Retrieval Configuration Used by the Saved Run

- Candidate k: `20`
- Supplementary k: `3`
- Supplementary candidate k: `10`
- Vector store chunk count: `4441`
- Manifest embedding backend/model: `ollama` / `nomic-embed-text`

## Important Caveat

The per-question verdicts are a structured comparison against the Codex reference answers, not an independent re-reading of every IPPL source file. A question is marked Correct when the local answer captures the central facts of the Codex reference; Partial when it contains relevant signal but misses important scope or implementation detail; and Incorrect when it abstains, points to the wrong subsystem, or omits the core reference answer.

Because the reference answers are intentionally concise, the grading emphasizes the main technical nouns, implementation locations, and algorithmic steps rather than exact wording. Ambiguous cases were treated conservatively as Partial rather than Correct. For this model, the report also notes leaked self-correction/planning text as a presentation-quality issue, but the verdict still primarily reflects factual alignment with the Codex reference.

## Overall Result

| Metric | Value |
|---|---:|
| Questions | 100 |
| Correct | 70 |
| Partial | 19 |
| Incorrect | 11 |
| Average score (`Correct=1`, `Partial=0.5`, `Incorrect=0`) | 0.795 |
| Answers with leaked self-correction/planning text | 3 |

## Main Findings

- Strongest areas: Api Usage, Boundary And Halo. These are mostly questions where the retrieved answer can be anchored to one well-described class, header, implementation file, or usage pattern.
- Weakest areas: Build And Install, Testing And Workflow. These questions require cross-file synthesis, precise implementation-location recovery, or careful numerical interpretation.
- This Qwen3.5 9B run is much slower than the Qwen2.5 q4_K_M runs evaluated earlier, with mean latency `18.14s` and median latency `11.45s`.
- Output quality is a major issue: `3` answers contain visible self-correction or planning text such as “Wait”, “Revised Evidence”, or “Final Plan”. These answers may still include correct facts, but they are not clean final responses.
- Several answers show the model trying to enforce strict grounding, but that often bloats the response and can obscure the actual benchmark answer.
- Remaining factual misses are still mostly retrieval/grounding misses: plausible evidence from neighboring IPPL subsystems can displace the exact Codex reference answer.

## Category Breakdown

| Category | Questions | Correct | Partial | Incorrect | Avg score |
|---|---:|---:|---:|---:|---:|
| File Purpose | 13 | 9 | 4 | 0 | 0.846 |
| Definition Location | 15 | 13 | 0 | 2 | 0.867 |
| Class Responsibility | 13 | 9 | 2 | 2 | 0.769 |
| Algorithm | 12 | 8 | 3 | 1 | 0.792 |
| Data Flow | 9 | 5 | 3 | 1 | 0.722 |
| Api Usage | 12 | 11 | 1 | 0 | 0.958 |
| Parallelism And Kokkos | 9 | 6 | 2 | 1 | 0.778 |
| Boundary And Halo | 5 | 4 | 1 | 0 | 0.900 |
| Numerical Meaning | 3 | 2 | 0 | 1 | 0.667 |
| Build And Install | 5 | 1 | 2 | 2 | 0.400 |
| Testing And Workflow | 4 | 2 | 1 | 1 | 0.625 |

## Detailed Per-Question Evaluation

### File Purpose

#### file_001 - What does Ippl.h do?

- Verdict: **Correct**
- Codex reference answer: Declares the top-level IPPL runtime handles (`Comm`, `Env`, `Info`, `Warn`, `Error`) and the lifecycle wrappers `initialize`, `finalize`, `fence`, and `abort`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols. The answer also leaks internal self-correction/planning text, which hurts presentation quality.
- Reference-token coverage: `0.53`
- Local answer excerpt: `Answer: Ippl.h serves as a central header file in the root module for IPPL, providing essential functions and variables required for managing application initialization, termination, communication, and error handling within parallel computations. It exposes...`

#### file_002 - What is the purpose of Ippl.cpp?

- Verdict: **Correct**
- Codex reference answer: Implements runtime setup/teardown: command-line option parsing, MPI communicator/environment creation, logger setup, Kokkos init/finalize, and abort/fence helpers.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.46`
- Local answer excerpt: `Answer: The `Ippl.cpp` file provides essential utility functions for managing runtime environment setup, configuration option validation, synchronization points (e.g., fence), resource cleanup via finalize, and standardized error handling within the IPPL fr...`

#### file_003 - What does FFT.hpp implement?

- Verdict: **Correct**
- Codex reference answer: Implements `FFTBase` setup plus the FFT specialization family for complex/real, sine, cosine, and cosine-I transforms on IPPL fields via heFFTe.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.41`
- Local answer excerpt: `Answer: The `FFT.hpp` file defines a base class `ippl::FFTBase<Field, FFT, Backend, T>` for common FFT functionality and provides specializations for different transform types including `RCTransform`, `CCTransform`, `SinTransform`, `CosTransform`, `Cos1Tran...`

#### file_004 - What is BareField.h responsible for?

- Verdict: **Partial**
- Codex reference answer: Defines the core distributed field container: Kokkos-backed storage, owned/allocated domains, field layout access, halo exchange hooks, and expression-style assignment.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.30`
- Local answer excerpt: `Answer: The file defines the `ippl::BareField` class, which serves as a fundamental abstraction for representing fields in scientific computations within the IPPL framework. It includes methods to access properties such as allocation status, communicator, d...`

#### file_005 - What does Field.h add on top of BareField?

- Verdict: **Correct**
- Codex reference answer: Adds mesh awareness and boundary-condition management on top of `BareField`, plus volume integral/average helpers.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.67`
- Local answer excerpt: `Answer: The `ippl::Field` class adds boundary condition accessors (`getFieldBC`, `setFieldBC`) and mesh interaction support via `get_mesh()` that are not present in `BareField`. Additionally, it provides specialized volume analysis methods like `getVolumeAv...`

#### file_006 - What role does HaloCells.h play in IPPL?

- Verdict: **Partial**
- Codex reference answer: Defines the halo-exchange machinery for fields: pack/unpack, boundary exchange, and periodic handling for ghost cells.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.33`
- Local answer excerpt: `Answer: The `HaloCells` class (defined in `data/raw/ippl/src/Field/HaloCells.h`) manages halo cells for field data to facilitate inter-process communication (IPC) in parallel computations. It handles guard/ghost cells of BareField and performs operations su...`

#### file_007 - What is the purpose of FieldLayout.h?

- Verdict: **Correct**
- Codex reference answer: Defines how a global `NDIndex` domain is partitioned across MPI ranks, including local subdomains, neighbors, and communication ranges.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.36`
- Local answer excerpt: `Answer: The `FieldLayout.h` file defines the `FieldLayout` class and related helper functions within the `ippl` namespace to manage field distribution, domain information, and layout configurations for scientific computations. The `FieldLayout<Dim>` templat...`

#### file_008 - What does ParticleBase.h define?

- Verdict: **Partial**
- Codex reference answer: Defines the generic particle container base class with positions, optional IDs, registered attributes, and a particle layout that controls migration.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.23`
- Local answer excerpt: `Answer: The `ParticleBase` class declaration is defined in `src/Particle/ParticleBase.h`, which serves as a foundational abstraction for managing particle data within IPPL and provides accessors such as `getAttributeNum`, `getLayout`, `getLocalNum`, `getTot...`

#### file_009 - What is the purpose of ParticleSpatialLayout.h?

- Verdict: **Partial**
- Codex reference answer: Defines the spatial particle layout that decides ownership by region and migrates particles to the correct rank after motion.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The `ParticleSpatialLayout` class is designed to manage spatial layout and communication regions for particles within the IPPL library, ensuring efficient distribution of particles across computational nodes based on their positions relative to a fi...`

#### file_010 - What does ParticleAttrib.h implement?

- Verdict: **Correct**
- Codex reference answer: Implements the `ParticleAttrib` storage object: a Kokkos-view-backed particle attribute with resize, serialization, and mirror/access helpers.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.44`
- Local answer excerpt: `Answer: The `ParticleAttrib.h` header defines the class template `ippl::ParticleAttrib` within the `ippl` namespace, providing serialization, memory management, and data retrieval operations associated with particles in simulations. It includes methods such...`

#### file_011 - What is UniformCartesian.h for?

- Verdict: **Correct**
- Codex reference answer: Defines the uniform Cartesian mesh class with spacing, origin, cell volume, total mesh volume, and vertex-position helpers.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.46`
- Local answer excerpt: `Answer: The `UniformCartesian.h` file defines the `ippl::UniformCartesian` class family within the `source:Meshes` module, specializing uniform Cartesian meshes by inheriting from a base `Mesh<T, Dim>` and providing accessors like `getDeltaVertex`, `getCell...`

#### file_012 - What does OrthogonalRecursiveBisection.h do?

- Verdict: **Correct**
- Codex reference answer: Declares the orthogonal recursive bisection domain-decomposition/load-balancing class and its cut/median/repartition helpers.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.67`
- Local answer excerpt: `Answer: The `OrthogonalRecursiveBisection.h` file defines the class `ippl::OrthogonalRecursiveBisection`, which implements an orthogonal recursive bisection algorithm for decomposing computational domains into balanced subdomains across multiple processors....`

#### file_013 - What is the purpose of CIC.h in the Interpolation subsystem?

- Verdict: **Correct**
- Codex reference answer: Declares the first-order cloud-in-cell interpolation helpers for scatter/gather between particles and grid fields.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.62`
- Local answer excerpt: `Answer: The `CIC.h` file in the Interpolation subsystem defines function declarations within the `ippl::detail` namespace that handle interpolation operations, specifically for Cloud-in-Cell (CIC) methods. It declares functions including `scatterToField`, `...`

### Definition Location

#### loc_001 - Where is FFT initialization implemented in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: FFT initialization lives in `src/FFT/FFT.hpp`, especially `FFTBase` construction/setup and the transform-specific constructors that build the heFFTe plans.
- Comparison: The answer cites a different implementation location than the Codex reference.
- Reference-token coverage: `0.35`
- Local answer excerpt: `Answer: The provided retrieved chunks do not contain specific information regarding where FFT initialization is implemented within the IPPL codebase, despite mentioning that IPPL builds upon heFFTe (distributed FFTs). The available `initialize` functions de...`

#### loc_002 - Where does IPPL set up the MPI environment?

- Verdict: **Correct**
- Codex reference answer: IPPL sets up MPI in `src/Ippl.cpp::initialize()` by constructing `mpi::Environment` and `mpi::Communicator`; the low-level `MPI_Init` check/call is in `src/Communicate/Environment.cpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.33`
- Local answer excerpt: `Answer: IPPL's context shows it uses `Comm->getCommunicator()` to obtain a communicator object during FFT and field setup operations (in files like `data/raw/ippl/src/FFT/FFT.hpp`), but none of the retrieved chunks explicitly describe where IPPL itself init...`

#### loc_003 - Where is Kokkos initialized and finalized inside IPPL?

- Verdict: **Correct**
- Codex reference answer: Kokkos is initialized and finalized directly in `src/Ippl.cpp` inside `ippl::initialize()` and `ippl::finalize()`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.67`
- Local answer excerpt: `Answer: Kokkos initialization occurs explicitly at the call site of `Kokkos::initialize(argc, argv)` inside the implementation function `ippl::initialize` defined in `data/raw/ippl/src/Ippl.cpp`. Finalization is managed by the framework's utility infrastruc...`

#### loc_004 - Where is the orthogonal recursive bisection load balancer implemented?

- Verdict: **Correct**
- Codex reference answer: The ORB load balancer is implemented in `src/Decomposition/OrthogonalRecursiveBisection.hpp` with declarations in the matching header.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.64`
- Local answer excerpt: `Answer: The orthogonal recursive bisection load balancer is implemented in the `src/Decomposition` directory of the codebase. The primary interface header file located at `data/raw/ippl/src/Decomposition/OrthogonalRecursiveBisection.h` defines the core clas...`

#### loc_005 - Where are boundary conditions applied to a Field?

- Verdict: **Correct**
- Codex reference answer: Field BCs are attached in `Field::setFieldBC()` and actually applied through `BConds::apply()` and the concrete face classes in `BcTypes.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact. The answer also leaks internal self-correction/planning text, which hurts presentation quality.
- Reference-token coverage: `0.56`
- Local answer excerpt: `Answer: Boundary conditions are configured on a field via the `ippl::Field` class using `setFieldBC(BConds_t& bc)`, which stores them in the private member variable `bc_m`. In FDTD simulations within solvers like `NonStandardFDTDSolver`, boundary checks and...`

#### loc_006 - Where is the CIC (cloud-in-cell) scatter implemented?

- Verdict: **Correct**
- Codex reference answer: CIC scatter is implemented in `src/Interpolation/CIC.hpp`, primarily `scatterToPoint()` and `scatterToField()`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.82`
- Local answer excerpt: `Answer: The Cloud-in-Cell (CIC) scatter implementation is located in the Interpolation module, specifically within `data/raw/ippl/src/Interpolation/CIC.hpp`, where definitions for functions like `scatterToField` and `scatterToPoint` are provided to distribu...`

#### loc_007 - Where is the CIC gather implemented?

- Verdict: **Correct**
- Codex reference answer: CIC gather is implemented in `src/Interpolation/CIC.hpp`, primarily `gatherFromPoint()` and `gatherFromField()`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.82`
- Local answer excerpt: `Answer: The CIC gather operations are implemented in `CIC.hpp`, which defines methods like `gatherFromField` and `gatherFromPoint` within the `ippl::detail` namespace using Cloud-in-Cell (CIC) interpolation techniques at path data/raw/ippl/src/Interpolation...`

#### loc_008 - Where is halo exchange for BareField implemented?

- Verdict: **Correct**
- Codex reference answer: Halo exchange for `BareField` is surfaced in `src/Field/BareField.hpp` and actually performed in `src/Field/HaloCells.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.54`
- Local answer excerpt: `Answer: The implementation uses the `detail::HaloCells` class which manages guard/ghost cells and handles inter-process communication (IPC) of halo data between distributed field partitions. In `BareField`, this is exposed as a type alias (`halo_type = deta...`

#### loc_009 - Where are the FFT-based open-boundary Poisson solver routines defined?

- Verdict: **Correct**
- Codex reference answer: The FFT open-boundary Poisson routines are defined in `src/PoissonSolvers/FFTOpenPoissonSolver.h` and `src/PoissonSolvers/FFTOpenPoissonSolver.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `1.00`
- Local answer excerpt: `Answer: The FFT-based open-boundary Poisson solver routines are defined in `src/PoissonSolvers/FFTOpenPoissonSolver.hpp` and declared in the corresponding header file `src/PoissonSolvers/FFTOpenPoissonSolver.h`. The class template is named `ippl::FFTOpenPoi...`

#### loc_010 - Where is the conjugate gradient solver algorithm implemented?

- Verdict: **Correct**
- Codex reference answer: The CG/PCG algorithm implementation is in `src/LinearSolvers/PCG.h`; the Poisson wrapper that instantiates it is `src/PoissonSolvers/PoissonCG.h`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.83`
- Local answer excerpt: `Answer: According to the retrieved codebase documentation, the Conjugate Gradient (CG) solver algorithm is primarily implemented via the `ippl::CG` class defined in the header file located at **src/LinearSolvers/PCG.h**. This core implementation supports so...`

#### loc_011 - Where is the FEM Poisson solver implemented?

- Verdict: **Correct**
- Codex reference answer: The FEM Poisson solver is implemented in `src/PoissonSolvers/FEMPoissonSolver.h`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.83`
- Local answer excerpt: `Answer: The FEM Poisson solver is implemented by the `FEMPoissonSolver` class located at `data/raw/ippl/src/PoissonSolvers/FEMPoissonSolver.h`, which inherits from `Poisson<FieldLHS, FieldRHS>` and uses a Preconditioned Conjugate Gradient (PCG) algorithm. T...`

#### loc_012 - Where is the FDTD Maxwell solver base class defined?

- Verdict: **Incorrect**
- Codex reference answer: The FDTD Maxwell solver base class is defined in `src/MaxwellSolvers/FDTDSolverBase.h` with implementation in `FDTDSolverBase.hpp`.
- Comparison: The answer cites a different implementation location than the Codex reference.
- Reference-token coverage: `0.60`
- Local answer excerpt: `Answer: The retrieved chunks do not contain a specific definition location for an "FDTD Maxwell solver base class." Chunk 2 describes `ippl::FieldSolverBase` as a generic abstract base class for field solvers in the Manager directory, but no chunk explicitl...`

#### loc_013 - Where is the LagrangeSpace class defined?

- Verdict: **Correct**
- Codex reference answer: The `LagrangeSpace` class is defined in `src/FEM/LagrangeSpace.h` with methods implemented in `src/FEM/LagrangeSpace.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.67`
- Local answer excerpt: `Answer: The `LagrangeSpace` class is defined in the header file located at `data/raw/ippl/src/FEM/LagrangeSpace.h`, which resides within the FEM module and defines the entity under the `ippl` namespace for Lagrangian finite element computations. The impleme...`

#### loc_014 - Where is the particle update routine (that moves particles across ranks) implemented?

- Verdict: **Correct**
- Codex reference answer: Particle migration between ranks is implemented in `ParticleSpatialLayout::update()` in `src/Particle/ParticleSpatialLayout.hpp`.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.80`
- Local answer excerpt: `Answer: The primary routine that moves particles across ranks is `ippl::ParticleSpatialLayout<T, Dim, Mesh, Properties...>::update`, located at `data/raw/ippl/src/Particle/ParticleSpatialLayout.hpp`. For spatial overlap layouts specifically, it uses the com...`

#### loc_015 - Where are IPPL timers defined?

- Verdict: **Correct**
- Codex reference answer: IPPL timers are defined by the singleton timing layer in `src/Utility/IpplTimings.h/.cpp`, not just the low-level `Timer` helper.
- Comparison: The answer names the relevant implementation location and captures the core reference fact.
- Reference-token coverage: `0.31`
- Local answer excerpt: `Answer: IPPL timers are configured during initialization through `ippl::initialize` function located at `data/raw/ippl/src/Ippl.cpp`. This function parses command-line arguments to configure timer settings including the fence enable option via `Timer::enabl...`

### Class Responsibility

#### cls_001 - What is the main responsibility of the BareField class?

- Verdict: **Correct**
- Codex reference answer: `BareField` is the core distributed field storage class: it owns the data view, domain metadata, layout link, and halo operations.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.62`
- Local answer excerpt: `Answer: The `ippl::BareField` class is a fundamental abstraction for representing fields in scientific computations within the IPPL framework. Its main responsibility includes managing memory and access patterns for multidimensional fields, including handli...`

#### cls_002 - What is the main responsibility of the Field class compared to BareField?

- Verdict: **Incorrect**
- Codex reference answer: `Field` extends `BareField` with a mesh, boundary-condition container, and mesh-aware integral/average semantics.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.19`
- Local answer excerpt: `Answer: The retrieved context does not contain information comparing a `Field` class to `ippl::BareField`. The available chunks only document `ippl::BareField`, which manages memory and access patterns for multidimensional fields with ghost cells, handles h...`

#### cls_003 - What does the FieldLayout class do and what are its main template parameters?

- Verdict: **Correct**
- Codex reference answer: `FieldLayout<Dim>` distributes a global `NDIndex<Dim>` over ranks and stores local domains, neighbors, and communication ranges; its only template parameter is `Dim`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.68`
- Local answer excerpt: `Answer: The FieldLayout class distributes how a given index space (represented by an NDIndex object) is distributed among MPI ranks. It performs initial partitioning, allowing specific dimensions to be marked as 'SERIAL' instead of 'PARALLEL'. The main temp...`

#### cls_004 - What is the purpose of the ParticleBase class and how is it meant to be used?

- Verdict: **Correct**
- Codex reference answer: `ParticleBase` is the user-extensible base container for particles; derived classes add attributes and register them so layout-driven migration can move them.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.60`
- Local answer excerpt: `Answer: The `ParticleBase` class serves as a foundational container and manager for particle data within IPPL, handling attributes like spatial positions (`R`) and global indices (`ID`). It is designed to be used by defining derived classes that inherit fro...`

#### cls_005 - What does the ParticleSpatialLayout class do?

- Verdict: **Correct**
- Codex reference answer: `ParticleSpatialLayout` decides which spatial region/rank owns each particle and performs the migration/update workflow after particles move.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.39`
- Local answer excerpt: `Answer: The `ippl::ParticleSpatialLayout` template class manages spatial layout and communication regions for particles within the IPPL framework, designed to optimize particle interactions across processors based on their positions relative to a fixed grid...`

#### cls_006 - What is the responsibility of UniformCartesian?

- Verdict: **Correct**
- Codex reference answer: `UniformCartesian` represents a uniform Cartesian mesh and exposes spacing/origin/volume and vertex-position geometry queries.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.62`
- Local answer excerpt: `Answer: The `UniformCartesian` class represents a uniform-spacing Cartesian mesh within IPPL's `source:Meshes` module, inheriting from `Mesh<T, Dim>`. Its responsibility is to encapsulate properties and operations associated with uniform Cartesian grids for...`

#### cls_007 - What does the Mesh base class define?

- Verdict: **Incorrect**
- Codex reference answer: `Mesh` is the abstract base interface for meshes: origin, grid size, spacing, vertex positions, and volume queries.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.20`
- Local answer excerpt: `Answer: The provided context is insufficient to detail what a generic Mesh base class defines; instead it documents centering abstractions such as the `CartesianCentering` class used for managing operations on Cartesian grids in mesh-based numerical simulat...`

#### cls_008 - What is the responsibility of the Communicator class in ippl::mpi?

- Verdict: **Correct**
- Codex reference answer: `ippl::mpi::Communicator` wraps MPI point-to-point, collectives, tag handling, and managed communication buffers.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The `ippl::mpi::Communicator` class encapsulates MPI communication functionalities including barriers, rank retrieval, size determination (`rank`, `size`, `barrier`). It manages MPI communicators and associated operations with methods such as `probe...`

#### cls_009 - What is the role of the Environment class in ippl::mpi?

- Verdict: **Correct**
- Codex reference answer: `ippl::mpi::Environment` manages MPI environment lifetime checks/teardown and provides an abort hook.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.50`
- Local answer excerpt: `Answer: The `ippl::mpi::Environment` class manages MPI environment setup and teardown within the IPPL codebase, essential for parallel scientific computations. It provides methods including `initialized()` to check if MPI is initialized, `finalized()` to ve...`

#### cls_010 - What does the Archive class do in the Communicate module?

- Verdict: **Partial**
- Codex reference answer: `Archive` serializes and deserializes Kokkos views and vector-valued views into raw byte buffers for MPI transfer.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.23`
- Local answer excerpt: `Answer: The `Archive` class in the `source:Communicate` module is defined as a templated family (`ippl::detail::Archive<Properties...>`) responsible for managing data buffers and handling serialization/deserialization operations within MPI contexts. Specifi...`

#### cls_011 - What is the role of the BConds class?

- Verdict: **Correct**
- Codex reference answer: `BConds` is the container of boundary-condition faces and orchestrates neighbor discovery, BC application, and ghost-to-physical assignment.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The `ippl::BConds` class serves as the container for field boundary condition (BC) objects in IPPL, responsible for managing and applying BCs by calling specific operations on associated BC classes such as finding neighbors and writing ghost cells t...`

#### cls_012 - What is the role of the BaseManager class?

- Verdict: **Correct**
- Codex reference answer: `BaseManager` provides the simulation loop skeleton: `pre_run`, `pre_step`, `advance`, `post_step`, and `run(nt)`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.87`
- Local answer excerpt: `Answer: The `BaseManager` class in the `ippl` namespace is an abstract base class that manages simulation lifecycles using a template method pattern, defining hooks such as `pre_run`, `pre_step`, `advance`, and `post_step`. The main `run(int nt)` orchestrat...`

#### cls_013 - What does the Index class represent and what operations does it support?

- Verdict: **Partial**
- Codex reference answer: `Index` represents a regular strided integer range/slice and supports range-style arithmetic and comparison operations used in domain descriptions.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.24`
- Local answer excerpt: `Answer: No explicit "Index class" is identified in the retrieved context. However, Chunk 1 describes a free function `index()` (lowercase) that returns an index value indicating which variant type is currently active within an object of a variant type. It s...`

### Algorithm

#### alg_001 - How does the FFT-based open-boundary Poisson solver compute the electrostatic potential?

- Verdict: **Correct**
- Codex reference answer: The FFT open-boundary solver embeds/extends the RHS onto larger domains, FFTs both the density and a precomputed Green's function, multiplies in Fourier space, inverse transforms, and optionally computes gradients/Hessians.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.56`
- Local answer excerpt: `Answer: The FFT-based Poisson solver computes electrostatic potential through a Fourier-space approach that transforms charge density (ρ) into frequency domain, multiplies by the Green's function representation in k-space, and applies inverse transform to r...`

#### alg_002 - How does the FFT-based periodic Poisson solver work in IPPL?

- Verdict: **Correct**
- Codex reference answer: The periodic FFT solver FFTs the charge density, divides each Fourier mode by `|k|^2` (with the zero mode handled separately), then inverse transforms; gradients are computed by multiplying by `ik/|k|^2` before the inverse FFT.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.45`
- Local answer excerpt: `Answer: The `FFTTruncatedGreenPeriodicPoissonSolver` class solves the periodic Poisson equation ($\nabla^2 \phi = -\rho$) and computes electric fields via $E = -\nabla \phi$. The solver utilizes a truncated Green's function defined as $G(r) = \text{forceCon...`

#### alg_003 - How does the truncated Green periodic Poisson solver differ from the standard periodic one?

- Verdict: **Correct**
- Codex reference answer: The truncated-Green periodic solver replaces the simple `1/|k|^2` kernel with the FFT of a truncated/erf-smoothed Green's function `forceConstant * erf(alpha r) / r`, then follows the same transform-multiply-inverse pattern.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.25`
- Local answer excerpt: `Answer: Based on the retrieved context, the **truncated Green** version (`FFTTruncatedGreenPeriodicPoissonSolver`) differs from a standard **periodic** solver (e.g., `FFTPeriodicPoissonSolver`) primarily by using a "truncated Green's function" to handle per...`

#### alg_004 - How does IPPL's CG solver iterate in the PCG.h implementation?

- Verdict: **Incorrect**
- Codex reference answer: In `PCG.h`, the CG iteration forms residual/direction fields, applies the operator, computes `alpha` and `beta` from inner products, updates the solution/residual/direction, and stops on tolerance or iteration count; the preconditioned variant inserts `M^{-1}` applications on the residual.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.23`
- Local answer excerpt: `Answer: The retrieved context does not describe the iteration mechanics of `ippl::PCG` from PCG.h; only API methods are documented (setOperator, setPreconditioner, getIterationCount) without their internal implementations or algorithmic workflow for CG iter...`

#### alg_005 - How is cloud-in-cell interpolation performed in IPPL (both scatter and gather directions)?

- Verdict: **Partial**
- Codex reference answer: CIC computes lower/upper weights per axis, scatters with atomic adds to the `2^Dim` neighboring grid points, and gathers by summing the same weighted stencil back to particles.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.26`
- Local answer excerpt: `Answer: Cloud-in-cell interpolation is implemented via `ippl::detail::scatterToField` and `ippl::detail::gatherFromField`, with index sequence arguments (`std::make_index_sequence<1 << Field::dim>{}`) representing dimension-specific operations. The scatter ...`

#### alg_006 - How does the standard FDTD solver advance the electromagnetic field in time?

- Verdict: **Correct**
- Codex reference answer: The standard FDTD solver advances the source-like field with a second-order finite-difference update using the previous and current time levels plus neighboring cells and source terms, then fills halos and reapplies BCs.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.42`
- Local answer excerpt: `Answer: The `StandardFDTDSolver` class advances fields in time via its `step()` method (in `MaxwellSolvers/StandardFDTDSolver.hpp`) by computing the next electromagnetic field values (`A_np1`) from current (`A_n`) and previous (`A_nm1`) time step data using...`

#### alg_007 - How does the LagrangeSpace class evaluate degrees of freedom per element?

- Verdict: **Correct**
- Codex reference answer: `LagrangeSpace` evaluates element DOFs by mapping local element indices to global DOF indices, then evaluates order-1 reference-element shape functions and gradients on those local DOFs.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.63`
- Local answer excerpt: `Answer: The LagrangeSpace class does not directly evaluate degrees of freedom per element; instead it inherits a DOF count parameter `getLagrangeNumElementDOFs(Dim, Order)` in its template specialization passed to the base FiniteElementSpace constructor. Th...`

#### alg_008 - How is Gauss-Jacobi quadrature implemented and used in IPPL FEM?

- Verdict: **Correct**
- Codex reference answer: Gauss-Jacobi quadrature computes nodes/weights by Newton iteration on Jacobi polynomial roots, starting from Chebyshev or LehrFEM-style guesses, and uses the resulting rule on reference elements in FEM.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.62`
- Local answer excerpt: `Answer: Gauss-Jacobi quadrature is implemented via the `ippl::GaussJacobiQuadrature` class located at `data/raw/ippl/src/FEM/Quadrature/GaussJacobiQuadrature.h`. It inherits from `Quadrature<T, NumNodes1D, ElementType>` as an abstract base that defines pure...`

#### alg_009 - How does the orthogonal recursive bisection decide where to cut the domain?

- Verdict: **Correct**
- Codex reference answer: ORB chooses a cut axis from the domain geometry and then finds a weight-balanced cut/median so recursive splits distribute load more evenly.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.47`
- Local answer excerpt: `Answer: The orthogonal recursive bisection decides the cut location by first identifying "the longest side of a multi-dimensional index" as the optimal axis for division using `ippl::OrthogonalRecursiveBisection::findCutAxis`. This method compares dimension...`

#### alg_010 - How does inverse transform sampling generate particles from a given distribution in IPPL?

- Verdict: **Correct**
- Codex reference answer: Inverse transform sampling maps uniform random values in CDF space to samples by estimating the inverse and refining it with Newton-Raphson, dimension by dimension.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.47`
- Local answer excerpt: `Answer: Inverse transform sampling in IPPL uses the `ippl::random::Distribution` and `ippl::random::InverseTransformSampling` classes to generate samples from target probability distributions by transforming uniformly distributed random numbers via inverse ...`

#### alg_011 - How does the FFT class interface with heFFTe to perform complex-to-complex and real-to-complex transforms?

- Verdict: **Partial**
- Codex reference answer: The FFT layer builds heFFTe boxes/plans in `setup()`, copies IPPL field data into the required views/subviews, calls heFFTe forward/backward transforms, and copies results back for CC/RC/DST/DCT variants.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.31`
- Local answer excerpt: `Answer: The `FFT` class interfaces with heFFTe by using template parameters such as `CCTransform`, `RCTransform`, and others to define transform types within the IPPL library while utilizing backend configurations in the ippl::detail namespace for optimizat...`

#### alg_012 - How does IPPL's preconditioned CG use the preconditioner defined in Preconditioner.h?

- Verdict: **Partial**
- Codex reference answer: PCG applies a chosen preconditioner from `Preconditioner.h` to the residual, uses the preconditioned residual in its inner products and direction updates, and iterates until tolerance/max iterations.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.22`
- Local answer excerpt: `Answer: IPPL's preconditioned Conjugate Gradient (CG) solver uses `ippl::preconditioner` abstract base class defined in `Preconditioner.h` to configure preconditioning strategies before solving linear systems with the CG algorithm. The `setPreconditioner` m...`

### Data Flow

#### flow_001 - How does charge density flow from particles to the grid in a typical PIC step in IPPL?

- Verdict: **Correct**
- Codex reference answer: In the PIC workflow, particle charges and positions are deposited onto the grid with CIC (`scatter`) or FEM assembly (`assemble_rhs_from_particles`), accumulated into `rho`, and then normalized/background-shifted in the manager before solving.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.35`
- Local answer excerpt: `Answer: The charge density flows from particles to the grid through `mble_rhs_from_particles(con` (also called `assemble_rhs_from_particles`) in IPPL, which performs a FEM-based PIC deposition step into field nodes/DOFs using shape functions and atomic oper...`

#### flow_002 - How does the electric field flow from the grid back to particles after a Poisson solve?

- Verdict: **Correct**
- Codex reference answer: After the field solve, the manager gathers the electric field back to particles with CIC `gather(...)` or FEM `interpolate_grad_to_diracs(...)`, storing particle-local `E` values for the push step.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.48`
- Local answer excerpt: `Answer: Based on the retrieved codebase documentation and implementation details, there is no explicit flow described for transferring electric field values from grid back to particles after a Poisson solve within the provided context. The `assemble_rhs_fro...`

#### flow_003 - How are halo cells exchanged between neighboring MPI ranks for a BareField?

- Verdict: **Partial**
- Codex reference answer: Halo exchange uses `FieldLayout` neighbor/range metadata to pack field subviews, send/receive them with MPI, unpack into ghost or physical regions, and handle serial-periodic dimensions locally.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.30`
- Local answer excerpt: `Answer: The `BareField` class uses its associated `getHalo()` accessor method and relies on the underlying `ippl::detail::HaloCells<T, Dim, ViewArgs...>` management mechanism for halo exchange between MPI ranks. The primary symbol handling communication is ...`

#### flow_004 - How are particles migrated between MPI ranks by ParticleSpatialLayout?

- Verdict: **Correct**
- Codex reference answer: `ParticleSpatialLayout::update()` applies particle BCs, locates destination ranks, advertises receive counts with RMA, sends all registered attributes, destroys invalid local particles, and receives the incoming ones.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.42`
- Local answer excerpt: `Answer: The `ParticleSpatialLayout::update` method migrates particles between MPI ranks after each time step when particle positions change enough to affect global layout, invoking a load balancing routine instead of regular updates at specified frequency. ...`

#### flow_005 - How does FieldLayout decide which index ranges live on which rank?

- Verdict: **Incorrect**
- Codex reference answer: `FieldLayout` uses the partitioner and the requested parallel/serial decomposition flags to assign each rank a local `NDIndex`, plus neighbor and communication range tables.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.33`
- Local answer excerpt: `Answer: The retrieved context indicates that `FieldLayout<Dim>` class template (defined in `src/FieldLayout/FieldLayout.hpp`) manages field layouts and their associated domain decompositions for parallel scientific simulations. Key methods supporting this i...`

#### flow_006 - How is a ParameterList used to configure the FFT and solver classes?

- Verdict: **Correct**
- Codex reference answer: `ParameterList` is merged into FFT and solver objects, then consumed by `setup()/initialize()/solve()` for communication mode, pencil/reorder flags, transform direction, solver type, tolerances, preconditioner settings, and output type.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.48`
- Local answer excerpt: `Answer: In IPPL, `ParameterList` objects manage configuration values via named keys using types such as `double`, `std::string`, or nested lists. The **FFT** class accepts a `const ParameterList& params` argument in its constructor (specifically `ippl::FFT<...`

#### flow_007 - How does data flow through the BaseManager's pre_step / advance / post_step hooks during a simulation?

- Verdict: **Partial**
- Codex reference answer: `BaseManager::run()` executes `pre_step()`, `advance()`, and `post_step()` for each timestep; derived managers use those hooks for deposit/solve/gather, time updates, and output.
- Comparison: The answer has some relevant signal but undercuts itself with uncertainty or abstention.
- Reference-token coverage: `0.43`
- Local answer excerpt: `Answer: The retrieved context identifies that `ippl::BaseManager` defines essential lifecycle methods including `run`, `pre_step`, `advance`, and `post_step` within the IPPL namespace (Chunk 1). These hooks are crucial for controlling execution flow and man...`

#### flow_008 - How does the FEM solver move data between fields and FEMVector representations?

- Verdict: **Correct**
- Codex reference answer: FEM solvers move data by assembling field data into FEM load/stiffness representations (`evaluateLoadVector`, `evaluateAx`, `FEMVector`) and then interpolating the solved field quantities back where needed.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.35`
- Local answer excerpt: `Answer: Data movement between fields and FEMVector representations within parallel distributed simulations is primarily handled via halo exchange operations defined in `FEMVector.hpp` using MPI communication wrappers found under the IPPL communicator infras...`

#### flow_009 - How does OrthogonalRecursiveBisection redistribute particles after rebalancing?

- Verdict: **Partial**
- Codex reference answer: After ORB recomputes the decomposition, particle ownership changes are realized by updating the layout/regions and then migrating particles with the usual particle update path.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.22`
- Local answer excerpt: `Answer: The `OrthogonalRecursiveBisection::binaryRepartition` method redistributes particles through a scatter operation (`scatterR`) that is invoked after each successful domain split, except on the first repartition where particle creation from an analyti...`

### Api Usage

#### api_001 - How do I create a 3D Field of doubles in IPPL?

- Verdict: **Partial**
- Codex reference answer: A typical 3D field is `Field<double, 3, UniformCartesian<double, 3>, Cell>` constructed from a `UniformCartesian` mesh and a `FieldLayout<3>`.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.29`
- Local answer excerpt: `Answer: To create a 3D Field of doubles in IPPL, you would construct an `ippl::Field<double>` instance using one of two constructor forms that accept a mesh and layout object, then call its `initialize` method. Specifically: the template type T should be do...`

#### api_002 - How do I construct a UniformCartesian mesh with custom spacing and origin?

- Verdict: **Correct**
- Codex reference answer: Construct the mesh as `UniformCartesian<double, Dim> mesh(domain, hx, origin);` where `hx` is the spacing vector and `origin` is the mesh origin.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.77`
- Local answer excerpt: `Answer: To construct a `UniformCartesian` mesh, call its constructor with three arguments per the declaration in `src/Meshes/UniformCartesian.h`: an `NDIndex<Dim>` object for grid point counts (`ndi`), a vector type for spacing along each dimension (`hx`), ...`

#### api_003 - How do I attach a boundary condition (e.g. periodic) to a Field?

- Verdict: **Correct**
- Codex reference answer: Create a `BConds<FieldT, Dim>`, assign per-face BC objects such as `PeriodicFace<FieldT>`, then call `field.setFieldBC(bc)`.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.44`
- Local answer excerpt: `Answer: To attach a boundary condition such as periodic to an EMField in IPPL, you must call `setFieldBC()` with a vector of shared pointers to configured BC objects (e.g., `PeriodicFace`). The configuration happens via the derived solver class's `setPeriod...`

#### api_004 - How do I define a custom particle class that adds mass and velocity attributes on top of ParticleBase?

- Verdict: **Correct**
- Codex reference answer: Define a class derived from `ParticleBase<ParticleSpatialLayout<...>>`, add `mass` and `velocity` attributes as members, and register them with `addAttribute()` in the constructor.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols. The answer also leaks internal self-correction/planning text, which hurts presentation quality.
- Reference-token coverage: `0.59`
- Local answer excerpt: `Answer: The IPPL framework utilizes the `ippl::ParticleBase<PLayout, IP...>` template as a foundational abstraction to manage particle data and attributes (Chunk 3). To add properties like mass or velocity, you use the member method `addAttribute` on a clas...`

#### api_005 - How do I call ippl::initialize and ippl::finalize in a main program?

- Verdict: **Correct**
- Codex reference answer: Call the free namespace functions `ippl::initialize(argc, argv);` and `ippl::finalize();` from `main`, as shown in the docs/examples.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.60`
- Local answer excerpt: `Answer: Call `ippl::initialize` at program startup with your command-line arguments (`int& argc`, `char* argv[]`) and MPI communicator (`MPI_Comm comm`). This sets up the IPPL library including MPI environment, communicators, Inform objects (Info/Warning/Er...`

#### api_006 - How do I set up and run a forward FFT on an IPPL Field?

- Verdict: **Correct**
- Codex reference answer: Set up the relevant layouts/fields/parameters, build an `FFT<CCTransform, ...>` or `FFT<RCTransform, ...>` object, and call `transform(FORWARD, ...)` on the field(s).
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.73`
- Local answer excerpt: `Answer: To set up and run a forward FFT in IPPL, instantiate the appropriate specialized `FFT` class (e.g., `FFT<RCTransform, RealField>` or `FFT<CCTransform, ComplexField>`) by passing an input layout (`const Layout_t& layoutInput`), an output layout (`con...`

#### api_007 - How do I construct an FFTPeriodicPoissonSolver and solve for the potential?

- Verdict: **Correct**
- Codex reference answer: Construct `FFTPeriodicPoissonSolver(lhs, rhs)` (or default construct then set fields/params), ensure the RHS is attached, and call `solve()` to write the potential/gradient outputs.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.57`
- Local answer excerpt: `Answer: To construct an FFTPeriodicPoissonSolver instance in IPPL, use its default constructor defined in data/raw/ippl/src/PoissonSolvers/FFTPeriodicPoissonSolver.h which initializes the base class and calls setDefaultParameters() to configure solver setti...`

#### api_008 - How do I invoke the conjugate gradient Poisson solver on a Field?

- Verdict: **Correct**
- Codex reference answer: Use `PoissonCG<FieldT>` (or the Alpine `FieldSolver` wrapper around it), set its fields/parameters, and call `solve()` so the internal CG/PCG object iterates on the field.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.45`
- Local answer excerpt: `Answer: To invoke the conjugate gradient (CG) Poisson solver on a Field, instantiate `ippl::PoissonCG` with references to left-hand side (`lhs_type&`) and right-hand side (`rhs_type&`) fields, then call its `solve()` method. The constructor takes field argu...`

#### api_009 - How do I sample particles from a normal distribution using IPPL Random utilities?

- Verdict: **Correct**
- Codex reference answer: For Gaussian draws, IPPL exposes both `randn` convenience generation and the more general `InverseTransformSampling` + `NormalDistribution` path.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.39`
- Local answer excerpt: `Answer: To sample particles from a normal distribution using IPPL Random utilities, instantiate an `ippl::random::NormalDistribution` object initialized via its constructor that accepts mean and standard deviation as a parameter array. Then construct or use...`

#### api_010 - How do I register particle attributes with ParticleBase so that they are communicated on migration?

- Verdict: **Correct**
- Codex reference answer: Register each particle attribute with `addAttribute(...)`; migration then serializes and transfers all registered attributes automatically.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.62`
- Local answer excerpt: `Answer: Register particle attributes by declaring `ParticleAttribute<T>` member variables within a user-defined class that inherits from `ippl::ParticleBase<PLayout>`, then calling the base-class inheritance constructor followed by `addAttribute()` calls in...`

#### api_011 - How do I access the MPI rank and size through the IPPL Communicator?

- Verdict: **Correct**
- Codex reference answer: Access rank and size with `ippl::Comm->rank()` and `ippl::Comm->size()` (or the same methods on a `Communicator` object).
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.60`
- Local answer excerpt: `Answer: To access the MPI process count (size) and current process ID (rank), call `.size()` or `.rank()` respectively on an instance of the `ippl::mpi::Communicator` class defined in `src/Communicate/Communicator.h`. Code initialization examples show usage...`

#### api_012 - How do I use IpplTimings to measure a region of code?

- Verdict: **Correct**
- Codex reference answer: Get a timer handle with `IpplTimings::getTimer("name")`, surround the code with `startTimer()` / `stopTimer()`, and print with `IpplTimings::print()`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.86`
- Local answer excerpt: `Answer: To measure a region of code using `IpplTimings`, you must use the singleton class via four steps in your source file after including `<Utility/IpplTimings.h>`. First, obtain or create a timer reference with `IpplTimings::TimerRef val = IpplTimings::...`

### Parallelism And Kokkos

#### par_001 - How does IPPL achieve performance portability across CPUs and GPUs?

- Verdict: **Correct**
- Codex reference answer: IPPL gets performance portability by combining Kokkos execution/memory abstractions with MPI and heFFTe, so the same code paths can target CPUs and GPUs.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.53`
- Local answer excerpt: `Answer: IPPL leverages the `Kokkos_Core` library (referenced via `Kokkos_Core.hpp`) to achieve performance portability across CPUs and GPUs, as described in Chunks 7-8 which state it includes Kokkos for parallel execution capabilities that enable device-agn...`

#### par_002 - Why does IPPL use Kokkos::View for field storage?

- Verdict: **Correct**
- Codex reference answer: IPPL uses `Kokkos::View` because fields need execution-space-aware storage, subviews, mirrors, and portable kernels across host/device memory spaces.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.41`
- Local answer excerpt: `Answer: IPPL uses `Kokkos::View` for field storage because it provides a typed interface to memory with explicit memory space and execution space semantics, as indicated by definitions such as `using view_type = typename detail::ViewType<T, Dim, ViewArgs......`

#### par_003 - How does IPPL parallelize loops over field indices using Kokkos RangePolicy?

- Verdict: **Correct**
- Codex reference answer: Loops are parallelized through `ippl::getRangePolicy` / `createRangePolicy` and the `ippl::parallel_for` wrapper over Kokkos `RangePolicy`/`MDRangePolicy`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.67`
- Local answer excerpt: `Answer: IPPL defines a `RangePolicy` struct in `ParallelDispatch.h` that encapsulates Kokkos' MDRangePolicy for multi-dimensional range management. The policy type is instantiated as `Kokkos::MDRangePolicy<PolicyArgs..., Kokkos::Rank<Dim>>`. IPPL provides u...`

#### par_004 - How does IPPL support mixed precision (float vs double) for fields?

- Verdict: **Partial**
- Codex reference answer: Precision is chosen by the field value type (`Field<float,...>` vs `Field<double,...>`), and the codebase also contains mixed-precision examples where fields/particles deliberately use different precisions.
- Comparison: The answer has some relevant signal but undercuts itself with uncertainty or abstention.
- Reference-token coverage: `0.35`
- Local answer excerpt: `Answer: The provided retrieved context does not contain specific information on how IPPL implements or manages mixed precision (float vs double) for fields, such as through Kokkos Views templated over `Kokkos::RealTraits<float>` and `Kokkos::RealTraits<doub...`

#### par_005 - How does IPPL handle multiple execution spaces like OpenMP and CUDA in the same build?

- Verdict: **Incorrect**
- Codex reference answer: Multiple execution spaces are enabled at build time through `IPPL_PLATFORMS` and Kokkos/HeFFTe backend flags; IPPL also has container helpers for multi-space data.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.28`
- Local answer excerpt: `Answer: The provided retrieval does not contain specific documentation or code demonstrating how IPPL handles multiple execution spaces like OpenMP and CUDA simultaneously within a single build. Retrieved chunks only discuss MPI-based parallel decomposition...`

#### par_006 - What is the purpose of ParallelDispatch.h and what helpers does it expose?

- Verdict: **Correct**
- Codex reference answer: `ParallelDispatch.h` wraps Kokkos policies and functors, exposing `RangePolicy`, `getRangePolicy`, `createRangePolicy`, `parallel_for`, and `parallel_reduce`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.78`
- Local answer excerpt: `Answer: The file `ParallelDispatch.h` provides abstractions and utilities for parallel execution within the IPPL framework, particularly including structs for coordinate representation (`Coords`) and range-based policies along with functions that facilitate...`

#### par_007 - How does the Archive class serialize/deserialize Kokkos views for MPI transfer?

- Verdict: **Partial**
- Codex reference answer: `Archive` serializes Kokkos views into one-dimensional byte buffers with Kokkos kernels and `memcpy`, then deserializes them back into views on receive.
- Comparison: The answer has some relevant signal but undercuts itself with uncertainty or abstention.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: The retrieved context is insufficient to describe how the Archive class serializes or deserializes Kokkos views for MPI transfer; it only contains generic namespace declarations within IPPL communication headers such as Buffers and Collectives witho...`

#### par_008 - How are MPI tags managed in IPPL to avoid collisions across subsystems?

- Verdict: **Correct**
- Codex reference answer: MPI tags are managed with fixed base tags in `Tags.h` and the cyclic tag allocator in `TagMaker`, which `Communicator` inherits.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.29`
- Local answer excerpt: `Answer: The retrieved codebase does not fully describe a collision-avoidance mechanism for overlapping MPI tags; Chunk 3 explicitly notes uncertainty about how shared tags like `PARTICLE_SEND = SOLVER_SEND (20000)` and their corresponding receive pairs are ...`

#### par_009 - What does Kokkos::fence do, and when does IPPL call the wrapper ippl::fence?

- Verdict: **Correct**
- Codex reference answer: `Kokkos::fence()` waits for outstanding kernels; IPPL exposes `ippl::fence()` as a runtime wrapper in `Ippl.cpp` and also fences internally after many kernel/data-movement steps.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.43`
- Local answer excerpt: `Answer: `ippl::fence` serves as a synchronization barrier within IPPL, ensuring parallel operations complete before subsequent steps proceed. It is called after data packing/unpacking (FEMVector/Tensor operations), halo cell exchanges, particle attribute pa...`

### Boundary And Halo

#### bc_001 - What boundary condition types are provided in BcTypes.h?

- Verdict: **Correct**
- Codex reference answer: `BcTypes.h` provides periodic, constant, zero, extrapolating, and no-BC face classes.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.60`
- Local answer excerpt: `Answer: The `BcTypes.h` header defines the abstract family of field boundary conditions centered on `ippl::detail::BCondBase`, alongside concrete specializations for specific behaviors: constant value application via `ConstantFace`, domain-boundary extrapol...`

#### bc_002 - How does a periodic boundary condition differ from a Neumann boundary condition in IPPL Fields?

- Verdict: **Partial**
- Codex reference answer: Periodic BCs wrap values from the opposite side of the domain; there is no explicit `NeumannFace` class in this codebase, so the closest non-periodic behavior is constant/extrapolating face treatment.
- Comparison: The answer has some relevant signal but undercuts itself with uncertainty or abstention.
- Reference-token coverage: `0.48`
- Local answer excerpt: `Answer: The retrieved context describes IPPL's periodic and non-periodic (absorbing) boundary condition implementations but does not contain information on "Neumann" boundaries as a distinct named option for Fields. Periodic conditions wrap field values acr...`

#### bc_003 - How are ghost cells populated during a halo exchange?

- Verdict: **Correct**
- Codex reference answer: Ghost cells are populated mainly by `fillHalo()` / `PeriodicFace::apply()`: source slabs are packed, exchanged, and unpacked into ghost regions; `accumulateHalo_noghost()` is a different operation.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.45`
- Local answer excerpt: `Answer: During halo exchange, ghost cells are populated via the `ippl::detail::HaloCells<T>::exchangeBoundaries` method in `src/Field/HaloCells.hpp`, which orchestrates MPI communication between neighboring processes. For each domain axis (excluding planes)...`

#### bc_004 - How are physical-cell values copied into ghost cells for periodic boundary conditions?

- Verdict: **Correct**
- Codex reference answer: Periodic ghost cells are filled from opposite-side physical cells in `applyPeriodicSerialDim()` and the multi-rank `PeriodicFace::apply()` path.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.37`
- Local answer excerpt: `Answer: Based on the retrieved context, periodic boundary condition handling uses `PeriodicFace` objects stored in a field's halo data buffer (`haloData_m`) within PeriodicFace. The method `FDTDSolverBase<EMField, SourceField, boundary_conditions>::applyBCs...`

#### bc_005 - How does the absorbing boundary condition in the MaxwellSolvers module damp outgoing waves?

- Verdict: **Correct**
- Codex reference answer: The absorbing Maxwell BC uses second-order Mur-style formulas with precomputed weights and previous/current/next boundary values plus tangential neighbors to damp outgoing waves.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.50`
- Local answer excerpt: `Answer: The absorbing boundary condition in `MaxwellSolvers` uses the struct `second_order_mur_boundary_conditions`, which applies second-order Mur ABCs to all boundaries of a 3D domain by distinguishing faces, edges, and corners (Chunk 2). At each point on...`

### Numerical Meaning

#### num_001 - What does the FFT-based Poisson solver physically compute in terms of Coulomb's law?

- Verdict: **Correct**
- Codex reference answer: The FFT Poisson solvers compute electrostatic potential (and optionally field/gradient) from charge density, i.e. the discretized Coulomb potential corresponding to `-Δφ = ρ`.
- Comparison: The answer captures the main Codex reference concepts.
- Reference-token coverage: `0.75`
- Local answer excerpt: `Answer: Based on the retrieved context, the `ippl::FFTOpenPoissonSolver` computes **electrostatic potential** (stored in FieldLHS) from a charge density field (FieldRHS). The physical computation involves performing FFT-based convolution of the Fourier-tran...`

#### num_002 - What is the physical meaning of the fields advanced by the FDTD solver?

- Verdict: **Correct**
- Codex reference answer: The Maxwell solvers evolve electromagnetic field data: electric and magnetic fields (`E`, `B`) driven by a source/four-current field.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.57`
- Local answer excerpt: `Answer: Based on the retrieved context, the fields advanced by the FDTD solver are electromagnetic fields including Eview and Bview components evaluated within EMField objects. The `step` method updates "electromagnetic field `A_np1`" using previous (`A_nm1...`

#### num_007 - What are the numerical tradeoffs between the FFT and CG Poisson solvers in IPPL?

- Verdict: **Incorrect**
- Codex reference answer: FFT Poisson is fast and direct on structured uniform grids with compatible BCs but less flexible; CG/PCG is iterative and may be slower/convergence-limited, but it is more flexible for alternative discretizations, BCs, and preconditioning.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.21`
- Local answer excerpt: `Answer: The retrieved context does not provide numerical tradeoff comparisons between FFT and CG Poisson solvers in IPPL. The available information covers only `ippl::CG` class implementation details for Conjugate Gradient (iterative solution, residual meas...`

### Build And Install

#### build_001 - Which third-party libraries does IPPL depend on, and what are they used for?

- Verdict: **Partial**
- Codex reference answer: Core third-party dependencies are MPI for distributed communication, Kokkos for performance portability, heFFTe for FFT backends/plans, FFTW/CuFFT as optional FFT backends, and GoogleTest for tests.
- Comparison: The answer has some relevant signal but undercuts itself with uncertainty or abstention.
- Reference-token coverage: `0.38`
- Local answer excerpt: `Answer: IPPL depends on MPI for parallel processing across nodes (via mpi::Environment and mpi::Communicator initialization in ippl.cpp) and Kokkos (included as Kokkos_Core.hpp header referenced alongside Ippl.h for portable CPU/GPU execution, initialized v...`

#### build_002 - What C++ standard does IPPL require, and why?

- Verdict: **Incorrect**
- Codex reference answer: IPPL requires C++20, as stated in the README badge and the installation examples/configuration flags.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.30`
- Local answer excerpt: `Answer: The provided retrieved context does not specify which C++ standard IPPL requires or provide reasons for that requirement. The codebase uses modern C++ features like `std::variant` and references Kokkos_Core.hpp, but no explicit statement about compi...`

#### build_003 - How is IPPL configured with CMake to enable a GPU build?

- Verdict: **Partial**
- Codex reference answer: GPU builds are enabled through CMake options like `IPPL_PLATFORMS=CUDA` or `IPPL_PLATFORMS="HIP;OPENMP"` plus matching Kokkos/architecture/backend flags (`Kokkos_ARCH_*`, `CMAKE_CUDA_ARCHITECTURES`, `Kokkos_ENABLE_HIP`, `Heffte_ENABLE_ROCM`, etc.).
- Comparison: The answer has some relevant signal but undercuts itself with uncertainty or abstention.
- Reference-token coverage: `0.37`
- Local answer excerpt: `Answer: The retrieved context does not contain any information regarding CMake configuration options or instructions to enable a GPU build for IPPL. The available chunks document library components like initialization functions, FFT backends (HeFFTe), field...`

#### build_004 - What options does INSTALLATION.md describe for configuring Kokkos for IPPL?

- Verdict: **Correct**
- Codex reference answer: `INSTALLATION.md` describes Kokkos version selection plus backend/architecture options used with IPPL builds, including CUDA and HIP/OpenMP examples and `IPPL_PLATFORMS` combinations.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.48`
- Local answer excerpt: `Answer: According to INSTALLATION.md, the primary CMake option for configuring Kokkos versioning is `Kokkos_VERSION`, with a default value of `4.5.00`. By default, IPPL attempts to use any compatible system-installed version; you can override by setting it ...`

#### build_005 - How do I install IPPL on the EULER cluster according to the documentation?

- Verdict: **Incorrect**
- Codex reference answer: The EULER install guide says to connect with VPN/SSH, switch to the new software stack, purge modules, load GCC/CMake/CUDA/OpenMPI, clone the repo, configure a build, compile, and test on an interactive node.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.10`
- Local answer excerpt: `Answer: The retrieved context does not contain any installation documentation or procedures for IPPL specific to the EULER cluster. The available chunks cover code structure (classes like `ParticleBase`, functions such as `ippl::initialize`) and file paths ...`

### Testing And Workflow

#### test_002 - What naming conventions does WORKFLOW.md require for variables, constants, and member variables?

- Verdict: **Correct**
- Codex reference answer: `WORKFLOW.md` requires camelCase variables, CAPITAL_CASE compile-time constants, and member names suffixed with `_m`.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.75`
- Local answer excerpt: `Answer: WORKFLOW.md requires variables to use camel casing (e.g., `myVariable`), compile-time constants to use capital casing (e.g., `MY_CONSTANT`), and member variables to be suffixed with `_m` (e.g., `memberVar_m`). For mathematical functions, host-only c...`

#### test_003 - When should code use Kokkos::sqrt versus std::sqrt according to WORKFLOW.md?

- Verdict: **Correct**
- Codex reference answer: Use `std::sqrt` in host-only code, and `Kokkos::sqrt` in device-capable code such as `KOKKOS_INLINE_FUNCTION` kernels.
- Comparison: The answer captures the main Codex reference concepts and names relevant files or symbols.
- Reference-token coverage: `0.75`
- Local answer excerpt: `Answer: Use `std::sqrt` for host-only code and use `Kokkos::sqrt` for device-code or code that might run on a GPU (such as functions marked with `KOKKOS_INLINE_FUNCTION`). This distinction ensures performance portability across different execution backends ...`

#### test_004 - How does IPPL profile MPI calls using mpiP?

- Verdict: **Incorrect**
- Codex reference answer: IPPL profiles MPI calls with mpiP by preloading `libmpiP.so`, optionally setting `MPIP` flags, then parsing the produced `.mpiP` output with the bundled `scripts/mpiP.py`.
- Comparison: The answer mostly abstains even though the Codex reference gives a concrete answer.
- Reference-token coverage: `0.19`
- Local answer excerpt: `Answer: The provided retrieved context does not contain any information about IPPL profiled MPI calls using "mpiP" or any similar profiling mechanism. The codebase documentation and source files available in context do not mention an mpiP profiler for instr...`

#### test_005 - What does the SLURM job template for Gwendolen in the README look like?

- Verdict: **Partial**
- Codex reference answer: The README does include a Gwendolen SLURM template showing the `gmerlin6` cluster, `gwendolen` partition, GPU count, and `srun ./<your_executable> <args> --kokkos-map-device-id-by=mpi_rank`.
- Comparison: The answer has real overlap with the Codex reference, but misses important scope, file, or algorithm details.
- Reference-token coverage: `0.21`
- Local answer excerpt: `Answer: The retrieved context indicates that SLURM job scripts exist in the README (referenced via "#SLURM Job Scripts" navigation link), with an external PSI cluster documentation reference provided for additional details. However, the specific Gwendolen j...`
