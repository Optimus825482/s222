"""
Domain Skills — Deep domain expertise modules for Multi-Agent Ops Center.
Provides specialized calculation, analysis, and advisory tools for
finance, law, engineering, and academia domains.

All calculations are pure Python (no numpy/pandas). Legal analysis is
keyword/pattern-based. Engineering estimates use simple math formulas.
Academic tools return structured templates.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any

from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)


# ── Data Model ───────────────────────────────────────────────────

@dataclass
class DomainModule:
    """A domain expertise module with its tools and capabilities."""
    domain_id: str
    name: str
    name_tr: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════
#  FINANCE DOMAIN
# ══════════════════════════════════════════════════════════════════

def calculate_dcf(
    cash_flows: list[float],
    discount_rate: float,
    terminal_growth: float = 0.02,
) -> dict:
    """Discounted Cash Flow valuation with terminal value."""
    if not cash_flows:
        return {"error": "cash_flows cannot be empty"}
    if discount_rate <= terminal_growth:
        return {"error": "discount_rate must be greater than terminal_growth"}

    pv_cash_flows: list[float] = []
    for i, cf in enumerate(cash_flows):
        pv = cf / ((1 + discount_rate) ** (i + 1))
        pv_cash_flows.append(round(pv, 2))

    # Gordon Growth terminal value at end of projection
    last_cf = cash_flows[-1]
    terminal_value = (last_cf * (1 + terminal_growth)) / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / ((1 + discount_rate) ** len(cash_flows))

    total_pv = sum(pv_cash_flows) + pv_terminal

    return {
        "pv_cash_flows": pv_cash_flows,
        "sum_pv_cash_flows": round(sum(pv_cash_flows), 2),
        "terminal_value": round(terminal_value, 2),
        "pv_terminal_value": round(pv_terminal, 2),
        "enterprise_value": round(total_pv, 2),
        "discount_rate": discount_rate,
        "terminal_growth": terminal_growth,
        "projection_years": len(cash_flows),
    }


def calculate_npv(cash_flows: list[float], discount_rate: float) -> float:
    """Net Present Value — first element is initial investment (typically negative)."""
    if not cash_flows:
        return 0.0
    npv = sum(cf / ((1 + discount_rate) ** i) for i, cf in enumerate(cash_flows))
    return round(npv, 2)


def calculate_irr(cash_flows: list[float], max_iterations: int = 1000) -> float | None:
    """Internal Rate of Return via Newton-Raphson method."""
    if not cash_flows or len(cash_flows) < 2:
        return None

    # Initial guess
    rate = 0.1

    for _ in range(max_iterations):
        # f(r) = sum of cf_i / (1+r)^i
        npv = sum(cf / ((1 + rate) ** i) for i, cf in enumerate(cash_flows))
        # f'(r) = sum of -i * cf_i / (1+r)^(i+1)
        d_npv = sum(
            -i * cf / ((1 + rate) ** (i + 1))
            for i, cf in enumerate(cash_flows)
            if i > 0
        )

        if abs(d_npv) < 1e-12:
            return None

        new_rate = rate - npv / d_npv

        if abs(new_rate - rate) < 1e-9:
            return round(new_rate, 6)

        rate = new_rate

    return None  # Did not converge


def calculate_wacc(
    equity_value: float,
    debt_value: float,
    cost_of_equity: float,
    cost_of_debt: float,
    tax_rate: float,
) -> float:
    """Weighted Average Cost of Capital."""
    total = equity_value + debt_value
    if total == 0:
        return 0.0
    we = equity_value / total
    wd = debt_value / total
    wacc = (we * cost_of_equity) + (wd * cost_of_debt * (1 - tax_rate))
    return round(wacc, 6)


def analyze_financial_ratios(
    revenue: float,
    net_income: float,
    total_assets: float,
    total_equity: float,
    total_debt: float,
    current_assets: float,
    current_liabilities: float,
) -> dict:
    """Comprehensive financial ratio analysis."""
    def safe_div(a: float, b: float) -> float | None:
        return round(a / b, 4) if b != 0 else None

    profit_margin = safe_div(net_income, revenue)
    roa = safe_div(net_income, total_assets)
    roe = safe_div(net_income, total_equity)
    debt_to_equity = safe_div(total_debt, total_equity)
    debt_to_assets = safe_div(total_debt, total_assets)
    current_ratio = safe_div(current_assets, current_liabilities)
    asset_turnover = safe_div(revenue, total_assets)

    # Health assessment
    health_flags: list[str] = []
    if current_ratio is not None and current_ratio < 1.0:
        health_flags.append("Liquidity risk: current ratio below 1.0")
    if debt_to_equity is not None and debt_to_equity > 2.0:
        health_flags.append("High leverage: debt-to-equity above 2.0")
    if profit_margin is not None and profit_margin < 0:
        health_flags.append("Negative profit margin")
    if roe is not None and roe < 0:
        health_flags.append("Negative return on equity")

    return {
        "profitability": {
            "profit_margin": profit_margin,
            "roa": roa,
            "roe": roe,
        },
        "leverage": {
            "debt_to_equity": debt_to_equity,
            "debt_to_assets": debt_to_assets,
        },
        "liquidity": {
            "current_ratio": current_ratio,
        },
        "efficiency": {
            "asset_turnover": asset_turnover,
        },
        "health_flags": health_flags,
        "overall_health": "healthy" if not health_flags else "attention_needed",
    }


def calculate_breakeven(
    fixed_costs: float,
    price_per_unit: float,
    variable_cost_per_unit: float,
) -> dict:
    """Break-even analysis."""
    contribution_margin = price_per_unit - variable_cost_per_unit
    if contribution_margin <= 0:
        return {
            "error": "Contribution margin is zero or negative — break-even not achievable",
            "contribution_margin": round(contribution_margin, 2),
        }

    breakeven_units = fixed_costs / contribution_margin
    breakeven_revenue = breakeven_units * price_per_unit
    cm_ratio = contribution_margin / price_per_unit

    return {
        "breakeven_units": round(breakeven_units, 2),
        "breakeven_revenue": round(breakeven_revenue, 2),
        "contribution_margin": round(contribution_margin, 2),
        "contribution_margin_ratio": round(cm_ratio, 4),
        "fixed_costs": fixed_costs,
        "price_per_unit": price_per_unit,
        "variable_cost_per_unit": variable_cost_per_unit,
    }


def portfolio_risk_analysis(
    returns: list[list[float]],
    weights: list[float],
) -> dict:
    """Portfolio risk analysis — pure Python variance/covariance calculation."""
    n_assets = len(returns)
    if n_assets == 0 or len(weights) != n_assets:
        return {"error": "returns and weights must have the same non-zero length"}

    # Normalize weights
    w_sum = sum(weights)
    if w_sum == 0:
        return {"error": "weights sum to zero"}
    w = [wi / w_sum for wi in weights]

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    def variance(xs: list[float]) -> float:
        m = mean(xs)
        return sum((x - m) ** 2 for x in xs) / len(xs) if xs else 0.0

    def covariance(xs: list[float], ys: list[float]) -> float:
        mx, my = mean(xs), mean(ys)
        n = min(len(xs), len(ys))
        if n == 0:
            return 0.0
        return sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / n

    # Individual asset stats
    asset_means = [mean(r) for r in returns]
    asset_vars = [variance(r) for r in returns]
    asset_stds = [math.sqrt(v) for v in asset_vars]

    # Covariance matrix
    cov_matrix: list[list[float]] = []
    for i in range(n_assets):
        row: list[float] = []
        for j in range(n_assets):
            row.append(covariance(returns[i], returns[j]))
        cov_matrix.append(row)

    # Portfolio expected return
    portfolio_return = sum(w[i] * asset_means[i] for i in range(n_assets))

    # Portfolio variance: w^T * Cov * w
    portfolio_variance = 0.0
    for i in range(n_assets):
        for j in range(n_assets):
            portfolio_variance += w[i] * w[j] * cov_matrix[i][j]

    portfolio_std = math.sqrt(max(portfolio_variance, 0.0))

    # Sharpe ratio approximation (risk-free rate = 0)
    sharpe = portfolio_return / portfolio_std if portfolio_std > 0 else 0.0

    return {
        "portfolio_expected_return": round(portfolio_return, 6),
        "portfolio_variance": round(portfolio_variance, 6),
        "portfolio_std_dev": round(portfolio_std, 6),
        "sharpe_ratio": round(sharpe, 4),
        "weights": [round(wi, 4) for wi in w],
        "asset_expected_returns": [round(m, 6) for m in asset_means],
        "asset_std_devs": [round(s, 6) for s in asset_stds],
        "covariance_matrix": [[round(c, 8) for c in row] for row in cov_matrix],
    }


# ══════════════════════════════════════════════════════════════════
#  LEGAL DOMAIN
# ══════════════════════════════════════════════════════════════════

# Regex patterns for contract clause detection
_CONTRACT_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "parties": [
        re.compile(r"(?:between|arasında|taraflar)\s*[:\-]?\s*(.+?)(?:and|ve|ile)", re.I),
        re.compile(r"(?:party\s*[ab12]|taraf\s*[12])\s*[:\-]?\s*(.+?)[\n,;]", re.I),
    ],
    "obligations": [
        re.compile(r"(?:shall|must|obligat|yükümlü|taahhüt|edecektir|mecbur)", re.I),
    ],
    "termination": [
        re.compile(r"(?:terminat|fesih|sona erm|iptal|cancel|expire|süre\s*sonu)", re.I),
    ],
    "liability": [
        re.compile(r"(?:liabilit|sorumluluk|tazminat|indemnif|damages|zarar)", re.I),
    ],
    "confidentiality": [
        re.compile(r"(?:confidential|gizlilik|non-disclosure|ifşa|sır)", re.I),
    ],
    "governing_law": [
        re.compile(r"(?:governing\s*law|applicable\s*law|uygulanacak\s*hukuk|yetki\s*mahkeme)", re.I),
    ],
}

_RED_FLAG_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Unlimited liability clause", re.compile(r"unlimited\s*liabilit|sınırsız\s*sorumluluk", re.I)),
    ("Auto-renewal without notice", re.compile(r"auto(?:matic)?\s*renew|otomatik\s*yenilen", re.I)),
    ("Unilateral termination right", re.compile(r"(?:sole|unilateral)\s*(?:right|discretion)\s*(?:to\s*)?terminat", re.I)),
    ("Non-compete exceeds 2 years", re.compile(r"non[\-\s]?compete.*(?:[3-9]|[1-9]\d)\s*year", re.I)),
    ("Broad indemnification clause", re.compile(r"indemnif.*(?:all|any|every)\s*(?:claim|loss|damage)", re.I)),
    ("Missing data protection clause", re.compile(r"(?:personal\s*data|kişisel\s*veri)", re.I)),
]


def analyze_contract_clauses(contract_text: str) -> dict:
    """Identify key clauses, parties, and red flags in a contract."""
    text = contract_text.strip()
    if not text:
        return {"error": "Empty contract text"}

    found_clauses: dict[str, bool] = {}
    clause_excerpts: dict[str, list[str]] = {}

    for clause_name, patterns in _CONTRACT_PATTERNS.items():
        matches: list[str] = []
        for pat in patterns:
            for m in pat.finditer(text):
                excerpt = m.group(0).strip()[:200]
                if excerpt:
                    matches.append(excerpt)
        found_clauses[clause_name] = len(matches) > 0
        if matches:
            clause_excerpts[clause_name] = matches[:3]

    # Red flags
    red_flags: list[str] = []
    for flag_name, pat in _RED_FLAG_PATTERNS:
        if pat.search(text):
            red_flags.append(flag_name)

    # Check for missing critical clauses
    missing: list[str] = []
    critical = ["termination", "liability", "governing_law"]
    for c in critical:
        if not found_clauses.get(c):
            missing.append(c)

    # Completeness score
    total_clauses = len(_CONTRACT_PATTERNS)
    found_count = sum(1 for v in found_clauses.values() if v)
    completeness = round(found_count / total_clauses, 2) if total_clauses else 0

    return {
        "clauses_found": found_clauses,
        "clause_excerpts": clause_excerpts,
        "red_flags": red_flags,
        "missing_critical_clauses": missing,
        "completeness_score": completeness,
        "word_count": len(text.split()),
    }


def check_kvkk_compliance(data_processing_description: str) -> dict:
    """Check KVKK (Turkish Data Protection Law) compliance."""
    text = data_processing_description.lower()

    checks = {
        "explicit_consent": _kw_check(text, [
            "açık rıza", "explicit consent", "onay", "consent form", "rıza beyanı",
        ]),
        "purpose_limitation": _kw_check(text, [
            "amaç", "purpose", "işleme amacı", "processing purpose", "belirli amaç",
        ]),
        "data_minimization": _kw_check(text, [
            "minimum veri", "data minimization", "gerekli veri", "sınırlı veri",
            "ölçülü", "proportional",
        ]),
        "storage_limitation": _kw_check(text, [
            "saklama süresi", "retention", "silme", "deletion", "imha",
            "storage period", "muhafaza",
        ]),
        "security_measures": _kw_check(text, [
            "güvenlik", "security", "şifreleme", "encryption", "erişim kontrol",
            "access control", "teknik tedbir",
        ]),
        "dpo_assigned": _kw_check(text, [
            "veri sorumlusu", "dpo", "data protection officer", "irtibat kişisi",
            "kvkk sorumlu",
        ]),
        "cross_border_transfer": _kw_check(text, [
            "yurt dışı", "cross-border", "transfer", "aktarım", "üçüncü ülke",
            "third country",
        ]),
    }

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    score = round(passed / total * 100, 1)

    issues: list[str] = []
    recommendations: list[str] = []
    for check_name, passed_check in checks.items():
        if not passed_check:
            label = check_name.replace("_", " ").title()
            issues.append(f"{label} not addressed")
            recommendations.append(f"Add {label.lower()} provisions to your data processing description")

    return {
        "compliance_score": score,
        "checks": checks,
        "passed": passed,
        "total": total,
        "issues": issues,
        "recommendations": recommendations,
        "jurisdiction": "TR",
        "law": "KVKK (6698)",
    }


def check_gdpr_compliance(data_processing_description: str) -> dict:
    """Check GDPR (EU General Data Protection Regulation) compliance."""
    text = data_processing_description.lower()

    checks = {
        "lawful_basis": _kw_check(text, [
            "lawful basis", "legal basis", "consent", "legitimate interest",
            "contractual necessity", "legal obligation",
        ]),
        "purpose_limitation": _kw_check(text, [
            "purpose", "specific purpose", "defined purpose", "processing purpose",
        ]),
        "data_minimization": _kw_check(text, [
            "data minimization", "minimum data", "adequate", "relevant", "limited",
        ]),
        "storage_limitation": _kw_check(text, [
            "retention", "storage period", "deletion", "erasure", "time limit",
        ]),
        "security_measures": _kw_check(text, [
            "security", "encryption", "pseudonymization", "access control",
            "technical measures", "organizational measures",
        ]),
        "dpo_assigned": _kw_check(text, [
            "dpo", "data protection officer", "privacy officer",
        ]),
        "data_subject_rights": _kw_check(text, [
            "right to access", "right to erasure", "right to rectification",
            "data portability", "right to object", "subject rights",
        ]),
        "dpia_conducted": _kw_check(text, [
            "dpia", "impact assessment", "data protection impact",
            "risk assessment", "privacy impact",
        ]),
        "cross_border_transfer": _kw_check(text, [
            "cross-border", "international transfer", "third country",
            "adequacy decision", "standard contractual clauses", "scc",
        ]),
    }

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    score = round(passed / total * 100, 1)

    issues: list[str] = []
    recommendations: list[str] = []
    for check_name, passed_check in checks.items():
        if not passed_check:
            label = check_name.replace("_", " ").title()
            issues.append(f"{label} not addressed")
            recommendations.append(f"Ensure {label.lower()} is documented per GDPR Art. requirements")

    return {
        "compliance_score": score,
        "checks": checks,
        "passed": passed,
        "total": total,
        "issues": issues,
        "recommendations": recommendations,
        "jurisdiction": "EU",
        "law": "GDPR (2016/679)",
    }


def assess_legal_risk(scenario: str) -> dict:
    """Assess legal risk level from a scenario description."""
    text = scenario.lower()

    risk_factors: list[str] = []
    mitigation_steps: list[str] = []

    risk_keywords = {
        "high": [
            ("personal data breach", "Implement incident response plan and notify authorities within 72h"),
            ("intellectual property infringement", "Conduct IP clearance search and obtain proper licenses"),
            ("regulatory non-compliance", "Engage compliance officer and conduct regulatory audit"),
            ("contract breach", "Review contract terms and seek legal counsel for remediation"),
            ("employment dispute", "Document all HR processes and consult employment lawyer"),
            ("kişisel veri ihlali", "KVKK kapsamında 72 saat içinde bildirim yapın"),
        ],
        "medium": [
            ("third party liability", "Review indemnification clauses and insurance coverage"),
            ("data processing", "Ensure data processing agreements are in place"),
            ("cross-border", "Verify international compliance requirements"),
            ("subcontractor", "Audit subcontractor agreements and compliance"),
            ("sözleşme", "Sözleşme maddelerini hukuk danışmanıyla gözden geçirin"),
        ],
        "low": [
            ("standard terms", "Periodic review of standard terms recommended"),
            ("internal policy", "Ensure policies are up to date and communicated"),
            ("documentation", "Maintain proper documentation and records"),
        ],
    }

    score = 0
    for level, patterns in risk_keywords.items():
        for keyword, mitigation in patterns:
            if keyword in text:
                risk_factors.append(f"[{level.upper()}] {keyword}")
                mitigation_steps.append(mitigation)
                if level == "high":
                    score += 3
                elif level == "medium":
                    score += 2
                else:
                    score += 1

    if score >= 6:
        risk_level = "high"
    elif score >= 3:
        risk_level = "medium"
    elif score >= 1:
        risk_level = "low"
    else:
        risk_level = "undetermined"
        risk_factors.append("No specific risk indicators detected — manual review recommended")
        mitigation_steps.append("Consult with a legal professional for thorough assessment")

    return {
        "risk_level": risk_level,
        "risk_score": score,
        "risk_factors": risk_factors,
        "mitigation_steps": mitigation_steps,
        "disclaimer": "This is an automated preliminary assessment. Consult a qualified legal professional.",
    }


def explain_legal_term(term: str, jurisdiction: str = "TR") -> dict:
    """Explain a legal term with jurisdiction context."""
    _terms: dict[str, dict[str, str]] = {
        "tüzel kişi": {
            "definition": "A legal entity (company, foundation, association) that has rights and obligations separate from its members.",
            "definition_tr": "Üyeleri dışında hak ve yükümlülüklere sahip hukuki varlık (şirket, vakıf, dernek).",
            "example": "A limited liability company (Ltd. Şti.) is a tüzel kişi.",
        },
        "müteselsil sorumluluk": {
            "definition": "Joint and several liability — each party is independently liable for the full obligation.",
            "definition_tr": "Her bir tarafın borcun tamamından bağımsız olarak sorumlu olması.",
            "example": "Partners in a general partnership have müteselsil sorumluluk.",
        },
        "haksız fiil": {
            "definition": "Tort — an unlawful act causing damage, giving rise to civil liability.",
            "definition_tr": "Hukuka aykırı fiil sonucu başkasına verilen zarar nedeniyle doğan sorumluluk.",
            "example": "Negligence causing property damage is a haksız fiil under Turkish Code of Obligations Art. 49.",
        },
        "ipotek": {
            "definition": "Mortgage — a security interest in real property given to a creditor.",
            "definition_tr": "Alacaklıya teminat olarak taşınmaz üzerinde kurulan ayni hak.",
            "example": "Banks require ipotek when issuing real estate loans.",
        },
        "force majeure": {
            "definition": "Unforeseeable circumstances preventing contract fulfillment — neither party is liable.",
            "definition_tr": "Sözleşmenin ifasını engelleyen öngörülemeyen ve kaçınılmaz olay — taraflar sorumlu tutulamaz.",
            "example": "Natural disasters, wars, and pandemics may qualify as force majeure.",
        },
        "indemnification": {
            "definition": "A contractual obligation to compensate another party for losses or damages.",
            "definition_tr": "Bir tarafın diğer tarafın zararlarını tazmin etme yükümlülüğü.",
            "example": "Service agreements often include indemnification clauses for IP infringement.",
        },
    }

    term_lower = term.lower().strip()
    entry = _terms.get(term_lower)

    if entry:
        return {
            "term": term,
            "jurisdiction": jurisdiction,
            **entry,
            "source": "built-in legal glossary",
        }

    return {
        "term": term,
        "jurisdiction": jurisdiction,
        "definition": f"Term '{term}' not found in built-in glossary.",
        "definition_tr": f"'{term}' terimi yerleşik sözlükte bulunamadı.",
        "suggestion": "Use web_search for detailed legal definitions or consult a legal professional.",
    }


def _kw_check(text: str, keywords: list[str]) -> bool:
    """Check if any keyword appears in text."""
    return any(kw in text for kw in keywords)


# ══════════════════════════════════════════════════════════════════
#  ENGINEERING DOMAIN
# ══════════════════════════════════════════════════════════════════

def review_system_design(
    description: str,
    requirements: dict | None = None,
) -> dict:
    """Review a system design and provide scores and recommendations."""
    text = description.lower()
    reqs = requirements or {}

    scores: dict[str, float] = {
        "scalability": 5.0,
        "reliability": 5.0,
        "security": 5.0,
    }
    recommendations: list[str] = []
    bottlenecks: list[str] = []
    suggested_patterns: list[str] = []

    # Scalability signals
    scale_positive = ["horizontal scal", "load balanc", "auto-scal", "microservice", "cache", "cdn", "queue", "sharding"]
    scale_negative = ["single server", "monolith", "no cache", "single point", "vertical only"]
    for kw in scale_positive:
        if kw in text:
            scores["scalability"] += 1.0
    for kw in scale_negative:
        if kw in text:
            scores["scalability"] -= 1.0
            bottlenecks.append(f"Scalability concern: '{kw}' detected")

    # Reliability signals
    rel_positive = ["redundan", "failover", "backup", "health check", "circuit breaker", "retry", "replica"]
    rel_negative = ["single point of failure", "no backup", "no redundan", "no failover"]
    for kw in rel_positive:
        if kw in text:
            scores["reliability"] += 1.0
    for kw in rel_negative:
        if kw in text:
            scores["reliability"] -= 1.5
            bottlenecks.append(f"Reliability concern: '{kw}' detected")

    # Security signals
    sec_positive = ["encrypt", "auth", "https", "tls", "rbac", "waf", "rate limit", "input validat"]
    sec_negative = ["no auth", "http only", "plain text", "no encrypt", "hardcoded secret"]
    for kw in sec_positive:
        if kw in text:
            scores["security"] += 1.0
    for kw in sec_negative:
        if kw in text:
            scores["security"] -= 1.5
            bottlenecks.append(f"Security concern: '{kw}' detected")

    # Clamp scores
    for k in scores:
        scores[k] = round(max(0.0, min(10.0, scores[k])), 1)

    overall = round(sum(scores.values()) / len(scores), 1)

    # Pattern suggestions
    if "microservice" not in text and "monolith" not in text:
        suggested_patterns.append("Consider defining architecture style (microservices vs monolith)")
    if "cache" not in text:
        suggested_patterns.append("Add caching layer (Redis/Memcached) for frequently accessed data")
    if "queue" not in text and "message" not in text:
        suggested_patterns.append("Consider async message queue for decoupling components")
    if "circuit breaker" not in text:
        suggested_patterns.append("Implement circuit breaker pattern for external service calls")

    if not recommendations:
        for bn in bottlenecks:
            recommendations.append(f"Address: {bn}")
    if overall < 5.0:
        recommendations.append("Overall score is low — consider a thorough architecture review")

    return {
        "scores": scores,
        "overall_score": overall,
        "bottlenecks": bottlenecks,
        "recommendations": recommendations,
        "suggested_patterns": suggested_patterns,
        "requirements_coverage": "partial" if reqs else "no_requirements_provided",
    }


def estimate_load_capacity(
    rps: float,
    avg_response_ms: float,
    num_instances: int = 1,
    concurrency_per_instance: int = 100,
) -> dict:
    """Estimate system load capacity and saturation point."""
    if rps <= 0 or avg_response_ms <= 0:
        return {"error": "rps and avg_response_ms must be positive"}

    avg_response_s = avg_response_ms / 1000.0
    capacity_per_instance = concurrency_per_instance / avg_response_s
    total_capacity = capacity_per_instance * num_instances
    utilization = rps / total_capacity if total_capacity > 0 else 1.0

    if utilization < 0.5:
        status = "healthy"
    elif utilization < 0.75:
        status = "moderate"
    elif utilization < 0.9:
        status = "high"
    else:
        status = "saturated"

    recommended_instances = math.ceil(rps / (capacity_per_instance * 0.7)) if capacity_per_instance > 0 else num_instances

    return {
        "current_rps": rps,
        "capacity_per_instance": round(capacity_per_instance, 1),
        "total_capacity_rps": round(total_capacity, 1),
        "utilization": round(utilization, 4),
        "status": status,
        "num_instances": num_instances,
        "recommended_instances": recommended_instances,
    }


# ══════════════════════════════════════════════════════════════════
#  ACADEMIC DOMAIN
# ══════════════════════════════════════════════════════════════════

def generate_literature_review_template(topic: str, num_sources: int = 10) -> dict:
    """Generate a structured literature review template."""
    return {
        "topic": topic,
        "template": {
            "title": f"Literature Review: {topic}",
            "sections": [
                {"name": "Introduction", "description": "Background and scope of the review"},
                {"name": "Methodology", "description": f"Search strategy, databases used, inclusion/exclusion criteria for ~{num_sources} sources"},
                {"name": "Thematic Analysis", "description": "Key themes and findings organized by subtopic"},
                {"name": "Critical Evaluation", "description": "Strengths, weaknesses, and gaps in existing literature"},
                {"name": "Synthesis", "description": "Integration of findings and emerging patterns"},
                {"name": "Conclusion", "description": "Summary of key insights and future research directions"},
            ],
            "recommended_databases": [
                "Google Scholar", "PubMed", "IEEE Xplore", "Scopus",
                "Web of Science", "JSTOR", "arXiv",
            ],
            "citation_format": "APA 7th Edition",
        },
        "num_sources": num_sources,
    }


def analyze_citation_network(citations: list[dict]) -> dict:
    """Analyze a citation network for key metrics."""
    if not citations:
        return {"error": "No citations provided"}

    total = len(citations)
    authors: dict[str, int] = {}
    years: dict[int, int] = {}
    journals: dict[str, int] = {}

    for c in citations:
        for author in c.get("authors", []):
            authors[author] = authors.get(author, 0) + 1
        year = c.get("year")
        if year:
            years[year] = years.get(year, 0) + 1
        journal = c.get("journal", "")
        if journal:
            journals[journal] = journals.get(journal, 0) + 1

    top_authors = sorted(authors.items(), key=lambda x: x[1], reverse=True)[:10]
    top_journals = sorted(journals.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_citations": total,
        "unique_authors": len(authors),
        "top_authors": [{"name": a, "count": c} for a, c in top_authors],
        "year_distribution": dict(sorted(years.items())),
        "top_journals": [{"name": j, "count": c} for j, c in top_journals],
    }


def suggest_methodology(research_type: str) -> dict:
    """Suggest research methodology based on research type."""
    methodologies: dict[str, dict] = {
        "quantitative": {
            "approach": "Quantitative Research",
            "methods": ["Survey", "Experiment", "Quasi-experiment", "Correlational study"],
            "data_collection": ["Structured questionnaires", "Standardized tests", "Sensor data"],
            "analysis": ["Descriptive statistics", "Regression analysis", "ANOVA", "Factor analysis"],
            "tools": ["SPSS", "R", "Python (scipy/statsmodels)", "Stata"],
        },
        "qualitative": {
            "approach": "Qualitative Research",
            "methods": ["Case study", "Ethnography", "Grounded theory", "Phenomenology"],
            "data_collection": ["Semi-structured interviews", "Focus groups", "Observation", "Document analysis"],
            "analysis": ["Thematic analysis", "Content analysis", "Narrative analysis", "Discourse analysis"],
            "tools": ["NVivo", "ATLAS.ti", "MAXQDA", "Dedoose"],
        },
        "mixed": {
            "approach": "Mixed Methods Research",
            "methods": ["Convergent parallel", "Explanatory sequential", "Exploratory sequential"],
            "data_collection": ["Surveys + Interviews", "Tests + Focus groups", "Observation + Questionnaires"],
            "analysis": ["Statistical analysis + Thematic analysis", "Joint display", "Meta-inference"],
            "tools": ["SPSS + NVivo", "R + ATLAS.ti", "Python + MAXQDA"],
        },
    }

    rt = research_type.lower().strip()
    if rt in methodologies:
        return {"research_type": research_type, **methodologies[rt]}

    return {
        "research_type": research_type,
        "suggestion": "Specify 'quantitative', 'qualitative', or 'mixed' for detailed methodology guidance.",
        "available_types": list(methodologies.keys()),
    }


# ══════════════════════════════════════════════════════════════════
#  DOMAIN REGISTRY
# ══════════════════════════════════════════════════════════════════

DOMAINS: dict[str, DomainModule] = {
    "finance": DomainModule(
        domain_id="finance",
        name="Finance & Valuation",
        name_tr="Finans & Değerleme",
        description="Financial modeling, valuation, ratio analysis, and portfolio management",
        capabilities=["DCF valuation", "NPV/IRR calculation", "WACC", "Financial ratios", "Break-even", "Portfolio risk"],
        tools=[
            {"name": "calculate_dcf", "description": "Discounted Cash Flow valuation", "params": ["cash_flows", "discount_rate", "terminal_growth"]},
            {"name": "calculate_npv", "description": "Net Present Value", "params": ["cash_flows", "discount_rate"]},
            {"name": "calculate_irr", "description": "Internal Rate of Return", "params": ["cash_flows"]},
            {"name": "calculate_wacc", "description": "Weighted Average Cost of Capital", "params": ["equity_value", "debt_value", "cost_of_equity", "cost_of_debt", "tax_rate"]},
            {"name": "analyze_financial_ratios", "description": "Comprehensive ratio analysis", "params": ["revenue", "net_income", "total_assets", "total_equity", "total_debt", "current_assets", "current_liabilities"]},
            {"name": "calculate_breakeven", "description": "Break-even analysis", "params": ["fixed_costs", "price_per_unit", "variable_cost_per_unit"]},
            {"name": "portfolio_risk_analysis", "description": "Portfolio risk & return analysis", "params": ["returns", "weights"]},
        ],
    ),
    "legal": DomainModule(
        domain_id="legal",
        name="Legal & Compliance",
        name_tr="Hukuk & Uyumluluk",
        description="Contract analysis, KVKK/GDPR compliance, risk assessment, legal terminology",
        capabilities=["Contract clause analysis", "KVKK compliance check", "GDPR compliance check", "Legal risk assessment", "Legal term explanation"],
        tools=[
            {"name": "analyze_contract_clauses", "description": "Identify clauses and red flags", "params": ["contract_text"]},
            {"name": "check_kvkk_compliance", "description": "KVKK compliance check", "params": ["data_processing_description"]},
            {"name": "check_gdpr_compliance", "description": "GDPR compliance check", "params": ["data_processing_description"]},
            {"name": "assess_legal_risk", "description": "Legal risk assessment", "params": ["scenario"]},
            {"name": "explain_legal_term", "description": "Legal term explanation", "params": ["term", "jurisdiction"]},
        ],
    ),
    "engineering": DomainModule(
        domain_id="engineering",
        name="Engineering & Architecture",
        name_tr="Mühendislik & Mimari",
        description="System design review, load testing estimation, architecture patterns",
        capabilities=["System design review", "Load capacity estimation", "Architecture scoring"],
        tools=[
            {"name": "review_system_design", "description": "Review and score system design", "params": ["description", "requirements"]},
            {"name": "estimate_load_capacity", "description": "Estimate load capacity", "params": ["rps", "avg_response_ms", "num_instances", "concurrency_per_instance"]},
        ],
    ),
    "academic": DomainModule(
        domain_id="academic",
        name="Academic Research",
        name_tr="Akademik Araştırma",
        description="Literature review, citation analysis, methodology guidance",
        capabilities=["Literature review template", "Citation network analysis", "Methodology suggestion"],
        tools=[
            {"name": "generate_literature_review_template", "description": "Generate literature review template", "params": ["topic", "num_sources"]},
            {"name": "analyze_citation_network", "description": "Analyze citation network", "params": ["citations"]},
            {"name": "suggest_methodology", "description": "Suggest research methodology", "params": ["research_type"]},
        ],
    ),
}


# ── Tool Dispatch ────────────────────────────────────────────────

_TOOL_MAP: dict[str, Any] = {
    # Finance
    "calculate_dcf": calculate_dcf,
    "calculate_npv": calculate_npv,
    "calculate_irr": calculate_irr,
    "calculate_wacc": calculate_wacc,
    "analyze_financial_ratios": analyze_financial_ratios,
    "calculate_breakeven": calculate_breakeven,
    "portfolio_risk_analysis": portfolio_risk_analysis,
    # Legal
    "analyze_contract_clauses": analyze_contract_clauses,
    "check_kvkk_compliance": check_kvkk_compliance,
    "check_gdpr_compliance": check_gdpr_compliance,
    "assess_legal_risk": assess_legal_risk,
    "explain_legal_term": explain_legal_term,
    # Engineering
    "review_system_design": review_system_design,
    "estimate_load_capacity": estimate_load_capacity,
    # Academic
    "generate_literature_review_template": generate_literature_review_template,
    "analyze_citation_network": analyze_citation_network,
    "suggest_methodology": suggest_methodology,
}


def list_domains() -> list[dict]:
    """Return all available domain modules."""
    return [
        {
            "domain_id": d.domain_id,
            "name": d.name,
            "name_tr": d.name_tr,
            "description": d.description,
            "capabilities": d.capabilities,
            "tool_count": len(d.tools),
        }
        for d in DOMAINS.values()
    ]


def get_domain_tools(domain_id: str) -> list[dict] | None:
    """Return tools for a specific domain, or None if domain not found."""
    domain = DOMAINS.get(domain_id)
    if domain is None:
        return None
    return domain.tools


async def execute_domain_tool(domain: str, tool_name: str, arguments: dict) -> dict:
    """Execute a domain-specific tool by name."""
    if domain not in DOMAINS:
        return {"error": f"Unknown domain: {domain}. Available: {list(DOMAINS.keys())}"}

    fn = _TOOL_MAP.get(tool_name)
    if fn is None:
        available = [t["name"] for t in DOMAINS[domain].tools]
        return {"error": f"Unknown tool: {tool_name}. Available in {domain}: {available}"}

    try:
        import asyncio
        if asyncio.iscoroutinefunction(fn):
            result = await fn(**arguments)
        else:
            result = fn(**arguments)
        increment_usage(domain)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": f"Tool execution failed: {e}"}


# ── Domain Auto-Discovery ────────────────────────────────────────

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "finance": [
        "finans", "finance", "valuation", "değerleme", "dcf", "npv", "irr",
        "wacc", "nakit akışı", "cash flow", "portföy", "portfolio", "risk",
        "bilanço", "balance sheet", "gelir tablosu", "income", "revenue",
        "kâr", "profit", "zarar", "loss", "yatırım", "investment", "borç",
        "debt", "özsermaye", "equity", "faiz", "interest", "bütçe", "budget",
        "maliyet", "cost", "break-even", "başabaş", "oran", "ratio",
        "likidite", "liquidity", "varlık", "asset", "sermaye", "capital",
    ],
    "legal": [
        "hukuk", "legal", "sözleşme", "contract", "kvkk", "gdpr", "kişisel veri",
        "personal data", "uyumluluk", "compliance", "mahkeme", "court",
        "dava", "lawsuit", "kanun", "law", "yönetmelik", "regulation",
        "madde", "clause", "ihlal", "violation", "ceza", "penalty",
        "gizlilik", "privacy", "telif", "copyright", "patent", "marka",
        "trademark", "lisans", "license", "sorumluluk", "liability",
    ],
    "engineering": [
        "mühendislik", "engineering", "mimari", "architecture", "sistem tasarımı",
        "system design", "yük", "load", "kapasite", "capacity", "ölçekleme",
        "scaling", "performans", "performance", "sunucu", "server", "api",
        "microservice", "mikro servis", "database", "veritabanı", "cache",
        "cdn", "latency", "gecikme", "throughput", "rps", "concurrent",
        "eşzamanlı", "availability", "erişilebilirlik", "uptime",
    ],
    "academic": [
        "akademik", "academic", "araştırma", "research", "literatür",
        "literature", "makale", "paper", "atıf", "citation", "metodoloji",
        "methodology", "tez", "thesis", "hipotez", "hypothesis", "analiz",
        "analysis", "veri toplama", "data collection", "örneklem", "sample",
        "istatistik", "statistics", "nitel", "qualitative", "nicel",
        "quantitative", "kaynak", "source", "referans", "reference",
    ],
}


def auto_detect_domain(query: str, top_k: int = 3) -> list[dict]:
    """
    Analyze a user query and detect which domain(s) are most relevant.
    Returns ranked list of matching domains with scores and suggested tools.
    """
    if not query or not query.strip():
        return []

    query_lower = query.lower()
    query_words = set(re.findall(r'\w+', query_lower))
    results = []

    for domain_id, domain in DOMAINS.items():
        score = 0.0
        matched_keywords: list[str] = []

        # 1) Check domain keywords (highest weight)
        domain_kws = DOMAIN_KEYWORDS.get(domain_id, [])
        for kw in domain_kws:
            kw_lower = kw.lower()
            if kw_lower in query_lower:
                score += 3.0
                matched_keywords.append(kw)
            elif any(w in kw_lower.split() for w in query_words if len(w) > 2):
                score += 1.0
                matched_keywords.append(kw)

        # 2) Check capabilities
        for cap in domain.capabilities:
            cap_lower = cap.lower()
            cap_words = set(cap_lower.split())
            overlap = query_words & cap_words
            if overlap:
                score += len(overlap) * 1.5
                matched_keywords.append(cap)

        # 3) Check tool names and descriptions
        suggested_tools: list[dict] = []
        for tool in domain.tools:
            tool_name_lower = tool["name"].lower().replace("_", " ")
            tool_desc_lower = tool.get("description", "").lower()
            tool_score = 0.0

            for w in query_words:
                if len(w) > 2:
                    if w in tool_name_lower:
                        tool_score += 2.0
                    if w in tool_desc_lower:
                        tool_score += 1.0

            if tool_score > 0:
                score += tool_score
                suggested_tools.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "relevance": round(tool_score, 1),
                })

        # 4) Check description match
        desc_lower = domain.description.lower()
        for w in query_words:
            if len(w) > 3 and w in desc_lower:
                score += 0.5

        if score > 0:
            # Sort suggested tools by relevance
            suggested_tools.sort(key=lambda t: t["relevance"], reverse=True)
            results.append({
                "domain_id": domain_id,
                "name": domain.name,
                "name_tr": domain.name_tr,
                "score": round(score, 1),
                "matched_keywords": list(set(matched_keywords))[:10],
                "suggested_tools": suggested_tools[:5],
                "capabilities": domain.capabilities,
            })

    # Sort by score descending
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def get_marketplace_catalog() -> list[dict]:
    """
    Return a unified marketplace catalog combining domain modules and dynamic skills.
    """
    catalog: list[dict] = []

    # Domain modules
    for domain_id, domain in DOMAINS.items():
        catalog.append({
            "id": f"domain:{domain_id}",
            "type": "domain",
            "name": domain.name,
            "name_tr": domain.name_tr,
            "description": domain.description,
            "capabilities": domain.capabilities,
            "tool_count": len(domain.tools),
            "tools": domain.tools,
            "installed": True,  # built-in domains are always installed
            "rating": 4.5,
            "downloads": 0,
            "category": "domain",
            "tags": DOMAIN_KEYWORDS.get(domain_id, [])[:8],
        })

    # Dynamic skills from DB
    try:
        from tools.dynamic_skills import list_skills
        skills = list_skills(limit=100)
        for skill in skills:
            catalog.append({
                "id": f"skill:{skill.get('id', '')}",
                "type": "skill",
                "name": skill.get("name", "Unnamed"),
                "name_tr": skill.get("name", "Unnamed"),
                "description": skill.get("description", ""),
                "capabilities": skill.get("keywords", []),
                "tool_count": 0,
                "tools": [],
                "installed": True,
                "rating": skill.get("rating", 0),
                "downloads": skill.get("usage_count", 0),
                "category": skill.get("category", "custom"),
                "tags": skill.get("keywords", []),
            })
    except Exception as e:
        logger.warning("Failed to load dynamic skills for marketplace: %s", e)

    return catalog


# ══════════════════════════════════════════════════════════════════
#  AUTO-DISCOVERY & MARKETPLACE
# ══════════════════════════════════════════════════════════════════

import importlib.util
import sqlite3
from pathlib import Path
from datetime import datetime

DISCOVERY_DIR = Path("data/domain_skills")
MARKETPLACE_DB = Path("data/dynamic_skills.db")


def _ensure_marketplace_db():
    """Create marketplace tables if not exist."""
    MARKETPLACE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(MARKETPLACE_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS domain_skill_registry (
            domain_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            name_tr TEXT NOT NULL,
            description TEXT,
            source TEXT DEFAULT 'discovered',
            enabled INTEGER DEFAULT 1,
            installed_at TEXT,
            usage_count INTEGER DEFAULT 0,
            rating REAL DEFAULT 0.0,
            version TEXT DEFAULT '1.0.0',
            author TEXT DEFAULT 'community'
        )
    """)
    conn.commit()
    conn.close()


