5. Migration Path for Legacy User Grouping Mechanisms
#####################################################

Status
******

**Draft** - 2025-06-03

Context
*******

Open edX currently uses several user grouping mechanisms (Cohorts, Teams,
Enrollment Track Groups), each with its own logic, storage, and integration
points. This fragmentation results in:

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

We select the behavior replication approach, eliminating direct dependencies on
legacy systems. This choice enables a simpler, cleaner architecture with:

- Full independence from legacy mechanisms from day one.
- Elimination of complex synchronization or integration layers.
- Reduced technical debt and maintenance costs during migration.

Existing user-facing functionalities will be replicated in the new model, with
migration executed in clear, isolated phases to minimize risk. Activation will
be controlled via feature flags, configurable per course, organization, or
platform.

See `ADR 6 <docs/decisions/0006-replication-of-legacy-mechanisms-behavior.rst>`_
for detailed rationale.

Consequences
************

- The new system can evolve independently, allowing greater flexibility.
- The responsibility for replicating legacy behavior lies entirely within the
  new model, which must be thoroughly validated.
- The transition can be carried out gradually, implementing one functionality
  at a time, allowing individual behavior validation and more targeted testing.
- Both new and legacy systems can coexist during rollout, avoiding user
  disruption.
- Legacy systems will be fully deprecated and removed post-transition,
  improving maintainability and extensibility.

Rejected Alternatives
*********************

Cross-System Synchronization
============================

This proposal involved creating a new unified model while maintaining indirect
synchronization with the legacy mechanisms through an abstraction layer. This
layer would be responsible for:

- Translating the logic of the new system to Cohorts, Teams, and Enrollment
  Track Groups.
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
