0004: Consistency and Refresh Framework for User Groups
########################################################

Status
******
**Draft**

Context
*******

The unified user grouping system needs to maintain consistent and up-to-date group membership as user data changes across the platform. Currently, Open edX uses different models for user grouping (cohorts, teams, course groups) with no clear approach to handling automatic membership updates. Mainly this updates are done manually by course staff or admin users by adding or removing users to the group, this new approach will be more automated to decrease the management overhead.

The system must support multiple types of criteria that depend on different data sources:

* Real-time data from the LMS (enrollment changes, profile updates)
* Analytics data from Aspects (engagement metrics, learning progress) 
* External system data that may not be immediately available

Key challenges include:

* **Race conditions**: Multiple updates happening simultaneously can create inconsistent states
* **Mixed refresh frequencies**: Some criteria need real-time updates while others can be cached
* **Cross-group dependencies**: Mutually exclusive groups require coordinated updates
* **Data availability**: External systems may be temporarily unavailable
* **Performance**: Frequent re-evaluation must not impact system performance

The User Group Consistency and Refresh Framework ADR outlines the need for event-based, scheduled, and manual update methods, with rules for handling inconsistencies, mutual exclusivity between criteria, and update priority when multiple methods are in use.

Decision
********

I. Primary Refresh Strategy
===========================

Use Event-Based Updates as Primary Mechanism
--------------------------------------------

To maintain group consistency in response to user data changes in near real-time, we will:

* Use Open edX Events as the primary mechanism for triggering group membership updates, prioritizing event-based updates over scheduled or manual methods whenever possible.
* Ensure that group-related update events are only emitted on transaction commit to guarantee consistency with committed data.
* Implement mappings between criteria and relevant events:

    CourseEnrollmentCriterion → COURSE_ENROLLMENT_CREATED & COURSE_ENROLLMENT_CHANGED
    UserStaffStatusCriterion → USER_STAFF_STATUS_CHANGED
    LastLoginCriterion → SESSION_LOGIN_COMPLETED

* Enable future extensions for 3rd-party plugins to generate events, with fallback to cronjob + command updates when events are unavailable.
* Implement fallback mechanisms to handle cases where events are missed or membership state becomes inconsistent, including manual reconciliation tools and scheduled consistency checks.

Implement Consistency Lock for Updates
--------------------------------------

To avoid inconsistent group membership updates (such as out-of-order updates), we will implement a coordinated update approach:

* **Atomic Update Scope**: Ensure that all group membership changes resulting from a single user data change are processed atomically, preventing users from being in inconsistent intermediate states.

* **Complete Update Definition**: Consider an update complete only when all groups affected by a user's data change have been updated, avoiding inconsistent middle states where a user might be partially updated across multiple groups.

* **Concurrency Control**: Implement coordination mechanisms to prevent concurrent evaluation of the same user's group membership across multiple update processes, while allowing parallel processing of different users.

* **Database Consistency**: Leverage Django ORM's transaction and locking capabilities to maintain data integrity during updates.

* **Update Coordination**: Implement the system so that when one update process is evaluating a user's group memberships, subsequent updates for the same user wait for completion to ensure they operate on current data.

**Example scenario requiring coordination:**
Given a user group with criteria C1 (last login over 1 week ago) and C2 (residence country in X list of countries):

* Event 1: User logs in at t0 (affects C1)
* Event 2: User changes residence country at t1 (affects C2)  
* Without coordination: Two concurrent processes might evaluate the same user's membership simultaneously, potentially leading to race conditions where the final membership state depends on timing rather than the actual criteria.

The coordination mechanism ensures that only one process evaluates a user's group membership at a time, while still allowing concurrent evaluation of different users for optimal performance.

Centralize Update Processing
----------------------------

To orchestrate refreshes consistently across event, scheduled, and manual triggers, we will:

* Implement a single asynchronous Django signal listener that acts as the centralized orchestrator for all update processing, regardless of trigger type (event, scheduled, or manual).
* Ensure that when a single event affects multiple groups for a user, all resulting membership changes are processed atomically as one coordinated update.

II. Evaluation Strategy
=======================

