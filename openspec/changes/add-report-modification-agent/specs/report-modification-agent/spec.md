# Report Modification Agent Specification

## ADDED Requirements

### Requirement: Agent Orchestration
The system SHALL provide a ReportModificationAgent that orchestrates the modification of existing reports through natural language requests.

#### Scenario: Basic report modification
- **GIVEN** an existing report with ID "report_123"
- **WHEN** user sends request "Change the microgrid ID to ZQGY0175"
- **THEN** the agent SHALL parse the intent, plan operations, execute modifications, and return a ModificationResult
- **AND** the result SHALL include the list of operations performed
- **AND** the result SHALL include a user-friendly explanation
- **AND** the result SHALL include the updated report content

#### Scenario: Multi-turn conversation
- **GIVEN** an active conversation session
- **WHEN** user sends first request "Change time to 1 week"
- **AND** then sends second request "Make the analysis more detailed"
- **THEN** the agent SHALL maintain context between requests
- **AND** the second modification SHALL build upon the first
- **AND** both modifications SHALL be reflected in the final report

#### Scenario: Failed modification with partial success
- **GIVEN** a modification request with multiple operations
- **WHEN** one operation fails during execution
- **THEN** the agent SHALL mark that operation as failed
- **AND** SHALL continue executing remaining operations
- **AND** SHALL return partial success status
- **AND** SHALL include error details in the failed operation

### Requirement: Modification Result Structure
The system SHALL return structured modification results using the ModificationResult schema.

#### Scenario: Successful modification result
- **WHEN** a modification completes successfully
- **THEN** the result SHALL include success=true
- **AND** SHALL include report_id
- **AND** SHALL include operations array with all performed operations
- **AND** SHALL include explanation text
- **AND** SHALL include modified_content as Markdown
- **AND** SHALL include metadata with timing and cost information

#### Scenario: Operation hierarchy
- **GIVEN** a parameter update that triggers dependency re-execution
- **WHEN** the modification completes
- **THEN** the operations array SHALL show parent-child relationships
- **AND** the parent operation SHALL be "parameter_update"
- **AND** the child operation SHALL be "variable_execution"
- **AND** each operation SHALL have unique ID

### Requirement: Session Management
The system SHALL support conversation sessions for multi-turn interactions.

#### Scenario: Create new session
- **WHEN** user initiates modification without session_id
- **THEN** the agent SHALL create a new session
- **AND** SHALL return the session_id in the response
- **AND** SHALL persist the session to database

#### Scenario: Resume existing session
- **GIVEN** an active session with ID "sess_abc123"
- **WHEN** user sends modification request with that session_id
- **THEN** the agent SHALL load conversation history
- **AND** SHALL use history as context for intent parsing
- **AND** SHALL append new turn to conversation history

#### Scenario: Session expiry
- **GIVEN** a session inactive for 24 hours
- **WHEN** cleanup job runs
- **THEN** the session SHALL be marked as inactive
- **AND** conversation history SHALL be retained for audit

### Requirement: Progress Reporting
The system SHALL report real-time progress of modifications via WebSocket.

#### Scenario: Progress updates during modification
- **GIVEN** a modification in progress
- **WHEN** each operation executes
- **THEN** progress updates SHALL be sent via WebSocket
- **AND** updates SHALL include operation description
- **AND** updates SHALL include current status (parsing, planning, executing, rendering)
- **AND** updates SHALL include percentage complete

### Requirement: Error Handling
The system SHALL handle errors gracefully and provide actionable feedback.

#### Scenario: Intent parsing failure
- **WHEN** LLM fails to parse user intent
- **THEN** the agent SHALL return an error response
- **AND** SHALL suggest the user rephrase their request
- **AND** SHALL NOT modify the report

#### Scenario: Variable execution failure
- **WHEN** a variable re-execution fails (e.g., SQL timeout)
- **THEN** the agent SHALL mark the operation as failed
- **AND** SHALL include error details
- **AND** SHALL NOT render the final report
- **AND** SHALL preserve the previous report version

#### Scenario: LLM service unavailable
- **WHEN** OpenAI API is unavailable
- **THEN** the agent SHALL retry up to 3 times
- **AND** if all retries fail, SHALL return appropriate error
- **AND** SHALL log the failure for monitoring

