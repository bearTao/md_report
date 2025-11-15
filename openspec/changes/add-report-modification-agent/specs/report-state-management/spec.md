# Report State Management Specification

## ADDED Requirements

### Requirement: Report State Versioning
The system SHALL maintain versioned snapshots of report state across modifications.

#### Scenario: Initial state creation
- **GIVEN** a newly generated report
- **WHEN** first modification session starts
- **THEN** ReportState SHALL be created at version 1
- **AND** SHALL capture all template variables with current values
- **AND** SHALL capture original template content
- **AND** SHALL capture report structure (sections)
- **AND** SHALL set generated_at timestamp

#### Scenario: State version increment
- **GIVEN** report at version N
- **WHEN** a modification is successfully applied
- **THEN** a new ReportState SHALL be created at version N+1
- **AND** previous version SHALL be retained
- **AND** report.version SHALL be updated to N+1
- **AND** created_at SHALL reflect modification time

#### Scenario: State snapshot storage
- **WHEN** report state snapshot is created
- **THEN** SHALL be persisted to report_states table
- **AND** SHALL include complete variables JSON
- **AND** SHALL include report_structure JSON
- **AND** SHALL include temp_template_content if modified
- **AND** SHALL enable rollback to any version

### Requirement: Variable Management
The system SHALL manage both template variables and runtime variables in unified structure.

#### Scenario: Template variable storage
- **GIVEN** variable defined in template YAML metadata
- **WHEN** stored in ReportState
- **THEN** VariableInfo SHALL have type="template"
- **AND** SHALL include source type (sql, api, ai_generation, etc.)
- **AND** SHALL include metadata from YAML
- **AND** SHALL include current value
- **AND** SHALL include last_modified timestamp

#### Scenario: Runtime variable storage
- **GIVEN** variable created during conversation (e.g., for new section)
- **WHEN** stored in ReportState
- **THEN** VariableInfo SHALL have type="runtime"
- **AND** SHALL include generation_context
- **AND** SHALL include created_in_turn
- **AND** SHALL NOT have YAML metadata
- **AND** SHALL be ephemeral (specific to this report instance)

#### Scenario: Variable value updates
- **WHEN** a variable value is updated
- **THEN** last_modified timestamp SHALL be updated
- **AND** is_dirty flag SHALL be set to true
- **AND** old value SHALL be preserved in previous version snapshot
- **AND** new value SHALL be in current state

#### Scenario: Variable lookup
- **WHEN** accessing variables in ReportState
- **THEN** SHALL support lookup by name
- **AND** SHALL support filtering by type (template/runtime)
- **AND** SHALL support filtering by source
- **AND** SHALL support filtering by dirty flag

### Requirement: Template Modification Tracking
The system SHALL track modifications to report templates separately from original templates.

#### Scenario: Temporary template creation
- **GIVEN** user requests template modification (add section)
- **WHEN** template is modified
- **THEN** temp_template_content SHALL be set in ReportState
- **AND** original_template_content SHALL remain unchanged
- **AND** rendering SHALL use temp_template_content
- **AND** report.using_temp_template flag SHALL be set to true

#### Scenario: Template modification accumulation
- **GIVEN** report with existing temporary template
- **WHEN** another section is added
- **THEN** SHALL modify existing temp_template_content
- **AND** SHALL not create new template
- **AND** changes SHALL accumulate

#### Scenario: Save as new template
- **WHEN** user requests to save modifications as new template
- **THEN** temp_template_content SHALL be saved as new Template record
- **AND** new template SHALL have new ID
- **AND** SHALL link to parent_template_id
- **AND** report SHALL optionally update to use new template

### Requirement: Report Structure Tracking
The system SHALL maintain structured information about report sections for navigation and modification.

