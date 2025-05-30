5. Migration Path for Legacy Mechanisms
#######################################

Status
******

**Draft** - 2025-06-03

Context
*******

Open edX currently uses several user grouping mechanisms (Cohorts, Teams,
Enrollment Tracks), each with its own logic, storage, and integration points.
This fragmentation:

- Complicates maintenance and evolution.
- Makes it difficult to implement new functionality.
- Limits interoperability and extensibility.

Two migration paths were evaluated to transition to a unified grouping system:

- **Cross-System Synchronization**: creates an abstraction layer that
  translates the new model to the legacy mechanisms.
- **Behavior Replication**: builds a new and independent system that replicates
  the observable behavior of the legacy mechanisms without integrating with
  them.

Decision
********

- The behavior replication path was selected, removing direct dependencies on
  the legacy systems.
- The new system does not synchronize with Cohorts, Teams, or Enrollment Tracks.
- Existing functionalities will be internally replicated within the new model.
- Migration will be carried out in clear and isolated phases to reduce risk.
- Activation will be controlled via feature flags, configurable by course,
  organization, or platform.

Consequences
************

- The new system can evolve with greater technical freedom.
- The responsibility for replicating legacy behavior lies entirely within the
  new model, which must be thoroughly validated.
- The transition can be carried out gradually, implementing one functionality
  at a time, allowing individual behavior validation and more targeted testing.

Rejected Alternatives
*********************

Cross-System Synchronization via an Abstraction Layer
=====================================================

This proposal involved creating a new unified model while maintaining indirect
synchronization with the legacy mechanisms through an abstraction layer. This
layer would be responsible for:

- Translating the logic of the new system to Cohorts, Teams, and Tracks.
- Ensuring backward compatibility during the entire transition.
- Enabling a gradual adoption while maintaining functional consistency with the
  legacy systems.

Reasons it was rejected:

- Significant increase in technical complexity: maintaining bi-directional
  synchronization between two systems introduces risk of errors, logic
  duplication, and hard-to-debug issues.
- Higher maintenance cost: any change in the platform or legacy models would
  also require updating the synchronization layer.
- Interference with the evolution of the new model: depending on legacy systems
  limits the ability of the new system to introduce more flexible criteria or
  rules.
- Greater difficulty in isolating and testing the new system: requiring the
  presence of legacy systems makes independent validation of the new model more
  complex.
- Legacy cleanup becomes harder: as long as active synchronization exists,
  legacy code cannot be removed without breaking dependencies.

References
**********

- `Cross-System Synchronization Proposal <https://openedx.atlassian.net/wiki/x/AoBhJwE>`_
- `Behavior Replication Proposal <https://openedx.atlassian.net/wiki/x/AgDiKgE>`_
