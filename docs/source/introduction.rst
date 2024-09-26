.. _introduction:

FederatedCode Overview
========================

**FederatedCode** is a solution for decentralized, and federated metadata about software
applications, with a focus on known vulnerabilities, package versions, origin and licensing.
These data are essential to support efficient **Software Composition Analysis (SCA)** with quality
open reference data about open source components.


Why FederatedCode?
--------------------

Modern software systems (and the organizations building and using them) rely on reusing free and
open source software (FOSS).

Knowing which free and open source code package is in use, its origin and security issues matters
because:

- You want to avoid using buggy, outdated or vulnerable components, and
- You're required to **know the license of third-party code** before using it.

This requires quality reference metadata to support efficient analysis and compliance processes
automation. Existing FOSS metadata databases are centralized and "too big to share" with locked
metadata behind gated APIs promoting lock-in and prohibiting privacy-preserving offline usage.

FederatedCode is a decentralized and federated system for FOSS metadata, enabling social review and
sharing of curated metadata along with air-gapped, local usage to preserve privacy and
confidentiality.

Because FederatedCode is decentralized and federated, it promotes sharing without having a single
centralized ownership and point of control.

FederatedCode's distributed metadata collection process includes metadata crawling, curation and
sharing, and its application to open source software package origin, license and vulnerabilities.
The project strives to implement the concepts outlined in "Federated and decentralized metadata
system" published at https://www.tdcommons.org/dpubs_series/5632/


What is FederatedCode?
---------------------------

**FederatedCode** is composed of multiple distributed sub-systems:

- A system to store versioned metadata as structure text (JSON, YAML) in multiple Git repositories
  structured to enable direct content retrieval using a Package URL (PURL),
- A series of utilities to synchronize AboutCode databases with these versioned metadata, and
- A system to publish package-centric events such as the release of a new package version, the
  publication of a vulnerability, the availability of detail scans, analysis and SBOMs using
  publish/subscribe mechanism over ActivityPub. This further enables distributed discussions and
  curation of the data, in the open.
