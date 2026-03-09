"""
Skill Finder — dynamic skill/knowledge discovery for agents.
Agents can search for relevant skills, get skill details,
and inject skill knowledge into their context.
"""

from __future__ import annotations

from typing import Any


# ── Skill Registry ───────────────────────────────────────────────
# Each skill has: id, name, category, description, keywords, knowledge
# "knowledge" is the actual instruction/context injected into the agent

SKILL_REGISTRY: list[dict[str, Any]] = [
    {
        "id": "deep-research",
        "name": "Deep Research",
        "category": "research",
        "description": "Multi-source deep research with cross-referencing and fact verification",
        "keywords": ["research", "investigate", "deep dive", "analysis", "report", "araştırma", "inceleme"],
        "knowledge": (
            "DEEP RESEARCH PROTOCOL:\n"
            "1. Break the topic into 3-5 sub-questions\n"
            "2. Search each sub-question independently\n"
            "3. Cross-reference findings across sources\n"
            "4. Identify contradictions and verify with additional searches\n"
            "5. Synthesize into structured report with citations\n"
            "6. Rate confidence per claim (high/medium/low)\n"
            "Always prefer primary sources over secondary. Date-stamp all findings."
        ),
    },
    {
        "id": "code-generation",
        "name": "Code Generation",
        "category": "coding",
        "description": "Production-quality code generation with best practices",
        "keywords": ["code", "program", "function", "class", "implement", "kod", "yazılım", "geliştir"],
        "knowledge": (
            "CODE GENERATION PROTOCOL:\n"
            "1. Understand requirements fully before writing\n"
            "2. Choose appropriate design patterns\n"
            "3. Write type-safe code with proper error handling\n"
            "4. Include docstrings and inline comments for complex logic\n"
            "5. Follow SOLID principles\n"
            "6. Consider edge cases and input validation\n"
            "7. Suggest tests for critical paths"
        ),
    },
    {
        "id": "data-analysis",
        "name": "Data Analysis",
        "category": "analysis",
        "description": "Statistical analysis, data interpretation, and visualization recommendations",
        "keywords": ["data", "statistics", "analyze", "chart", "graph", "trend", "veri", "analiz", "istatistik"],
        "knowledge": (
            "DATA ANALYSIS PROTOCOL:\n"
            "1. Identify data type (time-series, categorical, numerical)\n"
            "2. Check for missing values, outliers, distributions\n"
            "3. Apply appropriate statistical methods\n"
            "4. Visualize with the right chart type\n"
            "5. State assumptions and limitations\n"
            "6. Provide actionable insights, not just numbers"
        ),
    },
    {
        "id": "math-reasoning",
        "name": "Mathematical Reasoning",
        "category": "reasoning",
        "description": "Step-by-step mathematical problem solving and proof construction",
        "keywords": ["math", "calculate", "equation", "proof", "formula", "matematik", "hesapla", "denklem"],
        "knowledge": (
            "MATH REASONING PROTOCOL:\n"
            "1. Identify the problem type (algebra, calculus, probability, etc.)\n"
            "2. State given information and what needs to be found\n"
            "3. Show every step — no skipping\n"
            "4. Verify answer by substitution or alternative method\n"
            "5. Express answer with appropriate precision\n"
            "6. Explain the intuition behind the solution"
        ),
    },
    {
        "id": "creative-writing",
        "name": "Creative Writing",
        "category": "writing",
        "description": "High-quality content creation, copywriting, and text composition",
        "keywords": ["write", "essay", "article", "blog", "content", "copy", "yaz", "makale", "içerik"],
        "knowledge": (
            "CREATIVE WRITING PROTOCOL:\n"
            "1. Understand audience and purpose\n"
            "2. Create compelling hook/opening\n"
            "3. Structure with clear flow (intro → body → conclusion)\n"
            "4. Use active voice, concrete examples\n"
            "5. Vary sentence length for rhythm\n"
            "6. Edit for clarity and conciseness\n"
            "7. Match tone to context (formal/casual/technical)"
        ),
    },
    {
        "id": "debugging",
        "name": "Debugging & Troubleshooting",
        "category": "coding",
        "description": "Systematic bug finding, root cause analysis, and fix verification",
        "keywords": ["bug", "error", "fix", "debug", "crash", "issue", "hata", "düzelt", "sorun"],
        "knowledge": (
            "DEBUGGING PROTOCOL:\n"
            "1. Reproduce the issue — get exact error message\n"
            "2. Isolate: narrow down to smallest failing case\n"
            "3. Form hypothesis about root cause\n"
            "4. Verify hypothesis with targeted investigation\n"
            "5. Implement minimal fix\n"
            "6. Verify fix doesn't break other things\n"
            "7. Document what caused it and how to prevent recurrence"
        ),
    },
    {
        "id": "comparison",
        "name": "Comparison & Evaluation",
        "category": "analysis",
        "description": "Structured comparison of options, technologies, or approaches",
        "keywords": ["compare", "vs", "versus", "which", "better", "karşılaştır", "hangisi", "fark"],
        "knowledge": (
            "COMPARISON PROTOCOL:\n"
            "1. Define evaluation criteria upfront\n"
            "2. Research each option independently\n"
            "3. Create structured comparison matrix\n"
            "4. Weight criteria by importance to the use case\n"
            "5. Provide clear recommendation with reasoning\n"
            "6. Note trade-offs and context-dependent factors"
        ),
    },
    {
        "id": "summarization",
        "name": "Summarization",
        "category": "writing",
        "description": "Concise summarization of long content while preserving key information",
        "keywords": ["summarize", "summary", "tldr", "brief", "overview", "özet", "özetle", "kısalt"],
        "knowledge": (
            "SUMMARIZATION PROTOCOL:\n"
            "1. Read/analyze the full content first\n"
            "2. Identify key themes and main arguments\n"
            "3. Extract critical facts, numbers, and conclusions\n"
            "4. Structure: main point → supporting details → implications\n"
            "5. Keep summary to ~20% of original length\n"
            "6. Preserve nuance — don't oversimplify"
        ),
    },
    {
        "id": "translation",
        "name": "Translation & Localization",
        "category": "language",
        "description": "Accurate translation with cultural context and localization",
        "keywords": ["translate", "translation", "language", "çevir", "çeviri", "dil", "tercüme"],
        "knowledge": (
            "TRANSLATION PROTOCOL:\n"
            "1. Understand source text meaning and intent\n"
            "2. Translate meaning, not word-by-word\n"
            "3. Adapt idioms and cultural references\n"
            "4. Maintain tone and register of original\n"
            "5. Handle technical terms consistently\n"
            "6. Flag ambiguous passages"
        ),
    },
    {
        "id": "security-review",
        "name": "Security Review",
        "category": "security",
        "description": "Security analysis, vulnerability assessment, and hardening recommendations",
        "keywords": ["security", "vulnerability", "attack", "protect", "güvenlik", "zafiyet", "koruma"],
        "knowledge": (
            "SECURITY REVIEW PROTOCOL:\n"
            "1. Identify attack surface and threat model\n"
            "2. Check OWASP Top 10 vulnerabilities\n"
            "3. Review authentication and authorization\n"
            "4. Check input validation and output encoding\n"
            "5. Assess data protection (encryption, storage)\n"
            "6. Review dependency vulnerabilities\n"
            "7. Provide prioritized remediation plan"
        ),
    },
    {
        "id": "architecture-design",
        "name": "Architecture Design",
        "category": "architecture",
        "description": "System architecture design, patterns, and scalability planning",
        "keywords": ["architecture", "design", "system", "scale", "pattern", "mimari", "tasarım", "sistem"],
        "knowledge": (
            "ARCHITECTURE DESIGN PROTOCOL:\n"
            "1. Clarify requirements (functional + non-functional)\n"
            "2. Identify key quality attributes (performance, scalability, security)\n"
            "3. Select appropriate architectural patterns\n"
            "4. Define component boundaries and interfaces\n"
            "5. Plan for failure modes and recovery\n"
            "6. Document decisions with rationale (ADRs)\n"
            "7. Consider operational concerns (monitoring, deployment)"
        ),
    },
    {
        "id": "performance-optimization",
        "name": "Performance Optimization",
        "category": "performance",
        "description": "Performance profiling, bottleneck identification, and optimization",
        "keywords": ["performance", "optimize", "slow", "fast", "speed", "performans", "hız", "yavaş"],
        "knowledge": (
            "PERFORMANCE OPTIMIZATION PROTOCOL:\n"
            "1. Measure first — don't guess the bottleneck\n"
            "2. Profile with appropriate tools\n"
            "3. Identify the critical path\n"
            "4. Optimize the biggest bottleneck first\n"
            "5. Measure again after each change\n"
            "6. Consider caching, batching, parallelism\n"
            "7. Document before/after metrics"
        ),
    },
    # ── Domain-Specific Skills ───────────────────────────────────
    {
        "id": "financial-analysis",
        "name": "Financial Analysis",
        "category": "finance",
        "description": "Stock analysis, portfolio evaluation, financial modeling, market research",
        "keywords": ["finance", "stock", "portfolio", "investment", "market", "finans", "hisse", "yatırım", "borsa", "piyasa"],
        "knowledge": (
            "FINANCIAL ANALYSIS PROTOCOL:\n"
            "1. Identify the financial instrument/market being analyzed\n"
            "2. Gather fundamental data (P/E, EPS, revenue growth, debt ratios)\n"
            "3. Perform technical analysis if applicable (trends, support/resistance)\n"
            "4. Compare with sector peers and benchmarks\n"
            "5. Assess risk factors (market, credit, liquidity, operational)\n"
            "6. Provide clear buy/hold/sell reasoning with confidence level\n"
            "7. DISCLAIMER: This is analysis, not financial advice\n"
            "8. Always cite data sources and dates"
        ),
    },
    {
        "id": "sql-database",
        "name": "SQL & Database Query",
        "category": "database",
        "description": "SQL query writing, database schema design, query optimization",
        "keywords": ["sql", "database", "query", "table", "schema", "veritabanı", "sorgu", "tablo", "postgres", "mysql"],
        "knowledge": (
            "SQL DATABASE PROTOCOL:\n"
            "1. Understand the data model and relationships\n"
            "2. Write clear, readable SQL with proper formatting\n"
            "3. Use appropriate JOINs (INNER/LEFT/RIGHT based on need)\n"
            "4. Add WHERE clauses for filtering, avoid SELECT *\n"
            "5. Consider indexing for frequently queried columns\n"
            "6. Use CTEs for complex queries (readability)\n"
            "7. Always consider NULL handling\n"
            "8. Test with EXPLAIN ANALYZE for performance"
        ),
    },
    {
        "id": "legal-analysis",
        "name": "Legal Document Analysis",
        "category": "legal",
        "description": "Contract review, legal document analysis, compliance checking",
        "keywords": ["legal", "contract", "law", "compliance", "hukuk", "sözleşme", "mevzuat", "uyum", "yasal"],
        "knowledge": (
            "LEGAL ANALYSIS PROTOCOL:\n"
            "1. Identify document type (contract, policy, regulation)\n"
            "2. Extract key terms, obligations, and deadlines\n"
            "3. Identify potential risks and ambiguities\n"
            "4. Check for missing standard clauses\n"
            "5. Flag unusual or one-sided terms\n"
            "6. Summarize rights and obligations per party\n"
            "7. DISCLAIMER: This is analysis, not legal advice — consult a lawyer\n"
            "8. Note jurisdiction-specific considerations"
        ),
    },
    {
        "id": "medical-info",
        "name": "Medical Information",
        "category": "medical",
        "description": "Medical literature review, symptom analysis, health information",
        "keywords": ["medical", "health", "symptom", "disease", "tıp", "sağlık", "semptom", "hastalık", "tedavi"],
        "knowledge": (
            "MEDICAL INFORMATION PROTOCOL:\n"
            "1. Gather symptoms/conditions described\n"
            "2. Search medical literature and trusted sources\n"
            "3. Present differential diagnoses if applicable\n"
            "4. Cite medical references (PubMed, WHO, etc.)\n"
            "5. CRITICAL DISCLAIMER: This is informational only, NOT medical advice\n"
            "6. Always recommend consulting a healthcare professional\n"
            "7. Note when information may be outdated\n"
            "8. Avoid definitive diagnoses — present possibilities"
        ),
    },
    {
        "id": "project-planning",
        "name": "Project Planning & Management",
        "category": "planning",
        "description": "Project scoping, sprint planning, task estimation, roadmap creation",
        "keywords": ["project", "plan", "sprint", "roadmap", "estimate", "proje", "planlama", "tahmin", "yol haritası"],
        "knowledge": (
            "PROJECT PLANNING PROTOCOL:\n"
            "1. Define project scope and objectives clearly\n"
            "2. Break into milestones with measurable deliverables\n"
            "3. Decompose milestones into sprint-sized tasks\n"
            "4. Estimate using T-shirt sizing or story points\n"
            "5. Identify dependencies and critical path\n"
            "6. Allocate buffer for unknowns (20-30%)\n"
            "7. Define acceptance criteria for each task\n"
            "8. Plan for testing, documentation, and deployment"
        ),
    },
    # ── Development & agent improvement (Cursor/Kiro patterns) ─────
    {
        "id": "code-review",
        "name": "Code Review",
        "category": "coding",
        "description": "Structured code and PR review: correctness, security, performance, maintainability",
        "keywords": ["review", "pr", "code review", "inceleme", "kod inceleme", "pull request", "quality"],
        "knowledge": (
            "CODE REVIEW PROTOCOL:\n"
            "1. Correctness: logic, edge cases, error handling\n"
            "2. Security: OWASP-relevant issues, auth, input validation\n"
            "3. Performance: N+1, algorithms, resource use\n"
            "4. Maintainability: naming, structure, tests, docs\n"
            "5. Provide concrete suggestions; use get_agent_baseline when improving agent-related code\n"
            "6. Output: critical / suggestion / nice-to-have with clear priority"
        ),
    },
    {
        "id": "agent-improvement",
        "name": "Agent Performance Improvement",
        "category": "orchestration",
        "description": "Improve existing agents via baseline metrics, failure analysis, prompt and rollout",
        "keywords": ["agent", "improve", "performance", "prompt", "baseline", "eval", "agent iyileştirme", "performans"],
        "knowledge": (
            "AGENT IMPROVEMENT PROTOCOL:\n"
            "1. Establish baseline: use get_agent_baseline for task_success_rate, satisfaction, latency, token_ratio\n"
            "2. Identify failure modes: instruction misunderstanding, format errors, context loss, tool misuse\n"
            "3. Apply improvements: chain-of-thought, few-shot examples, role refinement, constitutional checks\n"
            "4. Validate: test suite + A/B; roll out in stages (alpha → beta → canary)\n"
            "5. Success criteria: success +15%%, corrections -25%%, no safety regression, latency within 10%%\n"
            "6. Use get_best_agent when assigning tasks by type"
        ),
    },
    {
        "id": "changelog-release",
        "name": "Changelog & Release Notes",
        "category": "writing",
        "description": "Write changelogs, release notes, and version documentation",
        "keywords": ["changelog", "release", "release notes", "version", "değişiklik", "sürüm", "notlar"],
        "knowledge": (
            "CHANGELOG/RELEASE PROTOCOL:\n"
            "1. Use version format: MAJOR.MINOR.PATCH (breaking / feature / fix)\n"
            "2. Group changes: Added, Changed, Deprecated, Removed, Fixed, Security\n"
            "3. One line per change; link to issues/PRs when possible\n"
            "4. Release notes: audience-friendly summary, migration notes for breaking changes\n"
            "5. Keep entries concise and actionable"
        ),
    },
    # ── Security & auditing ────────────────────────────────────────
    {
        "id": "security-audit",
        "name": "Security Audit",
        "category": "security",
        "description": "OWASP Top 10 vulnerability scanning, secret detection, and severity reporting",
        "keywords": ["security", "owasp", "vulnerability", "audit", "secret", "güvenlik", "zafiyet"],
        "knowledge": (
            "SECURITY AUDIT PROTOCOL:\n"
            "1. Scan for OWASP Top 10 vulnerabilities (injection, XSS, CSRF, etc.)\n"
            "2. Detect hardcoded secrets, API keys, passwords in codebase\n"
            "3. Check dependency vulnerabilities (CVE database)\n"
            "4. Analyze authentication and authorization flows\n"
            "5. Review input validation and output encoding\n"
            "6. Report findings with severity (critical/high/medium/low)\n"
            "7. Provide remediation steps for each finding"
        ),
    },
    # ── Data engineering ───────────────────────────────────────────
    {
        "id": "data-pipeline",
        "name": "Data Pipeline",
        "category": "data",
        "description": "ETL pipeline design, schema validation, and multi-format data processing",
        "keywords": ["etl", "pipeline", "data", "transform", "schema", "veri", "dönüşüm"],
        "knowledge": (
            "DATA PIPELINE PROTOCOL:\n"
            "1. Define source schema and target schema\n"
            "2. Validate input data against schema (JSON Schema / Pydantic)\n"
            "3. Design extraction → transformation → loading steps\n"
            "4. Handle format conversion (CSV, JSON, Parquet, XML)\n"
            "5. Implement error handling and dead-letter queues\n"
            "6. Add data quality checks at each stage\n"
            "7. Monitor pipeline health with metrics and alerts"
        ),
    },
    # ── API architecture ───────────────────────────────────────────
    {
        "id": "api-design",
        "name": "API Design",
        "category": "architecture",
        "description": "OpenAPI 3.0 specification generation, endpoint analysis, and REST best practices",
        "keywords": ["api", "openapi", "rest", "endpoint", "swagger", "specification"],
        "knowledge": (
            "API DESIGN PROTOCOL:\n"
            "1. Define resources and their relationships\n"
            "2. Design RESTful endpoints (proper HTTP methods, status codes)\n"
            "3. Generate OpenAPI 3.0 specification\n"
            "4. Define request/response schemas with validation\n"
            "5. Plan authentication and rate limiting\n"
            "6. Version API endpoints appropriately\n"
            "7. Document with examples and error responses"
        ),
    },
    # ── Testing & automation ───────────────────────────────────────
    {
        "id": "test-automation",
        "name": "Test Automation",
        "category": "testing",
        "description": "Pytest test generation with async support, fixtures, and coverage analysis",
        "keywords": ["test", "pytest", "unittest", "coverage", "fixture", "async", "mock"],
        "knowledge": (
            "TEST AUTOMATION PROTOCOL:\n"
            "1. Identify testable units (functions, classes, endpoints)\n"
            "2. Generate pytest tests with proper fixtures\n"
            "3. Support async test functions (pytest-asyncio)\n"
            "4. Create mock objects for external dependencies\n"
            "5. Aim for edge case coverage (empty, null, boundary)\n"
            "6. Generate parametrized tests for multiple inputs\n"
            "7. Report coverage gaps and suggest additional tests"
        ),
    },
    # ── Performance & optimization ─────────────────────────────────
    {
        "id": "performance-profiling",
        "name": "Performance Profiling",
        "category": "optimization",
        "description": "Big-O complexity analysis, N+1 query detection, and database index recommendations",
        "keywords": ["performance", "profiling", "optimization", "n+1", "index", "big-o", "performans"],
        "knowledge": (
            "PERFORMANCE PROFILING PROTOCOL:\n"
            "1. Analyze algorithmic complexity (Big-O notation)\n"
            "2. Detect N+1 query patterns in ORM usage\n"
            "3. Identify missing database indexes\n"
            "4. Profile memory allocation and garbage collection\n"
            "5. Measure and optimize API response times\n"
            "6. Recommend caching strategies (Redis, in-memory)\n"
            "7. Suggest batch processing for bulk operations"
        ),
    },
]


