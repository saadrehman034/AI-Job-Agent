"""
ui/streamlit_app.py
Streamlit frontend for the AI Job Application Agent.

Features:
- Upload resume (PDF/DOCX/TXT) or paste text
- Input job URL or paste job description
- Live progress tracking through agent pipeline
- View + download: resume, cover letter, email draft
- Match score visualization
- Application history
"""
import json
import os
import time
from pathlib import Path

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="AI Job Application Agent",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .score-big {
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
    }
    .score-green { color: #22c55e; }
    .score-amber { color: #f59e0b; }
    .score-red   { color: #ef4444; }
    .tag {
        display: inline-block;
        background: #e0e7ff;
        color: #3730a3;
        border-radius: 9999px;
        padding: 2px 12px;
        font-size: 0.75rem;
        margin: 2px;
    }
    .tag-missing {
        background: #fee2e2;
        color: #991b1b;
    }
    .section-card {
        background: #f8fafc;
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    .stProgress > div > div { background: #667eea; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    enable_critic = st.toggle("Enable Critic Loop", value=True, help="Agents review each other's output")
    generate_email = st.toggle("Generate Email Draft", value=True)
    st.divider()
    st.markdown("### 📊 Past Applications")

    if st.button("View History", use_container_width=True):
        try:
            resp = httpx.get(f"{API_BASE}/api/v1/applications", timeout=5)
            if resp.status_code == 200:
                apps = resp.json().get("data", [])
                if apps:
                    for app in apps[:5]:
                        score = app.get("match_score", "?")
                        score_color = "green" if score >= 70 else "orange" if score >= 50 else "red"
                        st.markdown(
                            f"**{app['job_title']}** @ {app['company_name']}  \n"
                            f"Score: :{score_color}[{score}%] · Status: {app['status']}"
                        )
                else:
                    st.info("No applications yet")
        except Exception:
            st.warning("API not reachable")

    st.divider()
    st.markdown("### 📝 Feedback")
    app_id_fb = st.text_input("Application ID")
    outcome_fb = st.selectbox("Outcome", ["interview", "offer", "rejected", "no_response"])
    if st.button("Submit Feedback", use_container_width=True):
        if app_id_fb:
            try:
                r = httpx.post(f"{API_BASE}/api/v1/feedback", json={
                    "application_id": app_id_fb,
                    "outcome": outcome_fb
                }, timeout=5)
                if r.status_code == 200:
                    st.success("✓ Feedback recorded")
                else:
                    st.error("Failed to submit feedback")
            except Exception:
                st.warning("API not reachable")
        else:
            st.warning("Enter an Application ID")


# ─────────────────────────────────────────────
# Main content
# ─────────────────────────────────────────────

st.markdown('<p class="main-header">💼 AI Job Application Agent</p>', unsafe_allow_html=True)
st.markdown("*Autonomous resume tailoring, cover letter generation, and application assistance*")
st.divider()

col1, col2 = st.columns([1, 1], gap="large")

# ── Left column: Inputs ────────────────────────────────────────────────────

with col1:
    st.markdown("### 📄 Your Profile")

    # Candidate basic info
    with st.expander("Personal Information", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Full Name *", placeholder="Jane Smith")
            email = st.text_input("Email *", placeholder="jane@email.com")
            phone = st.text_input("Phone", placeholder="+1 (555) 000-0000")
        with c2:
            location = st.text_input("Location", placeholder="San Francisco, CA")
            linkedin = st.text_input("LinkedIn", placeholder="linkedin.com/in/jane")
            github = st.text_input("GitHub", placeholder="github.com/jane")

    with st.expander("Professional Summary", expanded=True):
        summary = st.text_area(
            "Summary",
            placeholder="Senior software engineer with 6 years of experience building scalable systems...",
            height=80
        )
        skills_input = st.text_area(
            "Skills (comma-separated)",
            placeholder="Python, FastAPI, PostgreSQL, Docker, AWS, React...",
            height=60
        )

    with st.expander("Work Experience", expanded=True):
        st.info("Add your most recent 2-3 positions")
        num_jobs = st.number_input("Number of positions", 1, 5, 2)
        experience_list = []
        for i in range(num_jobs):
            st.markdown(f"**Position {i+1}**")
            c1, c2 = st.columns(2)
            with c1:
                title = st.text_input(f"Title", key=f"title_{i}", placeholder="Senior Engineer")
                company = st.text_input(f"Company", key=f"company_{i}", placeholder="Acme Corp")
            with c2:
                start = st.text_input(f"Start", key=f"start_{i}", placeholder="Jan 2022")
                end = st.text_input(f"End", key=f"end_{i}", placeholder="Present")
            bullets = st.text_area(
                f"Achievements (one per line)",
                key=f"bullets_{i}",
                placeholder="• Built microservices handling 10K req/s\n• Led team of 5 engineers",
                height=80
            )
            if title and company:
                experience_list.append({
                    "title": title, "company": company,
                    "start_date": start or "2022", "end_date": end or "Present",
                    "bullets": [b.strip().lstrip("•- ") for b in bullets.split("\n") if b.strip()]
                })

    with st.expander("Education"):
        degree = st.text_input("Degree", placeholder="B.S. Computer Science")
        institution = st.text_input("Institution", placeholder="MIT")
        grad_year = st.text_input("Year", placeholder="2018")

# ── Right column: Job + Generate ──────────────────────────────────────────────

with col2:
    st.markdown("### 🎯 Target Job")

    job_input_method = st.radio(
        "How to provide job description",
        ["🔗 Job URL", "📋 Paste Text"],
        horizontal=True
    )

    job_url = None
    job_text = None

    if job_input_method == "🔗 Job URL":
        job_url = st.text_input(
            "Job Posting URL",
            placeholder="https://boards.greenhouse.io/company/jobs/123456"
        )
        st.caption("Supports: Greenhouse, Lever, LinkedIn, Indeed, Workday, and more")
    else:
        job_text = st.text_area(
            "Paste Job Description",
            placeholder="Paste the full job description here...",
            height=200
        )

    st.markdown("---")

    # Validate inputs
    can_generate = (
        name and email and summary and
        (job_url or job_text) and
        len(experience_list) > 0
    )

    if not can_generate:
        missing = []
        if not name: missing.append("Name")
        if not email: missing.append("Email")
        if not summary: missing.append("Summary")
        if not (job_url or job_text): missing.append("Job URL or description")
        if not experience_list: missing.append("At least one work experience")
        st.warning(f"Complete these fields to continue: {', '.join(missing)}")

    generate_btn = st.button(
        "🚀 Generate Application",
        disabled=not can_generate,
        use_container_width=True,
        type="primary"
    )


# ─────────────────────────────────────────────
# Pipeline execution
# ─────────────────────────────────────────────

if generate_btn and can_generate:
    st.divider()
    st.markdown("## ⚡ Generating Your Application Package")

    progress_bar = st.progress(0)
    status_text = st.empty()

    steps = [
        ("🔍 Analyzing job posting...", 15),
        ("🔗 Matching your profile...", 35),
        ("📝 Writing tailored resume...", 60),
        ("✉️ Crafting cover letter...", 80),
        ("🔁 Running critic review...", 90) if enable_critic else ("⏭️ Skipping critic loop...", 90),
        ("📧 Drafting application email...", 98),
    ]

    for step_text, progress_val in steps:
        status_text.markdown(f"**{step_text}**")
        progress_bar.progress(progress_val)
        time.sleep(0.3)  # Visual feedback

    # Build request payload
    payload = {
        "job_url": job_url,
        "job_description_text": job_text,
        "enable_critic_loop": enable_critic,
        "generate_email": generate_email,
        "candidate_profile": {
            "name": name,
            "email": email,
            "phone": phone or None,
            "location": location or None,
            "linkedin": linkedin or None,
            "github": github or None,
            "summary": summary,
            "skills": [s.strip() for s in skills_input.split(",") if s.strip()],
            "experience": experience_list,
            "education": [
                {
                    "degree": degree or "B.S.",
                    "institution": institution or "University",
                    "year": grad_year or "2020"
                }
            ] if degree else [],
            "certifications": [],
            "raw_resume_text": summary,
        }
    }

    try:
        with st.spinner("Calling AI agents..."):
            resp = httpx.post(
                f"{API_BASE}/api/v1/analyze",
                json=payload,
                timeout=180  # 3 min for full pipeline
            )
            resp.raise_for_status()
            result = resp.json()

        progress_bar.progress(100)
        status_text.markdown("**✅ Done! Your application package is ready.**")

    except httpx.ConnectError:
        st.error(
            "⚠️ Cannot connect to the API server. "
            "Make sure the FastAPI backend is running: `uvicorn app.main:app --reload`"
        )
        st.stop()
    except httpx.TimeoutException:
        st.error("⏱️ Request timed out. The pipeline is running — try again in a moment.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Pipeline error: {e}")
        st.stop()

    # ── Results ─────────────────────────────────────────────────────────────

    st.divider()
    st.markdown("## 📦 Your Application Package")

    app_id = result.get("application_id", "N/A")
    st.caption(f"Application ID: `{app_id}` — save this for feedback submission")

    # ── Match Score ────────────────────────────────────────────────────────
    match = result.get("profile_match", {})
    overall = match.get("overall_score", 0)
    score_class = "score-green" if overall >= 70 else "score-amber" if overall >= 50 else "score-red"

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Match Score", "📄 Resume", "✉️ Cover Letter", "📧 Email Draft", "🔍 Job Analysis"
    ])

    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="score-big {score_class}">{overall}%</div>', unsafe_allow_html=True)
            st.markdown("<div style='text-align:center;color:gray'>Overall Match</div>", unsafe_allow_html=True)
        with c2:
            s = match.get("skill_match_score", 0)
            st.metric("Skill Match", f"{s}%", delta=None)
            st.progress(s / 100)
        with c3:
            s = match.get("experience_match_score", 0)
            st.metric("Experience Match", f"{s}%")
            st.progress(s / 100)
        with c4:
            s = match.get("education_match_score", 0)
            st.metric("Education Match", f"{s}%")
            st.progress(s / 100)

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**✅ Matched Skills**")
            matched = match.get("matched_skills", [])
            st.markdown(" ".join(f'<span class="tag">{s}</span>' for s in matched), unsafe_allow_html=True)

            st.markdown("**💪 Transferable Skills**")
            transfer = match.get("transferable_skills", [])
            st.markdown(" ".join(f'<span class="tag">{s}</span>' for s in transfer), unsafe_allow_html=True)

        with c2:
            st.markdown("**❌ Skill Gaps**")
            missing = match.get("missing_skills", [])
            if missing:
                st.markdown(" ".join(f'<span class="tag tag-missing">{s}</span>' for s in missing), unsafe_allow_html=True)
            else:
                st.success("No significant gaps identified!")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Strengths for this role:**")
            st.info(match.get("strengths_summary", ""))
        with c2:
            st.markdown("**Gap analysis:**")
            st.warning(match.get("gaps_summary", ""))

        rec = match.get("recommendation", "apply")
        if rec == "apply":
            st.success(f"🎯 Recommendation: **Apply** — You're a strong candidate!")
        elif rec == "apply-with-note":
            st.warning(f"📌 Recommendation: **Apply with caveats** — Address skill gaps in cover letter")
        else:
            st.error(f"⛔ Recommendation: **Skip** — Significant mismatch")

    with tab2:
        resume = result.get("tailored_resume", {})
        resume_md = resume.get("markdown_content", "")
        ats_score = resume.get("ats_score_estimate", 0)

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("ATS Score Estimate", f"{ats_score}%")
        col_b.metric("Keywords Included", len(resume.get("keywords_included", [])))
        col_c.metric("Keywords Missing", len(resume.get("keywords_missing", [])))

        if resume.get("keywords_missing"):
            st.caption("Missing keywords: " + ", ".join(resume["keywords_missing"][:8]))

        # Critic feedback
        if result.get("resume_critique"):
            critique = result["resume_critique"]
            with st.expander(f"🔁 Critic Review — Score: {critique['score']}/10"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Strengths**")
                    for s in critique.get("strengths", []):
                        st.markdown(f"✓ {s}")
                with c2:
                    st.markdown("**Suggestions**")
                    for s in critique.get("suggestions", []):
                        st.markdown(f"→ {s}")

        st.markdown("---")
        st.markdown(resume_md)

        # Edit mode
        if st.checkbox("✏️ Edit resume"):
            edited_resume = st.text_area("Edit resume (Markdown)", value=resume_md, height=400, key="edit_resume")
            if st.button("Save edits"):
                st.session_state["final_resume"] = edited_resume
                st.success("✓ Saved to session")

        if resume.get("docx_path"):
            fname = Path(resume["docx_path"]).name
            st.markdown(f"📥 [Download Resume DOCX]({API_BASE}/api/v1/download/{fname})")

    with tab3:
        cl = result.get("cover_letter", {})
        cl_md = cl.get("markdown_content", "")

        col_a, col_b = st.columns(2)
        col_a.metric("Word Count", cl.get("word_count", 0))
        col_b.metric("Tone", cl.get("tone", "").title())

        if result.get("cover_letter_critique"):
            critique = result["cover_letter_critique"]
            with st.expander(f"🔁 Critic Review — Score: {critique['score']}/10"):
                for s in critique.get("suggestions", []):
                    st.markdown(f"→ {s}")

        st.markdown("---")
        st.markdown(cl_md)

        if st.checkbox("✏️ Edit cover letter"):
            edited_cl = st.text_area("Edit cover letter (Markdown)", value=cl_md, height=300, key="edit_cl")

        if cl.get("docx_path"):
            fname = Path(cl["docx_path"]).name
            st.markdown(f"📥 [Download Cover Letter DOCX]({API_BASE}/api/v1/download/{fname})")

    with tab4:
        email_draft = result.get("application_email")
        if email_draft:
            st.markdown(f"**Subject:** `{email_draft['subject']}`")
            st.divider()
            st.markdown(email_draft["body"])
            st.caption(f"*{email_draft['attachments_note']}*")

            # Copy button
            if st.button("📋 Copy email to clipboard"):
                st.code(f"Subject: {email_draft['subject']}\n\n{email_draft['body']}")
        else:
            st.info("Email generation was disabled or failed.")

    with tab5:
        job_analysis = result.get("job_analysis", {})
        st.markdown(f"## {job_analysis.get('job_title', 'Unknown Role')}")
        st.markdown(f"**Company:** {job_analysis.get('company_name', '')}")
        st.markdown(f"**Level:** {job_analysis.get('experience_level', '').title()}")
        st.markdown(f"**Experience:** {job_analysis.get('experience_years', 'Not specified')}")
        st.markdown(f"**Remote Policy:** {job_analysis.get('remote_policy', 'Unknown').title()}")
        if job_analysis.get("salary_range"):
            st.markdown(f"**Salary:** {job_analysis['salary_range']}")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Required Skills**")
            for s in job_analysis.get("required_skills", []):
                st.markdown(f"• {s}")
            st.markdown("**Tech Stack**")
            for s in job_analysis.get("tech_stack", []):
                st.markdown(f"• {s}")

        with c2:
            st.markdown("**ATS Keywords**")
            kws = job_analysis.get("keywords", [])
            st.markdown(" ".join(f'<span class="tag">{k}</span>' for k in kws[:15]), unsafe_allow_html=True)

            st.markdown("**Hidden Expectations**")
            for h in job_analysis.get("hidden_expectations", []):
                st.markdown(f"⚡ {h}")

        st.markdown("---")
        processing_time = result.get("total_processing_time_seconds", 0)
        st.caption(f"⏱️ Generated in {processing_time:.1f}s · Application ID: `{app_id}`")

        if result.get("errors"):
            with st.expander("⚠️ Warnings"):
                for e in result["errors"]:
                    st.warning(e)
