---
name: analisis-ia-docs
description: Updates analisis_ia/docs after a closed slice. Writes PROGRESS.md, CHANGELOG.md, and ARCHITECTURE.md in English. Use proactively when finishing a milestone in analisis_ia/; never for tiny uncommitted edits.
---

# analisis_ia documentation

## When to use

After a slice or milestone in `analisis_ia/` is actually finished (scaffold, a module, an endpoint group). Not after every file tweak.

## Rules

- English only in `analisis_ia/docs/`.
- Never edit `ds_copilot/`.
- Chat summaries stay in Spanish; these files stay in English.
- Do not invent completed work. Match git/filesystem reality.

## Files

| File | Update when |
|------|-------------|
| `analisis_ia/docs/PROGRESS.md` | Status, done vs next. Always on slice close. |
| `analisis_ia/docs/CHANGELOG.md` | Dated technical entry (added/changed/fixed). Always on slice close. |
| `analisis_ia/docs/ARCHITECTURE.md` | Folder map, MVC mapping, product agents, Cursor agents. Only if structure or boundaries changed. |

## Format

- `PROGRESS.md`: current slice, completed, blocked, next.
- `CHANGELOG.md`: newest entry at the top, `YYYY-MM-DD`, short bullets.
- `ARCHITECTURE.md`: what each folder is for; Cursor subagents vs in-app agents; no Streamlit.
