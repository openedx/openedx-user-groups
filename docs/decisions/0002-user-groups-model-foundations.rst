0002: User Groups Model Foundations
###################################

Status
******

**Draft**

.. TODO: When ready, update the status from Draft to Provisional or Accepted.

.. Standard statuses
    - **Draft** if the decision is newly proposed and in active discussion
    - **Provisional** if the decision is still preliminary and in experimental phase
    - **Accepted** *(date)* once it is agreed upon
    - **Superseded** *(date)* with a reference to its replacement if a later ADR changes or reverses the decision

    If an ADR has Draft status and the PR is under review, you can either use the intended final status (e.g. Provisional, Accepted, etc.), or you can clarify both the current and intended status using something like the following: "Draft (=> Provisional)". Either of these options is especially useful if the merged status is not intended to be Accepted.

Context
*******

Open edX currently relies on multiple user grouping mechanisms (cohorts, teams, course groups), each with distinct limitations and challenges. These models are difficult to extend, duplicate logic across the platform, and are not designed for reuse in contexts like messaging, segmentation, or analytics.

There is increasing demand for more flexible grouping capabilities, including dynamic membership based on user behavior or attributes. At the same time, existing grouping systems offer rigid schemas and limited extensibility, making it hard to adapt to evolving needs.

The user groups project aims to address these challenges by creating a unified, extensible user groups model that can be used across the Open edX platform. This new model will provide a foundation for managing user groups in a more flexible and powerful way, allowing for better segmentation, messaging, and analytics capabilities.

Some of the key goals of the user groups project include:
* Support dynamic grouping strategies by allowing user groups to be defined based on shared attributes, behaviors, or platform activity, not just manual or random assignment.
* Unify user grouping mechanisms by replacing fragmented models (cohorts, teams, course groups) with a single, consistent data structure and interface.
* Decouple user groups from specific features to support reuse across diverse contexts, such as content access, discussions, messaging, and analytics.
* Standardize group modeling and storage to reduce duplication, improve clarity, and simplify development and operational workflows.
* Enable extensibility by supporting configurable, pluggable criteria that allow new grouping behaviors without modifying core platform code.

This ADR documents the key architectural decisions for the foundational data model and conceptual framework of the unified user grouping system.

.. This section describes the forces at play, including technological, political, social, and project local. These forces are probably in tension, and should be called out as such. The language in this section is value-neutral. It is simply describing facts.

Key Concepts
============

The user groups project will introduce several key concepts that will form the foundation of the new user groups model:

* **User Group**: A named set of users that can be used for various purposes, such as access control, messaging, collaboration, or analytics. User groups are defined by their membership criteria and can be either manually assigned or dynamically computed based on user attributes or behaviors.
* **Criterion**: A rule or condition that defines how users are selected for a user group. Criteria can be based on user attributes (e.g., profile information, course progress) or behaviors (e.g., activity logs, engagement metrics).
* **Criterion Type**: A specific implementation of a criterion that defines how it evaluates users.
* **Scope**: The context in which a user group can be applied. Scopes define whether a group is specific to a course, an organization, or the entire Open edX platform instance. This allows for flexible segmentation and management of user groups across different levels of the platform.
* **Group Mode**: The method by which a user group is populated. There are two primary modes:
  * **Manual**: Users are explicitly assigned to the group, either through a user interface or bulk upload (e.g., CSV).
  * **Dynamic**: Membership is computed based on one or more Criterion rules, allowing for automatic updates as user attributes or behaviors change.

Decision
********

I. Core Group Model
===================

Introduce a unified UserGroup model to represent user segmentation
------------------------------------------------------------------

To define a flexible and extensible data model for user grouping we will:

* Use a single UserGroup model to represent named sets of users, regardless of their use case (access control, messaging, collaboration, analytics) in contrast to how legacy groups currently work.
* Define two group modes:
  * Manual groups are populated through explicit user assignment (e.g., CSV upload or UI).
  * Dynamic groups compute membership from one or more ``Criterion`` rules.
* Associate dynamic groups with one or more ``Criterion`` entities, combined using logical operators (AND/OR), to define membership logic.
* Store essential metadata directly in the model, including name, description, scope, enabled status, and timestamps, to support management and traceability.

Restrict group membership to a single scope (course, organization, or instance)
-------------------------------------------------------------------------------

To ensure clarity and prevent confusion, we will:
* Restrict each ``UserGroup`` to a single scope (course, organization, or instance) to avoid ambiguity in where groups can be applied.
* Use a scope field to indicate the group's applicability, ensuring that groups are only used in contexts where they are relevant.
* Design the system to allow for easy filtering and querying of groups by scope, enabling efficient management and retrieval of relevant groups.
* Ensure that the scope is enforced at the application level, preventing groups from being used in contexts outside their defined scope.

II. Group Membership Evaluation
===============================

Store group membership in a single entity evaluated from criteria
-----------------------------------------------------------------

To unify how group membership is modeled and determined across all group modes, we will:

