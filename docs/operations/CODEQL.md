# CodeQL Configuration

## Current failure

The GitHub default-setup workflow selected `c-cpp`, but Cloud-X currently contains no C or C++ source/header files. The C/C++ extractor therefore fails with `No source files found`.

## Active language policy

For the current repository, CodeQL should analyze supported languages that are actually present:

- `javascript-typescript`
- `python`
- GitHub Actions analysis may remain enabled when GitHub offers it.

C/C++ must not be selected unless C or C++ source is intentionally added later.

## Current setup choice

Cloud-X currently uses GitHub CodeQL **default setup**. Keep default setup for now and edit its language selection in repository settings so C/C++ is deselected.

Do not add a competing advanced CodeQL workflow while default setup remains active. If Cloud-X later needs custom build steps, queries, path rules or matrices, switch deliberately to advanced setup and encode the explicit language matrix in the repository.