#### Scenario: Structure extraction from content
- **GIVEN** generated report Markdown content
- **WHEN** ReportStructure is built
- **THEN** SHALL parse all Markdown headings (# to ######)
- **AND** each Section SHALL include level (1-6)
- **AND** SHALL include title text
- **AND** SHALL include start_line and end_line
- **AND** SHALL include content_preview (first 100 chars)

#### Scenario: Variable usage tracking per section
- **WHEN** building ReportStructure
- **THEN** each Section SHALL list variables_used
- **AND** SHALL identify which variables appear in that section
- **AND** SHALL enable targeted re-rendering (future optimization)

#### Scenario: Content statistics
- **WHEN** ReportStructure includes ContentStats
- **THEN** SHALL detect and count tables
- **AND** SHALL detect and count images
- **AND** SHALL detect and count code blocks
- **AND** SHALL store in content_stats

### Requirement: User Input Preservation
The system SHALL preserve original user inputs for reference and re-generation.

#### Scenario: Store initial inputs
- **GIVEN** report generated with user inputs
- **WHEN** ReportState is created
- **THEN** user_inputs SHALL include all user_input variables
- **AND** SHALL be stored as JSON dict
- **AND** SHALL enable re-generation with same inputs

#### Scenario: Update inputs during modification
- **WHEN** user input parameter is changed via modification
- **THEN** user_inputs SHALL be updated
- **AND** SHALL reflect in next state version
- **AND** original inputs SHALL be in previous version

### Requirement: State Consistency
The system SHALL ensure consistency between report state and actual report content.

#### Scenario: Validate state after modification
- **WHEN** report state is updated
- **THEN** all referenced variables SHALL exist in variables dict
- **AND** temp_template_content SHALL be valid Jinja2 if present
- **AND** report_structure SHALL match rendered content

#### Scenario: Detect state corruption
- **WHEN** loading report state from database
- **THEN** SHALL validate JSON schema
- **AND** if validation fails, SHALL log error
- **AND** MAY attempt recovery from previous version
- **AND** SHALL prevent cascading failures

### Requirement: State Querying and Filtering
The system SHALL provide efficient querying of report state for various purposes.

#### Scenario: Get all dirty variables
- **WHEN** determining what needs re-execution
- **THEN** SHALL filter variables with is_dirty=true
- **AND** SHALL return list of variable names
- **AND** SHALL be efficient (no full scan if indexed)

#### Scenario: Get variables by source type
- **WHEN** analyzing what data sources are used
- **THEN** SHALL filter by source (sql, api, ai_generation, etc.)
- **AND** SHALL return matching VariableInfo objects
- **AND** SHALL support multiple source types in one query

#### Scenario: Get runtime variables for session
- **WHEN** reviewing what was created in conversation
- **THEN** SHALL filter by type="runtime"
- **AND** SHALL order by created_in_turn
- **AND** SHALL show conversation evolution

### Requirement: State Diff and Comparison
The system SHALL support comparing state versions to show what changed.

#### Scenario: Variable value changes
- **GIVEN** report state at version N and N+1
- **WHEN** computing diff
- **THEN** SHALL identify variables with changed values
- **AND** SHALL show old_value and new_value
- **AND** SHALL include variable name and type

#### Scenario: Structure changes
- **GIVEN** report states before and after template modification
- **WHEN** computing diff
- **THEN** SHALL identify added sections
- **AND** SHALL identify modified sections
- **AND** SHALL identify removed sections (if applicable)

#### Scenario: Template changes
- **WHEN** temp_template_content differs from original
- **THEN** SHALL highlight template modifications
- **AND** MAY provide line-level diff (future enhancement)

### Requirement: State Metadata
The system SHALL track metadata about state lifecycle and usage.

#### Scenario: State timestamps
- **WHEN** state is created or updated
- **THEN** SHALL record generated_at timestamp
- **AND** SHALL record version number
- **AND** SHALL enable temporal queries

#### Scenario: State size tracking
- **WHEN** storing state
- **THEN** SHALL track total number of variables
- **AND** SHALL track number of template vs runtime variables
- **AND** SHALL log warnings if state grows too large (>1000 variables)

### Requirement: State Rollback Support
The system SHALL enable rolling back to previous report versions.

#### Scenario: List available versions
- **WHEN** user requests version history
- **THEN** SHALL return all ReportState versions
- **AND** SHALL include version number
- **AND** SHALL include timestamp
- **AND** SHALL include summary of changes

#### Scenario: Rollback to previous version
- **WHEN** user requests rollback to version N
- **THEN** SHALL load ReportState from version N
- **AND** SHALL render report with that state
- **AND** SHALL create new version N+X with reverted state
- **AND** SHALL preserve history (no deletion)

### Requirement: State Export and Import
The system SHALL support exporting and importing report state for backup and migration.

#### Scenario: Export state as JSON
- **WHEN** exporting report state
- **THEN** SHALL serialize complete ReportState to JSON
- **AND** SHALL include all variables with values
- **AND** SHALL include template content
- **AND** SHALL include metadata
- **AND** JSON SHALL be self-contained

#### Scenario: Import state from JSON
- **WHEN** importing report state
- **THEN** SHALL validate JSON schema
- **AND** SHALL restore all variables
- **AND** SHALL restore template modifications
- **AND** SHALL assign new version number
- **AND** SHALL validate after import

