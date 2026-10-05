# Repository guidance

This repository contains a portable website-building specification and reference catalog. It does not contain a deployed website or shared CMS.

- For a website-building task, start with AGENT_ENTRY.md and follow the task-specific links.
- For changes to this repository, edit the maintained Skill and reference sources rather than generated customer websites.
- Preserve stable reference IDs and distinguish public-source descriptions from visual observations and recommendations.
- Keep credentials, private site checks, customer data, and local machine paths out of commits.
- Run the existing package-checker tests when changing its implementation. Documentation changes need link and JSON validation.
- Do not mark a generated website as tested merely because this repository's offline checks pass.


- The user requires every Skill update to be committed and pushed to this GitHub repository after relevant validation. Keep VERSION, CHANGELOG.md, VALIDATION.md and manifest.json current; report any failed synchronization explicitly.
