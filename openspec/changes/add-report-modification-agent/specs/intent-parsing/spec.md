# Intent Parsing Specification

## ADDED Requirements

### Requirement: Natural Language Intent Parsing
The system SHALL parse user modification requests written in natural language into structured ModificationIntent objects using LLM.

#### Scenario: Simple parameter update
- **WHEN** user requests "把微网格ID改成ZQGY0175"
- **THEN** intent parser SHALL return ModificationIntent with type="update_parameter"
- **AND** SHALL identify target_variable="wgid"
- **AND** SHALL extract new_value="ZQGY0175"

#### Scenario: AI content refinement
- **WHEN** user requests "这段分析太简单了,请写详细点"
- **THEN** intent parser SHALL return ModificationIntent with type="refine_ai_content"
- **AND** SHALL identify the target variable from context (last AI-generated variable)
- **AND** SHALL extract refinement_instruction="增加详细度"

#### Scenario: Add new section
- **WHEN** user requests "帮我加上竞对对比分析"
- **THEN** intent parser SHALL return ModificationIntent with type="add_section"
- **AND** SHALL extract section_title="竞对对比分析"
- **AND** SHALL infer section_description
- **AND** MAY infer position_description

#### Scenario: Modify existing section
- **WHEN** user requests "把问题分析部分改一下,加上根因分析"
- **THEN** intent parser SHALL return ModificationIntent with type="modify_section"
- **AND** SHALL identify section_title from report structure
- **AND** SHALL extract modification requirements

### Requirement: Multi-Intent Recognition
The system SHALL recognize and parse multiple intents from a single user request.

#### Scenario: Multiple independent modifications
- **WHEN** user requests "把时间改成一周,分析写详细点"
- **THEN** intent parser SHALL return array with 2 intents
- **AND** first intent SHALL be update_parameter for time
- **AND** second intent SHALL be refine_ai_content for analysis

#### Scenario: Dependent modifications
- **WHEN** user requests "把ID改成ZQGY0175,然后重新生成报告"
- **THEN** intent parser SHALL recognize parameter update
- **AND** SHALL NOT create separate intent for "重新生成" (implicit)

### Requirement: Context-Aware Parsing
The system SHALL use conversation history and report state to resolve ambiguities.

#### Scenario: Pronoun resolution
- **GIVEN** previous turn discussed "分析" variable
- **WHEN** user says "把它写详细点"
- **THEN** intent parser SHALL resolve "它" to "分析" variable
- **AND** SHALL create appropriate refinement intent

#### Scenario: Relative value interpretation
- **GIVEN** current time_period is "3天"
- **WHEN** user says "再延长一周"
- **THEN** intent parser SHALL calculate new value as "10天"
- **OR** SHALL express as relative modification

#### Scenario: Incremental changes
- **GIVEN** previous modification added "竞对分析" section
- **WHEN** user says "再加上市场占有率对比"
- **THEN** intent parser SHALL understand this as modification to existing section
- **OR** additional content in same section

### Requirement: Report Structure Awareness
The system SHALL understand report structure (sections, variables) when parsing intents.

#### Scenario: Section reference by title
- **GIVEN** report contains section "## 问题分析"
- **WHEN** user says "修改问题分析部分"
- **THEN** intent parser SHALL match section by title
- **AND** SHALL include section metadata in intent

#### Scenario: Variable reference by name or description
- **GIVEN** report has variable "problem_analysis" with description "问题分析总结"
- **WHEN** user says "把问题分析改得更深入"
- **THEN** intent parser SHALL identify target as "problem_analysis" variable

#### Scenario: Position-relative references
- **WHEN** user says "在问题分析后面加上解决方案"
- **THEN** intent parser SHALL identify position relative to existing section
- **AND** SHALL include position_description in intent

### Requirement: Structured Output
The system SHALL produce structured, validated intent objects that can be reliably processed.

#### Scenario: Pydantic validation
- **WHEN** intent parsing completes
- **THEN** result SHALL be validated against ModificationIntent Pydantic model
- **AND** SHALL include all required fields
- **AND** SHALL have type-correct values

