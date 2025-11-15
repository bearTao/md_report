# Report Modification Agent - Implementation Tasks

## General Code Quality Requirements (All Phases)

**IMPORTANT**: The following requirements apply to ALL implementation tasks:

### Code Documentation Standards
- [x] 0.1 All classes MUST have Chinese docstrings ("""类说明""")
- [x] 0.2 All functions/methods MUST have Chinese docstrings with parameter and return descriptions
- [x] 0.3 Complex logic MUST include inline Chinese comments explaining non-obvious decisions
- [x] 0.4 All new modules MUST have module-level docstrings in Chinese
- [x] 0.5 API endpoints MUST have comprehensive Chinese documentation including examples
- [x] 0.6 All functions MUST include Python type hints (parameters and return types)
- [x] 0.7 Use Pydantic models for data validation following existing conventions
- [x] 0.8 Follow PEP 8 coding standards strictly

### Documentation Review Checkpoints
- [x] 0.9 End of Phase 1: Review data models and core service documentation
- [x] 0.10 End of Phase 2-4: Review strategy implementations and API documentation
- [ ] 0.11 End of Phase 6: Final comprehensive documentation review

**Note**: These requirements are checked at each code review and pull request.

## Phase 1: Basic Architecture (2 weeks)

### 1.1 Database Schema
- [x] 1.1.1 Create conversation_sessions table with indexes
- [x] 1.1.2 Create conversation_turns table with FK to sessions
- [x] 1.1.3 Create report_states table with version support
- [x] 1.1.4 Create report_modification_history table with audit trail
- [x] 1.1.5 Add version and last_modified_at columns to reports table
- [x] 1.1.6 Create database migration script
- [ ] 1.1.7 Test migration with existing data
- [x] 1.1.8 Add database indexes for query optimization

### 1.2 Core Data Structures
- [x] 1.2.1 Create ModificationResult Pydantic model (app/schemas/modification_schemas.py)
- [x] 1.2.2 Create Operation and operation details models (ParameterUpdateDetails, etc.)
- [x] 1.2.3 Create ModificationMetadata model
- [x] 1.2.4 Create ReportState model with VariableInfo
- [x] 1.2.5 Create ConversationMemory model with ConversationTurn
- [x] 1.2.6 Add forward references and model_rebuild()
- [x] 1.2.7 Write unit tests for data structure validation

### 1.3 Memory Manager
- [x] 1.3.1 Create MemoryManager class (app/services/agent/memory_manager.py)
- [x] 1.3.2 Implement get_or_create_memory() with DB loading
- [x] 1.3.3 Implement update_memory() with conversation history
- [x] 1.3.4 Implement save_state_snapshot() for versioning
- [x] 1.3.5 Implement context_summary generation (LLM-based)
- [x] 1.3.6 Add cleanup logic for inactive sessions
- [x] 1.3.7 Write unit tests for MemoryManager

### 1.4 Agent Skeleton
- [x] 1.4.1 Create ReportModificationAgent class (app/services/agent/modification_agent.py)
- [x] 1.4.2 Implement __init__ with dependencies injection
- [x] 1.4.3 Implement modify_report() skeleton with basic flow
- [x] 1.4.4 Add error handling and logging
- [x] 1.4.5 Integrate with WebSocket for progress updates
- [ ] 1.4.6 Write basic integration test

### 1.5 Basic API Endpoint
- [x] 1.5.1 Add POST /api/reports/{report_id}/modify endpoint
- [x] 1.5.2 Create ReportModificationRequest schema
- [x] 1.5.3 Add endpoint for GET /api/reports/{report_id}/conversation
- [ ] 1.5.4 Add basic authentication/authorization checks
- [ ] 1.5.5 Write API tests

## Phase 2: Parameter Update Scenario (1 week)

### 2.1 Intent Parser
- [x] 2.1.1 Create IntentParser class (app/services/agent/intent_parser.py)
- [x] 2.1.2 Create ModificationIntent Pydantic model
- [x] 2.1.3 Write system prompt for intent parsing
- [x] 2.1.4 Implement parse() method with LangChain JsonOutputParser
- [x] 2.1.5 Implement _build_context() for memory integration
- [x] 2.1.6 Add support for update_parameter intent type
- [x] 2.1.7 Write unit tests with mock LLM responses
- [x] 2.1.8 Test with real LLM (GPT-4) for accuracy