* Define a separate ``UserGroupMembership`` entity to represent the many-to-many relationship between users and groups.
* Populate this entity for all group modes -manual or dynamic- by evaluating associated ``Criterion`` entries.
* Represent manual groups using a ``ManualCriterion`` type to ensure consistency with dynamic groups.
* Allow users to belong to multiple groups, without enforcing exclusivity at the ``UserGroup`` model level.
* Include metadata fields in the ``UserGroupMembership`` entity (e.g., timestamps) to support visibility, filtering, and auditability.
* Avoid embedding user lists directly in the ``UserGroup`` model to maintain a clean separation between group definition and membership state.
* Support periodic, on-demand or event-based updates for dynamic groups to keep memberships current, while static groups update through their criterion logic when the group is created.

Represent group logic as composable rules via logical operators
---------------------------------------------------------------

To allow for expressive group definitions, we will:

* Enable dynamic groups to define membership based on multiple Criterion entries.
* Combine multiple criteria using logical operators (AND, OR) to express complex inclusion logic.
* Store operator configuration in the group model or linked rule entity.

III. Extensible Criterion Framework
===================================

Design criteria as extensible, pluggable subtypes with centralized runtime resolution
=====================================================================================

To model ``Criterion`` rules in a flexible and schema-light way, we will:

* Use a registry-based subtype pattern where each ``Criterion`` stores a type string mapped to a registered Python class.
* Resolve these classes at runtime via a central registry loaded during application startup.
* Encapsulate both evaluation logic (how users are selected) and validation logic (supported operators and config structure) within the criteria type class.
* Persist all rule configurations using a generic format (``type``, ``operator``, ``value``) within a single table. Where:
  * ``type`` is the registered ``Criterion type`` name (ID).
  * ``operator`` is a string representing the logical operator (e.g., "equals", "contains", "greater_than").
  * ``value`` is a JSON-serializable object containing the specific configuration for that Criterion type.
* Use a JSON field to store the configuration for each Criterion, allowing for flexible and extensible rule definitions without requiring schema migrations.
* Require dynamic groups to define membership using one or more of these registered Criterion entries.
* Express exclusion (e.g., "users not in country X") using standard operators like !=, not in, and not exists. Do not define separate anti-criterion concepts.
* Allow all inclusion and exclusion logic to be handled using the same Criterion structure, reducing complexity and duplication.

Model each criteria type as a pluggable Python class
====================================================

Building on the registry-based resolution model, here we define how each criteria type is implemented and extended. To support extensibility and reuse, we will:\

* Define each ``Criterion`` type as a pluggable Python class that implements a common interface for evaluation and validation.
* Use a registry pattern to allow new Criterion types to be added without modifying the core platform code.
* Store the type name and configuration in the database, allowing for flexible rule definitions that can be extended over time.
* Allow developers to create new Criterion types by implementing the required interface and registering them with the central registry.
* Ensure that each Criterion type can be evaluated independently, allowing for complex membership rules to be defined using combinations of different types.

Delegate criteria configuration validation to the criterion type class
======================================================================

To ensure that each Criterion type can validate its own configuration, we will:

* Building on the pluggable criteria type design, assigning each type class the responsibility for validating its configuration at runtime through a common interface. Each Criterion type will define:
  * Its accepted operators (e.g., "equals", "contains", "greater_than").
  * Its expected value schema (e.g., string, integer, list).
  * Logic to validate input when the group is created or updated.
* Store the validation logic within the Criterion type class, allowing for flexible and extensible rule definitions without requiring schema migrations.
* Use a JSON field to store the configuration for each Criterion, allowing for flexible and extensible rule definitions without requiring schema migrations.
* Ensure that the validation logic can handle different data types and structures, allowing for complex configurations to be defined.
* Allow for custom validation logic to be added by developers when creating new Criterion types, ensuring that each type can enforce its own rules and constraints.

Restrict Criterion types to a single scope (course, organization, or instance)
==============================================================================

To ensure that each Criterion type is applicable only within coherent scopes, we will:
* Restrict each Criterion type to a single scope (course, organization, or instance) to avoid ambiguity in where criteria can be applied.
* Declared the scope of each criterion type class using a class-level attribute, ensuring that it is enforced at the application level.
* Only allow Criterion types to be used within groups that match their declared scope, preventing misuse or confusion.
* Allow for criteria types to support multiple scopes in the future, but require explicit declaration of the scope when defining the type.

Version each criterion type to support future changes
=====================================================

To ensure that the user groups model can evolve over time while maintaining backward compatibility, we will:

* Introduce a versioning system for each Criterion type, allowing for changes to be made without breaking existing configurations.
* Store the version number alongside the type name in the database, allowing for easy identification of the configuration format. The version must be included in the name of the Criterion type, e.g., "ProgressCriterionV2".
* Allow for gradual migration of existing configurations to new versions, ensuring that users can continue to use the system without disruption.

.. This section describes our response to these forces. It is stated in full sentences, with active voice. "We will …"

