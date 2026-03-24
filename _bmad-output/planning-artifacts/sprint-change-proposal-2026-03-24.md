# Sprint Change Proposal

**Project:** slate
**Date:** 2026-03-24
**Prepared By:** John, Product Manager
**Mode:** Batch
**Change Trigger:** Refactor the planning artifacts so the epic/story plan is implementation-ready, aligns UX back to MVP, and preserves PRD coverage.
**Approval Status:** Approved by Raziur on 2026-03-24

## 1. Issue Summary

Implementation readiness review exposed a planning problem, not a product-definition problem.

- PRD coverage is strong: all 28 FRs are represented in the epics.
- Execution readiness is weak: several stories are technical enablers disguised as user stories, several stories are too large to implement safely, and UX scope extends beyond the current MVP boundary.
- If implementation starts now, the team will likely lose velocity inside Epic 1, build against ambiguous UX scope, and struggle to verify completion because some work items are not independently shippable.

### Evidence

- `epics.md` Story 1.1, Story 1.2, Story 1.3, and Story 1.9 are foundation/setup tasks rather than user-complete slices.
- `epics.md` Story 2.1, Story 3.2, and Story 5.1 bundle too many outcomes into single backlog items.
- `ux-design-specification.md` defines plugin-management UX (Plugins tab, create plugin flow, reload flow, configuration dialogs) that is not part of the MVP PRD scope.
- `architecture.md` is largely consistent with the PRD, but it assumes a clean implementation sequence that the current story breakdown does not support well.

## 2. Checklist Findings

### Section 1 - Understand the Trigger and Context

- [x] 1.1 Trigger identified: readiness review of the current epic/story plan
- [x] 1.2 Core problem defined: implementation plan quality and scope drift
- [x] 1.3 Evidence gathered from PRD, epics, architecture, UX, and readiness report

### Section 2 - Epic Impact Assessment

- [x] 2.1 Current epic can proceed only after story restructuring
- [x] 2.2 Epic-level changes required: modify existing epics, no new epic required
- [x] 2.3 Future epics reviewed for sizing and dependency impact
- [x] 2.4 No epic invalidated, but Epic 6 requires expanded scope clarity
- [x] 2.5 Epic order can remain mostly intact; story sequencing inside epics needs refinement

### Section 3 - Artifact Conflict and Impact Analysis

- [x] 3.1 PRD conflict is moderate: scope definition is sound, but a few operational/UX expectations should be clarified
- [x] 3.2 Architecture conflict is low: structure is solid, but implementation guidance should acknowledge enablers vs vertical slices
- [x] 3.3 UX conflict is significant around plugin-management scope and a few over-specified interaction details
- [x] 3.4 Secondary artifacts impacted: readiness report, future sprint status, and implementation sequencing

### Section 4 - Path Forward Evaluation

- [x] 4.1 Option 1 Direct Adjustment: Viable | Effort: Medium | Risk: Low
- [ ] 4.2 Option 2 Potential Rollback: Not viable | No code implementation exists to justify rollback
- [ ] 4.3 Option 3 PRD MVP Review: Partially viable, but full MVP reduction is unnecessary
- [x] 4.4 Recommended path: Hybrid leaning heavily to Option 1

### Section 5 - Sprint Change Proposal Components

- [x] 5.1 Issue summary created
- [x] 5.2 Epic and artifact impacts documented
- [x] 5.3 Recommended path with rationale included
- [x] 5.4 MVP impact and action plan defined
- [x] 5.5 Agent handoff plan defined

### Section 6 - Final Review and Handoff

- [x] 6.1 Checklist reviewed for completeness
- [x] 6.2 Proposal drafted for accuracy and actionability
- [x] 6.3 User approval obtained
- [N/A] 6.4 No `sprint-status.yaml` file exists in the project to update
- [x] 6.5 Next-step and handoff plan confirmed

## 3. Impact Analysis

### Epic Impact

