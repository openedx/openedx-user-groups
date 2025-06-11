0002: User Groups Model Foundations
###################################

Status
******
Draft

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

This ADR documents the key architectural decisions for the unified user grouping system's foundational data model and conceptual framework.

Key Concepts
============

The user groups project will introduce several key concepts that will form the foundation of the new user groups model:

* **User Group**: A named set of users that can be used for various purposes, such as access control, messaging, collaboration, or analytics. User groups are defined by their membership criteria and can be either manually assigned or dynamically computed based on user attributes or behaviors.
* **Criterion**: A rule or condition that defines how users are selected for a user group. Criteria can be based on user attributes (e.g., profile information, course progress) or behaviors (e.g., activity logs, engagement metrics).
* **Criterion Type**: A specific implementation of a criterion that defines how it evaluates users.
* **Scope**: The context in which a user group can be applied. Scopes define whether a group is specific to a course, an organization, or the entire Open edX platform instance. This allows for flexible segmentation and management of user groups across different levels of the platform.
* **Group Type**: The method by which a user group is populated. There are two primary modes:

  * **Manual**: Users are explicitly assigned to the group, either through a user interface or bulk upload (e.g., CSV).
  * **Dynamic**: Membership is computed based on one or more Criterion rules, allowing for automatic updates as user attributes or behaviors change.

NOTE: The group type only determines whether the group will be automatically updated, and it's mainly a nomenclature determined by the criteria chosen.

Decision
********

I. Foundation Models
====================

Introduce a unified UserGroup model to represent user segmentation
------------------------------------------------------------------

To create a unified user groups model, we will:

* Introduce a single ``UserGroup`` model to represent user segmentation across the Open edX platform, replacing legacy group models like cohorts, teams, and course groups.
* Define two group types to distinguish how groups are populated:

  * **Manual groups**: Populated through explicit user assignment (e.g., CSV upload or UI).
  * **Dynamic groups**: Compute membership from one or more ``Criterion`` rules.

* Associate dynamic groups with one or more ``Criterion`` entities, combined using logical operators (AND/OR), to define membership logic.
* Store essential metadata directly in the model, including name, description, scope, enabled status, and timestamps, to support management and traceability.
* Plan for this model to eventually replace cohorts, teams, and course groups, creating a unified representation for all user segmentation on the platform. These groups will be used for various purposes, such as content gating, discussions, messaging, and analytics without requiring custom implementations for each use case.

Include an explicit scope relationship in the UserGroup model (course, org, or instance)
----------------------------------------------------------------------------------------

To ensure groups are only used where intended, we will:

* Add a scope field to the model that defines whether the group applies at the course, organization, or platform level.
* Use this field to filter visibility, evaluation applicability, and downstream usage (e.g., access control, analytics) for each group.
* Ensure that groups are only evaluated and applied within their defined scope, preventing cross-scope confusion or misuse.
* Use a unique constraint (name, scope) to avoid using the same group twice in the same scope.
* Use a generic FK in the scope model to support any kind of object but initially limit to existing: course, org, instance.

Store group membership in a separate many-to-many model (UserGroupMembership)
-----------------------------------------------------------------------------

To decouple group definition from membership state, we will:

* Define a join table (``UserGroupMembership``) to persist the list of users assigned to each group.
* Use this table for both static (manual) and dynamic (evaluated) groups to standardize downstream access.
* Avoid embedding membership directly within the ``UserGroup`` model to simplify querying, filtering, and updates.
* Ensure services can reference group membership directly without requiring on-demand evaluation.
* Use this model to store metadata about the membership, such as timestamps for when a user was added or removed, to support auditing and traceability.

Allow users to belong to multiple groups, even within the same scope
--------------------------------------------------------------------

To support overlapping use cases and flexible segmentation, we will:

* Not enforce exclusivity at the data model level between groups, even within the same scope (e.g., course).
* Permit users to be part of multiple groups simultaneously, unless constrained by other mechanisms referencing the group (e.g., content access restrictions).

Store core operational metadata in the model, but not full audit history
------------------------------------------------------------------------

To support minimal traceability without overloading the schema, we will:

* Include fields like created, updated, enabled, last_refresh, and member_count directly in the ``UserGroup`` model.
* Avoid embedding full audit trails (e.g., historical criteria changes or user diffs) in the model.
* Rely on logs, analytics systems, or external audit services for long-term tracking and monitoring.

II. Extensible Criterion Framework
===================================

Adopt a registry-based criteria subtype model using type-mapped Python classes
------------------------------------------------------------------------------

To define how dynamic group membership rules are structured and evaluated, we will:

* Represent each rule (criterion) using a type string that maps to a Python class (criteria type) responsible for evaluation and validation.
* Load criteria type classes at runtime through a registry, avoiding schema-level coupling and enabling dynamic binding of behavior.
* Encapsulate both the logic (how to compute membership) and schema validation (allowed operators, value shape) in the criteria type class.
* Connect dynamic user groups to this model by requiring that every dynamic group defines membership through one or more registered criteria types.
* Select this pattern over a model-subtype approach to eliminate the need for migrations, simplify extension, and support plugin-based development workflows.