def _register_builtin_domains():
    """Register built-in domains in marketplace DB."""
    _ensure_marketplace_db()
    conn = sqlite3.connect(str(MARKETPLACE_DB))
    now = datetime.utcnow().isoformat()
    for d in DOMAINS.values():
        conn.execute("""
            INSERT OR IGNORE INTO domain_skill_registry 
            (domain_id, name, name_tr, description, source, enabled, installed_at, version, author)
            VALUES (?, ?, ?, ?, 'builtin', 1, ?, '2.0.0', 'system')
        """, (d.domain_id, d.name, d.name_tr, d.description, now))
    conn.commit()
    conn.close()


def discover_domain_skills() -> dict:
    """Scan data/domain_skills/ for new domain modules and register them."""
    _ensure_marketplace_db()
    _register_builtin_domains()

    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
    discovered = []
    errors = []

    for py_file in DISCOVERY_DIR.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(
                f"domain_plugin_{py_file.stem}", str(py_file)
            )
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            config = getattr(module, "DOMAIN_CONFIG", None)
            if not config or not isinstance(config, dict):
                continue

            domain_id = config.get("domain_id", py_file.stem)

            # Build DomainModule
            dm = DomainModule(
                domain_id=domain_id,
                name=config.get("name", domain_id),
                name_tr=config.get("name_tr", config.get("name", domain_id)),
                description=config.get("description", ""),
                capabilities=config.get("capabilities", []),
                tools=config.get("tools", []),
            )

            # Register in DOMAINS
            DOMAINS[domain_id] = dm

            # Register tool functions
            for tool_def in config.get("tools", []):
                fn = getattr(module, tool_def["name"], None)
                if fn:
                    _TOOL_MAP[tool_def["name"]] = fn

            # Save to DB
            conn = sqlite3.connect(str(MARKETPLACE_DB))
            now = datetime.utcnow().isoformat()
            conn.execute("""
                INSERT OR REPLACE INTO domain_skill_registry
                (domain_id, name, name_tr, description, source, enabled, installed_at,
                 version, author)
                VALUES (?, ?, ?, ?, 'discovered', 1, ?,
                        ?, ?)
            """, (
                domain_id, dm.name, dm.name_tr, dm.description, now,
                config.get("version", "1.0.0"), config.get("author", "community")
            ))
            conn.commit()
            conn.close()

            discovered.append(domain_id)
            logger.info(f"Discovered domain skill: {domain_id}")

        except Exception as e:
            errors.append({"file": py_file.name, "error": str(e)})
            logger.warning(f"Failed to load domain skill {py_file.name}: {e}")

    return {
        "discovered": discovered,
        "errors": errors,
        "total_domains": len(DOMAINS),
    }