Configure Update Strategy at Criterion Level
--------------------------------------------

To provide flexibility while maintaining consistency, we will:

* **Criterion-Level Configuration**: Configure update strategies (event-based, scheduled, manual) at the individual criterion type level rather than at the group level, allowing each criterion type to define its optimal refresh approach based on its data source characteristics.

* **Mixed Strategy Support**: Enable groups to contain criteria with different update strategies, with the centralized orchestrator coordinating updates across all criteria types within a group. For groups with criteria of mixed refresh frequencies (event-based + scheduled):

  * Allow mixed refresh frequencies per group, with event-based updates taking priority over scheduled updates when both are triggered simultaneously.
  * Trigger re-evaluation when any criterion's update frequency threshold is reached (scheduled update). Example: If C1 is event-based and C2 is cached daily, the group is refreshed:

    * Immediately on C1 events.
    * On scheduled daily refresh for C2 (unless already refreshed by C1 events).

  * Set refresh frequency per criterion type based on data volatility and system performance requirements, as outlined in the long-term requirements.

* **Event Mapping Registration**: Require each criterion type to register its event mappings and refresh frequency as part of its type definition, making update behavior explicit and maintainable.

* **Priority Handling**: When multiple update strategies apply to the same group (due to mixed criteria), prioritize event-based updates over scheduled updates, ensuring the most current data drives group membership.

This approach enables optimal refresh strategies for each data source while maintaining consistent group membership across all criteria types.

Apply Whole Predicate Re-Evaluation on Update
---------------------------------------------

To simplify consistency logic, we will:

* On receiving an event for any part of a group's predicate:

  * Re-evaluate the entire predicate for the affected user(s), not just the criteria that triggered the update to keep the membership up to date.
  * Support both single-user refresh (for individual events) and full group refresh (for bulk operations) depending on event semantics.

* This approach is preferred over implementing fine-grained "only update if the configured field changed" logic to keep the system simple and robust.

Summary Rules for Group Refresh Priority
----------------------------------------

To provide predictable behavior, we will:

* Prioritize event-based updates over other refresh methods
* Use scheduled updates as fallback for eventual consistency
* Allow criteria or groups to restrict to a single update method if operationally needed
* Trigger all syncs for a given scope at the same time to avoid cross-group inconsistencies

III. Mutual Exclusivity Management
=====================================

To enforce mutual exclusivity where required while allowing other groups to overlap, we will implement a dual-approach exclusivity system:

Define Exclusivity Domains Through Update Framework
---------------------------------------------------

* **Automatic Exclusivity Domains**: When the criteria of group G1 and group G2 are mutually exclusive (C1, ..., Cn ∩ C'1, ..., C'n = ∅), these groups automatically form a **mutual exclusivity domain** that is managed by the event-based update framework.

* **Event-Based Exclusivity Management**: Groups within the same exclusivity domain are automatically coordinated through the centralized update orchestrator, ensuring that when a user's data changes, all groups in the domain are updated atomically.

**Example of automatic exclusivity domain:**

* G1: Course enrollment mode "honor". Students ``{u1, …, un}``
* G2: Course enrollment mode "audit". Students ``{v1, …, vn}``
* When ``u1`` is downgraded to audit, both G1 and G2 are automatically updated within a single transaction, removing U1 from G1 and adding to G2.

Complement with Collection-Based Exclusivity
--------------------------------------------

* **Manual Exclusivity Collections**: Introduce Group Collections as sets of groups that are mutually exclusive with one another, used to enforce exclusivity at the model level for manually-defined groups that do not have automatic updates.

* **Collection Definition**: Group Collections are defined as either:

  * Automatically created based on dynamic rules for criteria-based groups
  * Manually defined by course staff or admin users for manual groups

* **Collection Membership**: Ensure each group belongs to a collection, with a default collection for non-exclusive groups. Collections prevent users from being assigned to multiple groups within the same exclusive collection.

* **Hybrid Approach**: The combination of Group Collections + refresh & consistency framework guarantees that a user is never in two groups that are mutually exclusive by nature (contradictory), whether the exclusivity is:
  
  * **Natural/Automatic**: Derived from mutually exclusive criteria (handled by update framework)
  * **Administrative/Manual**: Defined by course staff or admin users (handled by Group Collections)