**Epic 1: Editor Core & Project Startup**
- Keep the epic.
- Reframe technical stories as enablers or narrower implementation slices.
- Preserve startup, file opening, tabs, save guard, and theme initialization outcomes.

**Epic 2: File Explorer & Project Navigation**
- Keep the epic.
- Split the current monolithic file-explorer story into navigation and file-operations slices.

**Epic 3: Source Control & Code Review**
- Keep the epic.
- Split Source Control panel delivery from commit workflow and branch-switching complexity.

**Epic 4: Search & Replace**
- Mostly healthy.
- Consider adding stronger edge-case ACs for dirty-file warnings and missing-ripgrep behavior.

**Epic 5: Theme & Preferences**
- Keep the epic.
- Split display/theme controls from persistence-heavy preferences and live preview details.

**Epic 6: Plugin Extensibility**
- Keep the epic.
- Expand beyond documentation so plugin loading, failure isolation, and proof-of-public-API are represented as deliverable work.

### Story Impact

**Stories requiring restructure**
- Story 1.1 `Project Initialization & Packaging`
- Story 1.2 `Core Layer - Models, Events & EventBus`
- Story 1.3 `Plugin API Contracts & PluginManager`
- Story 1.9 `Development Tooling & CI`
- Story 2.1 `File Explorer Plugin`
- Story 3.2 `Source Control Plugin`
- Story 5.1 `Preferences Plugin`
- Story 6.1 `Plugin Developer Experience & Documentation`

### Artifact Conflicts

**PRD**
- Mostly stable.
- Needs small clarifications on MVP boundary for plugin management and on which UX/accessibility expectations are release-gating.

**Architecture**
- Stable.
- Needs minor wording updates so implementation planning explicitly distinguishes enablers from user-facing slices.

**UX**
- Needs the biggest correction.
- Plugin-management flows should move to post-MVP/future-state unless the PRD is expanded.

### Technical Impact

- No architecture rewrite required.
- No tech-stack change required.
- Backlog quality improvement now will reduce thrash later in dev, QA, and architecture interpretation.

## 4. Recommended Approach

### Chosen Path

**Hybrid approach:** direct adjustment of epics/stories plus targeted PRD/UX/architecture corrections.

### Why This Path

- The product definition is not broken; the execution plan is.
- Rolling back anything is pointless because the issue is in planning artifacts, not shipped code.
- A full MVP rethink is overkill. The core value proposition remains strong and coherent.
- The fastest safe move is to tighten the backlog, trim UX overreach, and add traceability where needed.

### Effort, Risk, and Timeline Impact

- **Effort:** Medium
- **Risk:** Low to Medium
- **Timeline Impact:** Short delay now, lower delivery risk later

## 5. Detailed Change Proposals

### A. Epics / Stories Changes

#### Proposal A1 - Reframe technical foundation stories in Epic 1

**Story:** 1.1 `Project Initialization & Packaging`
**Section:** Story title and framing

**OLD:**
- As a developer, I want a properly structured Python project with pyproject.toml and directory layout, So that I have a clean foundation to build all layers on top of.

**NEW:**
- Rename to `Story 1.1: Bootstrap runnable Slate shell`
- As a user, I want Slate to launch into a minimal native window from the CLI, So that implementation starts from a real runnable application shell.
- Move packaging, directory layout, and dependency setup into implementation tasks/enablers beneath the story.

**Rationale:**
- WHY keep pretending infrastructure is user value? It is necessary work, but it should support a user-visible outcome.

#### Proposal A2 - Narrow infrastructure-heavy stories into implementation slices

**Stories:** 1.2, 1.3, 1.9
**Section:** Story granularity and classification

**OLD:**
- Large developer-facing stories for core models/event bus, plugin API/contracts, and tooling/CI.

**NEW:**
- Treat these as either:
  - enabler stories tied to Epic 1, or
  - implementation tasks under user-valued stories such as startup shell, tab opening, and plugin-host registration.
