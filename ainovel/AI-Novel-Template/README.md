# AI-Novel-Template

The **Template** of the AI Novel Operating System (ANES v2). It answers one
question: *what a new project looks like*. It produces a fresh, conformant
**Project instance** (ADR-004) — it is neither the rules (Standard) nor the
engine (Runtime).

> This repo pins **Standard `2.0.0`**.

## Why this exists (ADR-004)

A Project is an *instance*, never the Standard. Without a Template, every new
novel would be hand-copied from a fixture or a README example, and the
Project/Standard separation would erode. The Template makes Project
initialization **reproducible**.

## How it works — generated, not hand-built

`tools/init_project.py` reads the Standard's **generated catalog**
(`phase-1/generated/json-schema/catalog.json`) and scaffolds the empty Registry
tree from it. The directory layout therefore can never drift from the Standard,
because both the Template and the Runtime read the same catalog.

## Usage

```sh
python3 tools/init_project.py \
  --standard ../AI-Novel-Standard \
  --out ../my-novel-01 \
  --project-id my-novel-01
```

Produces:

```
my-novel-01/
  README.md
  registry/
    facts/        # one empty dir per project-scoped entity (from catalog)
      characters/ relationships/ timelines/ events/ world_rules/ items/
    derived/      # summary/ snapshot/ analysis/
    _meta/
      registry-version   # 1
      standard.pin       # 2.0.0
      project-id         # my-novel-01
      mint-ledger.yaml   # append-only, empty
```

The resulting Project passes the Runtime's deterministic gate immediately (an
empty Registry is trivially conformant), so you can start minting entities into a
known-good baseline.

## Relationship to the Runtime fixture

The Runtime's `tests/fixtures/proj-demo` is a *test fixture* (has data, exercises
the spine). A Template-generated Project is *empty* and meant to grow into a real
novel. Keeping them separate stops the fixture from becoming a stealth template.
