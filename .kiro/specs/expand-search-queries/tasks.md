# Implementation Plan: Expand Search Queries

## Overview

This implementation adds 11 new search queries to the PKL Research Tool's configuration:
- 7 queries for web/fullstack development (including Indonesian terms like "jasa pembuatan website")
- 4 queries for game development (including Indonesian terms like "studio game")

The changes are localized to the `config.py` file's `QUERIES_BY_ROLE` dictionary. All new queries will automatically work with the existing search command and role-fit tagging logic.

## Tasks

- [x] 1. Update QUERIES_BY_ROLE dictionary with new queries
  - Add 7 new queries to the `fullstack` key in `QUERIES_BY_ROLE` dictionary in `src/pkl_research/config.py`
  - Add 4 new queries to the `game` key in `QUERIES_BY_ROLE` dictionary
  - Maintain alphabetical or logical ordering within each role category for readability
  - Preserve all existing queries (software, ai, fullstack, game categories)
  - _Requirements: 1.1-1.7, 2.1-2.4, 3.1, 3.4, 4.1_

- [ ]* 2. Write unit tests for query configuration
  - Create test file `tests/test_config_queries.py` if it doesn't exist
  - Test that all required fullstack queries are present in `QUERIES_BY_ROLE['fullstack']`
  - Test that all required game queries are present in `QUERIES_BY_ROLE['game']`
  - Test that existing software and ai queries are preserved
  - Test that QUERIES_BY_ROLE maintains the expected dictionary structure with keys: software, ai, fullstack, game
  - _Requirements: 3.1, 3.4_

- [ ]* 3. Manual verification with search command
  - Run `pkl-research search --help` to verify the command is available
  - Optionally run a limited search to confirm queries are used (requires browser, can be skipped)
  - Verify that query suffix "jakarta selatan" is automatically appended (check search logs if running actual search)
  - _Requirements: 3.2, 4.2_

- [x] 4. Update documentation
  - Check if `README.md` or `docs/` folder documents the search queries
  - If documentation exists, update it to mention the expanded query coverage
  - If no documentation mentions queries, skip this task
  - _Requirements: 4.1_

- [x] 5. Final checkpoint
  - Ensure all tests pass
  - Verify config.py syntax is valid (no Python syntax errors)
  - Confirm the implementation is complete

## Notes

- Tasks marked with `*` are optional and can be skipped for faster delivery
- The core change is updating the `QUERIES_BY_ROLE` dictionary in `config.py`
- Existing search command logic automatically uses new queries without code changes
- All queries will automatically get "jakarta selatan" suffix via existing `QUERY_SUFFIX` logic
- Role-fit tagging uses existing heuristics in the filter logic (no changes needed)
