# Requirements Document

## Introduction

This feature expands the search query coverage for the PKL Research Tool by adding new search terms to find more web development agencies and game studios in Jakarta Selatan. The tool currently scrapes Google Maps to find IT companies using role-specific queries. This enhancement adds 11 new queries (7 for web/fullstack development, 4 for game development) to increase discovery of companies that may not appear with existing generic terms.

## Glossary

- **Query_Manager**: The component responsible for managing and organizing search queries in the configuration system
- **QUERIES_BY_ROLE**: Python dictionary in `config.py` that groups search queries by role focus (software, ai, fullstack, game)
- **Search_Engine**: The component that executes Google Maps searches using configured queries
- **Query_Suffix**: The automatic "jakarta selatan" text appended to all search queries

## Requirements

### Requirement 1: Add Web/Fullstack Development Queries

**User Story:** As a PKL applicant, I want expanded web development search queries, so that I can discover more web agencies and fullstack development companies that may use Indonesian or specific service-based terminology.

#### Acceptance Criteria

1. THE Query_Manager SHALL include the query "jasa pembuatan website" in the fullstack role category
2. THE Query_Manager SHALL include the query "web agency" in the fullstack role category
3. THE Query_Manager SHALL include the query "web design company" in the fullstack role category
4. THE Query_Manager SHALL include the query "backend developer" in the fullstack role category
5. THE Query_Manager SHALL include the query "frontend developer" in the fullstack role category
6. THE Query_Manager SHALL include the query "fullstack agency" in the fullstack role category
7. THE Query_Manager SHALL include the query "pembuatan aplikasi web" in the fullstack role category

### Requirement 2: Add Game Development Queries

**User Story:** As a PKL applicant interested in game development, I want expanded game industry search queries, so that I can find more game studios and publishers using both English and Indonesian terminology.

#### Acceptance Criteria

1. THE Query_Manager SHALL include the query "game publisher" in the game role category
2. THE Query_Manager SHALL include the query "studio game" in the game role category
3. THE Query_Manager SHALL include the query "pembuat game" in the game role category
4. THE Query_Manager SHALL include the query "game developer indonesia" in the game role category

### Requirement 3: Preserve Existing Query Structure

**User Story:** As a developer, I want existing queries and system behavior to remain unchanged, so that the tool continues to work reliably for existing use cases.

#### Acceptance Criteria

1. WHEN new queries are added, THE Query_Manager SHALL preserve all existing queries in their respective role categories
2. WHEN queries are executed, THE Search_Engine SHALL append the Query_Suffix "jakarta selatan" to all queries including new ones
3. WHEN search results are tagged, THE Search_Engine SHALL apply role_fit tags using the existing heuristic rules
4. THE Query_Manager SHALL maintain the existing dictionary structure QUERIES_BY_ROLE with keys: software, ai, fullstack, game

### Requirement 4: Configuration File Modification

**User Story:** As a developer, I want the new queries stored in the configuration file, so that they are centrally managed and easy to modify.

#### Acceptance Criteria

1. THE Query_Manager SHALL store all queries in the QUERIES_BY_ROLE dictionary in `config.py`
2. WHEN the configuration is loaded, THE Query_Manager SHALL make new queries immediately available to the search command
3. THE Query_Manager SHALL maintain alphabetical or logical ordering within each role category for readability
