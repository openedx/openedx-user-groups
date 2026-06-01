0005. Migration Path for Legacy User Grouping Mechanisms
########################################################

Status
******

**Draft** - 2025-06-03

Context
*******

Open edX currently uses several user grouping mechanisms (cohorts, teams, course groups), each with its own data models, business logic, storage, and integration points. This fragmentation results in:

- Maintenance and evolution complications.
- New functionality implementation difficulties.
- Interoperability and extensibility limitations.

These legacy mechanisms were not designed for reuse across contexts such as messaging, analytics, or advanced segmentation, and lack support for dynamic grouping based on user attributes or behavior.

To address these limitations, we proposed a **unified user grouping model**, as described in `ADR 2 <0002-user-groups-model-foundations.rst>`_, with a standardized structure that supports both static and dynamic groups, scoped at the course, organization, or platform level. Unlike legacy mechanisms, this unified system allows flexible group definitions and enables modular extensibility. It decouples user groups from specific platform features and enables reuse across diverse contexts (content gating, discussions, analytics, messaging, etc.).

To migrate from the legacy mechanisms to this new model, two paths were evaluated:

- **Cross-System Synchronization**: Introduces an abstraction layer that continuously translates the new model's state into the legacy mechanisms. This enables the new model to act as a central source while preserving backward compatibility by updating legacy structures in real time.
- **Behavior Replication**: Builds the new unified and independent grouping system that directly replicates the observable behavior of the legacy mechanisms within its own logic. Instead of integrating with or updating legacy mechanisms, it reproduces their functionality internally and gradually replaces them without requiring active synchronization.

The key difference between these two strategies lies in how they relate to the legacy mechanisms, which in turn affects the complexity of the migration process, the technical debt incurred, and the long-term maintainability of the grouping architecture.

Decision
********

We select the behavior replication approach, eliminating direct dependencies on legacy mechanisms. This choice enables a simpler, cleaner architecture with:

- Full independence from legacy mechanisms from day one.
- Elimination of complex synchronization or integration layers.
- Reduced technical debt and maintenance costs during migration.

Existing user-facing functionalities will be replicated in the new model with migration executed in clear, isolated phases to minimize risk. Activation will be controlled via feature flags, configurable per course, organization, or platform.

See `ADR 6 <0006-replication-of-legacy-mechanisms-behavior.rst>`_ for detailed rationale.

Consequences
************

- The new system can evolve independently, allowing greater flexibility.
- The responsibility for replicating legacy behavior lies entirely within the new model, which must be thoroughly validated.
- The transition can be carried out gradually, implementing one functionality at a time, allowing individual behavior validation and more targeted testing.
- Both new and legacy mechanisms can coexist during rollout, avoiding user disruption.
- Legacy mechanisms will be fully deprecated and removed post-transition, improving maintainability and extensibility. Courses that still rely on legacy grouping systems at the time of removal will not be automatically migrated. It will be the responsibility of course authors or site operators to manually transition their configurations to the new system before deprecation occurs. Failure to do so may result in the loss of grouping data or functionality associated with cohorts, teams, or enrollment track groups.

Rejected Alternatives
*********************

Cross-System Synchronization
============================

This approach, like the selected one, builds on top of the new unified grouping system. However, it differs in that it maintains indirect synchronization with the legacy mechanisms through an abstraction layer.

The synchronization strategy involves monitoring changes in either system (new or legacy), interpreting those changes through registered evaluators, and propagating updates to maintain alignment. This ensures both systems reflect a consistent state, at the cost of added runtime logic and maintenance overhead.

This layer would be responsible for:

- **Translating the logic of the new system to legacy mechanisms**: Establishing a bi-directional synchronization layer that ensures both systems remain consistent. This abstraction layer would monitor changes in the unified model, such as group creation, updates to membership, or criteria changes. It would then propagate these changes to the corresponding legacy mechanisms.

  Likewise, any modifications in the legacy mechanisms would also need to be captured and reflected back in the new model to maintain alignment. This translation mechanism would allow legacy features (e.g., content gating, discussions, ORA assignments) to continue operating using their existing infrastructure. They would be effectively controlled by the unified model behind the scenes.

- **Ensuring backward compatibility during the entire transition**: The platform must preserve full functional integrity of the legacy grouping mechanisms (cohorts, teams, course groups) while the new model is introduced. The abstraction layer would need to convert the unified model's definitions into updates to legacy models and APIs. This ensures that existing behaviors remain unchanged for instructors, learners, and third-party integrations.

- **Enabling gradual adoption while maintaining functional consistency**: Migrate to the new grouping model incrementally, activating it course-by-course or organization-wide using feature flags. During this phased adoption, the abstraction layer ensures both models can operate in parallel without conflict. This allows selective rollout, targeted validation, and fallback to legacy behavior if needed. All while maintaining consistent user experience and platform behavior.

Reasons for rejection:

- **Significant increase in technical complexity**: Maintaining bi-directional synchronization between two systems introduces risk of errors, logic duplication, and hard-to-debug issues.
- **Higher maintenance cost**: Any change in the platform or legacy models would also require updating the synchronization layer.
- **Interference with the evolution of the new model**: Depending on legacy mechanisms limits the ability of the new system to introduce more flexible criteria or rules.
- **Greater difficulty in isolating and testing the new system**: Requiring the presence of legacy mechanisms makes independent validation of the new model more complex.
- **Legacy cleanup becomes harder**: As long as active synchronization exists, legacy code cannot be removed without breaking dependencies.

Comparison Summary
------------------

The following table summarizes the key differences between the two migration strategies:

+-----------------------------+----------------------------------------------+------------------------------------------------+
| Aspect                      | Cross-System Synchronization                 | Behavior Replication                           |
+=============================+==============================================+================================================+
| Legacy Dependency           | Requires maintaining legacy systems          | No dependency on legacy systems                |
+-----------------------------+----------------------------------------------+------------------------------------------------+
| Synchronization Complexity  | High: requires bi-directional sync layer     | None: new system operates independently        |
+-----------------------------+----------------------------------------------+------------------------------------------------+
| Backward Compatibility      | Full, via real-time updates to legacy state  | Achieved by replicating observable behaviors   |
+-----------------------------+----------------------------------------------+------------------------------------------------+
| Testing & Validation        | Difficult: both systems must stay in sync    | Easier: new model can be tested in isolation   |
+-----------------------------+----------------------------------------------+------------------------------------------------+
| Migration Strategy          | Gradual, but tightly coupled with legacy     | Gradual, with clean separation                 |
+-----------------------------+----------------------------------------------+------------------------------------------------+
| Long-Term Maintenance       | Higher effort due to dual-system complexity  | Lower effort after transition is complete      |
+-----------------------------+----------------------------------------------+------------------------------------------------+
| Time to Legacy Removal      | Longer: active sync delays removal           | Shorter: legacy can be phased out per feature  |
+-----------------------------+----------------------------------------------+------------------------------------------------+

References
**********

- `Cross-System Synchronization Proposal <https://openedx.atlassian.net/wiki/x/AoBhJwE>`_
- `Behavior Replication Proposal <https://openedx.atlassian.net/wiki/x/AgDiKgE>`_
