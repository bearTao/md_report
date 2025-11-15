# Operation Execution Specification

## ADDED Requirements

### Requirement: Operation Planning
The system SHALL translate parsed intents into executable operation plans with proper sequencing and dependencies.

#### Scenario: Simple operation planning
- **GIVEN** a single update_parameter intent
- **WHEN** operation planner creates plan
- **THEN** SHALL create OperationStep for parameter_update
- **AND** SHALL analyze dependencies
- **AND** if dependencies exist, SHALL create child OperationStep for variable_execution

#### Scenario: Complex multi-intent planning
- **GIVEN** intents: [update_parameter, refine_ai_content]
- **WHEN** planning operations
- **THEN** SHALL create sequential operation steps
- **AND** SHALL ensure parameter update completes before AI refinement
- **AND** SHALL assign unique IDs (op_1, op_2, etc.)

#### Scenario: Dependency chain planning
- **GIVEN** parameter update affects 3 dependent variables
- **WHEN** planning operations
- **THEN** SHALL create parent operation for parameter update
- **AND** SHALL create child operation for variable re-execution
- **AND** child metadata SHALL list all 3 variables to re-execute

### Requirement: Parameter Update Execution
The system SHALL execute parameter updates and automatically re-execute dependent variables.

#### Scenario: Update user input parameter
- **GIVEN** variable "wgid" with current value "ZQGY0174"
- **WHEN** executing parameter update to "ZQGY0175"
- **THEN** SHALL update value in ReportState.variables["wgid"]
- **AND** SHALL mark variable as dirty
- **AND** SHALL update last_modified timestamp
- **AND** SHALL return ParameterUpdateDetails with old and new values

#### Scenario: Re-execute dependent variables
- **GIVEN** "overview" variable depends on "wgid"
- **WHEN** "wgid" is updated
- **THEN** SHALL identify "overview" as dependent
- **AND** SHALL call ExecutionScheduler to re-execute "overview"
- **AND** SHALL use updated "wgid" value in execution
- **AND** SHALL update ReportState with new "overview" value

#### Scenario: Multiple parameter updates
- **GIVEN** intents to update both "wgid" and "time_period"
- **WHEN** executing operations
- **THEN** SHALL batch parameter updates
- **AND** SHALL compute union of all dependent variables
- **AND** SHALL re-execute each dependent variable once

### Requirement: AI Content Refinement Execution
The system SHALL refine AI-generated content by modifying prompts and re-generating.

#### Scenario: Refine with instruction
- **GIVEN** variable "analysis_summary" was AI-generated
- **AND** refinement instruction "增加详细度"
- **WHEN** executing refinement
- **THEN** SHALL retrieve original generation context
- **AND** SHALL modify prompt to include refinement instruction
- **AND** SHALL call AI executor with modified prompt
- **AND** SHALL update variable value with new content

#### Scenario: Track refinement details
- **WHEN** refinement completes
- **THEN** AIRefinementDetails SHALL include before_length
- **AND** SHALL include after_length
- **AND** SHALL include model used
- **AND** SHALL include tokens_used
- **AND** SHALL include cost_usd

#### Scenario: Handle refinement failure
- **WHEN** AI generation fails during refinement
- **THEN** SHALL preserve original value
- **AND** SHALL return operation with status="failed"
- **AND** SHALL include error message
- **AND** SHALL NOT update report state

### Requirement: Template Modification Execution
The system SHALL modify report templates by adding or changing sections using temporary templates.

#### Scenario: Add new section with data
- **GIVEN** intent to add "竞对对比分析" section
- **WHEN** executing template modification
- **THEN** SHALL analyze data requirements using LLM
- **AND** SHALL generate SQL/API queries for required data
- **AND** SHALL execute queries and store as runtime variables
- **AND** SHALL generate Jinja2 template for new section using LLM
- **AND** SHALL find appropriate insertion point in template
- **AND** SHALL insert Jinja2 content into temporary template

#### Scenario: Section insertion point detection
- **GIVEN** request to add section "after 问题分析"
- **WHEN** finding insertion point
- **THEN** SHALL parse current template to identify sections
- **AND** SHALL locate "问题分析" section
- **AND** SHALL determine line number for insertion
- **AND** SHALL handle nested sections correctly