Consequences
************

These decisions will have the following consequences:

1. A unified ``UserGroup`` model will simplify user segmentation across the Open edX platform, allowing for consistent management and application of user groups.
2. The separation of group membership from the group definition will enable more flexible and dynamic user grouping strategies, reducing duplication of logic across the platform.
3. The extensible Criterion framework will allow for new grouping behaviors to be added without modifying core platform code, enabling rapid iteration.
4. Making the ``UserGroup`` agnostic to specific features will allow it to be reused across different contexts, such as content gating, discussions, messaging, and analytics without requiring custom implementations for each use case. This will also reduce complexity and duplication of logic across the platform.
   and make it easier to maintain and extend the user groups functionality.
5. The restriction of group membership to a single scope will prevent confusion and ensure that groups are only used in contexts where they are relevant, improving clarity and usability for administrators and users.
6. The composable rule system will allow for complex group definitions to be created using combinations of different Criterion types, enabling more sophisticated user segmentation strategies.
7. The pluggable Criterion type system will allow for new grouping behaviors to be added without modifying core platform code, enabling rapid iteration and extensibility.
8. The validation logic within each Criterion type will ensure that configurations are correct and consistent, reducing the risk of errors and improving the reliability of group membership evaluation.
9. The versioning system for Criterion types will allow for changes to be made without breaking existing configurations, ensuring that the user groups model can evolve over time while maintaining backward compatibility.
10. The overall design will create a foundation for user segmentation features, such as messaging, analytics, and reporting, by providing a consistent and extensible model for user groups.
11. The user groups model will eventually replace legacy grouping mechanisms (cohorts, teams, course groups), providing a unified representation for all user segmentation on the platform.
12. Criterion types are not reusable across different groups, as they are scoped to a single group. This means that each group must define its own set of criteria, which may lead to duplication of logic if similar criteria are used across multiple groups. However, this design choice simplifies the evaluation process and ensures that each group can have its own unique set of rules without interference from other groups.

.. This section describes the resulting context, after applying the decision. All consequences should be listed here, not just the "positive" ones. A particular decision may have positive, negative, and neutral consequences, but all of them affect the team and project in the future.

Rejected Alternatives
*********************

Another alternative for defining criterion types in the user groups project was a model-based approach, where each criterion type would be represented as its own Django model. This approach, while providing a clear separation of concerns and allowing for complex criteria definitions, had several drawbacks that led to its rejection:


Model-based Criteria Subtypes
=============================

In this approach, each criterion type is represented as its own Django model, inheriting from a shared  base class. These models define the fields required for their evaluation (such as a number of days, grade, etc) and include a method to return matching users. Evaluation is done by calling each model's method during group processing. 

This structure allows clear separation between criterion types and their usage, and relies on Django's ORM relationships to manage them. New types are introduced by creating new models and registering them so the system can discover and evaluate them when needed.

This design is inspired by model extension patterns introduced in `openedx-learning for content extensibility <https://github.com/openedx/openedx-learning/blob/main/docs/decisions/0003-content-extensibility.rst>`_.

Pros:

* Clear separation of concerns between different criterion types.
* Each type can have its own fields and validation logic out-of-the-box, making it easy to extend.
* Supports advanced use cases for complex criteria that require multiple fields or relationships.
* Allows for easy discovery and evaluation of criterion types through Django's model registry.
* The responsibility of each criterion is of the models, while each group criterion manages the usage of the model (less coupling).

Cons:
* Introduces additional complexity with multiple models and relationships, which can make the system harder to maintain.
* Each new criterion requires a model and a migration. Even small changes involve versioning and review, which slows down iteration and increases maintenance effort.
* Fetching and evaluating criteria across multiple models requires a more complex implementation that may be more difficult implement and debug.
* May lead to performance issues if many criterion types are defined, as each type requires its own database table.
* The model-based approach may not be as flexible as a registry-based system, where new types can be added without requiring migrations or changes to the database schema.

Because of these drawbacks, we decided to use a registry-based approach for defining criterion types, which allows for greater flexibility and extensibility without the overhead of managing multiple models and migrations.

For more details on the model-based approach, see the `Model-based Criteria Subtypes <https://openedx.atlassian.net/wiki/spaces/OEPM/pages/4923228186/Model-based+Criteria+Subtypes>`_ section in the User Groups confluence space.

.. This section lists alternate options considered, described briefly, with pros and cons.

References
**********

Confluence space for the User Groups project: `User Groups confluence space <https://openedx.atlassian.net/wiki/spaces/OEPM/pages/4901404678/User+Groups>`_.

.. (Optional) List any additional references here that would be useful to the future reader. See `Documenting Architecture Decisions`_ and `OEP-19 on ADRs`_ for further input.

.. _Documenting Architecture Decisions: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
.. _OEP-19 on ADRs: https://open-edx-proposals.readthedocs.io/en/latest/best-practices/oep-0019-bp-developer-documentation.html#adrs