- If they remain as stories, explicitly mark them `Enabler` and reduce ACs to the minimum needed for the next user-visible slice.

**Rationale:**
- This preserves sequencing discipline without pretending these items are independently shippable user stories.

#### Proposal A3 - Split File Explorer delivery into two stories

**Story:** 2.1 `File Explorer Plugin`
**Section:** Story scope

**OLD:**
- One story covers tree rendering, lazy loading, file opening, context menu CRUD, icons, shortcut behavior, and breadcrumbs.

**NEW:**
- `Story 2.1: Browse project tree and open files`
  - tree view
  - lazy loading
  - open file via event
  - panel registration and shortcut
- `Story 2.2: Manage project files from the explorer`
  - create file/folder
  - rename/delete
  - breadcrumb refinement
  - error handling for file operations

**Rationale:**
- Navigation and file mutation are different risk surfaces and should be validated separately.

#### Proposal A4 - Split Source Control into review-first slices

**Story:** 3.2 `Source Control Plugin`
**Section:** Story scope

**OLD:**
- One story covers status listing, status badges, diff launch, staging, commit UI, commit validation, branch switching, error handling, and keyboard focus.

**NEW:**
- `Story 3.2: View repository changes and open diffs`
- `Story 3.3: Stage and unstage files from Source Control`
- `Story 3.4: Commit staged changes with inline validation`
- `Story 3.5: Switch branches from Source Control`

**Rationale:**
- WHY overload the most critical workflow? Review, staging, commit, and branch switching deserve separate acceptance and test boundaries.

#### Proposal A5 - Split Preferences into settings domains

**Story:** 5.1 `Preferences Plugin`
**Section:** Story scope

**OLD:**
- One story covers all editor preferences, display toggles, theme mode, schemes, live preview, persistence, and shortcut behavior.

**NEW:**
- `Story 5.1: Configure editor display and editing preferences`
- `Story 5.2: Configure theme mode and color schemes`
- Keep persistence ACs shared but explicit in each relevant story.

**Rationale:**
- This reduces ambiguity, isolates live-preview complexity, and makes testing cleaner.

#### Proposal A6 - Expand Epic 6 to prove the plugin promise

**Story:** 6.1 `Plugin Developer Experience & Documentation`
**Section:** Story completeness

**OLD:**
- Documentation-heavy proof of plugin extensibility.

**NEW:**
- `Story 6.1: Load and isolate plugins through the public API`
- `Story 6.2: Provide plugin developer documentation and example plugin`

**Rationale:**
- The product promise is extensibility. Documentation alone does not prove the system works.

### B. PRD Changes

#### Proposal B1 - Clarify plugin-management MVP boundary

**Section:** `Product Scope` / `Growth Features` / Plugin-related journeys

**OLD:**
- Third-party plugin loading is post-MVP, but the broader narrative can be read as implying richer plugin-management UX than the FR set requires.

**NEW:**
- Add explicit note: MVP includes public plugin API and built-in plugins using that API; plugin marketplace, in-app plugin creation/scaffolding, and user-facing plugin-management UX are post-MVP unless explicitly promoted into scope.

**Rationale:**
- Removes ambiguity between product scope and UX exploration.

#### Proposal B2 - Promote release-gating quality expectations into explicit requirements language

**Section:** `Non-Functional Requirements` or `Additional Requirements`

**OLD:**
- Accessibility, graceful degradation, and some feedback-state expectations are present, but not consistently framed as release gates.

**NEW:**
- Add explicit release-gating statements for:
  - missing-tool graceful degradation
  - keyboard accessibility for core workflows
  - visible error/success feedback for save, commit, search, and git failures

**Rationale:**
- If it matters enough to design and build, it should be traceable enough to test.

### C. Architecture Changes

#### Proposal C1 - Distinguish enablers from user-visible slices in implementation guidance

**Section:** `Implementation Handoff` / `Implementation Sequence`

