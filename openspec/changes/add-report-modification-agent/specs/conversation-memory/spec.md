# Conversation Memory Specification

## ADDED Requirements

### Requirement: Conversation Memory Structure
The system SHALL maintain structured conversation memory including session metadata, conversation history, and report state.

#### Scenario: Memory initialization
- **WHEN** a new modification session starts
- **THEN** a ConversationMemory SHALL be created
- **AND** SHALL include session_id
- **AND** SHALL include report_id
- **AND** SHALL include started_at timestamp
- **AND** SHALL include initial ReportState

#### Scenario: Memory persistence
- **WHEN** conversation memory is updated
- **THEN** it SHALL be persisted to the database
- **AND** SHALL be retrievable by session_id
- **AND** SHALL survive application restarts

### Requirement: Conversation History Tracking
The system SHALL track all conversation turns with user messages and assistant responses.

#### Scenario: Record conversation turn
- **GIVEN** an active conversation session
- **WHEN** user sends a modification request
- **AND** agent generates a response
- **THEN** a ConversationTurn SHALL be created
- **AND** SHALL include turn_id (sequential)
- **AND** SHALL include timestamp
- **AND** SHALL include user_message
- **AND** SHALL include assistant_response
- **AND** SHALL include operations_performed (operation IDs)
- **AND** SHALL include state_changes (variable modifications)

#### Scenario: Retrieve conversation history
- **GIVEN** a session with 5 conversation turns
- **WHEN** loading memory for context
- **THEN** all 5 turns SHALL be loaded
- **AND** SHALL be ordered by turn_id
- **AND** SHALL include all messages and metadata

#### Scenario: Recent conversation windowing
- **GIVEN** a session with 15 conversation turns
- **WHEN** building context for intent parsing
- **THEN** only the most recent 3 turns SHALL be included
- **AND** older turns SHALL be summarized in context_summary

### Requirement: Context Summary Generation
The system SHALL generate summaries of long conversation histories to manage context window.

#### Scenario: Summary generation trigger
- **GIVEN** a conversation with 10 turns
- **WHEN** the 11th turn is added
- **THEN** a context summary SHALL be generated
- **AND** SHALL use LLM to summarize turns 1-8
- **AND** SHALL retain full detail for turns 9-11

#### Scenario: Summary content
- **WHEN** a context summary is generated
- **THEN** it SHALL include key modifications performed
- **AND** SHALL include current parameter values
- **AND** SHALL include important user preferences expressed
- **AND** SHALL be concise (<500 words)

### Requirement: Report State Snapshot
The system SHALL maintain complete report state including all variables and metadata.

#### Scenario: Initial state capture
- **GIVEN** an existing generated report
- **WHEN** first modification session starts
- **THEN** ReportState SHALL be created with all template variables
- **AND** SHALL include user_inputs from original generation
- **AND** SHALL include report_structure (sections)
- **AND** SHALL include original_template_content
- **AND** SHALL set version=1

#### Scenario: State updates
- **WHEN** variables are modified
- **THEN** the VariableInfo SHALL be updated
- **AND** last_modified timestamp SHALL be updated
- **AND** is_dirty flag SHALL be set to true
- **AND** version SHALL be incremented

#### Scenario: Runtime variable addition
- **WHEN** a new variable is created during conversation (e.g., for new section)
- **THEN** VariableInfo SHALL be added to state
- **AND** type SHALL be "runtime"
- **AND** generation_context SHALL be populated
- **AND** created_in_turn SHALL reference the conversation turn

### Requirement: Variable Information Tracking
The system SHALL track comprehensive information for all variables (template and runtime).

#### Scenario: Template variable info
- **GIVEN** a template variable from the original report
- **WHEN** stored in ReportState
- **THEN** VariableInfo SHALL include name
- **AND** SHALL include value (current)
- **AND** SHALL include type="template"
- **AND** SHALL include source (e.g., "sql", "api")
- **AND** SHALL include metadata from YAML definition

#### Scenario: Runtime variable info
- **GIVEN** a variable created during conversation
- **WHEN** stored in ReportState
- **THEN** VariableInfo SHALL include name
- **AND** SHALL include value
- **AND** SHALL include type="runtime"
- **AND** SHALL include generation_context
- **AND** SHALL include created_in_turn number

#### Scenario: Generation context preservation
- **WHEN** a runtime variable is created with AI generation
- **THEN** generation_context SHALL include prompt_template used
- **AND** SHALL include data_sources referenced
- **AND** SHALL include generation_params
- **AND** SHALL enable re-generation with same parameters

### Requirement: Memory Querying
The system SHALL provide efficient querying of conversation memory and state.

#### Scenario: Load memory by session
- **WHEN** MemoryManager.get_or_create_memory(session_id) is called
- **THEN** complete ConversationMemory SHALL be loaded
- **AND** SHALL include all conversation turns
- **AND** SHALL include current ReportState
- **AND** SHALL load within 100ms for typical session (<50 turns)

#### Scenario: Query variables by type
- **WHEN** filtering variables in ReportState
- **THEN** SHALL support filtering by type (template vs runtime)
- **AND** SHALL support filtering by source type
- **AND** SHALL support filtering by is_dirty flag

#### Scenario: State changes history
- **WHEN** reviewing what changed in a conversation
- **THEN** each ConversationTurn SHALL include state_changes
- **AND** state_changes SHALL list variable names and their new values
- **AND** SHALL enable audit trail reconstruction

### Requirement: Memory Cleanup
The system SHALL manage memory lifecycle and cleanup inactive sessions.

#### Scenario: Mark session inactive
- **GIVEN** a session with last_activity_at > 24 hours ago
- **WHEN** cleanup job runs
- **THEN** session SHALL be marked is_active=false
- **AND** conversation history SHALL be retained
- **AND** report state SHALL be retained for audit

#### Scenario: Prevent access to inactive session
- **WHEN** user attempts to continue an inactive session
- **THEN** system SHALL return session_expired error
- **AND** SHALL offer to create new session

#### Scenario: Archive old sessions
- **GIVEN** inactive sessions older than 90 days
- **WHEN** archive job runs (if implemented)
- **THEN** sessions MAY be moved to archive storage
- **AND** SHALL remain accessible for audit purposes

### Requirement: Memory Consistency
The system SHALL maintain consistency between database and in-memory state.

#### Scenario: Transactional updates
- **WHEN** modifying report state
- **THEN** all related updates SHALL occur in a database transaction
- **AND** if any update fails, all SHALL be rolled back
- **AND** memory SHALL remain consistent with database

#### Scenario: Concurrent modification prevention
- **WHEN** multiple requests target the same session simultaneously
- **THEN** system SHALL serialize the requests
- **OR** SHALL use optimistic locking to detect conflicts
- **AND** SHALL prevent data corruption