Operational Rules for Exclusivity Domains
-----------------------------------------

* **Event-Based Domains**: For groups in automatic exclusivity domains with event-based updates, the update framework handles coordination automatically through the centralized orchestrator. For example:

  * When ``u1`` is enrolled in track "honor" and then gets downgraded to "audit", a single enrollment change event triggers coordinated updates across the mutually exclusive domain:
  
    * Remove ``u1`` from "Honor Students" group
    * Add ``u1`` to "Audit Students" group
  * Both operations happen atomically within one transaction
  
  The domain is automatically formed because "honor" and "audit" enrollment tracks are naturally mutually exclusive - a user cannot be in both simultaneously.

* **Non-Event-Based Domains**: For groups with mutually exclusive criteria that cannot be updated by events (whether due to external data sources, missing event implementation, or other constraints), mutual exclusivity is naturally maintained when groups share the same update schedule. For example:

  * **External data**: Account type groups ("Free Tier", "Premium", "Enterprise") updated from external billing system daily - all updated together in the same batch operation
  * **Missing events**: User skill level groups ("Beginner", "Intermediate", "Advanced") where skill assessment data exists but events aren't implemented yet - updated together via scheduled refresh
  * **Performance constraints**: Heavy analytics-based groups that are too expensive to update in real-time - updated together during off-peak hours

In this case the mutual exclusivity is enforced by the source of the data, not by the update framework or the groups themselves.

* **Manual Collection Domains**: For manually defined groups that are exclusive by user definition and do not have automatic updates:

  * Enforce exclusivity through Group Collections, which reinforce membership exclusivity at the model level.
  * Collections act as explicit exclusivity domains defined by administrators.

**Key Principle**: Groups are not inherently mutually exclusive; rather, they become part of exclusivity domains either:

* **Automatically**: When their criteria are naturally mutually exclusive (managed by update framework)
* **Explicitly**: When administrators define them as exclusive through Group Collections (managed at model level)

The system guarantees that a user is never in conflicting groups at any given time by coordinating updates within each exclusivity domain.

IV. Operational Controls
========================

Group-Level Management Overrides
---------------------------------

To give operators flexibility in managing the refresh framework, we will:

* **Group Freezing**: Allow freezing updates for a group (stop all refreshes temporarily), useful for operational debugging or data stability. Frozen groups will not be visible to the orchestrator until unfrozen.

* **Frequency Overrides**: Allow operational overrides of refresh frequencies for individual groups or criteria when needed.

* **Method Restrictions**: Support restricting groups to a single update method (event-only, scheduled-only, or manual-only) when operationally required.

Dependencies
************

**Cross-ADR Dependencies:**

This ADR builds upon and extends the foundational architecture established in previous ADRs:

* **Model Foundation Dependency**: The refresh and consistency framework operates on the UserGroup, Criterion, and UserGroupMembership models defined in :doc:`ADR 0002: User Groups Model Foundations <../0002-user-groups-model-foundations>`.
* **Runtime Architecture Dependency**: The event-based update system utilizes the evaluation engine, orchestration layer, and backend clients defined in :doc:`ADR 0003: Runtime Architecture <../0003-runtime-architecture>`.
* **Criterion Type Integration**: Event mappings and refresh strategies are defined as part of each criterion type's registration, following the registry-based approach established in ADR 0003.

**Internal Framework Dependencies:**

Within this ADR, the decisions have the following dependencies:

* **Centralized Update Processing** depends on the **Event-Based Updates** mechanism for coordination.
* **Consistency Lock Implementation** requires the **Centralized Update Processing** orchestrator to function.
* **Mutual Exclusivity Management** depends on both **Update Framework** and **Collection-Based Exclusivity** systems.
* **Operational Controls** require all update mechanisms to be established before overrides can be applied.

Consequences
************

These decisions will have the following consequences:

1. Event-based updates will be preferred over other update strategies, and the implementation of new events related to the student-author lifecycle will be encouraged over other solutions, promoting real-time consistency across the platform.