Define a generic schema for Criterion using three persisted fields
------------------------------------------------------------------

To support flexible, extensible rule definitions without schema changes, we will:

* Store each criterion as a single record with the fields:

  * ``type``: identifies the criteria type class (e.g., "last_login")
  * ``operator``: the comparison logic (e.g., >, in, !=, exists)
  * ``value``: a JSON-encoded configuration object (e.g., 10, ["es", "fr"])

* Avoid adding model fields per rule type by using a generic schema and deferring validation to runtime.
* Enable a single ``Criterion`` table to store all types of rules consistently, regardless of data source, scope, or logic.
* Ensure this model structure is compatible with the registry-based type system.

Define each Criterion Type as reusable template instead of group-specific
-------------------------------------------------------------------------

To enable reuse of criteria definitions across groups while maintaining isolation, we will:

* Use templates that define how a criterion behaves: name, config model, supported operators, evaluator, and validations. These templates are the criteria types that are associated with the ``Criterion`` entries.
* Enable the reuse of criteria type definitions across groups. The isolation of each group comes when saving the instance data related to each group, since each can differ in the value configured.
* Allow different criteria to be configured differently and independently for each group, but they'll follow the same template behaving just the same but differing in instances.
* Store ``Criterion`` entries as private to each group; there is no global repository of shared criteria.
* Allow the same rule type (e.g., "last_login") to be configured differently across groups.
* Enable group owners or plugins to evolve their criteria independently without introducing shared state or coupling.

Save entire rule determining membership for a user group as a logic tree
------------------------------------------------------------------------

As an evolution of the simple criterion model to support complex rules with different operator combinations, we will:

* Save the templates with the configurations of the groups in the user groups model as logic trees to express complex conditions like: X AND Y (Z OR W)::

    {
      "AND": [
        { "property": "X", "operator": "...", "value": ... },
        { "property": "Y", "operator": "...", "value": ... },
        {
          "OR": [
            { "property": "Z", "operator": "...", "value": ... },
            { "property": "W", "operator": "...", "value": ... }
          ]
        }
      ]
    }

* Do not persist criterion types but use template classes (Python classes from before) for reusing definitions across groups.
* Enable more dynamic behavior while maintaining the same level of validation (done by the Python class itself).
* Allow complex boolean expressions to be defined using the tree structure, where each node represents a criterion and its associated operator.
* Ensure the logic tree can be evaluated in a predictable order, respecting operator precedence and grouping.
* Use this structure to evaluate group membership by traversing the tree and applying the defined criteria to each user.

Restrict criteria types to specific scopes and enforce compatibility with group scope
-------------------------------------------------------------------------------------

To prevent invalid configurations and ensure rules apply only where meaningful, we will:

* Define criteria types with a declared scope (e.g., course, organization, instance).
* Identify criteria types by the pair <type_name, scope> so that "last_login" for a course may differ from (or be unavailable at) org level.
* Allow only criteria types matching the group's scope to be used when configuring a group.
* Use this mapping to determine which rule types are available at each level of the platform.
* Enforce this constraint at the model level during validation and at runtime during group creation or update.

Version Criterion templates
---------------------------

To ensure expected behavior is maintained throughout releases, we will:

* Version criterion templates so the expected behavior maintains throughout releases.
* Store the version number alongside the type name in the database by including it in the criterion type name (e.g., "ProgressCriterionV2").
* Allow gradual migration of existing configurations to new versions, ensuring users can continue using the system without disruption.

Offload criteria configuration validation to the criteria type class at runtime
-------------------------------------------------------------------------------

To keep the model schema minimal and extensible, we will:

* Not enforce structure or constraints on the value field at the database level.
* Store configuration as unstructured JSON to support heterogeneous criteria types in a single table.
* Delegate validation responsibility to the criteria type class, which defines:

  * Its accepted operators
  * Its expected value schema
  * Logic to validate input when the group is created or updated

* Define the model as schema-light by design and shift enforcement to the type layer, enabling extension without schema migrations.

Support exclusion logic through operators rather than anti-criteria
-------------------------------------------------------------------

To simplify the model and unify rule semantics, we will:

* Express exclusion (e.g., "users not in country X") using standard operators like !=, not in, and not exists.
* Not define separate anti-criterion concepts.
* Allow all inclusion and exclusion logic to be handled using the same ``Criterion`` structure, reducing complexity and duplication.

III. Group Membership Evaluation
=================================

Populate membership for dynamic groups via evaluation of associated criteria
----------------------------------------------------------------------------

To support computed membership while preserving consistency with manual groups, we will:

* Treat dynamic group membership as derived data, computed by evaluating the group's criteria.
* Store the evaluation result in the ``UserGroupMembership`` table, replacing any previous members.
* Keep manual and dynamic groups consistent by using the same membership storage model, even if the population method differs.
* Ensure dynamic groups are evaluated periodically or on demand to keep their membership current.

Represent manual groups using manual criteria rather than separate mechanisms
-----------------------------------------------------------------------------

