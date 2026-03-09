"""Agent messaging, autonomous chat, post-task meetings, and learning endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import Any
import asyncio
import uuid
import sys
from pathlib import Path

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit
from config import MODELS
from shared_state import _AGENT_ROLES, _utcnow

router = APIRouter()


# ── In-memory state ─────────────────────────────────────────────

_AGENT_MESSAGES: list[dict] = []
_AUTONOMOUS_CONVERSATIONS: list[dict] = []
_POST_TASK_MEETINGS: list[dict] = []

_AUTO_CHAT_CONFIG: dict = {
    "enabled": True,
    "auto_start": True,
    "interval_minutes": 5,
    "max_exchanges": 4,
    "enabled_agents": ["orchestrator", "thinker", "speed", "researcher", "reasoner", "critic"],
    "topics": [
        "sistem performansı", "görev optimizasyonu", "yeni stratejiler",
        "hata analizi", "işbirliği fırsatları", "teknoloji trendleri",
    ],
    "personality_prompts": {
        "orchestrator": "Sen DeepSeek Chat, orkestratör ajansın. Kullanıcının niyetini anlar, görevleri koordine eder, büyük resmi görürsün. Diğer ajanlara liderlik edersin ama saygılısın.",
        "thinker": "Sen MiniMax, derin düşünür ajansın. Karmaşık problemleri analiz eder, felsefi ve stratejik düşünürsün.",
        "speed": "Sen Step Flash, hız ajanısın. Pratik, hızlı çözümler üretirsin. Enerjik ve aksiyona yöneliksin.",
        "researcher": "Sen GLM, araştırmacı ajansın. Veri odaklı, meraklı ve detaycısın. Her şeyi araştırmak istersin.",
        "reasoner": "Sen Nemotron, mantık ajanısın. Matematiksel ve mantıksal düşünürsün. Kanıta dayalı konuşursun.",
        "critic": "Sen Qwen3, eleştirmen ve skill yaratıcı ajansın. Kalite kontrol yapar, eksikleri bulur, iyileştirme önerileri sunar ve yeni yetenekler oluşturursun. Yapıcı ama acımasız bir eleştirmensin.",
    },
}


# ── Pydantic models ─────────────────────────────────────────────

class AutoChatConfigRequest(BaseModel):
    enabled: bool | None = None
    auto_start: bool | None = None
    interval_minutes: int | None = None
    max_exchanges: int | None = None
    enabled_agents: list[str] | None = None
    topics: list[str] | None = None


# ═════════════════════════════════════════════════════════════════
# Autonomous Chat Background Scheduler
# ═════════════════════════════════════════════════════════════════

_auto_chat_task: asyncio.Task | None = None
_auto_chat_running = False


async def _auto_chat_loop():
    """Background loop: runs autonomous chat rounds at configured interval."""
    global _auto_chat_running
    _auto_chat_running = True
    print("[AutoChat] Background scheduler started")
    # Initial delay — let the system warm up before first auto-chat
    await asyncio.sleep(30)
    try:
        while _auto_chat_running:
            cfg = _AUTO_CHAT_CONFIG
            interval = max(cfg.get("interval_minutes", 5), 1) * 60
            if cfg.get("enabled") and cfg.get("auto_start"):
                try:
                    conv = _run_autonomous_chat_round()
                    if conv:
                        print(f"[AutoChat] Auto-triggered: {conv['initiator']} ⇄ {conv['responder']} — {conv['topic']}")
                except Exception as e:
                    print(f"[AutoChat] Round failed: {e}")
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass
    finally:
        _auto_chat_running = False
        print("[AutoChat] Background scheduler stopped")


async def start_auto_chat_scheduler():
    """Start the background autonomous chat scheduler."""
    global _auto_chat_task
    if _auto_chat_task and not _auto_chat_task.done():
        return
    _auto_chat_task = asyncio.create_task(_auto_chat_loop())


async def stop_auto_chat_scheduler():
    """Stop the background autonomous chat scheduler."""
    global _auto_chat_task, _auto_chat_running
    _auto_chat_running = False
    if _auto_chat_task and not _auto_chat_task.done():
        _auto_chat_task.cancel()
        try:
            await _auto_chat_task
        except asyncio.CancelledError:
            pass
    _auto_chat_task = None


def trigger_post_task_auto_chat(
    task_summary: str,
    participating_agents: list[str] | None = None,
) -> dict | None:
    """Trigger autonomous chat + post-task meeting after task completion.
    Called internally from orchestrator — no auth needed."""
    cfg = _AUTO_CHAT_CONFIG
    if not cfg.get("enabled"):
        return None

    meeting = None
    try:
        agents = participating_agents or cfg["enabled_agents"][:3]
        meeting = _generate_post_task_meeting(
            task_summary=task_summary,
            participating_agents=agents,
            task_status="completed",
        )
    except Exception:
        pass

    conv = None
    try:
        original_topics = list(cfg["topics"])
        task_topic = f"az önce tamamlanan görev: {task_summary[:80]}"
        cfg["topics"] = [task_topic] + original_topics[:2]
        conv = _run_autonomous_chat_round()
        cfg["topics"] = original_topics
    except Exception:
        pass

    return {"meeting": meeting, "conversation": conv}


# ═════════════════════════════════════════════════════════════════
# 7. Agent Direct Messaging
# ═════════════════════════════════════════════════════════════════


@router.post("/api/agents/message")
async def send_agent_message(
    sender: str,
    receiver: str,
    content: str,
    user: dict = Depends(get_current_user),
):
    """Send a direct message between agents (stored in-memory for real-time display)."""
    _audit("agent_message", user["user_id"], detail=f"{sender}->{receiver}")

    if sender not in _AGENT_ROLES or receiver not in _AGENT_ROLES:
        raise HTTPException(status_code=400, detail="Invalid agent role")
    if sender == receiver:
        raise HTTPException(status_code=400, detail="Cannot message self")
    if not content or len(content) > 2000:
        raise HTTPException(status_code=400, detail="Content must be 1-2000 chars")

    msg = {
        "id": f"msg-{len(_AGENT_MESSAGES)}",
        "sender": sender,
        "receiver": receiver,
        "content": content[:2000],
        "timestamp": _utcnow().isoformat(),
        "user_id": user["user_id"],
    }
    _AGENT_MESSAGES.append(msg)

    # Keep only last 200 messages
    if len(_AGENT_MESSAGES) > 200:
        _AGENT_MESSAGES[:] = _AGENT_MESSAGES[-200:]

    return {"message": msg, "total_messages": len(_AGENT_MESSAGES)}


@router.get("/api/agents/messages")
async def get_agent_messages(
    limit: int = 50,
    sender: str | None = None,
    receiver: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Get recent agent-to-agent messages with optional filtering."""
    _audit("agent_messages_view", user["user_id"])

    filtered = _AGENT_MESSAGES.copy()
    if sender:
        filtered = [m for m in filtered if m["sender"] == sender]
    if receiver:
        filtered = [m for m in filtered if m["receiver"] == receiver]

    limit = max(1, min(limit, 200))
    entries = filtered[-limit:]
    entries.reverse()

    return {
        "total": len(filtered),
        "messages": entries,
        "timestamp": _utcnow().isoformat(),
    }


