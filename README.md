# hsafm-eventaudit

**Version `0.2.0rc1` — scientific source and archived data accompanying the EventAudit METHODS study.**

EventAudit evaluates observational evidence for the start and end boundaries of existing detector-defined high-speed atomic force microscopy (HS-AFM) tracks. When the available evidence supports a finite time interval, it reports that interval; otherwise, it records why a finite interval cannot be assigned. EventAudit does not change the original accepted detections or track assignments.

This repository provides selected scientific source code, method specifications, and archived outputs for inspection and reuse.

## Contents

- Author-owned Python scientific source, method and benchmark specifications, selected numerical summaries, and source-identity records.
- Selected source modules corresponding to external validation, supplied as documentation-normalized copies. Files with identical names may represent different historical versions and should not be interchanged.
- Two author-controlled archived datasets in `data/`: **14,958 synthetic observation records** and **119,664 archived method-prediction rows**. These records are not 14,958 independent physical events.

The repository contains **60 curated files**. The included files are a selection of the original research materials, not the entire historical working archive. For the archived data and their identities, see `data/README.md` and the included source-identity records. For environment information, see `docs/ENVIRONMENT_METHODS_ONLY.md`, `requirements.txt`, and `pyproject.toml`.

Selected Python module descriptions were standardized for this curated distribution. Scientific algorithms and numerical parameters were not changed; checksum references used to identify distributed source files were updated accordingly. The historical and distributed source hashes are recorded separately in `release/FROZEN_SELECTED_SOURCE_IDENTITIES.tsv`.

## Data and usage scope

Third-party raw HS-AFM `.asd` recordings and images are not redistributed here. Sealed synthetic evaluation truth is also excluded; truth-based re-scoring requires separately authorized inputs. Workflows depending on other omitted historical inputs or environment-specific configuration may require additional materials.

## Licensing and attribution

**Scientific code author:** Kateryna Muzyka ([ORCID](https://orcid.org/0000-0002-3029-2919)). Author-owned original scientific Python code is licensed under **BSD-3-Clause** (`LICENSE`). Selected author-owned synthetic observations, archived method predictions, numerical summaries, and written documentation are covered by **CC BY 4.0** as specified in `LICENSES/CC-BY-4.0-NOTICE.md`. Third-party materials retain their original owners' rights. The licensing of earlier archives does not determine the licensing of this separate curated distribution.

For citation metadata, see `CITATION.cff`.

## Source identity and availability

Version `0.2.0rc1` identifies this curated distribution. A tagged GitHub Release, Zenodo deposit, and DOI are not claimed here.