### Requirement: Cost Tracking
The system SHALL track and report costs for AI-based operations.

#### Scenario: Cost calculation
- **GIVEN** modifications that use LLM (intent parsing, AI refinement)
- **WHEN** modification completes
- **THEN** the metadata SHALL include total_cost_usd
- **AND** individual AI operations SHALL include cost details
- **AND** costs SHALL be based on token usage

#### Scenario: Cost attribution
- **WHEN** AI refinement is performed
- **THEN** the AIRefinementDetails SHALL include tokens_used
- **AND** SHALL include cost_usd
- **AND** SHALL include model name

### Requirement: State Management
The system SHALL maintain consistent report state across modifications.

#### Scenario: State versioning
- **GIVEN** a report at version 1
- **WHEN** a modification is applied
- **THEN** a new state snapshot SHALL be created at version 2
- **AND** the report version SHALL be incremented
- **AND** previous state SHALL be retained for rollback

#### Scenario: Variable tracking
- **WHEN** a parameter is updated
- **THEN** the ReportState SHALL reflect the new value
- **AND** the variable's last_modified timestamp SHALL be updated
- **AND** the variable SHALL be marked as dirty (is_dirty=true)
- **AND** dependent variables SHALL also be marked dirty

### Requirement: Integration with Existing Services
The system SHALL reuse existing ExecutionScheduler, TemplateRenderer, and VariableExecutors.

#### Scenario: Variable re-execution
- **WHEN** a parameter is updated
- **THEN** dependent variables SHALL be re-executed using ExecutionScheduler
- **AND** the execution SHALL follow the existing DAG topology
- **AND** SHALL use the appropriate VariableExecutor for each variable type

#### Scenario: Template rendering
- **WHEN** generating modified report content
- **THEN** TemplateRenderer SHALL be used
- **AND** SHALL render with updated variable values
- **AND** SHALL support temporary template modifications

#### Scenario: WebSocket integration
- **WHEN** modifications are in progress
- **THEN** progress updates SHALL use existing WebSocketManager
- **AND** SHALL maintain compatibility with existing progress format

### Requirement: Code Quality and Documentation
The system SHALL maintain high code quality with comprehensive Chinese documentation and comments.

#### Scenario: Chinese comments for classes and functions
- **WHEN** implementing any class or function
- **THEN** SHALL include Chinese docstring explaining purpose
- **AND** docstring SHALL describe parameters and return values
- **AND** SHALL follow existing project docstring conventions
- **AND** SHALL use """中文说明""" format for multi-line docstrings

#### Scenario: Complex logic documentation
- **WHEN** implementing complex business logic (e.g., dependency resolution, intent parsing)
- **THEN** SHALL include inline Chinese comments explaining the logic
- **AND** comments SHALL clarify non-obvious decisions
- **AND** comments SHALL explain algorithm choices
- **AND** SHALL avoid stating the obvious (what code already shows)

#### Scenario: Type hints and validation
- **WHEN** defining functions and methods
- **THEN** SHALL include Python type hints for all parameters
- **AND** SHALL include return type hints
- **AND** SHALL use Pydantic models for data validation
- **AND** SHALL follow existing typing conventions in the codebase

#### Scenario: Module-level documentation
- **WHEN** creating new Python modules
- **THEN** SHALL include module-level docstring in Chinese
- **AND** docstring SHALL explain module purpose and main components
- **AND** SHALL list key classes and functions if module is complex
- **AND** SHALL follow format: """模块说明"""

#### Scenario: API endpoint documentation
- **WHEN** adding new API endpoints
- **THEN** SHALL include Chinese docstring with endpoint description
- **AND** SHALL document request/response schemas
- **AND** SHALL include example usage
- **AND** SHALL document error cases
- **AND** SHALL follow existing API documentation patterns

#### Scenario: Code examples in comments
- **WHEN** complex usage patterns exist
- **THEN** MAY include code examples in comments
- **AND** examples SHALL be in Chinese with English code
- **AND** examples SHALL be concise and relevant
- **AND** examples SHALL be tested and working