def find_skills(query: str, max_results: int = 3) -> list[dict]:
    """
    Search skill registry by keyword matching.
    Returns top matching skills with their knowledge.
    """
    query_lower = query.lower()
    query_words = set(query_lower.split())

    scored: list[tuple[float, dict]] = []
    for skill in SKILL_REGISTRY:
        score = 0.0
        # Check keywords
        for kw in skill["keywords"]:
            kw_lower = kw.lower()
            if kw_lower in query_lower:
                score += 3.0
            elif any(w in kw_lower for w in query_words):
                score += 1.5

        # Check name and description
        if any(w in skill["name"].lower() for w in query_words):
            score += 2.0
        if any(w in skill["description"].lower() for w in query_words):
            score += 1.0

        if score > 0:
            scored.append((score, skill))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "id": s["id"],
            "name": s["name"],
            "category": s["category"],
            "description": s["description"],
            "relevance_score": round(sc, 1),
        }
        for sc, s in scored[:max_results]
    ]


def get_skill_knowledge(skill_id: str) -> str | None:
    """Get the full knowledge/instructions for a skill by ID."""
    for skill in SKILL_REGISTRY:
        if skill["id"] == skill_id:
            return skill["knowledge"]
    return None


def format_skill_results(skills: list[dict]) -> str:
    """Format skill search results for LLM context."""
    if not skills:
        return "<skills>\n  No matching skills found.\n</skills>"

    lines = []
    for s in skills:
        lines.append(
            f"  [{s['id']}] {s['name']} ({s['category']})\n"
            f"      {s['description']}\n"
            f"      Relevance: {s['relevance_score']}"
        )
    return "<available_skills>\n" + "\n".join(lines) + "\n</available_skills>"


def format_skill_knowledge(skill_id: str, knowledge: str) -> str:
    """Format skill knowledge for injection into agent context."""
    return (
        f"<skill id=\"{skill_id}\">\n"
        f"{knowledge}\n"
        f"</skill>"
    )
