# AI-assisted development record

I used AI assistance during this hackathon as a development partner, while
reviewing the generated suggestions, running the application, and accepting
only changes that matched the ShiftSwap requirements.

## How AI assistance was used

- **Architecture:** Helped break the project into a Next.js frontend,
  FastAPI backend, SQLite persistence layer, service layer, and rules module.
- **Seed-data analysis:** Inspected the supplied seed structure and mapped staff,
  roles, certifications, assignments, and shifts without replacing the seed.
- **Backend implementation:** Assisted with SQLite schema design, one-time seed
  initialization, REST endpoints, transactional listing transitions, and
  action-history records.
- **Business rules:** Helped identify and implement certification, owner,
  overlap, 11-hour rest, weekly 40-hour, manager restriction, pending-claim,
  overnight-shift, and approval-revalidation cases.
- **Frontend implementation:** Assisted with the responsive dashboard, the
  role-selection entry screen, logout flow, shared recent activity section,
  API client, loading states, empty states, success messages, and refusal
  reason display.
- **Testing and audit:** Helped create focused backend tests and run lint,
  production builds, API checks, browser checks, persistence checks, and the
  complete post-implementation audit.
- **Documentation:** Helped update the local setup instructions, architecture
  notes, assumptions, and known limitations.

## What I accepted

- The modular backend structure and SQLite persistence approach.
- Backend-owned validation so frontend behavior does not duplicate business
  rules.
- Explicit history records for successful and rejected actions.
- Focused tests for state transitions, multiple refusal reasons, time rules,
  approval revalidation, and restart persistence.
- A simple, non-gradient interface designed for a hackathon demo.

## What I reviewed or changed

- I checked the actual API response shapes before wiring the frontend.
- I corrected the test/import and startup details needed for local Windows
  execution.
- I reviewed the rule implementation and corrected cross-week overlap/rest
  validation so those checks consider all assigned shifts, while weekly hours
  remain scoped to the target shift's start week.
- I kept the supplied seed data intact and verified its parsed content against
  the repository version.
- I ran the backend tests, frontend lint, frontend production build, live API
  health check, browser flow, and persistence checks rather than relying only
  on generated code.

## What I rejected

- Replacing the supplied seed data.
- Adding paid services, API keys, or external hosted dependencies.
- Moving business validation into the frontend.
- Adding real authentication to a demo that explicitly uses selectable
  identities.
- Deploying, committing, or pushing changes as part of this audit.