#### Scenario: Intent completeness
- **WHEN** intent type is "update_parameter"
- **THEN** intent SHALL include target_variable
- **AND** SHALL include new_value
- **WHEN** intent type is "refine_ai_content"
- **THEN** intent SHALL include ai_variable
- **AND** SHALL include refinement_instruction

#### Scenario: Malformed LLM output handling
- **WHEN** LLM returns invalid JSON
- **THEN** parser SHALL retry with clarified prompt
- **AND** if retry fails, SHALL raise parsing error
- **AND** SHALL log the malformed output

### Requirement: Prompt Engineering
The system SHALL use well-designed prompts that guide LLM to accurate intent recognition.

#### Scenario: System prompt structure
- **WHEN** calling LLM for intent parsing
- **THEN** system prompt SHALL describe role as "报告修改意图分析专家"
- **AND** SHALL list supported intent types
- **AND** SHALL provide examples for each type
- **AND** SHALL specify output format (JSON)

#### Scenario: Context inclusion
- **WHEN** building user prompt
- **THEN** SHALL include current report parameters
- **AND** SHALL include report section structure
- **AND** SHALL include available variables (template + runtime)
- **AND** SHALL include recent conversation history (last 3 turns)
- **AND** SHALL include context summary (if >10 turns)

#### Scenario: Few-shot examples
- **WHEN** system prompt is constructed
- **THEN** SHALL include 2-3 examples per intent type
- **AND** examples SHALL be in Chinese (matching user language)
- **AND** examples SHALL cover common patterns

### Requirement: Error Handling
The system SHALL gracefully handle parsing failures and ambiguous requests.

#### Scenario: Ambiguous request clarification
- **WHEN** user request is too vague (e.g., "改一下")
- **THEN** intent parser MAY return clarification_needed response
- **AND** SHALL suggest what information is needed
- **OR** SHALL make best-effort interpretation with low confidence

#### Scenario: Unsupported modification type
- **WHEN** user requests something outside supported intent types
- **THEN** SHALL return error indicating unsupported_operation
- **AND** SHALL suggest alternative formulations

#### Scenario: LLM timeout
- **WHEN** LLM call exceeds timeout (30s)
- **THEN** SHALL retry once with same prompt
- **AND** if second attempt fails, SHALL return timeout error
- **AND** SHALL log for monitoring

### Requirement: Performance
The system SHALL parse intents efficiently to maintain responsive user experience.

#### Scenario: Parsing latency
- **WHEN** intent parsing is invoked
- **THEN** SHALL complete within 3 seconds for 90% of requests
- **AND** SHALL use GPT-4 or equivalent model
- **AND** SHALL optimize prompt length to reduce tokens

#### Scenario: Cost efficiency
- **WHEN** parsing a typical modification request
- **THEN** token usage SHALL be less than 2000 tokens
- **AND** cost SHALL be less than $0.02 per parse
- **AND** SHALL use efficient prompt construction

### Requirement: Intent Confidence
The system SHALL indicate confidence levels for parsed intents when uncertainty exists.

#### Scenario: High confidence intent
- **WHEN** request clearly matches an intent pattern
- **THEN** intent MAY include confidence=high
- **AND** SHALL proceed without confirmation

#### Scenario: Low confidence intent
- **WHEN** request is ambiguous or unusual
- **THEN** intent MAY include confidence=low
- **AND** agent MAY request user confirmation (future enhancement)

### Requirement: Multilingual Support
The system SHALL support intent parsing for Chinese natural language (primary) with potential for English.

#### Scenario: Chinese language parsing
- **WHEN** user sends request in Chinese
- **THEN** SHALL parse correctly with high accuracy (>80%)
- **AND** SHALL handle mixed Chinese-English input (e.g., "把wgid改成ZQGY0175")

#### Scenario: English language parsing (future)
- **WHEN** user sends request in English
- **THEN** SHALL parse with comparable accuracy
- **AND** SHALL use same intent structure

