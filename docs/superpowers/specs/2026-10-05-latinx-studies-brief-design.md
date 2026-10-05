# Latinx Studies brief (CIP 05.0107) and frozen brief numbering

**Date:** 2026-10-05
**Status:** Implemented 2026-10-05 (surgical splice).

## Goal

1. Add a labor-market brief for the Latinx Studies minor (LTST) on CIP `05.0107`,
   noting on the brief that CIPs `05.0134` and `05.0203` give identical figures.
2. Stop renumbering: briefs 001-084 keep their numbers permanently; each new brief is
   appended as the next number.

## Decisions

- **Name:** `Latinx Studies`, the unit's current name. No degree or "minor" suffix,
  matching the `Creative Writing` / `Public Policy` precedent.
- **CIP:** `05.0107` Latin American Studies. `05.0134` (Latin American and Caribbean
  Studies) and `05.0203` (Hispanic-American, Puerto Rican, and Mexican-American/Chicano
  Studies) were checked: in the raw CIP2020-SOC2018 crosswalk each has exactly one row,
  to SOC `25-1062` Area, Ethnic, and Cultural Studies Teachers, Postsecondary. All three
  therefore produce the same brief figures, which are also the figures on brief 056
  (`Language and Area Studies: Spanish/Latin America (BA)`, also `05.0107`).
- **No multi-CIP program support.** The pipeline and component assume one CIP per
  program. Adding a union-of-SOCs mode would change nothing here (the union is still one
  SOC), so it was not built.
- **Shared CIP, no award double count.** `mn_ltst` is mapped `multiple_programs_share_cip`
  with award share `0`: IPEDS Completions does not report minors, and `05.0107`'s reported
  awards stay with `ba_spla`. `ba_spla`'s brief record is unchanged (the brief shows no
  awards).
- **Printed note.** New optional inventory column `brief_note`, carried through the
  one-pager workbook into an optional record field `note`, which the `op2-brief`
  component prints as an extra "How to read this" bullet. Records without a note do not
  get the key, so every existing record stays byte-identical.

## Numbering change

- One-time migration: the `PROGRAMS2` array was reordered into the printed order as of
  2026-09-09 (alphabetical, verified page-by-page then), and the page shell's
  `.sort((a,b)=>a.name.localeCompare(b.name))` was removed, so the shell prints array
  order. The screen-only cover line dropped "alphabetical".
- `program_briefs.load_program_names` now reads page order from the bundle instead of
  re-sorting the inventory, and fails if the bundle and inventory name sets disagree.
  This also removes the risk noted on 2026-09-09 that JavaScript `localeCompare` and
  Python `str.casefold` could collate differently and mislabel split pages.
- `build_briefs_bundle` already appends new records at the end, so the next addition is
  086 with no further change.

## Component asset change

`HowToRead` in the `op2-brief` component gained one conditional, after the
single-teaching bullet:

```js
if(p.note){
  bullets.push(p.note);
}
```

## Build chain used

1. Rows added to `program_inventory.csv` (`mn_ltst`, `Latinx Studies`, `LTST`, `CAS`,
   `Minor`, `minor`, with `brief_note`) and `program_cip_map.csv`.
2. `python -m src.run` (no `--force`): 76 CIP summary rows (unchanged; `05.0107` was
   already present), 85 program rows. All core sources were cache hits; the date-stamped
   state proxy re-downloaded and was identical to the 2026-09-09 pull.
3. `python -m src.build_briefs_bundle`: one record appended.
4. `python -m src.program_briefs`: 85-page full set, 85 individual PDFs, delivery ZIP.

## Verification

- The 84 existing records are identical to the pre-change bundle and sit in their
  original positions; the fresh workbook reproduces all 85 records exactly.
- Extracted text of pages 1-84 of the new full set is identical to the pre-change full
  set. Every page carries the expected name at its position (whitespace-insensitive).
- Page 85 renders `Latinx Studies`, CIP 05.0107, one occupation, the note, no draft stamp,
  no proxy box, on one page.
- Full-set pages == individual PDFs == ZIP entries == 85; the ZIP's 84 previous entry
  names are all unchanged.
- `pytest` green (62 tests).

## Public references for the crosswalk

- NCES CIP-SOC crosswalk resources: https://nces.ed.gov/ipeds/cipcode/resources.aspx?y=56
- Crosswalk file: https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx
- Per-CIP views (O*NET education crosswalk, built on the NCES crosswalk):
  https://www.onetonline.org/crosswalk/CIP?s=05.0107 (also `05.0134`, `05.0203`)