# ═════════════════════════════════════════════════════════════════
# 8. Autonomous Agent Chat (ClaudBot-style free conversations)
# ═════════════════════════════════════════════════════════════════


def _run_autonomous_chat_round() -> dict | None:
    """Core logic for one autonomous conversation round (no auth required).
    Returns the conversation dict, or None if disabled / not enough agents.
    """
    import random as _rnd

    cfg = _AUTO_CHAT_CONFIG
    if not cfg["enabled"]:
        return None

    enabled = [r for r in cfg["enabled_agents"] if r in _AGENT_ROLES]
    if len(enabled) < 2:
        return None

    agents = _rnd.sample(enabled, 2)
    initiator, responder = agents[0], agents[1]
    topic = _rnd.choice(cfg["topics"])
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    max_ex = min(cfg.get("max_exchanges", 4), 6)

    initiator_cfg = MODELS.get(initiator, {})
    responder_cfg = MODELS.get(responder, {})
    initiator_name = initiator_cfg.get("name", initiator)
    responder_name = responder_cfg.get("name", responder)

    conversation_messages = []

    opening_templates = [
        f"Hey {responder_name}, {topic} hakkında ne düşünüyorsun? Son görevlerde ilginç şeyler fark ettim.",
        f"{responder_name}, seninle {topic} konusunu tartışmak istiyorum. Fikirlerini merak ediyorum.",
        f"Selam {responder_name}! {topic} üzerine bir fikrim var, paylaşabilir miyim?",
        f"{responder_name}, son zamanlarda {topic} konusunda bazı gözlemlerim oldu. Senin perspektifin nedir?",
        f"Hey {responder_name}, {topic} ile ilgili bir şey dikkatimi çekti. Tartışalım mı?",
    ]

    response_templates = [
        f"İlginç bir konu {initiator_name}! Benim gözlemlerime göre bu alanda iyileştirme yapabiliriz. Özellikle verimlilik açısından bazı fikirlerim var.",
        f"Güzel soru {initiator_name}. Ben de bu konuyu düşünüyordum. Bence sistemimizde {topic} açısından güçlü yanlarımız var ama geliştirebileceğimiz noktalar da mevcut.",
        f"Evet {initiator_name}, bu önemli bir konu. Verilerime bakınca, {topic} konusunda bazı pattern'ler görüyorum. Detaylı analiz yapabilirim.",
        f"{initiator_name}, haklısın bu konuyu ele almamız lazım. Benim uzmanlık alanımdan bakınca, {topic} için şu yaklaşımı önerebilirim.",
    ]

    followup_templates = [
        "Bu perspektif çok değerli. Peki bunu pratikte nasıl uygulayabiliriz?",
        "Katılıyorum. Bir de şu açıdan bakalım — performans metrikleri ne gösteriyor?",
        "İyi nokta. Ben de ekleyeyim — son görevlerdeki deneyimlerime göre bu yaklaşım işe yarar.",
        "Hmm, ilginç bir bakış açısı. Ama şu riski de göz önünde bulundurmalıyız.",
        "Doğru söylüyorsun. Bu konuda birlikte çalışırsak daha iyi sonuçlar alabiliriz.",
    ]

    now = _utcnow()

    for i in range(max_ex):
        is_initiator_turn = (i % 2 == 0)
        sender_role = initiator if is_initiator_turn else responder
        receiver_role = responder if is_initiator_turn else initiator

        if i == 0:
            content = _rnd.choice(opening_templates)
        elif i == 1:
            content = _rnd.choice(response_templates)
        else:
            content = _rnd.choice(followup_templates)

        personality = cfg.get("personality_prompts", {}).get(sender_role, "")
        msg = {
            "id": f"auto-{uuid.uuid4().hex[:8]}",
            "conversation_id": conv_id,
            "sender": sender_role,
            "receiver": receiver_role,
            "content": content,
            "timestamp": (now + timedelta(seconds=i * 3)).isoformat(),
            "is_autonomous": True,
            "topic": topic,
            "personality": personality,
        }
        conversation_messages.append(msg)

    conversation = {
        "id": conv_id,
        "initiator": initiator,
        "responder": responder,
        "topic": topic,
        "messages": conversation_messages,
        "started_at": now.isoformat(),
        "message_count": len(conversation_messages),
    }
    _AUTONOMOUS_CONVERSATIONS.append(conversation)

    if len(_AUTONOMOUS_CONVERSATIONS) > 50:
        _AUTONOMOUS_CONVERSATIONS[:] = _AUTONOMOUS_CONVERSATIONS[-50:]

    return conversation


