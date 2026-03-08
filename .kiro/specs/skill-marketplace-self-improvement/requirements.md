# Requirements Document

## Introduction

Bu spec, mevcut multi-agent sistemine iki büyük yetenek katmayı hedefler: (1) Skill Marketplace — skill'lerin keşfedildiği, paylaşıldığı, derecelendirildiği ve şablon olarak sunulduğu bir altyapı; (2) Self-Improvement Loop — agent performans metriklerinin otomatik olarak skill seçimine, prompt stratejisi optimizasyonuna ve agent routing kararlarına geri besleme olarak döndüğü kapalı bir iyileştirme döngüsü. Mevcut `tools/dynamic_skills.py` (PostgreSQL-backed skill CRUD), `tools/agent_eval.py` (SQLite-based scoring), `tools/confidence.py` (heuristic confidence), `core/event_bus.py` (async pub-sub), ve `pipelines/engine.py` (pipeline execution) üzerine inşa edilir.

## Glossary

- **Marketplace_API**: Skill keşfi, listeleme, arama, rating ve paylaşım işlemlerini sunan FastAPI endpoint katmanı
- **Skill_Registry**: `tools/dynamic_skills.py` üzerindeki PostgreSQL-backed skill deposu; skill CRUD, arama ve Kiro SKILL.md disk formatını yönetir
- **Skill_Template**: Yeni skill oluşturmak için kullanılan önceden tanımlanmış yapı şablonu (frontmatter, knowledge, references, scripts)
- **Rating_System**: Skill'lere kullanıcı ve agent tarafından puan ve yorum atanmasını sağlayan PostgreSQL-backed değerlendirme sistemi
- **Performance_Collector**: Agent çalıştırmalarından metrik toplayan ve `evaluations.db` ile event bus üzerinden veri yayan bileşen
- **Optimization_Engine**: Toplanan performans verilerini analiz ederek skill seçimi, prompt stratejisi ve agent routing kararlarını optimize eden bileşen
- **A/B_Test_Manager**: Prompt stratejilerinin istatistiksel olarak karşılaştırılmasını yöneten bileşen; varyant atama, metrik toplama ve significance hesaplama yapar
- **Dynamic_Router**: Tarihsel performans verisine dayanarak görevleri en uygun agent'a yönlendiren bileşen; mevcut `get_best_agent_for_task` fonksiyonunu genişletir
- **Feedback_Loop**: Event bus üzerinden performans olaylarını dinleyerek Optimization_Engine'e ileten kapalı döngü mekanizması
- **Skill_Score**: Bir skill'in kullanım sayısı, ortalama rating ve başarı oranından hesaplanan bileşik kalite puanı (0.0–5.0)
- **Prompt_Strategy**: Bir agent'ın belirli görev tipi için kullandığı system prompt, few-shot örnekler ve chain-of-thought talimatlarının bütünü
- **Statistical_Significance**: İki prompt stratejisi arasındaki performans farkının rastlantısal olmadığını doğrulayan istatistiksel test sonucu (p < 0.05)
- **Agent_Performance_Score**: Bir agent'ın belirli görev tipindeki başarı oranı, latency, token verimliliği ve kullanıcı memnuniyetinden hesaplanan bileşik puan (0.0–10.0)
- **Routing_Weight**: Dynamic_Router'ın her agent'a atadığı, tarihsel performansa dayalı görev yönlendirme ağırlığı (0.0–1.0)
- **Exploration_Rate**: Dynamic_Router'ın düşük performanslı agent'lara yeni görev atama oranı; keşif-sömürü dengesini sağlar (0.0–1.0)

## Requirements

### Requirement 1: Skill Discovery API

**User Story:** As a developer, I want to discover and search skills through a structured API, so that I can find relevant capabilities for my tasks.

#### Acceptance Criteria