#### Scenario: Jinja2 generation
- **WHEN** generating Jinja2 for new section
- **THEN** SHALL include proper heading level (## or ###)
- **AND** SHALL use Jinja2 syntax ({% if %}, {% for %})
- **AND** SHALL reference created variables with {{ var_name }}
- **AND** SHALL include null/empty value handling
- **AND** SHALL validate generated Jinja2 syntax

#### Scenario: Runtime variable creation
- **WHEN** new section requires new data
- **THEN** SHALL create VariableInfo with type="runtime"
- **AND** SHALL populate generation_context
- **AND** SHALL set created_in_turn to current turn
- **AND** SHALL execute variable to get actual value
- **AND** SHALL add to ReportState.variables

### Requirement: Operation Execution Strategy Pattern
The system SHALL use strategy pattern to execute different operation types with unified interface.

#### Scenario: Strategy selection
- **WHEN** OperationExecutor.execute() is called with OperationStep
- **THEN** SHALL select appropriate strategy based on step.type
- **AND** for "parameter_update" SHALL use ParameterUpdateStrategy
- **AND** for "ai_refinement" SHALL use AIRefinementStrategy
- **AND** for "template_modification" SHALL use TemplateModificationStrategy

#### Scenario: Strategy execution result
- **WHEN** any strategy executes
- **THEN** SHALL return StrategyResult
- **AND** result SHALL include operation-specific details
- **AND** SHALL update memory.report_state as side effect
- **AND** SHALL record execution time

### Requirement: Integration with Existing Services
The system SHALL integrate seamlessly with ExecutionScheduler, TemplateRenderer, and VariableExecutors.

#### Scenario: Use ExecutionScheduler for variable execution
- **WHEN** re-executing dependent variables
- **THEN** SHALL create ExecutionScheduler instance
- **AND** SHALL build DAG with only affected variables
- **AND** SHALL execute using scheduler's batch execution
- **AND** SHALL handle same error conditions as normal generation

#### Scenario: Use TemplateRenderer for final rendering
- **WHEN** generating final report content
- **THEN** SHALL use TemplateRenderer.render()
- **AND** SHALL pass temporary template if modified
- **AND** SHALL pass all variables (template + runtime)
- **AND** SHALL handle rendering errors consistently

#### Scenario: Use VariableExecutors for new variables
- **WHEN** executing newly created runtime variables
- **THEN** SHALL use appropriate VariableExecutor (SqlExecutor, ApiExecutor, etc.)
- **AND** SHALL follow same execution patterns as template variables
- **AND** SHALL support all 8 variable source types

### Requirement: Operation Result Structure
The system SHALL return structured operation results with complete details for each operation type.

#### Scenario: Parameter update result
- **WHEN** parameter update operation completes
- **THEN** result SHALL include Operation with type="parameter_update"
- **AND** details SHALL be ParameterUpdateDetails
- **AND** SHALL list all ParameterChange objects (name, old_value, new_value)
- **AND** if child operations exist, SHALL include in children array

#### Scenario: Variable execution result
- **WHEN** variable re-execution completes
- **THEN** result SHALL include Operation with type="variable_execution"
- **AND** details SHALL be VariableExecutionDetails
- **AND** SHALL list all ExecutedVariable objects
- **AND** each SHALL include status (success/failed/cached/skipped)
- **AND** each SHALL include execution_time_ms

#### Scenario: Nested operation hierarchy
- **GIVEN** parameter update with 2 dependent variables
- **WHEN** operations complete
- **THEN** parent operation SHALL have id="op_1"
- **AND** child operation SHALL have id="op_1_1", parent_id="op_1"
- **AND** result SHALL reflect hierarchy in operations array

### Requirement: Error Recovery
The system SHALL handle operation failures gracefully and provide recovery options.

#### Scenario: Partial operation failure
- **GIVEN** multi-step operation plan
- **WHEN** step 2 fails but step 1 succeeded
- **THEN** SHALL mark step 2 as status="failed"
- **AND** SHALL NOT rollback step 1 changes
- **AND** SHALL continue with subsequent steps if independent
- **AND** SHALL return partial success result

#### Scenario: Critical operation failure
- **WHEN** parameter update fails due to validation error
- **THEN** SHALL mark operation as failed
- **AND** SHALL NOT proceed to dependent variable execution
- **AND** SHALL return complete error details
- **AND** SHALL preserve original report state

#### Scenario: Automatic retry for transient failures
- **WHEN** variable execution fails with timeout or network error
- **THEN** SHALL retry up to 2 times
- **AND** SHALL use exponential backoff
- **AND** if all retries fail, SHALL mark as failed
- **AND** SHALL log retry attempts

### Requirement: Performance Optimization
The system SHALL execute operations efficiently to maintain responsiveness.

#### Scenario: Parallel variable execution
- **WHEN** multiple variables are marked for re-execution
- **AND** they have no dependencies between them
- **THEN** SHALL execute them in parallel using ExecutionScheduler
- **AND** SHALL limit concurrent executions to avoid overload

#### Scenario: Cached results reuse
- **WHEN** a variable was recently executed (within session)
- **AND** its dependencies haven't changed
- **THEN** MAY reuse cached result
- **AND** SHALL mark as status="cached" in ExecutedVariable

#### Scenario: Incremental rendering
- **WHEN** only specific sections were modified
- **THEN** MAY optimize rendering by caching unchanged sections (future enhancement)
- **OR** SHALL always do full re-render (initial implementation)

### Requirement: Operation Metadata
The system SHALL track comprehensive metadata for each operation for observability.

#### Scenario: Execution timing
- **WHEN** any operation executes
- **THEN** SHALL record start time
- **AND** SHALL record end time
- **AND** SHALL calculate execution_time_ms
- **AND** SHALL include in operation result

#### Scenario: Cost tracking for AI operations
- **WHEN** AI-based operation executes (intent parsing, refinement, Jinja2 generation)
- **THEN** SHALL track token usage
- **AND** SHALL calculate cost based on model pricing
- **AND** SHALL include in operation details
- **AND** SHALL aggregate in modification metadata

#### Scenario: Change summary generation
- **WHEN** SQL or API variables are re-executed
- **THEN** MAY generate change_summary comparing old vs new results
- **AND** SHALL use rule-based diff for structured data
- **AND** MAY use LLM for complex content (if change_summary is important)
- **AND** SHALL include in ExecutedVariable

