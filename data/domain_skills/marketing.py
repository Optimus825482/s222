"""Marketing & Analytics domain skill plugin."""

import math

DOMAIN_CONFIG = {
    "domain_id": "marketing",
    "name": "Marketing & Analytics",
    "name_tr": "Pazarlama & Analitik",
    "description": "ROI calculation, conversion rate analysis, A/B test significance, and campaign metrics",
    "capabilities": ["ROI calculation", "Conversion analysis", "A/B test significance", "CAC/LTV calculation"],
    "version": "1.0.0",
    "author": "community",
    "tools": [
        {"name": "calculate_roi", "description": "Calculate Return on Investment", "params": ["investment", "revenue"]},
        {"name": "ab_test_significance", "description": "Check A/B test statistical significance", "params": ["visitors_a", "conversions_a", "visitors_b", "conversions_b"]},
        {"name": "calculate_cac_ltv", "description": "Calculate Customer Acquisition Cost and Lifetime Value", "params": ["marketing_spend", "new_customers", "avg_revenue_per_customer", "avg_lifespan_months"]},
    ],
}


def calculate_roi(investment: float, revenue: float) -> dict:
    """Calculate ROI percentage."""
    if investment <= 0:
        return {"error": "Investment must be positive"}
    roi = ((revenue - investment) / investment) * 100
    return {
        "investment": investment,
        "revenue": revenue,
        "profit": round(revenue - investment, 2),
        "roi_percent": round(roi, 2),
        "status": "profitable" if roi > 0 else "loss",
        "status_tr": "kârlı" if roi > 0 else "zararlı",
    }


def ab_test_significance(
    visitors_a: int, conversions_a: int,
    visitors_b: int, conversions_b: int,
    confidence_level: float = 0.95,
) -> dict:
    """Check if A/B test results are statistically significant."""
    if visitors_a <= 0 or visitors_b <= 0:
        return {"error": "Visitor counts must be positive"}

    rate_a = conversions_a / visitors_a
    rate_b = conversions_b / visitors_b

    # Pooled standard error
    se_a = math.sqrt(rate_a * (1 - rate_a) / visitors_a) if rate_a > 0 else 0.001
    se_b = math.sqrt(rate_b * (1 - rate_b) / visitors_b) if rate_b > 0 else 0.001
    se = math.sqrt(se_a**2 + se_b**2)

    z_score = (rate_b - rate_a) / se if se > 0 else 0

    # Z-critical for common confidence levels
    z_critical = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(confidence_level, 1.96)

    significant = abs(z_score) > z_critical
    winner = "B" if rate_b > rate_a else "A" if rate_a > rate_b else "tie"
    lift = ((rate_b - rate_a) / rate_a * 100) if rate_a > 0 else 0

    return {
        "variant_a": {"visitors": visitors_a, "conversions": conversions_a, "rate": round(rate_a * 100, 2)},
        "variant_b": {"visitors": visitors_b, "conversions": conversions_b, "rate": round(rate_b * 100, 2)},
        "z_score": round(z_score, 3),
        "significant": significant,
        "confidence_level": confidence_level,
        "winner": winner,
        "lift_percent": round(lift, 2),
        "recommendation": f"Variant {winner} is the winner with {round(abs(lift), 1)}% lift" if significant else "Not enough evidence. Continue testing.",
        "recommendation_tr": f"Varyant {winner} %{round(abs(lift), 1)} artışla kazanan" if significant else "Yeterli kanıt yok. Teste devam edin.",
    }


def calculate_cac_ltv(
    marketing_spend: float,
    new_customers: int,
    avg_revenue_per_customer: float,
    avg_lifespan_months: int,
) -> dict:
    """Calculate CAC and LTV metrics."""
    if new_customers <= 0:
        return {"error": "new_customers must be positive"}

    cac = marketing_spend / new_customers
    ltv = avg_revenue_per_customer * avg_lifespan_months
    ltv_cac_ratio = ltv / cac if cac > 0 else 0

    if ltv_cac_ratio >= 3:
        health = "excellent"
        health_tr = "mükemmel"
    elif ltv_cac_ratio >= 1:
        health = "good"
        health_tr = "iyi"
    else:
        health = "poor"
        health_tr = "kötü"

    return {
        "cac": round(cac, 2),
        "ltv": round(ltv, 2),
        "ltv_cac_ratio": round(ltv_cac_ratio, 2),
        "health": health,
        "health_tr": health_tr,
        "payback_months": round(cac / avg_revenue_per_customer, 1) if avg_revenue_per_customer > 0 else None,
    }