1. THE Marketplace_API SHALL expose a `GET /api/skills` endpoint that returns a paginated list of active skills from the Skill_Registry with fields: id, name, category, description, source, use_count, avg_score, created_at
2. THE Marketplace_API SHALL expose a `GET /api/skills/search?q={query}` endpoint that returns skills matching the query ranked by relevance_score descending
3. WHEN a search query is provided, THE Marketplace_API SHALL match against skill name, description, keywords, and category fields
4. THE Marketplace_API SHALL expose a `GET /api/skills/{skill_id}` endpoint that returns full skill details including knowledge content, references, and usage statistics
5. WHEN a skill_id does not exist or is inactive, THE Marketplace_API SHALL return HTTP 404 with a descriptive error message
6. THE Marketplace_API SHALL support filtering by category and source via query parameters on the list endpoint

### Requirement 2: Skill Rating and Review System

**User Story:** As a user, I want to rate and review skills, so that the community can identify high-quality skills and the system can prioritize them.

#### Acceptance Criteria

1. THE Marketplace_API SHALL expose a `POST /api/skills/{skill_id}/ratings` endpoint that accepts a score (1–5 integer), optional review text, and reviewer identifier
2. WHEN a rating is submitted, THE Rating_System SHALL persist the rating in PostgreSQL and update the skill's avg_score in the Skill_Registry
3. THE Marketplace_API SHALL expose a `GET /api/skills/{skill_id}/ratings` endpoint that returns paginated ratings with score, review text, reviewer, and created_at
4. WHEN an agent completes a task using a skill, THE Performance_Collector SHALL automatically submit an agent-generated rating based on the task's evaluation score from agent_eval
5. THE Rating_System SHALL calculate the Skill_Score as a weighted combination: (0.4 × avg_rating) + (0.3 × normalized_use_count) + (0.3 × success_rate)
6. IF a rating submission contains a score outside the 1–5 range, THEN THE Marketplace_API SHALL return HTTP 422 with a validation error message

### Requirement 3: Skill Template Library

**User Story:** As a developer, I want to create skills from predefined templates, so that I can quickly build well-structured skills without starting from scratch.

#### Acceptance Criteria

1. THE Marketplace_API SHALL expose a `GET /api/skill-templates` endpoint that returns available Skill_Template definitions with id, name, description, and category
2. THE Marketplace_API SHALL expose a `POST /api/skills/from-template` endpoint that accepts a template_id and customization parameters (name, description, keywords, knowledge overrides) and creates a new skill in the Skill_Registry
3. THE Skill_Registry SHALL persist template-created skills with source field set to "template:{template_id}"
4. WHEN a skill is created from a template, THE Skill_Registry SHALL write the Kiro SKILL.md format to disk at `data/skills/{skill_id}/` including frontmatter, knowledge, and empty references/scripts/assets directories
5. THE Marketplace_API SHALL provide templates for categories: research, coding, analysis, reasoning, writing, security, architecture, performance, and domain-specific

### Requirement 4: Community Skill Sharing

**User Story:** As a developer, I want to export and import skills, so that skills can be shared across instances and with the community.

#### Acceptance Criteria

1. THE Marketplace_API SHALL expose a `POST /api/skills/{skill_id}/export` endpoint that returns the skill as a JSON package containing all metadata, knowledge, and reference file contents
2. THE Marketplace_API SHALL expose a `POST /api/skills/import` endpoint that accepts a skill JSON package and creates the skill in the Skill_Registry with source set to "community-import"
3. WHEN importing a skill with an id that already exists, THE Skill_Registry SHALL create a new skill with a suffixed id rather than overwriting the existing skill
4. THE Marketplace_API SHALL expose a `POST /api/skills/{skill_id}/fork` endpoint that creates a copy of an existing skill with a new id and source set to "fork:{original_skill_id}"
5. IF an imported skill package is missing required fields (id, name, description, knowledge), THEN THE Marketplace_API SHALL return HTTP 422 listing the missing fields

### Requirement 5: Performance Metrics Collection

**User Story:** As a system operator, I want agent performance metrics collected automatically after each task execution, so that the self-improvement loop has data to optimize against.

#### Acceptance Criteria