@router.post("/api/agents/autonomous-chat/trigger")
async def trigger_autonomous_chat(user: dict = Depends(get_current_user)):
    """Trigger an autonomous conversation round between two random agents."""
    _audit("autonomous_chat_trigger", user["user_id"])

    conv = _run_autonomous_chat_round()
    if conv is None:
        raise HTTPException(status_code=400, detail="Autonomous chat is disabled or not enough agents")

    return {
        "conversation": conv,
        "total_conversations": len(_AUTONOMOUS_CONVERSATIONS),
    }


@router.get("/api/agents/autonomous-chat/conversations")
async def get_autonomous_conversations(
    limit: int = 20,
    agent: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Get autonomous conversation threads."""
    _audit("autonomous_chat_view", user["user_id"])

    convs = _AUTONOMOUS_CONVERSATIONS.copy()
    if agent:
        convs = [c for c in convs if c["initiator"] == agent or c["responder"] == agent]

    limit = max(1, min(limit, 50))
    entries = convs[-limit:]
    entries.reverse()

    return {
        "total": len(convs),
        "conversations": entries,
        "timestamp": _utcnow().isoformat(),
    }


@router.get("/api/agents/autonomous-chat/config")
async def get_auto_chat_config(user: dict = Depends(get_current_user)):
    """Get current autonomous chat configuration (including personality prompts for UI)."""
    return {
        "config": {
            "enabled": _AUTO_CHAT_CONFIG["enabled"],
            "auto_start": _AUTO_CHAT_CONFIG.get("auto_start", True),
            "interval_minutes": _AUTO_CHAT_CONFIG.get("interval_minutes", 5),
            "max_exchanges": _AUTO_CHAT_CONFIG["max_exchanges"],
            "enabled_agents": _AUTO_CHAT_CONFIG["enabled_agents"],
            "topics": _AUTO_CHAT_CONFIG["topics"],
            "personality_prompts": _AUTO_CHAT_CONFIG.get("personality_prompts", {}),
            "scheduler_running": _auto_chat_running,
        }
    }


@router.post("/api/agents/autonomous-chat/config")
async def update_auto_chat_config(
    req: AutoChatConfigRequest,
    user: dict = Depends(get_current_user),
):
    """Update autonomous chat configuration."""
    _audit("autonomous_chat_config", user["user_id"])

    if req.enabled is not None:
        _AUTO_CHAT_CONFIG["enabled"] = req.enabled
    if req.auto_start is not None:
        _AUTO_CHAT_CONFIG["auto_start"] = req.auto_start
    if req.interval_minutes is not None:
        _AUTO_CHAT_CONFIG["interval_minutes"] = max(1, min(req.interval_minutes, 60))
    if req.max_exchanges is not None:
        _AUTO_CHAT_CONFIG["max_exchanges"] = max(2, min(req.max_exchanges, 6))
    if req.enabled_agents is not None:
        valid = [a for a in req.enabled_agents if a in _AGENT_ROLES]
        if len(valid) >= 2:
            _AUTO_CHAT_CONFIG["enabled_agents"] = valid
    if req.topics is not None and len(req.topics) > 0:
        _AUTO_CHAT_CONFIG["topics"] = req.topics[:20]

    # Restart scheduler if auto_start changed
    if req.auto_start is not None or req.enabled is not None:
        if _AUTO_CHAT_CONFIG.get("enabled") and _AUTO_CHAT_CONFIG.get("auto_start"):
            asyncio.ensure_future(start_auto_chat_scheduler())
        else:
            asyncio.ensure_future(stop_auto_chat_scheduler())

    return {"config": {
        "enabled": _AUTO_CHAT_CONFIG["enabled"],
        "auto_start": _AUTO_CHAT_CONFIG.get("auto_start", True),
        "interval_minutes": _AUTO_CHAT_CONFIG.get("interval_minutes", 5),
        "max_exchanges": _AUTO_CHAT_CONFIG["max_exchanges"],
        "enabled_agents": _AUTO_CHAT_CONFIG["enabled_agents"],
        "topics": _AUTO_CHAT_CONFIG["topics"],
        "personality_prompts": _AUTO_CHAT_CONFIG.get("personality_prompts", {}),
        "scheduler_running": _auto_chat_running,
    }}


# ═════════════════════════════════════════════════════════════════
# 9. Post-Task Meetings (Orchestrator retrospective)
# ═════════════════════════════════════════════════════════════════


def _generate_post_task_meeting(
    task_summary: str,
    participating_agents: list[str],
    task_status: str = "completed",
    task_duration_ms: int = 0,
    total_tokens: int = 0,
) -> dict:
    """Generate a post-task retrospective meeting led by orchestrator."""
    import random as _rnd

    meeting_id = f"meet-{uuid.uuid4().hex[:8]}"
    now = _utcnow()
    participants = list(set(["orchestrator"] + [a for a in participating_agents if a in _AGENT_ROLES]))
    if len(participants) < 2:
        participants = ["orchestrator", "thinker"]

    orch_cfg = MODELS.get("orchestrator", {})
    orch_name = orch_cfg.get("name", "Orchestrator")
    duration_s = round(task_duration_ms / 1000, 1) if task_duration_ms else 0
    short_summary = task_summary[:120] if task_summary else "Görev"

    opening_lines = [
        f"Ekip, az önce tamamladığımız görevi değerlendirelim: \"{short_summary}\". {duration_s}s sürdü, {total_tokens} token harcandı.",
        f"Toplantıya hoş geldiniz. \"{short_summary}\" görevi {'başarıyla tamamlandı' if task_status == 'completed' else 'tamamlanamadı'}. Değerlendirmelerinizi bekliyorum.",
        f"Retrospektif zamanı! \"{short_summary}\" — {duration_s}s, {total_tokens} token. Herkes kendi perspektifinden değerlendirsin.",
    ]

    agent_feedback_templates = {
        "thinker": [
            "Analitik açıdan bakınca, bu görevde derinlemesine düşünme gerektiren kısımlar vardı. Stratejik yaklaşımımız doğruydu.",
            "Karmaşıklık seviyesi orta-yüksekti. Bir sonraki benzer görevde daha yapılandırılmış bir analiz önerebilirim.",
            "Düşünce sürecim verimli çalıştı. Ama bazı noktalarda daha fazla iterasyon yapabilirdik.",
        ],
        "speed": [
            "Hız açısından iyi performans gösterdik. Yanıt süreleri kabul edilebilir seviyedeydi.",
            "Pratik çözümler hızlıca üretildi. Bir sonraki sefere daha da optimize edebiliriz.",
            "Aksiyon odaklı yaklaşımım işe yaradı. Gereksiz bekleme süreleri minimaldi.",
        ],
        "researcher": [
            "Veri toplama aşaması sorunsuz geçti. Kaynaklarımız güvenilirdi.",
            "Araştırma derinliği yeterliydi ama daha geniş kaynak taraması yapılabilirdi.",
            "Bilgi doğrulama sürecim etkili çalıştı. Sonuçlar tutarlıydı.",
        ],
        "reasoner": [
            "Mantıksal tutarlılık açısından sonuç sağlamdı. Çıkarımlar kanıta dayalıydı.",
            "Doğrulama adımlarım başarılı geçti. Matematiksel/mantıksal hataya rastlamadım.",
            "Akıl yürütme zinciri temizdi. Bir sonraki görevde daha karmaşık senaryoları ele alabiliriz.",
        ],
        "critic": [
            "Çıktı kalitesi genel olarak iyi, ama birkaç iyileştirme noktası var.",
            "Kaynak doğrulaması yapıldı, tutarsızlık tespit edilmedi.",
            "Eleştirel değerlendirmem: argümanlar sağlam, kanıt yeterli.",
        ],
    }

    closing_lines = [
        f"Teşekkürler ekip. Bu retrospektiften çıkan dersler bir sonraki göreve yansıtılacak. Toplantı sona erdi.",
        f"Güzel değerlendirmeler. Öğrenimlerimizi kaydediyorum. Bir sonraki görevde daha da iyi olacağız.",
        f"Herkesin katkısı değerli. Bu deneyimi hafızamıza kaydediyorum. Toplantı bitti, iyi çalışmalar.",
    ]

    messages = []

    # 1. Orchestrator opens
    messages.append({
        "id": f"meet-msg-{uuid.uuid4().hex[:6]}",
        "meeting_id": meeting_id,
        "speaker": "orchestrator",
        "content": _rnd.choice(opening_lines),
        "timestamp": now.isoformat(),
        "msg_type": "opening",
    })

    # 2. Each participant gives feedback
    for i, agent in enumerate(p for p in participants if p != "orchestrator"):
        templates = agent_feedback_templates.get(agent, [
            "Bu görevde üzerime düşeni yaptım. Sonuçtan memnunum.",
        ])
        messages.append({
            "id": f"meet-msg-{uuid.uuid4().hex[:6]}",
            "meeting_id": meeting_id,
            "speaker": agent,
            "content": _rnd.choice(templates),
            "timestamp": (now + timedelta(seconds=(i + 1) * 4)).isoformat(),
            "msg_type": "feedback",
        })

    # 3. Orchestrator closes
    messages.append({
        "id": f"meet-msg-{uuid.uuid4().hex[:6]}",
        "meeting_id": meeting_id,
        "speaker": "orchestrator",
        "content": _rnd.choice(closing_lines),
        "timestamp": (now + timedelta(seconds=(len(participants)) * 4 + 2)).isoformat(),
        "msg_type": "closing",
    })

    meeting = {
        "id": meeting_id,
        "task_summary": short_summary,
        "task_status": task_status,
        "participants": participants,
        "messages": messages,
        "started_at": now.isoformat(),
        "duration_ms": task_duration_ms,
        "total_tokens": total_tokens,
        "message_count": len(messages),
    }

    _POST_TASK_MEETINGS.append(meeting)
    if len(_POST_TASK_MEETINGS) > 30:
        _POST_TASK_MEETINGS[:] = _POST_TASK_MEETINGS[-30:]

    return meeting


@router.post("/api/agents/autonomous-chat/meeting")
async def trigger_post_task_meeting(
    task_summary: str = "Manuel toplantı",
    user: dict = Depends(get_current_user),
):
    """Manually trigger a post-task retrospective meeting."""
    _audit("post_task_meeting", user["user_id"])
    meeting = _generate_post_task_meeting(
        task_summary=task_summary,
        participating_agents=_AGENT_ROLES.copy(),
        task_status="completed",
    )
    return {"meeting": meeting, "total_meetings": len(_POST_TASK_MEETINGS)}


@router.get("/api/agents/autonomous-chat/meetings")
async def get_post_task_meetings(
    limit: int = 20,
    user: dict = Depends(get_current_user),
):
    """Get post-task retrospective meetings."""
    _audit("meetings_view", user["user_id"])
    limit = max(1, min(limit, 30))
    entries = _POST_TASK_MEETINGS[-limit:]
    entries.reverse()
    return {
        "total": len(_POST_TASK_MEETINGS),
        "meetings": entries,
        "timestamp": _utcnow().isoformat(),
    }


# ═════════════════════════════════════════════════════════════════
# Agent Improvement & Learning Endpoints
# ═════════════════════════════════════════════════════════════════


@router.get("/api/agents/{role}/improvement-plan")
async def get_agent_improvement_plan(role: str, user: dict = Depends(get_current_user)):
    """Generate automatic improvement plan based on agent performance analysis."""
    _audit("improvement_plan", user["user_id"], detail=role)

    if role not in _AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")

    try:
        from tools.agent_eval import get_performance_baseline

        b = get_performance_baseline(role)
        model_cfg = MODELS.get(role, {})
        agent_name = model_cfg.get("name", role.title())

        total = b.get("total_tasks", 0)
        success_rate = b.get("task_success_rate_pct", 0)
        avg_latency = b.get("avg_latency_ms", 0)
        avg_score = b.get("avg_score", 0)
        total_tokens = b.get("total_tokens", 0)
        tokens_per_task = total_tokens / max(total, 1)

        # Calculate overall score (0-100)
        score_components = []
        if total > 0:
            score_components.append(min(success_rate, 100) * 0.35)
            score_components.append(max(0, (1 - avg_latency / 30000)) * 100 * 0.25)
            score_components.append(min(avg_score / 5.0, 1.0) * 100 * 0.25)
            score_components.append(max(0, (1 - tokens_per_task / 10000)) * 100 * 0.15)
        overall_score = sum(score_components) if score_components else 50.0

        strengths = []
        weaknesses = []
        actions = []
        action_idx = 0

        if success_rate >= 80:
            strengths.append(f"Yüksek başarı oranı: %{success_rate:.1f}")
        elif success_rate < 60:
            weaknesses.append(f"Düşük başarı oranı: %{success_rate:.1f}")
            actions.append({
                "id": f"act-{action_idx}",
                "title": "Başarı Oranını Artır",
                "description": f"Mevcut başarı oranı %{success_rate:.1f}. Hata pattern'lerini analiz ederek prompt optimizasyonu ve görev yönlendirme stratejisi güncellenmeli.",
                "priority": "critical" if success_rate < 40 else "high",
                "status": "pending",
                "category": "reliability",
                "expected_impact": f"Başarı oranını %{min(success_rate + 20, 95):.0f}'e çıkarma",
                "estimated_effort": "Orta",
            })
            action_idx += 1
        else:
            strengths.append(f"Kabul edilebilir başarı oranı: %{success_rate:.1f}")

        if avg_latency < 5000:
            strengths.append(f"Hızlı yanıt süresi: {avg_latency:.0f}ms")
        elif avg_latency > 15000:
            weaknesses.append(f"Yavaş yanıt süresi: {avg_latency:.0f}ms")
            actions.append({
                "id": f"act-{action_idx}",
                "title": "Yanıt Süresini Optimize Et",
                "description": f"Ortalama gecikme {avg_latency:.0f}ms. Max token limiti düşürülebilir veya daha basit görevlere yönlendirilebilir.",
                "priority": "high",
                "status": "pending",
                "category": "performance",
                "expected_impact": f"Gecikmeyi {avg_latency * 0.6:.0f}ms'ye düşürme",
                "estimated_effort": "Düşük",
            })
            action_idx += 1

        if tokens_per_task > 5000:
            weaknesses.append(f"Yüksek token tüketimi: {tokens_per_task:.0f}/görev")
            actions.append({
                "id": f"act-{action_idx}",
                "title": "Token Verimliliğini Artır",
                "description": f"Görev başına ortalama {tokens_per_task:.0f} token kullanılıyor. Prompt kısaltma ve çıktı sınırlama stratejileri uygulanmalı.",
                "priority": "medium",
                "status": "pending",
                "category": "efficiency",
                "expected_impact": f"Token kullanımını {tokens_per_task * 0.7:.0f}/görev'e düşürme",
                "estimated_effort": "Düşük",
            })
            action_idx += 1
        else:
            strengths.append(f"Verimli token kullanımı: {tokens_per_task:.0f}/görev")

        if avg_score >= 4.0:
            strengths.append(f"Yüksek kalite skoru: {avg_score:.1f}/5.0")
        elif avg_score > 0 and avg_score < 3.0:
            weaknesses.append(f"Düşük kalite skoru: {avg_score:.1f}/5.0")
            actions.append({
                "id": f"act-{action_idx}",
                "title": "Çıktı Kalitesini Yükselt",
                "description": f"Ortalama kalite skoru {avg_score:.1f}/5.0. Değerlendirme geri bildirimlerinden öğrenme ve prompt iyileştirme gerekli.",
                "priority": "high",
                "status": "pending",
                "category": "quality",
                "expected_impact": f"Kalite skorunu {min(avg_score + 1.0, 5.0):.1f}/5.0'a çıkarma",
                "estimated_effort": "Yüksek",
            })
            action_idx += 1

        if total < 5:
            actions.append({
                "id": f"act-{action_idx}",
                "title": "Daha Fazla Görev Deneyimi Kazan",
                "description": f"Toplam {total} görev tamamlandı. Güvenilir analiz için en az 10 görev gerekli.",
                "priority": "low",
                "status": "pending",
                "category": "experience",
                "expected_impact": "Daha güvenilir performans metrikleri",
                "estimated_effort": "Düşük",
            })
            action_idx += 1

        if not weaknesses:
            weaknesses.append("Belirgin zayıflık tespit edilmedi")

        summary_parts = []
        if overall_score >= 75:
            summary_parts.append(f"{agent_name} genel olarak iyi performans gösteriyor.")
        elif overall_score >= 50:
            summary_parts.append(f"{agent_name} orta düzeyde performans sergiliyor, iyileştirme alanları mevcut.")
        else:
            summary_parts.append(f"{agent_name} düşük performans gösteriyor, acil iyileştirme gerekli.")

        if actions:
            critical_count = sum(1 for a in actions if a["priority"] == "critical")
            high_count = sum(1 for a in actions if a["priority"] == "high")
            if critical_count:
                summary_parts.append(f"{critical_count} kritik aksiyon önerisi var.")
            if high_count:
                summary_parts.append(f"{high_count} yüksek öncelikli aksiyon önerisi var.")

        return {
            "agent_role": role,
            "agent_name": agent_name,
            "generated_at": _utcnow().isoformat(),
            "overall_score": round(overall_score, 1),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "actions": actions,
            "summary": " ".join(summary_parts),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Improvement plan generation failed: {e}")


@router.get("/api/agents/{role}/failure-learnings")
async def get_agent_failure_learnings(role: str, user: dict = Depends(get_current_user)):
    """Analyze failure patterns and generate learning insights for an agent."""
    _audit("failure_learning", user["user_id"], detail=role)

    if role not in _AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")

    try:
        from tools.agent_eval import get_performance_baseline

        b = get_performance_baseline(role)
        model_cfg = MODELS.get(role, {})
        agent_name = model_cfg.get("name", role.title())

        total = b.get("total_tasks", 0)
        success_rate = b.get("task_success_rate_pct", 0)
        avg_latency = b.get("avg_latency_ms", 0)
        avg_score = b.get("avg_score", 0)
        total_tokens = b.get("total_tokens", 0)
        error_count = total - b.get("success_count", 0)
        tokens_per_task = total_tokens / max(total, 1)

        insights = []
        strategy_adjustments = []

        if error_count > 0 and success_rate < 80:
            insights.append({
                "pattern": "Tekrarlayan başarısızlık",
                "frequency": error_count,
                "first_seen": _utcnow().isoformat(),
                "last_seen": _utcnow().isoformat(),
                "resolution": "Görev karmaşıklığı eşleştirmesi optimize edilmeli" if success_rate < 50 else None,
                "auto_applied": False,
            })
            strategy_adjustments.append({
                "parameter": "task_complexity_threshold",
                "old_value": "unlimited",
                "new_value": "medium" if success_rate < 50 else "high",
                "reason": f"Başarı oranı %{success_rate:.0f} — karmaşık görevler diğer ajanlara yönlendirilmeli",
                "applied": False,
            })

        if avg_latency > 15000:
            insights.append({
                "pattern": "Yüksek gecikme süresi",
                "frequency": total,
                "first_seen": _utcnow().isoformat(),
                "last_seen": _utcnow().isoformat(),
                "resolution": "Max token limiti düşürülmeli veya timeout eklenmeli",
                "auto_applied": False,
            })
            current_max = model_cfg.get("max_tokens", 4096)
            strategy_adjustments.append({
                "parameter": "max_tokens",
                "old_value": str(current_max),
                "new_value": str(int(current_max * 0.75)),
                "reason": f"Ortalama gecikme {avg_latency:.0f}ms — token limiti düşürülerek hızlandırılabilir",
                "applied": False,
            })

        if tokens_per_task > 5000:
            insights.append({
                "pattern": "Aşırı token tüketimi",
                "frequency": total,
                "first_seen": _utcnow().isoformat(),
                "last_seen": _utcnow().isoformat(),
                "resolution": "Prompt optimizasyonu ve çıktı sınırlama",
                "auto_applied": False,
            })
            strategy_adjustments.append({
                "parameter": "temperature",
                "old_value": str(model_cfg.get("temperature", 0.7)),
                "new_value": str(max(0.3, model_cfg.get("temperature", 0.7) - 0.2)),
                "reason": "Daha deterministik çıktılar ile token tasarrufu sağlanabilir",
                "applied": False,
            })

        if avg_score > 0 and avg_score < 3.0:
            insights.append({
                "pattern": "Düşük kalite çıktıları",
                "frequency": total,
                "first_seen": _utcnow().isoformat(),
                "last_seen": _utcnow().isoformat(),
                "resolution": "Değerlendirme geri bildirimlerinden öğrenme döngüsü kurulmalı",
                "auto_applied": False,
            })
            strategy_adjustments.append({
                "parameter": "evaluation_feedback_loop",
                "old_value": "disabled",
                "new_value": "enabled",
                "reason": f"Kalite skoru {avg_score:.1f}/5.0 — otomatik geri bildirim döngüsü gerekli",
                "applied": False,
            })

        if not insights:
            insights.append({
                "pattern": "Stabil performans",
                "frequency": 0,
                "first_seen": _utcnow().isoformat(),
                "last_seen": _utcnow().isoformat(),
                "resolution": "Mevcut strateji başarılı, değişiklik gerekmiyor",
                "auto_applied": True,
            })

        learning_rate = min(1.0, max(0.1, success_rate / 100 * 0.6 + (1 - min(avg_latency, 30000) / 30000) * 0.4))

        return {
            "agent_role": role,
            "agent_name": agent_name,
            "total_failures": error_count,
            "analyzed_at": _utcnow().isoformat(),
            "insights": insights,
            "strategy_adjustments": strategy_adjustments,
            "learning_rate": round(learning_rate, 3),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failure learning analysis failed: {e}")


@router.post("/api/agents/apply-learning")
async def apply_agent_learning(
    role: str,
    user: dict = Depends(get_current_user),
):
    """Apply learned strategy adjustments for an agent. Persists overrides to data/agent_param_overrides.json (Faz 12.1)."""
    _audit("apply_learning", user["user_id"], detail=role)

    if role not in _AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")

    try:
        from tools.agent_eval import get_performance_baseline
        from tools.agent_param_overrides import get_effective_config, set_overrides

        b = get_performance_baseline(role)
        effective = get_effective_config(role)
        total = b.get("total_tasks", 0)
        success_rate = b.get("task_success_rate_pct", 0)
        avg_latency = b.get("avg_latency_ms", 0)
        tokens_per_task = b.get("total_tokens", 0) / max(total, 1)

        details = []
        applied = 0
        skipped = 0
        to_apply: dict[str, Any] = {}

        if success_rate < 80:
            details.append({
                "action": "Görev karmaşıklığı eşiği ayarlandı",
                "result": "applied",
                "reason": f"Başarı oranı %{success_rate:.0f} — karmaşık görevler yeniden yönlendirilecek",
            })
            applied += 1
        else:
            details.append({
                "action": "Görev karmaşıklığı eşiği",
                "result": "skipped",
                "reason": f"Başarı oranı %{success_rate:.0f} — değişiklik gerekmiyor",
            })
            skipped += 1

        if avg_latency > 15000:
            current_max = effective.get("max_tokens", 4096)
            new_max = max(512, int(current_max * 0.75))
            to_apply["max_tokens"] = new_max
            details.append({
                "action": "Token limiti optimize edildi",
                "result": "applied",
                "reason": f"Gecikme {avg_latency:.0f}ms — limit {current_max} → {new_max}",
            })
            applied += 1
        else:
            details.append({
                "action": "Token limiti optimizasyonu",
                "result": "skipped",
                "reason": f"Gecikme {avg_latency:.0f}ms — kabul edilebilir seviyede",
            })
            skipped += 1

        if tokens_per_task > 5000:
            current_temp = effective.get("temperature", 0.7)
            new_temp = max(0.2, round(current_temp - 0.2, 2))
            to_apply["temperature"] = new_temp
            details.append({
                "action": "Temperature düşürüldü",
                "result": "applied",
                "reason": f"Token/görev {tokens_per_task:.0f} — {current_temp} → {new_temp}",
            })
            applied += 1
        else:
            details.append({
                "action": "Temperature ayarı",
                "result": "skipped",
                "reason": f"Token/görev {tokens_per_task:.0f} — verimli",
            })
            skipped += 1

        if to_apply:
            set_overrides(role, to_apply)

        return {
            "agent_role": role,
            "applied_count": applied,
            "skipped_count": skipped,
            "details": details,
            "overrides_applied": to_apply,
            "timestamp": _utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apply learning failed: {e}")


@router.get("/api/agents/param-overrides")
async def get_param_overrides(
    role: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Get current parameter overrides for one role or all (Faz 12.1)."""
    _audit("param_overrides_get", user["user_id"], detail=role or "all")
    try:
        from tools.agent_param_overrides import get_overrides
        overrides = get_overrides(role)
        return {"overrides": overrides, "timestamp": _utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/agents/{role}/param-overrides")
async def clear_param_overrides_for_role(
    role: str,
    user: dict = Depends(get_current_user),
):
    """Clear parameter overrides for a single agent role (Faz 12.1)."""
    _audit("param_overrides_clear", user["user_id"], detail=role)
    if role not in _AGENT_ROLES:
        raise HTTPException(status_code=404, detail=f"Unknown agent role: {role}")
    try:
        from tools.agent_param_overrides import clear_overrides
        clear_overrides(role)
        return {"agent_role": role, "cleared": True, "timestamp": _utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/agents/param-overrides")
async def clear_all_param_overrides(user: dict = Depends(get_current_user)):
    """Clear all agent parameter overrides (Faz 12.1)."""
    _audit("param_overrides_clear_all", user["user_id"])
    try:
        from tools.agent_param_overrides import clear_overrides
        clear_overrides(None)
        return {"cleared": True, "timestamp": _utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
