# Report Modification Agent - Technical Design

## Context

The report generation system currently supports creating reports from templates with 8 variable types (user_input, sql, api, ai_generation, system, constant, image, vision_ai). The system uses:
- ExecutionScheduler for DAG-based variable execution
- TemplateRenderer for Jinja2 rendering
- VariableExecutors (strategy pattern) for different data sources
- WebSocket for real-time progress updates

Users want to modify generated reports without regenerating from scratch. This requires:
- Understanding natural language modification requests
- Tracking report state across conversations
- Executing modifications while preserving consistency
- Providing friendly explanations of changes

## Goals / Non-Goals

### Goals
- Enable natural language report modification (e.g., "change the time period to one week")
- Support multi-turn conversations with context awareness
- Allow parameter updates with automatic dependency resolution
- Enable AI content refinement with prompt modification
- Support template structure changes (add/modify sections)
- Reuse existing services (Scheduler, Renderer, Executors)
- Maintain cost efficiency (minimize LLM calls)
- Provide clear explanations of modifications

### Non-Goals
- Real-time collaborative editing (single user per session)
- Version control with branching/merging
- Automatic conflict resolution between users
- Fine-grained permission control (assumed single user context)
- Support for arbitrary code execution in templates

## Decisions

### Decision 1: Agent Architecture Pattern
**Choice**: Single orchestrating agent with specialized sub-components (IntentParser, OperationPlanner, OperationExecutor, MemoryManager)

**Rationale**:
- Clear separation of concerns (parsing, planning, execution)
- Easier to test and maintain each component
- Allows independent optimization of each stage
- Follows existing patterns in the codebase (ExecutionScheduler, VariableExecutors)

**Alternatives considered**:
- Multi-agent system with autonomous agents → Too complex for current needs
- Simple prompt engineering without structure → Insufficient control and reliability

### Decision 2: Memory Management Strategy
**Choice**: Unified ReportState with both template and runtime variables

**Rationale**:
- Template variables: Defined in YAML, can be re-executed
- Runtime variables: Created during conversation, have generation context
- Single source of truth for all variables simplifies lookups
- Supports dependency tracking across both types

**Alternatives considered**:
- Separate storage for template vs runtime variables → More complex queries
- No distinction between types → Loses important metadata

### Decision 3: Temporary Template Approach
**Choice**: Create temporary template content for modifications, optionally save as new template

**Rationale**:
- Preserves original template integrity
- Allows experimentation without permanent changes
- Supports "save as template" workflow for successful modifications
- Enables rollback by discarding temporary template

**Alternatives considered**:
- Direct template modification → Risky, hard to rollback
- Copy-on-write templates → Storage overhead, version management complexity

### Decision 4: Intent Parsing with LLM
**Choice**: Use LLM (GPT-4) for intent parsing with structured output (Pydantic)

**Rationale**:
- Handles natural language flexibility and ambiguity
- Structured output ensures reliable parsing
- Supports multi-intent requests (e.g., "change time and add competitor analysis")
- LangChain JsonOutputParser provides validation

**Alternatives considered**:
- Rule-based NLU → Insufficient for natural language variety
- Fine-tuned model → Overhead not justified for current scale

### Decision 5: Operation Execution Strategy Pattern
**Choice**: Strategy pattern with different executors (ParameterUpdate, AIRefinement, TemplateModification)

**Rationale**:
- Mirrors existing VariableExecutor pattern (familiar to codebase)
- Easy to add new modification types
- Encapsulates type-specific logic
- Testable in isolation

### Decision 6: Cost Control Strategy
**Choice**: 
- Use LLM only for intent parsing and AI content generation
- Use rule-based logic for dependency resolution and change detection
- Provide optional `change_summary` via rules, fallback to AI

**Rationale**:
- Most operations don't need AI intelligence
- Dependency graphs can be computed algorithmically
- Change detection for SQL/API results uses diff algorithms
- Cost scales with user interactions, not data processing

### Decision 7: Database Schema Design
**Choice**: Four new tables: conversation_sessions, conversation_turns, report_states, report_modification_history

**Rationale**:
- conversation_sessions: Session lifecycle management
- conversation_turns: Complete conversation history for context
- report_states: Versioned snapshots of report state
- report_modification_history: Audit trail for all modifications
- Normalized design for query efficiency

**Alternatives considered**:
- Single table with nested JSON → Hard to query, poor performance
- In-memory only → Loses data on restart, no audit trail

## Architecture

### System Layers

```
┌─────────────────────────────────────────┐
│         User Interface Layer            │
│  - REST API: /api/reports/{id}/modify   │
│  - WebSocket: Real-time progress        │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│      Agent Orchestration Layer          │
│  ┌─────────────────────────────────┐   │
│  │  ReportModificationAgent        │   │
│  │  - IntentParser (LLM)           │   │
│  │  - OperationPlanner (rules)     │   │
│  │  - OperationExecutor (strategies)│  │
│  │  - ExplanationGenerator (LLM)   │   │
│  │  - MemoryManager (DB)           │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│         Service Layer (REUSE)           │
│  - ExecutionScheduler                   │
│  - TemplateRenderer                     │
│  - VariableExecutors (8 types)          │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│         Data Layer (EXTEND)             │
│  - Database (PostgreSQL)                │
│  - External APIs                        │
│  - AI Services (OpenAI via LangChain)   │
└─────────────────────────────────────────┘
```