def toggle_domain_skill(domain_id: str, enabled: bool) -> dict:
    """Enable or disable a domain skill."""
    _ensure_marketplace_db()
    conn = sqlite3.connect(str(MARKETPLACE_DB))
    cur = conn.execute(
        "UPDATE domain_skill_registry SET enabled = ? WHERE domain_id = ?",
        (1 if enabled else 0, domain_id)
    )
    conn.commit()
    conn.close()

    if cur.rowcount == 0:
        return {"error": f"Domain not found: {domain_id}"}

    # If disabling, remove from active DOMAINS (but keep builtin)
    if not enabled and domain_id in DOMAINS:
        _conn = sqlite3.connect(str(MARKETPLACE_DB))
        row = _conn.execute(
            "SELECT source FROM domain_skill_registry WHERE domain_id = ?",
            (domain_id,)
        ).fetchone()
        _conn.close()
        if row and row[0] == "discovered":
            del DOMAINS[domain_id]
    elif enabled and domain_id not in DOMAINS:
        # Re-discover to reload
        discover_domain_skills()

    return {"domain_id": domain_id, "enabled": enabled}


def increment_usage(domain_id: str):
    """Increment usage counter for a domain skill."""
    try:
        _ensure_marketplace_db()
        conn = sqlite3.connect(str(MARKETPLACE_DB))
        conn.execute(
            "UPDATE domain_skill_registry SET usage_count = usage_count + 1 WHERE domain_id = ?",
            (domain_id,)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_marketplace_data() -> list[dict]:
    """Get all domain skills with marketplace metadata."""
    _ensure_marketplace_db()
    _register_builtin_domains()

    conn = sqlite3.connect(str(MARKETPLACE_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM domain_skill_registry ORDER BY source, domain_id").fetchall()
    conn.close()

    result = []
    for row in rows:
        d = dict(row)
        # Enrich with live data from DOMAINS registry
        domain = DOMAINS.get(d["domain_id"])
        if domain:
            d["capabilities"] = domain.capabilities
            d["tool_count"] = len(domain.tools)
            d["tools"] = domain.tools
            d["active"] = True
        else:
            d["capabilities"] = []
            d["tool_count"] = 0
            d["tools"] = []
            d["active"] = False
        result.append(d)

    return result
