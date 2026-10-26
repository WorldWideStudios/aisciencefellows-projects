# Baebugs Find Your Protocol — source-bound discovery MVP

Purpose: make the Baebugs workflow and evidence discoverable without implying
that any laboratory method, model or instrument was physically executed.

## Contract
1. Curated templates are in protocols/catalog.json, independently addressable by SHA-256
   of canonical JSON. Content identity is distinct from occurrence/context identity.
2. site/protocols/build_catalog.py binds every declared source file to a real
   AoK file leaf and recomputes exact bytes; source drift FAILS CLOSED.
3. Declared source edges are content-addressed as REFERENCES_SOURCE_ATOM in the
   derived protocol projection. This does not modify historical DAISY hypergraphs
   or Merkle/MMR commitments and does not establish causality.
4. Users can search, bookmark, organize into named collections, create private BYO protocols, remix
   templates, and export local browser review receipts. The application is static
   and transmits no imported data to a backend.
5. Public share links contain only public template IDs. Local remixes can be
   exported explicitly by the researcher, never silently published.
6. A guided checklist records EXECUTED browser interactions, not verified
   physical processing. No robot, reagent, sample capture or assay commands exist.
7. Source-specific rights are shown with each leaf. Self-reported BYO licenses are
   UNKNOWN until independently reviewed. No signatures are asserted.
8. LocalStorage is not enterprise-grade durable storage; explicit export is the
   recovery path. Authenticated cloud sync and physical lab integration are DEFERRED.
9. Existing custody breaks stay visible and unresolved in the parent evidence pack.

## Deferred
Persistent team collections, authenticated protocols, eLabFTW/LIMS connectors,
robot control, signed human authorization, scientific accuracy and real-time
Merkle root recomputation.

## Validation
Run isolated tests/test_protocol_discovery.py, regenerate Baebugs AoK and MVP
snapshots, and execute site/mvp/build_public_site.py with a full pinned commit.
Static deployment contents are a derived view, not a new MMR commitment.