2. Criteria will handle their own update strategies, since they understand what affects them, enabling optimal refresh approaches for each data source while maintaining system modularity.

3. For simplicity, the rules for a group will be re-evaluated each time any criterion changes, reducing complexity and edge cases while ensuring comprehensive membership updates.

4. Concurrent evaluation of groups sharing criteria will be coordinated to avoid race conditions, ensuring data integrity and preventing inconsistent intermediate states during updates.

5. With collections, groups can be mutually exclusive or could overlap depending on their configuration, providing flexibility while keeping groups agnostic of business rules for exclusivity management.

6. The centralized orchestrator provides consistent update coordination across all trigger types (event, scheduled, manual), simplifying the implementation of complex refresh workflows.

7. The atomic update scope ensures that all group membership changes resulting from a single user data change are processed together, preventing users from being in inconsistent states.

8. The whole predicate re-evaluation approach simplifies the system logic by avoiding fine-grained change detection, making the framework easier to maintain and debug.

9. The mixed update strategy support within groups enables optimal refresh frequencies for different data sources while maintaining consistent group membership across all criteria types.

10. The dual-approach exclusivity system (automatic domains + manual collections) provides comprehensive mutual exclusivity enforcement without requiring groups to be inherently exclusive.

11. The operational controls for group freezing and frequency overrides provide administrators with flexibility for maintenance, debugging, and performance optimization scenarios.

12. The event system dependency creates potential points of failure if events are missed, requiring robust fallback mechanisms and monitoring to ensure system reliability.

13. The performance overhead of re-evaluating entire predicates may impact system performance under high load, necessitating careful optimization and monitoring of evaluation patterns.

14. The implementation complexity of event orchestration and locking mechanisms requires thorough testing and validation to ensure correct behavior across all update scenarios.

15. The framework enables real-time group membership updates that improve user experience and system accuracy while providing fallback mechanisms for reliability.

16. The coordination mechanism for mutual exclusivity domains ensures that users are never in conflicting groups at any given time, maintaining data integrity across related group definitions.

Rejected Alternatives
*********************

Configure the Update Strategy at the User Group Level
=====================================================

Configure the update strategy at the user group level, rather than at the criterion level.

**Pros:**

* Simpler group-level configuration - one strategy per group.
* No need to coordinate multiple update strategies within a single group.

**Cons:**

* Less flexible - cannot optimize update strategy per data source.
* Groups with mixed data sources (real-time + batch) forced to use suboptimal strategy.
* Harder to maintain when criterion types have different optimal refresh patterns.

Rejected in favor of criterion-level configuration to allow optimal update strategies for each data source type.

Enforce Mutually Exclusiveness at the User Group Level
======================================================

Enforce mutual exclusiveness at the user group level, rather than at the criterion level.

**Pros:**

* No need to implement the coordination mechanism for the update process.

**Cons:**

* More complex to implement since it would require for the new model to conditionally apply the exclusivity rules during the update process across multiple groups.

Rejected in favor of the current approach to allow exclusive and non-exclusive groups to coexist.

Fine-Grained Criterion Update Strategy
======================================

Implementing fine-grained updates where only the specific criteria that changed would be re-evaluated, rather than re-evaluating entire group predicates.

**Pros:**

* Better performance by avoiding unnecessary evaluations.
* More granular control over update operations.

**Cons:**

* Significantly increased implementation complexity.
* Difficult to ensure consistency across related criteria.
* Risk of inconsistent states due to incomplete evaluations.

Rejected in favor of whole predicate re-evaluation to maintain simplicity and ensure consistency.

References
**********

* :doc:`ADR 0002: User Groups Model Foundations <../0002-user-groups-model-foundations>`
* :doc:`ADR 0003: Runtime Architecture <../0003-runtime-architecture>`
* `User Group Consistency and Refresh Framework document <https://openedx.atlassian.net/wiki/spaces/OEPM/pages/4976115715/User+Group+Consistency+and+Refresh+Framework>`_
* `Long-Term Requirements for the Unified Model <https://openedx.atlassian.net/wiki/spaces/OEPM/pages/4905762858/Long-Term+Requirements+for+the+Unified+Model>`_