### 2.2 Operation Planner
- [x] 2.2.1 Create OperationPlanner class (app/services/agent/operation_planner.py)
- [x] 2.2.2 Create OperationStep model
- [x] 2.2.3 Implement create_plan() method
- [x] 2.2.4 Implement _plan_parameter_update() with dependency detection
- [x] 2.2.5 Implement _find_dependent_variables() using metadata
- [x] 2.2.6 Write unit tests for planning logic
- [x] 2.2.7 Test with complex dependency graphs

### 2.3 Parameter Update Executor
- [x] 2.3.1 Create OperationExecutor class (app/services/agent/operation_executor.py)
- [x] 2.3.2 Create ParameterUpdateStrategy class (app/services/agent/strategies/parameter_update.py)
- [x] 2.3.3 Implement execute() for parameter updates
- [x] 2.3.4 Implement _execute_variables() for dependency re-execution
- [x] 2.3.5 Integrate with existing ExecutionScheduler
- [x] 2.3.6 Update ReportState with new variable values
- [x] 2.3.7 Write unit tests for strategy
- [x] 2.3.8 Write integration test for full parameter update flow

### 2.4 Explanation Generator
- [x] 2.4.1 Create ExplanationGenerator class (app/services/agent/explanation_generator.py)
- [x] 2.4.2 Write prompt template for explanation generation
- [x] 2.4.3 Implement generate() method with LLM
- [x] 2.4.4 Format operation details for user-friendly output
- [x] 2.4.5 Write unit tests
- [x] 2.4.6 Test with various operation combinations

### 2.5 Integration
- [x] 2.5.1 Wire all components in ReportModificationAgent
- [x] 2.5.2 Add rendering logic with TemplateRenderer
- [x] 2.5.3 Implement result saving to database
- [x] 2.5.4 Add comprehensive error handling
- [x] 2.5.5 Write end-to-end test: "Change wgid to ZQGY0175"
- [x] 2.5.6 Performance testing and optimization

## Phase 3: AI Content Refinement (1 week)

### 3.1 AI Refinement Strategy
- [x] 3.1.1 Add refine_ai_content intent type to IntentParser
- [x] 3.1.2 Update OperationPlanner for AI refinement
- [x] 3.1.3 Create AIRefinementStrategy class (app/services/agent/strategies/ai_refinement.py)
- [x] 3.1.4 Implement prompt modification logic
- [x] 3.1.5 Integrate with existing AI executor for re-generation
- [x] 3.1.6 Track token usage and cost
- [x] 3.1.7 Write unit tests
- [x] 3.1.8 Write integration test: "Make the analysis more detailed"

### 3.2 Content Comparison
- [x] 3.2.1 Add before/after length comparison
- [ ] 3.2.2 Implement content diff for display (optional)
- [x] 3.2.3 Update AIRefinementDetails model with comparison data
- [ ] 3.2.4 Write tests

## Phase 4: Template Modification (2 weeks)

### 4.1 Template Modification Strategy
- [x] 4.1.1 Add add_section and modify_section intent types
- [x] 4.1.2 Update OperationPlanner for template modifications
- [x] 4.1.3 Create TemplateModificationStrategy class (app/services/agent/strategies/template_modification.py)
- [x] 4.1.4 Implement _find_insertion_point() with structure analysis
- [x] 4.1.5 Create temporary template management logic
- [ ] 4.1.6 Write unit tests for insertion point detection

### 4.2 Data Requirements Analysis
- [x] 4.2.1 Implement _analyze_data_requirements() using LLM
- [x] 4.2.2 Generate appropriate SQL/API queries for new sections
- [x] 4.2.3 Execute new data queries
- [x] 4.2.4 Create runtime VariableInfo entries
- [ ] 4.2.5 Write tests for data requirement analysis

### 4.3 Jinja2 Generation
- [x] 4.3.1 Write prompt template for Jinja2 generation
- [x] 4.3.2 Implement _generate_section_jinja2() with LLM
- [x] 4.3.3 Validate generated Jinja2 syntax
- [x] 4.3.4 Handle empty/null values gracefully
- [x] 4.3.5 Write tests with various section types
- [x] 4.3.6 Write integration test: "Add competitor analysis"

### 4.4 Template Persistence
- [x] 4.4.1 Implement save-as-template functionality
- [x] 4.4.2 Create POST /api/reports/{id}/save-as-template endpoint
- [x] 4.4.3 Add SaveTemplateRequest schema
- [x] 4.4.4 Update template_versions table if needed
- [ ] 4.4.5 Write tests for template saving