**OLD:**
- Architecture provides a correct dependency order, but backlog translation encourages large foundation-heavy stories.

**NEW:**
- Add guidance: foundational work may be captured as enablers/tasks, but implementation stories should prefer thin vertical slices that prove user-facing progress while respecting dependency order.

**Rationale:**
- Aligns architecture reality with delivery reality.

#### Proposal C2 - Make plugin extensibility proof expectations concrete

**Section:** `Requirements Coverage Validation` or `Implementation Handoff`

**OLD:**
- Plugin system support exists architecturally, but proof criteria are diffuse.

**NEW:**
- Add explicit implementation checkpoint: demonstrate a plugin loaded through the public API, panel/action registration, and failure isolation without host crash.

**Rationale:**
- This turns architectural intent into a real acceptance bar.

### D. UX Changes

#### Proposal D1 - Move plugin-management UI flows out of MVP UX baseline

**Section:** Journey 3 and plugin-related UX components

**OLD:**
- Preferences -> Plugins tab
- Create New Plugin scaffold dialog
- Reload/restart flow
- Installed plugins list and configure flow

**NEW:**
- Mark these flows as `Post-MVP / Future-state UX`.
- Keep MVP UX focused on built-in plugin panels and public API-backed extensibility, not end-user plugin management.

**Rationale:**
- The UX spec is currently promising interaction surfaces the PRD does not require for v1.

#### Proposal D2 - Tag over-specified interaction details as aspirational unless traced

**Section:** Loading states, multi-monitor behavior, plugin configuration dialogs, command palette references

**OLD:**
- Several details read like mandatory MVP behavior.

**NEW:**
- Label these items as `aspirational`, `future enhancement`, or add matching PRD/epic traceability where truly required.

**Rationale:**
- Prevents accidental scope creep through design prose.

## 6. PRD MVP Impact

- **MVP remains viable.**
- No core goal needs to be abandoned.
- This proposal sharpens the plan; it does not shrink the product.
- Only UX scope should be narrowed where it currently exceeds documented MVP commitments.

## 7. High-Level Action Plan

1. Update `epics.md` first; this is the main delivery blocker.
2. Make targeted PRD clarifications on MVP plugin boundary and release-gating quality expectations.
3. Update `ux-design-specification.md` to mark plugin-management flows and aspirational interactions appropriately.
4. Add minor architecture wording updates to reinforce vertical-slice planning.
5. Re-run readiness validation after artifact updates.

## 8. Handoff Plan

### Scope Classification

**Moderate**

### Route To

- **Product Manager / Scrum Master**
  - rewrite epics and stories
  - confirm backlog sequencing
- **Product Manager**
  - update PRD scope clarifications
- **UX Designer / Product Manager**
  - trim or relabel future-state UX flows
- **Architect**
  - add implementation-guidance clarifications if needed

### Success Criteria

- Every planned story is either clearly user-valued or explicitly marked as an enabler
- Oversized stories are split into independently testable slices
- UX scope matches MVP scope
- Plugin-system proof expectations are explicit
- Readiness status improves from `NEEDS WORK` to `READY` or near-ready on recheck

## 9. Decision Request

Recommended decision: **Approve** this sprint change proposal and route directly into artifact updates.

Pending your approval, the next best move is to update `/_bmad-output/planning-artifacts/epics.md` first, then tighten `/_bmad-output/planning-artifacts/prd.md`, `/_bmad-output/planning-artifacts/ux-design-specification.md`, and `/_bmad-output/planning-artifacts/architecture.md`.

## 10. Approved Handoff

**Scope:** Moderate

**Routed To:**
- Product Manager / Scrum Master for backlog restructuring
- Product Manager for PRD clarification
- UX Designer / Product Manager for UX scope correction
- Architect for minor implementation-guidance alignment

**Immediate Next Step:**
- Update `/_bmad-output/planning-artifacts/epics.md` to split oversized stories and reclassify enablers before touching other planning artifacts.
