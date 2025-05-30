6. Replication of Legacy Mechanisms Behavior
############################################

Status
******

**Draft** - 2025-06-03

Context
*******

The new unified user grouping system introduced in Open edX is intended to
replace the existing grouping mechanisms (Cohorts, Teams, and Enrollment Track
Groups) without depending on them directly. To achieve this, a behavior
replication strategy was selected: implement, within the new model, the
observable functionalities currently provided by legacy mechanisms, but without
maintaining synchronization with their internal structures.

The proposal is organized into four phases to enable a progressive, safe, and
decoupled transition from legacy code. Each phase includes specific technical
decisions to ensure that the new model can fully assume the responsibilities of
the legacy mechanisms without requiring synchronization between systems.

Decision
********

- The new grouping system will be implemented independently of the legacy
  models.
- No synchronization or abstraction layer will be established between the new
  system and the legacy groups.
- The observable behavior of legacy mechanisms will be functionally replicated
  in the new system.
- Each phase will be executed incrementally and validated independently,
  allowing for iterative learning and risk control.
- Once all functionalities have been replicated, the legacy mechanisms will be
  removed and group management will migrate to a centralized administrative
  interface.

Consequences
************

- It will be possible to validate that the new system can fully replace the
  legacy mechanisms, without requiring synchronization or coupling.
- The migration can proceed in a safe and controlled manner, with both
  implementations coexisting temporarily.

Phases
******

Phase 1: Implementation of the new grouping system
==================================================

- A new user grouping model will be implemented, composed of its corresponding
  entities, allowing the creation of manual (static) groups.
- Only group creation and management via direct user assignment will be
  supported in this phase.
- Dynamic user groups based on criteria are not included in this phase.
- The system will be deployed behind a feature flag, and a temporary
  management interface will be exposed via the instructor dashboard.
- There is no interaction or synchronization with the legacy mechanisms.

Phase 2: Replication of legacy group behavior
=============================================

The unified user grouping system will be extended to support dynamic groups
based on criteria, and replicate the key functionalities of the legacy
mechanisms (Enrollment Track Groups, Cohorts, Teams). During this phase, both
systems will coexist without interference. Functionality will be implemented
incrementally, focusing on one category at a time.

Functionalities included in this phase:

- **Support for dynamic groups:**
  Groups can be created manually or generated automatically based on criteria,
  enabling greater flexibility.

- **Mutual exclusivity:**
  Groups defined within a collection must not share users.

- **Content access restriction:**
  Units or components can be made visible only to users in specific groups.

- **Support for divided discussions:**
  Users can only see and participate in discussion threads assigned to their
  group.

- **Support for ORA assignments:**
  Assignments can be answered only by members of designated groups.

- **Hierarchical structures:**
  Groups can be nested or organized into group collections.

Phase 3: Removal of legacy mechanisms
=====================================

Once the replicated functionalities have been validated, the following will be
removed:

- Models and signals related to Cohorts, Teams, and Enrollment Track Groups.
- LMS and Studio endpoints and views associated with these mechanisms.
- Configuration and logic in legacy MFEs.
- Legacy interfaces will be gradually disabled.
- Related feature flags will be removed, making the new system the only active
  grouping source.

Phase 4: Migration to the new administrative panel
==================================================

- A centralized administrative interface will be developed to manage
  groupings at the course, organization, and platform levels.
- This new UI will replace the temporary tab in the instructor dashboard.
- It will allow users to create and edit groups, visualize grouping criteria,
  and perform manual or bulk assignments.
- Access to the interface will be controlled by administrative permissions.

References
**********

- `Behavior Replication Proposal <https://openedx.atlassian.net/wiki/x/AgDiKgE>`_