1. WHEN an agent completes a subtask in the PipelineEngine, THE Performance_Collector SHALL record: agent_role, task_type, score (from agent_eval), latency_ms, tokens_used, skill_ids_used, prompt_strategy_id, and timestamp
2. THE Performance_Collector SHALL publish a `METRIC_RECORDED` event to the event bus on channel "metrics" containing the recorded metric payload
3. THE Performance_Collector SHALL store metrics in PostgreSQL in a `performance_metrics` table with indexes on agent_role, task_type, and created_at
4. THE Marketplace_API SHALL expose a `GET /api/metrics/agents/{agent_role}` endpoint that returns aggregated performance statistics: avg_score, success_rate, avg_latency_ms, total_tasks, and per-task-type breakdown
5. THE Marketplace_API SHALL expose a `GET /api/metrics/skills/{skill_id}` endpoint that returns skill usage statistics: total_uses, avg_score_when_used, and per-agent breakdown
6. WHILE the system is running, THE Performance_Collector SHALL maintain a rolling 24-hour in-memory cache of recent metrics for low-latency queries

### Requirement 6: Automated A/B Testing of Prompt Strategies

**User Story:** As a system operator, I want to compare prompt strategies with statistical rigor, so that I can confidently deploy the better-performing strategy.

#### Acceptance Criteria

1. THE A/B_Test_Manager SHALL support creating experiments with: experiment_id, agent_role, task_type, control_strategy (Prompt_Strategy), variant_strategy (Prompt_Strategy), and traffic_split_ratio (0.0–1.0)
2. WHEN a task is routed to an agent with an active experiment, THE A/B_Test_Manager SHALL assign the task to control or variant group based on the traffic_split_ratio using deterministic hashing on the task id
3. THE A/B_Test_Manager SHALL track per-variant metrics: sample_count, avg_score, avg_latency_ms, success_rate, and token_efficiency
4. WHEN both variants have accumulated a minimum of 30 samples each, THE A/B_Test_Manager SHALL calculate Statistical_Significance using a two-sample t-test with p-value threshold of 0.05
5. WHEN an experiment reaches Statistical_Significance with the variant outperforming control, THE A/B_Test_Manager SHALL publish an `EXPERIMENT_CONCLUDED` event on the event bus with the winning strategy details
6. THE Marketplace_API SHALL expose a `GET /api/experiments` endpoint listing active and completed experiments with their current metrics and significance status
7. THE Marketplace_API SHALL expose a `POST /api/experiments` endpoint to create new A/B test experiments
8. IF an experiment is created for an agent_role and task_type that already has an active experiment, THEN THE A/B_Test_Manager SHALL return an error indicating a conflicting active experiment

### Requirement 7: Performance-Driven Skill Selection

**User Story:** As a system operator, I want skill selection to be informed by historical performance data, so that agents receive the most effective skills for each task type.

#### Acceptance Criteria

1. WHEN the PipelineEngine prepares a subtask for execution, THE Optimization_Engine SHALL rank available skills by Skill_Score for the given task_type and agent_role combination
2. THE Optimization_Engine SHALL select the top-N skills (configurable, default 3) with the highest Skill_Score for injection into the agent's context
3. WHEN a skill has fewer than 5 usage records for a given task_type, THE Optimization_Engine SHALL apply an exploration bonus of 0.5 to the Skill_Score to encourage discovery of underused skills
4. THE Optimization_Engine SHALL persist skill-task-agent performance associations in a `skill_performance` PostgreSQL table with columns: skill_id, agent_role, task_type, avg_score, use_count, last_used_at
5. WHEN a task completes, THE Feedback_Loop SHALL update the skill_performance records for all skills that were injected during that task execution

### Requirement 8: Dynamic Agent Routing

**User Story:** As a system operator, I want agent routing to adapt based on historical performance, so that tasks are assigned to the agent most likely to succeed.

#### Acceptance Criteria

