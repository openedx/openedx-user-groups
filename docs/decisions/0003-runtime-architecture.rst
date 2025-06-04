0003: Runtime Architecture for Criteria Evaluation and Plugin Discovery
################################################################

Status
******

**Draft**

Context
*******

ADR 0002 introduced a unified model for user grouping based on configurable, pluggable criteria. To support this, we need a runtime architecture that enables dynamic evaluation, plugin discovery, and backend integration.

This ADR defines that runtime behavior. It introduces a central registry for resolving Criterion types, an evaluation engine for computing group membership, and a plugin system for extending logic without modifying core code.

The goal is to ensure a flexible, scalable, and extensible system that supports new criteria, reusable data access, and consistent runtime evaluation.

Key Concepts
============

* **Criterion Type Class**: A pluggable Python class implementing evaluation and validation logic for a specific rule.
* **Criteria Registry**: A centralized registry for resolving available criterion types at runtime.
* **Evaluation Engine**: A core component responsible for evaluating a group's dynamic membership.
* **Data Sources**: Backend clients (e.g., MySQL via Django ORM, Superset API) used to fetch user data.

Decision
********

I. Extensible Runtime Criteria and Data Integration
===================================================

Introduce pluggable Criterion Types
-----------------------------------

To define a flexible and extensible runtime architecture for user grouping we will:

* Define each ``Criterion`` type as a pluggable Python class that implements a shared interface.
* Register new criterion types using a plugin mechanism (e.g., stevedore entry points) at startup.
* Ensure each type encapsulates:
  * A type name (e.g., "last_login")
  * Supported operators (e.g., <, =, exists)
  * A configuration schema (Pydantic/attrs)
  * Evaluation logic to return user IDs
* Restrict each Criterion type to a single scope (course, org, or site-wide).

For more details on the Criterion Type design, see ADR 0002.

Standardize Data Source Integration
-----------------------------------

To separate concerns and improve maintainability we will:

* Delegate data access to backend clients (e.g., ``DjangoORMUsersBackend``, ``SupersetClientUsersBackend``, ``SISClientUsersBackend``).
* Expose shared methods such as ``get_users_by_progress()`` or ``get_users_by_login()``.
* Ensure criteria remain agnostic to data source implementation.
* Use a consistent interface for all backends to fetch user data, allowing them to be swapped or extended without affecting the criteria logic.
* Avoid direct queries in Criterion types to prevent duplication and maintain performance by offering reusable backend APIs.
* Allow developers to register or extend backend clients using a consistent interface.

Pass Backend Clients to Criterion Types
---------------------------------------

To ensure that Criterion types can access the necessary backend clients without hardcoding dependencies we will:

* Use dependency injection to pass backend clients to Criterion types to use during evaluation.
* Ensure each Criterion type can specify which backend clients it requires in its configuration schema.
* Use a factory pattern to instantiate and provide the correct backend clients based on the Criterion type's configuration.
* Allow backend clients to be registered dynamically at application startup, enabling new data sources to be added without modifying core code.
* Use a centralized registry to resolve and instantiate backend clients as needed, ensuring testability and extensibility.
* Ensure that backend clients can be mocked or replaced in tests to maintain isolation and testability.

II. Centralized Runtime Registry System
=======================================

Manage Criterion Resolution via Registry
----------------------------------------

To resolve and manage criterion types dynamically at runtime we will:

* Load all ``Criterion Type`` Python classes at application startup using a registry pattern with ``stevedore`` entry points.
* Use a centralized in-memory registry to map type names to their corresponding classes.
* Use this registry to resolve the ``Criterion.type`` string at runtime associating as a property of the ``Criterion`` model.

III. Plugin Mechanism for Discovery and Registration
====================================================

Support External and Local Plugin Criteria
------------------------------------------

To support third-party and operator-defined criteria extensions we will:

* Allow plugins to register new Criterion types by defining them in their ``setup.py``.
* Use ``stevedore`` entry points to discover and load these plugins at application startup.
* Ensure plugins can define their own configuration schemas and validation logic by overriding the base ``Criterion`` class.
* Provide a clear API for plugin authors to register new criterion types without modifying core code.

IV. Evaluation Engine for Membership Resolution
===============================================

Evaluate Dynamic Group Membership at Runtime
--------------------------------------------

To compute user membership based on group criteria we will:

* Introduce a dedicated evaluation engine responsible for computing group membership when a group is evaluated.
* Design the engine to:
  * Accept groups with one or more registered criteria.
  * Resolve each criterion type via the centralized registry.
  * Use backend clients to retrieve the necessary user data.
  * Combine individual criterion results using the group's configured logical operator (AND, OR).
  * Apply lazy evaluation strategies (e.g., Q objects) to optimize performance and scalability.
* Ensure the evaluation engine supports complex combinations of criteria and is decoupled from data source implementations by using backend clients and providing a consistent interface for combining results.

Optimize Execution and Query Planning
-------------------------------------

To ensure scalability and flexibility we will:

* Use lazy evaluation techniques (e.g., Q objects in Django).
* Optimize combined queries where feasible.
* Allow backends to share logic across criteria to minimize duplicate queries.
* Implement short-circuiting logic to avoid unnecessary evaluations.
* Use most selective criteria first to reduce the dataset size early in the evaluation process.

V. Group Service Layer and Runtime API
======================================

Expose High-Level Group Management API
--------------------------------------

To offer a unified interface for runtime evaluation workflows we will:

* Provide service layer APIs to:
  * Create and manage groups with associated criteria.
  * Evaluate group membership dynamically based on the defined criteria.
  * Resolve criterion types using the centralized registry.
  * Handle backend client interactions for data retrieval.
* Encapsulate registry resolution and evaluation logic and all interactions with backend clients behind this API to avoid direct access to the registry or backend clients in business logic.
* Ensure the API abstracts away the complexity of resolving criterion types and evaluating group membership.

VI. Schema-Based UI Integration
===============================

Enable Configurable UI via Schema Definitions
---------------------------------------------

To support flexible forms and UI generation we will:

* Require each Criterion Type to define its config schema.
* Use this schema to render dynamic fields in admin or course staff interfaces.

Consequences
************

1. The runtime architecture allows for dynamic evaluation of user groups based on pluggable criteria, enabling flexible and extensible grouping logic.
2. The centralized registry system simplifies the resolution of criterion types, ensuring consistent behavior across the application.
3. The plugin mechanism enables third-party and operator-defined criteria extensions without modifying core code, promoting maintainability and extensibility.
4. The evaluation engine provides a scalable and efficient way to compute group membership, leveraging backend clients for data retrieval.
5. The service layer API abstracts the complexity of group management, providing a clear interface for developers and operators.
6. The schema-based UI integration allows for dynamic and configurable forms, improving user experience for group management.
7. The architecture avoids duplicated logic and ensures consistent performance by using shared backend clients and lazy evaluation techniques.
8. The design supports future enhancements, such as additional criterion types or data sources, without requiring significant changes to the core architecture.

Rejected Alternatives
*********************

* **Criterion-Owned Queries**: Led to duplicated logic, inconsistent performance, and harder maintenance.
* **Model-Based Criteria**: Rejected in ADR 0002 due to maintenance overhead, schema migrations, and limited agility.

References
**********


