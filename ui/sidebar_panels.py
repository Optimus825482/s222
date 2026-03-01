"""
Sidebar panels for Teachability, Agent Evaluation, RAG, Dynamic Skills, and MCP management.
"""

from __future__ import annotations

import streamlit as st


def render_teachability_panel() -> None:
    """Show user teachings/preferences with ability to deactivate."""
    with st.expander("📚 Öğretiler & Tercihler", expanded=False):
        try:
            from tools.teachability import get_all_teachings, deactivate_teaching, save_teaching

            teachings = get_all_teachings(active_only=True)
            if not teachings:
                st.caption("Henüz öğreti yok. Sohbette tercihlerinizi belirtin.")
                return

            for t in teachings[:10]:
                col_text, col_btn = st.columns([5, 1])
                with col_text:
                    st.markdown(
                        f"<div style='font-size:11px;color:#94a3b8;'>"
                        f"<b>[{t['category']}]</b> {t['instruction'][:80]}"
                        f"<br><span style='color:#475569;'>Kullanım: {t['use_count']}x</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    if st.button("🗑️", key=f"del_teach_{t['id']}", help="Devre dışı bırak"):
                        deactivate_teaching(t["id"])
                        st.rerun()

            st.caption(f"Toplam: {len(teachings)} aktif öğreti")
        except Exception:
            st.caption("Teachability yüklenemedi.")


def render_agent_eval_panel() -> None:
    """Show agent performance scores."""
    with st.expander("📊 Agent Performansı", expanded=False):
        try:
            from tools.agent_eval import get_agent_stats

            stats = get_agent_stats()
            if not stats:
                st.caption("Henüz değerlendirme verisi yok.")
                return

            for s in stats:
                role = s["agent_role"]
                avg = s["avg_score"]
                total = s["total_tasks"]

                # Color based on score
                if avg >= 4.0:
                    color = "#10b981"
                elif avg >= 3.0:
                    color = "#f59e0b"
                else:
                    color = "#ef4444"

                st.markdown(
                    f"<div style='font-size:12px;margin-bottom:6px;'>"
                    f"<b style='color:{color};'>{role}</b> — "
                    f"⭐ {avg}/5.0 · {total} görev"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                st.progress(min(avg / 5.0, 1.0))

        except Exception:
            st.caption("Evaluation verisi yüklenemedi.")


def render_rag_panel() -> None:
    """RAG document management — upload and view ingested docs."""
    with st.expander("🗂️ Bilgi Tabanı (RAG)", expanded=False):
        try:
            from tools.rag import ingest_document, list_documents

            # Upload section
            uploaded = st.file_uploader(
                "Doküman yükle",
                type=["txt", "md", "csv", "json"],
                key="rag_upload",
                label_visibility="collapsed",
            )
            if uploaded:
                content = uploaded.read().decode("utf-8", errors="replace")
                result = ingest_document(
                    content=content,
                    title=uploaded.name,
                    source=f"upload:{uploaded.name}",
                )
                if result["success"]:
                    st.success(f"✅ {result['chunks']} chunk yüklendi")
                else:
                    st.error(f"Hata: {result.get('error', '?')}")

            # Document list
            docs = list_documents()
            if docs:
                st.caption(f"{len(docs)} doküman yüklü")
                for d in docs[:8]:
                    st.markdown(
                        f"<div style='font-size:11px;color:#94a3b8;'>"
                        f"📄 {d['title']} ({d['chunk_count']} chunk)"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("Henüz doküman yüklenmedi.")

        except Exception:
            st.caption("RAG modülü yüklenemedi.")


def render_dynamic_skills_panel() -> None:
    """Dynamic skill registry — view, create, import skills."""
    with st.expander("🧩 Skill Registry", expanded=False):
        try:
            from tools.dynamic_skills import (
                list_skills, create_skill, delete_skill,
                seed_builtin_skills, import_skills_from_file,
            )

            # Ensure builtins are seeded
            seed_builtin_skills()

            skills = list_skills(active_only=True)

            # Tabs: Browse / Create / Import
            tab_browse, tab_create = st.tabs(["📋 Listele", "➕ Oluştur"])

            with tab_browse:
                if not skills:
                    st.caption("Henüz skill yok.")
                else:
                    # Group by source
                    builtin = [s for s in skills if s["source"] == "builtin"]
                    custom = [s for s in skills if s["source"] != "builtin"]

                    if custom:
                        st.caption(f"🔧 Özel: {len(custom)}")
                        for s in custom[:10]:
                            col_t, col_d = st.columns([5, 1])
                            with col_t:
                                st.markdown(
                                    f"<div style='font-size:11px;color:#94a3b8;'>"
                                    f"<b style='color:#a78bfa;'>[{s['category']}]</b> {s['name']}"
                                    f"<br><span style='color:#475569;'>{s['description'][:60]}</span>"
                                    f"</div>",
                                    unsafe_allow_html=True,
                                )
                            with col_d:
                                if st.button("🗑️", key=f"del_skill_{s['id']}", help="Sil"):
                                    delete_skill(s["id"])
                                    st.rerun()

                    st.caption(f"📦 Yerleşik: {len(builtin)} · Toplam: {len(skills)}")

            with tab_create:
                with st.form("create_skill_form", clear_on_submit=True):
                    s_id = st.text_input("Skill ID", placeholder="my-custom-skill")
                    s_name = st.text_input("İsim", placeholder="Custom Analysis")
                    s_cat = st.selectbox("Kategori", ["custom", "coding", "research", "analysis", "writing", "security", "finance", "database"])
                    s_desc = st.text_input("Açıklama", placeholder="Ne işe yarar?")
                    s_knowledge = st.text_area("Bilgi / Protokol", height=120, placeholder="PROTOCOL:\n1. Step one\n2. Step two...")
                    s_keywords = st.text_input("Anahtar kelimeler (virgülle)", placeholder="api, test, debug")

                    if st.form_submit_button("✅ Oluştur"):
                        if s_id and s_name and s_knowledge:
                            kw_list = [k.strip() for k in s_keywords.split(",") if k.strip()] if s_keywords else []
                            create_skill(
                                skill_id=s_id,
                                name=s_name,
                                description=s_desc or s_name,
                                knowledge=s_knowledge,
                                category=s_cat,
                                keywords=kw_list,
                                source="user",
                            )
                            st.success(f"✅ Skill oluşturuldu: {s_name}")
                            st.rerun()
                        else:
                            st.warning("ID, İsim ve Bilgi alanları zorunlu.")

        except Exception:
            st.caption("Dynamic Skills yüklenemedi.")


def render_mcp_panel() -> None:
    """MCP server management — register, discover tools, view history."""
    with st.expander("🔌 MCP Sunucuları", expanded=False):
        try:
            from tools.mcp_client import (
                list_servers, register_server, remove_server,
                list_discovered_tools, get_call_history,
            )

            servers = list_servers(active_only=True)

            tab_servers, tab_add = st.tabs(["📡 Sunucular", "➕ Ekle"])

            with tab_servers:
                if not servers:
                    st.caption("Henüz MCP sunucusu kayıtlı değil.")
                else:
                    for srv in servers:
                        col_info, col_del = st.columns([5, 1])
                        with col_info:
                            tools = list_discovered_tools(srv["id"])
                            tool_count = len(tools)
                            st.markdown(
                                f"<div style='font-size:11px;color:#94a3b8;'>"
                                f"<b style='color:#10b981;'>🟢 {srv['name']}</b>"
                                f"<br><span style='color:#475569;'>"
                                f"{srv['command']} · {tool_count} tool</span>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                        with col_del:
                            if st.button("🗑️", key=f"del_mcp_{srv['id']}", help="Kaldır"):
                                remove_server(srv["id"])
                                st.rerun()

                # Recent call history
                history = get_call_history(limit=5)
                if history:
                    st.caption("Son çağrılar:")
                    for h in history:
                        status = "✅" if h["success"] else "❌"
                        st.markdown(
                            f"<div style='font-size:10px;color:#475569;'>"
                            f"{status} {h['server_id']}:{h['tool_name']} "
                            f"({h['latency_ms']:.0f}ms)"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

            with tab_add:
                with st.form("add_mcp_form", clear_on_submit=True):
                    m_id = st.text_input("Server ID", placeholder="github")
                    m_name = st.text_input("İsim", placeholder="GitHub MCP")
                    m_cmd = st.text_input("Komut", placeholder="uvx")
                    m_args = st.text_input("Argümanlar (virgülle)", placeholder="mcp-server-github@latest")
                    m_desc = st.text_input("Açıklama", placeholder="GitHub API erişimi")

                    if st.form_submit_button("✅ Kaydet"):
                        if m_id and m_cmd:
                            args_list = [a.strip() for a in m_args.split(",") if a.strip()] if m_args else []
                            register_server(
                                server_id=m_id,
                                name=m_name or m_id,
                                command=m_cmd,
                                args=args_list,
                                description=m_desc or "",
                            )
                            st.success(f"✅ MCP sunucusu eklendi: {m_name or m_id}")
                            st.rerun()
                        else:
                            st.warning("Server ID ve Komut zorunlu.")

        except Exception:
            st.caption("MCP modülü yüklenemedi.")