1. THE Dynamic_Router SHALL calculate Agent_Performance_Score for each agent-task_type pair using: (0.4 × success_rate) + (0.25 × normalized_avg_score) + (0.2 × latency_efficiency) + (0.15 × token_efficiency)
2. THE Dynamic_Router SHALL convert Agent_Performance_Scores into Routing_Weights using softmax normalization across all eligible agents for a given task_type
3. WHEN routing a task, THE Dynamic_Router SHALL select the agent with the highest Routing_Weight, subject to the Exploration_Rate
4. THE Dynamic_Router SHALL maintain an Exploration_Rate (configurable, default 0.1) that routes a fraction of tasks to non-optimal agents to prevent performance stagnation
5. WHEN an agent's Routing_Weight for a task_type drops below 0.05, THE Dynamic_Router SHALL publish a `ROUTING_WEIGHT_LOW` event on the event bus for observability
6. THE Dynamic_Router SHALL recalculate Routing_Weights every 50 completed tasks or every 1 hour, whichever comes first
7. THE Marketplace_API SHALL expose a `GET /api/routing/weights` endpoint that returns current Routing_Weights per agent per task_type

### Requirement 9: Self-Improvement Feedback Loop

**User Story:** As a system operator, I want a closed feedback loop that automatically applies performance insights, so that the system continuously improves without manual intervention.

#### Acceptance Criteria

1. THE Feedback_Loop SHALL subscribe to the "metrics" channel on the event bus and process `METRIC_RECORDED` events
2. WHEN the Feedback_Loop detects that an agent's success_rate for a task_type drops below 60% over the last 20 tasks, THE Optimization_Engine SHALL trigger a skill re-ranking for that agent-task_type combination
3. WHEN an `EXPERIMENT_CONCLUDED` event is received with a winning variant, THE Feedback_Loop SHALL update the agent's active Prompt_Strategy via the agent_param_overrides system
4. THE Feedback_Loop SHALL publish an `OPTIMIZATION_APPLIED` event on the event bus whenever a routing weight, skill ranking, or prompt strategy is updated, including before and after values
5. THE Feedback_Loop SHALL maintain an optimization log in PostgreSQL table `optimization_history` with columns: id, optimization_type, agent_role, task_type, before_value, after_value, reason, created_at
6. WHILE the system is running, THE Feedback_Loop SHALL process feedback events within 5 seconds of receipt

### Requirement 10: Prompt Strategy Management

**User Story:** As a developer, I want to define, version, and manage prompt strategies, so that A/B testing and optimization have well-defined strategies to compare.

#### Acceptance Criteria

1. THE Marketplace_API SHALL expose a `POST /api/prompt-strategies` endpoint that accepts: agent_role, task_type, name, system_prompt, few_shot_examples (list), chain_of_thought_instructions, and metadata
2. THE Marketplace_API SHALL expose a `GET /api/prompt-strategies` endpoint that returns prompt strategies filterable by agent_role and task_type
3. THE Optimization_Engine SHALL store Prompt_Strategies in a PostgreSQL `prompt_strategies` table with version tracking (auto-incrementing version per agent_role+task_type)
4. WHEN a new Prompt_Strategy is created for an existing agent_role+task_type combination, THE Optimization_Engine SHALL increment the version number and retain previous versions for rollback
5. THE Marketplace_API SHALL expose a `POST /api/prompt-strategies/{strategy_id}/activate` endpoint that sets the strategy as the active strategy for its agent_role and task_type
6. IF a prompt strategy activation would conflict with an active A/B experiment, THEN THE Marketplace_API SHALL return HTTP 409 indicating the active experiment must be concluded first

### Requirement 11: Performance Dashboard Data API

**User Story:** As a system operator, I want to access comprehensive performance data through APIs, so that the frontend dashboard can visualize system health and optimization progress.

#### Acceptance Criteria

1. THE Marketplace_API SHALL expose a `GET /api/dashboard/overview` endpoint returning: total_skills, total_experiments, active_experiments, optimization_count_24h, and per-agent summary scores
2. THE Marketplace_API SHALL expose a `GET /api/dashboard/agents/{agent_role}/history` endpoint returning time-series performance data with configurable granularity (hourly, daily) and date range
3. THE Marketplace_API SHALL expose a `GET /api/dashboard/optimization-log` endpoint returning paginated entries from the optimization_history table
4. THE Marketplace_API SHALL expose a `GET /api/dashboard/skill-leaderboard` endpoint returning skills ranked by Skill_Score with usage and rating statistics
5. WHEN time-series data is requested, THE Marketplace_API SHALL aggregate metrics into the requested granularity buckets and return: avg_score, success_rate, avg_latency_ms, and task_count per bucket