### Component Interactions

```
User Request → ReportModificationAgent.modify_report()
  ↓
1. MemoryManager.get_or_create_memory()
  → Load/Create ConversationMemory from DB
  
2. IntentParser.parse(user_request, memory)
  → LLM call with context
  → Returns List[ModificationIntent]
  
3. OperationPlanner.create_plan(intents, memory)
  → Rule-based planning
  → Returns List[OperationStep]
  
4. For each OperationStep:
   OperationExecutor.execute(step, memory)
     → Strategy selection
     → Updates memory.report_state
     → Returns Operation result
  
5. TemplateRenderer.render(temp_template, variables)
  → Generates final Markdown
  
6. ExplanationGenerator.generate(request, operations)
  → LLM call for friendly response
  
7. Save results to DB + Update memory
  
8. Return ModificationResult
```

### Data Flow

**Report State Evolution**:
```
Initial Report Generation:
  Template + Variables → Report v1
  → ReportState created with template variables

First Modification:
  User: "Change time to 1 week"
  → Intent parsed
  → Parameter updated in ReportState
  → Dependencies re-executed
  → Report v2 generated
  → ReportState updated (version 2)

Second Modification:
  User: "Add competitor analysis"
  → Intent parsed
  → New runtime variable created
  → Temporary template modified
  → Report v3 generated
  → ReportState updated (version 3)
```

## Risks / Trade-offs

### Risk 1: LLM Intent Parsing Accuracy
**Mitigation**:
- Use GPT-4 for higher accuracy
- Structured output with validation
- Show parsed intent to user for confirmation (future enhancement)
- Fallback to asking clarifying questions

### Risk 2: Temporary Template Management
**Mitigation**:
- Clear documentation for users
- Visual indicator that template is modified
- "Save as template" flow well-documented
- Automatic cleanup of old temporary templates

### Risk 3: Cost Escalation from LLM Calls
**Mitigation**:
- Minimize LLM usage (only parsing and generation)
- Cache common intent patterns (future)
- Use cheaper models for simple requests (future)
- Cost tracking and limits per session

### Risk 4: Conversation Context Window
**Mitigation**:
- Summarize old conversations after 10 turns
- Store summaries in conversation_sessions.context_summary
- Pass only recent turns + summary to LLM

### Risk 5: Concurrent Modifications
**Mitigation**:
- One active conversation per report at a time (enforced by session_id)
- Show warning if another session is active
- Use optimistic locking for report_states

## Migration Plan

### Phase 1: Schema Migration
1. Create new database tables (conversation_sessions, etc.)
2. Add indices for performance
3. Add version column to reports table
4. Test with existing data (should not affect current operations)

### Phase 2: Service Implementation
1. Implement core data structures (ReportState, ConversationMemory)
2. Implement MemoryManager with DB persistence
3. Add IntentParser with test prompts
4. Add OperationPlanner with rule-based logic
5. Implement OperationExecutor strategies

### Phase 3: API Integration
1. Add `/api/reports/{id}/modify` endpoint
2. Add `/api/reports/{id}/conversation` endpoint
3. Add `/api/reports/{id}/save-as-template` endpoint
4. Update WebSocket for modification progress

### Phase 4: Frontend Integration (out of scope for this backend change)
1. Add modification UI component
2. Add conversation history display
3. Add template save dialog

### Rollback Plan
- New tables are independent, can be dropped without affecting existing functionality
- New API endpoints can be disabled via feature flag
- No changes to existing generation flow

## Open Questions

1. **Should we support undo/redo?**
   - Decision: Not in initial release, trackable via conversation history
   
2. **How long should conversation sessions persist?**
   - Decision: 24 hours of inactivity, then mark as inactive (not deleted)
   
3. **Should we support exporting conversation history?**
   - Decision: Future enhancement, not critical for MVP
   
4. **How to handle conflicts if template is updated during conversation?**
   - Decision: Lock template version at conversation start, show warning if template changed

5. **Cost limits per session?**
   - Decision: Optional configuration, default unlimited for MVP

## Performance Considerations

- Intent parsing: ~1-2s (LLM call)
- Operation planning: <100ms (rule-based)
- Operation execution: Depends on operation type
  - Parameter update: Fast (in-memory)
  - Variable re-execution: 1-30s (depends on data source)
  - AI refinement: 2-10s (LLM call)
  - Template modification: 1-3s (LLM for Jinja2 generation)
- Final rendering: <1s (Jinja2)
- Total per modification: 5-45s (typical), up to 60s (complex)

WebSocket progress updates keep user informed throughout.

## Testing Strategy

### Unit Tests
- IntentParser with various user requests
- OperationPlanner with different intent combinations
- Each OperationExecutor strategy independently
- MemoryManager CRUD operations

### Integration Tests
- Complete modification flow (parameter update)
- Multi-turn conversation scenarios
- Dependency resolution across modifications
- Error handling and recovery

### End-to-End Tests
- Real LLM integration tests (separate test suite)
- Full user scenarios from proposal document
- Performance benchmarks

## Success Criteria

1. Users can modify reports via natural language (>80% intent recognition accuracy)
2. Multi-turn conversations maintain context correctly
3. Parameter updates trigger correct dependency re-execution
4. AI content refinement produces improved output
5. Template modifications work without breaking existing sections
6. Average modification time <30 seconds
7. Cost per modification <$0.10 (GPT-4)
8. No breaking changes to existing functionality

