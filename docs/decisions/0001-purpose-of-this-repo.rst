0001 Purpose of This Repo
#########################

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

The user groups project is an initiative within the Open edX platform to enhance user management capabilities, specifically focusing on the organization and usage of user groups, with the ultimate goal of replacing legacy groups like cohorts or teams. The goal is to create a more flexible and powerful system for managing user groups, which will ultimately improve the overall user experience and administrative efficiency within the Open edX platform.

For more details, please refer to `User Groups confluence space <https://openedx.atlassian.net/wiki/spaces/OEPM/pages/4901404678/User+Groups>`_.

.. This section describes the forces at play, including technological, political, social, and project local. These forces are probably in tension, and should be called out as such. The language in this section is value-neutral. It is simply describing facts.

Decision
********

We will create a repository to hold the architecture for the user groups project, which is part of the Open edX platform's user management capabilities.

.. This section describes our response to these forces. It is stated in full sentences, with active voice. "We will …"

Consequences
************

This repository will serve as a central location for documenting the architecture and design decisions related to the user groups project.

.. This section describes the resulting context, after applying the decision. All consequences should be listed here, not just the "positive" ones. A particular decision may have positive, negative, and neutral consequences, but all of them affect the team and project in the future.

Rejected Alternatives
*********************

Using edx-platform repository for the user groups project effort.

.. This section lists alternate options considered, described briefly, with pros and cons.

References
**********

Confluence space for the User Groups project: `User Groups confluence space <https://openedx.atlassian.net/wiki/spaces/OEPM/pages/4901404678/User+Groups>`_.

.. (Optional) List any additional references here that would be useful to the future reader. See `Documenting Architecture Decisions`_ and `OEP-19 on ADRs`_ for further input.

.. _Documenting Architecture Decisions: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
.. _OEP-19 on ADRs: https://open-edx-proposals.readthedocs.io/en/latest/best-practices/oep-0019-bp-developer-documentation.html#adrs
