---
applyTo: "docs/**/*.md"
---

# Documentation Guidelines

## Academic Tone for Conference Submission

All documentation must maintain a formal, academic tone suitable for the **AIMS 2025 conference** submission.

**Writing style**:
- Use formal, technical language appropriate for peer review
- Avoid colloquialisms and informal expressions
- Present ideas objectively with supporting evidence
- Use precise terminology consistently
- Structure arguments logically with clear motivation and justification
- Include citations and references where appropriate

**Examples**:
- ❌ "We think this is a cool approach"
- ✅ "This approach addresses the fundamental challenge of..."
- ❌ "Our system is way better than others"
- ✅ "Our evaluation demonstrates a 40% improvement in retrieval accuracy compared to baseline approaches"

## DEVLOG Entry Format

When editing `DEVLOG.md`, follow the existing entry format:

```markdown
### YYYY-MM-DD - Brief Title of Change 📊

**Status:** ✅ Complete | 🚧 In Progress | ⚠️ Blocked

**Summary:**
One-paragraph summary of what was implemented or changed.

**Key Findings:**

**✅ What's Complete:**
- Bullet point 1
- Bullet point 2

**❌ What's Missing:**
- Bullet point 1
- Bullet point 2

**Current Project Completion:**
- **Phase X**: XX% ✅/🚧/❌ (X/Y tests passing)

**Evidence from Codebase:**
\`\`\`bash
# Directory structures, file listings, or command outputs
\`\`\`
```

**Guidelines**:
- Always include date in YYYY-MM-DD format
- Use status emojis consistently
- Be specific about file paths and line numbers
- Include evidence (test results, file structures, command outputs)
- Update completion percentages accurately

## ADR (Architecture Decision Record) Format

When creating new ADRs in `docs/ADR/`, follow the established template and conventions:

**File naming**: `NNN-brief-description.md` (e.g., `007-lifecycle-engine-design.md`)

**Structure**:
```markdown
# ADR-NNN: Title of Decision

**Status:** Proposed | Accepted | Deprecated | Superseded  
**Date:** Month DD, YYYY  
**Supersedes:** ADR-XXX (if applicable)

## 1. Context

Describe the problem space, constraints, and requirements that motivate
this decision. Include:
- Current state and limitations
- Key drivers for change
- Relevant research or prior art

## 2. Decision

State the decision clearly and unambiguously. Include:
- What we will do
- Why this approach was chosen
- Key architectural commitments

## 3. Consequences

### Positive
- Benefit 1
- Benefit 2

### Negative
- Trade-off 1
- Trade-off 2

### Neutral
- Implementation consideration 1

## 4. Implementation Plan

Outline the implementation approach:
- Phase 1: ...
- Phase 2: ...

## 5. Alternatives Considered

Document alternatives that were evaluated:

### Alternative 1: Description
**Pros**: ...
**Cons**: ...
**Why rejected**: ...
```

**ADR guidelines**:
- Maintain consistent numbering (check existing ADRs)
- Reference related ADRs explicitly
- Include rationale for decisions
- Document alternatives and why they were rejected
- Update status as decisions evolve
- Use technical precision and academic tone

## Cross-Referencing

**Internal references**:
- Link to other documentation: `[ADR-003](../ADR/003-four-layers-memory.md)`
- Reference code: `` See `src/memory/ciar_scorer.py:85-130` for implementation ``
- Link to specs: `[Use Case 01](uc-01.md)`

**External references**:
- Academic papers: Include full citation
- Code repositories: Include GitHub URL with commit hash
- Documentation: Include URL and access date

## Diagrams and Visual Aids

Use Mermaid for architecture diagrams:

```markdown
\`\`\`mermaid
graph TD
    A[Component A] --> B[Component B]
    B --> C[Component C]
\`\`\`
```

**Diagram guidelines**:
- Use consistent styling across all diagrams
- Label all components clearly
- Include legend if needed
- Keep diagrams focused on one concept
- Update diagrams when architecture changes

## Technical Specifications

For technical specification documents (`uc-*.md`, `sd-*.md`, `dd-*.md`):

**Use Case (uc-*.md)**:
- Clear title and description
- Actors and preconditions
- Main flow and alternative flows
- Success criteria

**Sequence Diagram (sd-*.md)**:
- Component interactions
- Message flows
- Error handling paths

**Data Dictionary (dd-*.md)**:
- Data structures with types
- Field descriptions
- Validation rules
- Example values

## Version Control

- Keep documentation synchronized with code changes
- Update relevant docs when making architectural changes
- Mark outdated sections clearly
- Update status and dates in ADRs when decisions change