To unify group definition and membership logic, we will:

* Model manual groups as having a special criteria type (e.g., ``ManualCriterion``) rather than introducing a separate mechanism.
* Use the same ``Criterion`` table and configuration system for both manual and dynamic groups, differing only in how users are assigned.
* Maintain consistency by storing manual group members in the same ``UserGroupMembership`` table used for evaluated groups.
* The manual criterion type will simply list the users assigned to the group, allowing for a consistent evaluation interface.
* Allow manual groups to be evaluated like dynamic groups, enabling consistent access patterns and simplifying the evaluation engine.

Consequences
************

These decisions will have the following consequences:

1. A unified ``UserGroup`` model will simplify user segmentation across the Open edX platform, allowing for consistent management and application of user groups.

2. The separation of group membership from the group definition will enable more flexible and dynamic user grouping strategies, reducing duplication of logic across the platform.

3. The extensible criterion framework will allow for new grouping behaviors to be added without modifying core platform code, enabling rapid iteration.

4. Making the ``UserGroup`` agnostic to specific features will allow it to be reused across different contexts, such as content gating, discussions, messaging, and analytics without requiring custom implementations for each use case.

5. The restriction of group membership to a single scope will prevent confusion and ensure that groups are only used in contexts where they are relevant, improving clarity and usability for administrators and users.

6. The composable rule system will allow for complex group definitions to be created using combinations of different criterion types, enabling more sophisticated user segmentation strategies.

7. The pluggable criterion type system will allow for new grouping behaviors to be added without modifying core platform code, enabling rapid iteration and extensibility.

8. The validation logic within each criterion type will ensure that configurations are correct and consistent, reducing the risk of errors and improving the reliability of group membership evaluation.

9. The versioning system for criterion types will allow for changes to be made without breaking existing configurations, ensuring that the user groups model can evolve over time while maintaining backward compatibility.

10. The overall design will create a foundation for user segmentation features, such as messaging, analytics, and reporting, by providing a consistent and extensible model for user groups.

11. The user groups model will eventually replace legacy grouping mechanisms (cohorts, teams, course groups), providing a unified representation for all user segmentation on the platform.

12. The extensible criterion framework establishes the foundation for pluggable evaluation logic without requiring knowledge of specific runtime implementation details.

13. The logic tree structure will enable complex boolean expressions while maintaining predictable evaluation order and hierarchy.

14. The registry-based approach will eliminate migration overhead for new criterion types while maintaining type safety through runtime validation.

15. The manual criterion approach will provide a consistent interface for both manual and dynamic groups, simplifying the evaluation engine implementation.

16. The scope-based restriction of criteria types will prevent invalid configurations and ensure rules apply only where meaningful.

Rejected Alternatives
**********************

Model-based Criteria Subtypes
==============================

Another alternative for defining criterion types in the user groups project was a model-based approach, where each criterion type would be represented as its own Django model. This approach, while providing a clear separation of concerns and allowing for complex criteria definitions, had several drawbacks that led to its rejection.

In this approach, each criterion type is represented as its own Django model, inheriting from a shared base class. These models define the fields required for their evaluation (such as a number of days, grade, etc) and include a method to return matching users. Evaluation is done by calling each model's method during group processing.

This structure allows clear separation between criterion types and their usage, and relies on Django's ORM relationships to manage them. New types are introduced by creating new models and registering them so the system can discover and evaluate them when needed.

This design is inspired by model extension patterns introduced in `openedx-learning for content extensibility <https://github.com/openedx/openedx-learning/blob/main/docs/decisions/0003-content-extensibility.rst>`_.

**Pros:**

* Clear separation of concerns between different criterion types.
* Each type can have its own fields and validation logic out-of-the-box, making it easy to extend.
* Supports advanced use cases for complex criteria that require multiple fields or relationships.
* Allows for easy discovery and evaluation of criterion types through Django's model registry.
* The responsibility of each criterion is of the models, while each group criterion manages the usage of the model (less coupling).

**Cons:**

* Introduces additional complexity with multiple models and relationships, which can make the system harder to maintain.
* Each new criterion requires a model and a migration. Even small changes involve versioning and review, which slows down iteration and increases maintenance effort.
* Fetching and evaluating criteria across multiple models requires a more complex implementation that may be more difficult to implement and debug.
* May lead to performance issues if many criterion types are defined, as each type requires its own database table.
* The model-based approach may not be as flexible as a registry-based system, where new types can be added without requiring migrations or changes to the database schema.

Because of these drawbacks, we decided to use a registry-based approach for defining criterion types, which allows for greater flexibility and extensibility without the overhead of managing multiple models and migrations.

For more details on the model-based approach, see the `Model-based Criteria Subtypes <https://openedx.atlassian.net/wiki/spaces/OEPM/pages/4923228186/Model-based+Criteria+Subtypes>`_ section in the User Groups confluence space.

References
**********

Confluence space for the User Groups project: `User Groups confluence space <https://openedx.atlassian.net/wiki/spaces/OEPM/pages/4901404678/User+Groups>`_.