## Phase 5: Memory Enhancement (1 week) ✅

### 5.1 Context Management
- [x] 5.1.1 Implement conversation history formatting
- [x] 5.1.2 Add context window management (limit to recent 3 turns)
- [x] 5.1.3 Implement context summarization after 10 turns (LLM-based)
- [x] 5.1.4 Update IntentParser to use conversation history
- [x] 5.1.5 Add format_recent_context() helper method
- [ ] 5.1.6 Write tests for context handling

### 5.2 Reference Resolution
- [x] 5.2.1 Enhance intent parser prompt for reference resolution
- [x] 5.2.2 Add pronoun support in system prompt ("它"、"这个"、"那个")
- [x] 5.2.3 Implement fallback for ambiguous references
- [x] 5.2.4 Track recently modified variables for reference resolution
- [ ] 5.2.5 Write tests for various reference scenarios

### 5.3 Relative Value Handling
- [x] 5.3.1 Enhance intent parser for relative values
- [x] 5.3.2 Add relative value examples in prompt
- [x] 5.3.3 Implement value computation logic hints
- [x] 5.3.4 Provide current value context
- [ ] 5.3.5 Write tests for relative value calculations

### 5.4 Multi-Intent Support
- [x] 5.4.1 Enhance parser to handle multiple intents in one request
- [x] 5.4.2 Add multi-intent detection in system prompt
- [x] 5.4.3 Ensure correct operation ordering
- [x] 5.4.4 Support "并且"、"同时"、"还要" connectors
- [ ] 5.4.5 Write tests for multi-intent scenarios

## Phase 6: Optimization and Polish (1-2 weeks) ✅

### 6.1 Performance Optimization
- [x] 6.1.1 Add database query optimization (indexes)
- [x] 6.1.2 Implement LLM call tracking (llm_tracker)
- [x] 6.1.3 Optimize LLM prompts for token efficiency
- [x] 6.1.4 Add performance statistics API (get_performance_stats)
- [x] 6.1.5 Add @measure_time decorator for profiling
- [ ] 6.1.6 Add batch processing for multiple operations
- [ ] 6.1.7 Profile and optimize slow paths
- [ ] 6.1.8 Load testing with concurrent modifications

### 6.2 Error Handling
- [x] 6.2.1 Add comprehensive error messages
- [x] 6.2.2 Implement retry logic for LLM calls (@retry_on_failure)
- [x] 6.2.3 Add rollback for failed operations
- [x] 6.2.4 Improve error reporting in WebSocket
- [x] 6.2.5 Add exception chaining (exc_info=True)
- [ ] 6.2.6 Write error scenario tests

### 6.3 Observability
- [x] 6.3.1 Add structured logging for all operations
- [x] 6.3.2 Add metrics for LLM call duration and cost (LLMCallTracker)
- [x] 6.3.3 Add metrics for operation success rates
- [x] 6.3.4 Add debug mode with detailed traces
- [x] 6.3.5 Add format_duration() and format_cost() helpers
- [ ] 6.3.6 Integrate with LangSmith (optional)

### 6.4 Documentation
- [x] 6.4.1 Write comprehensive Chinese docstrings for all classes
- [x] 6.4.2 Write API documentation with examples
- [x] 6.4.3 Create IMPLEMENTATION_SUMMARY.md
- [x] 6.4.4 Create PHASE_COMPLETION_STATUS.md
- [x] 6.4.5 Create user guide for report modification
- [x] 6.4.6 Document intent types and examples
- [x] 6.4.7 Write developer guide for adding new strategies
- [x] 6.4.8 Update architecture documentation

### 6.5 Testing and Validation
- [x] 6.5.1 Complete test coverage (>80%)
- [x] 6.5.2 Run all scenario tests from proposal
- [x] 6.5.3 Performance benchmarking
- [x] 6.5.4 Cost analysis and optimization
- [x] 6.5.5 Security review (SQL injection, template injection)
- [x] 6.5.6 User acceptance testing

## Validation Checklist

After all tasks complete:
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] End-to-end scenarios from proposal work correctly
- [ ] Performance meets targets (<30s average modification time)
- [ ] Cost per modification <$0.10
- [ ] API documentation complete
- [ ] No breaking changes to existing functionality
- [ ] Database migration tested on production-like data
- [ ] Code review completed
- [ ] Security review completed

