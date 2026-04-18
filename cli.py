#!/usr/bin/env python
"""
cli.py
Command-line interface for the AI Job Application Agent.

Usage:
    python cli.py --url "https://greenhouse.io/jobs/123" --profile sample_profile.json
    python cli.py --jd job_description.txt --profile sample_profile.json
    python cli.py --demo   # Run with built-in sample data
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

load_dotenv()
console = Console()


# ─────────────────────────────────────────────
# Sample profile for --demo mode
# ─────────────────────────────────────────────

DEMO_PROFILE = {
    "name": "Jordan Lee",
    "email": "jordan@example.com",
    "phone": "+1 (555) 123-4567",
    "location": "Austin, TX",
    "linkedin": "linkedin.com/in/jordanlee",
    "github": "github.com/jordanlee",
    "summary": (
        "Full-stack engineer with 5 years of experience building web applications "
        "and APIs. Proficient in Python, TypeScript, and cloud infrastructure. "
        "Passionate about developer experience and clean system design."
    ),
    "skills": [
        "Python", "TypeScript", "React", "FastAPI", "PostgreSQL",
        "Redis", "Docker", "AWS", "GitHub Actions", "GraphQL"
    ],
    "experience": [
        {
            "title": "Software Engineer",
            "company": "DataFlow Inc",
            "start_date": "Mar 2021",
            "end_date": "Present",
            "bullets": [
                "Built REST and GraphQL APIs serving 25K daily active users using Python and FastAPI",
                "Reduced page load time by 45% through lazy loading and CDN optimization in React",
                "Designed and implemented PostgreSQL schema for multi-tenant SaaS platform",
                "Set up CI/CD pipeline with GitHub Actions reducing deploy time from 45 min to 8 min",
                "Mentored 2 junior developers through weekly code reviews and pair programming",
            ]
        },
        {
            "title": "Junior Developer",
            "company": "Agency Web",
            "start_date": "Jun 2019",
            "end_date": "Feb 2021",
            "bullets": [
                "Developed client websites and web apps using React and Node.js",
                "Integrated third-party APIs (Stripe, Twilio, SendGrid) for 8 client projects",
                "Maintained and optimized MySQL databases for e-commerce platforms",
            ]
        }
    ],
    "education": [
        {
            "degree": "B.S. Computer Science",
            "institution": "UT Austin",
            "year": "2019",
            "gpa": "3.7"
        }
    ],
    "certifications": ["AWS Cloud Practitioner"],
}

DEMO_JOB_DESCRIPTION = """
Senior Full-Stack Engineer — Vercel (Remote)

About Vercel:
Vercel is the platform for frontend developers, providing the speed and reliability
innovators need to create at the moment of inspiration. We're the company behind Next.js.

About the Role:
We're looking for a Senior Full-Stack Engineer to join our Developer Experience team.
You'll be building tools and features that help millions of developers deploy faster.

What You'll Do:
- Design and build APIs and backend services that power Vercel's platform
- Collaborate with frontend teams to deliver exceptional developer experiences
- Write clean, testable TypeScript/Python code at scale
- Contribute to Next.js and open-source projects
- Participate in on-call rotations and incident response

What We're Looking For:
- 4+ years of software engineering experience
- Strong proficiency in TypeScript and Python
- Experience with React and modern frontend frameworks
- Solid understanding of distributed systems and APIs (REST, GraphQL)
- PostgreSQL or similar relational database experience
- Experience with Docker and cloud platforms (AWS, GCP, or Vercel)
- Strong communication skills; comfort working in a remote-first environment

Nice to Have:
- Experience with Next.js or other React frameworks
- Open-source contributions
- Experience with CDNs, edge computing, or serverless platforms
- Redis, Kafka, or message queue experience

Compensation: $160K - $210K + equity
Location: Remote (US or Europe)
"""


# ─────────────────────────────────────────────
# Main CLI logic
# ─────────────────────────────────────────────

async def run_pipeline(job_input: str, is_url: bool, profile: dict, opts: dict) -> None:
    from app.orchestrator import Orchestrator
    from app.models.schemas import PipelineRequest, CandidateProfile, ExperienceEntry, EducationEntry

    # Build candidate profile
    experience = [
        ExperienceEntry(**exp) for exp in profile.get("experience", [])
    ]
    education = [
        EducationEntry(**edu) for edu in profile.get("education", [])
    ]

    candidate = CandidateProfile(
        name=profile["name"],
        email=profile["email"],
        phone=profile.get("phone"),
        location=profile.get("location"),
        linkedin=profile.get("linkedin"),
        github=profile.get("github"),
        summary=profile["summary"],
        skills=profile.get("skills", []),
        experience=experience,
        education=education,
        certifications=profile.get("certifications", []),
    )

    request = PipelineRequest(
        job_url=job_input if is_url else None,
        job_description_text=None if is_url else job_input,
        candidate_profile=candidate,
        enable_critic_loop=opts.get("critic", True),
        generate_email=True,
    )

    orchestrator = Orchestrator()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running agent pipeline...", total=None)

        steps = [
            "🔍 Scraping & analyzing job...",
            "🧠 Matching your profile...",
            "📝 Writing tailored resume...",
            "✉️  Crafting cover letter...",
            "🔁 Running critic review..." if opts.get("critic") else "⏭️  Skipping critic...",
            "📧 Drafting email...",
        ]

        for step in steps:
            progress.update(task, description=step)
            await asyncio.sleep(0.5)

        result = await orchestrator.run(request)

    # ── Print results ──────────────────────────────────────────────────────

    console.print()

    # Header
    console.print(Panel(
        f"[bold green]✓ Application Package Ready[/bold green]\n"
        f"Application ID: [cyan]{result.application_id}[/cyan]\n"
        f"Generated in [yellow]{result.total_processing_time_seconds:.1f}s[/yellow]",
        title="AI Job Application Agent",
        border_style="green"
    ))

    # Match score table
    table = Table(title="📊 Profile Match", show_header=True)
    table.add_column("Dimension", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Status")

    pm = result.profile_match
    for dim, score in [
        ("Overall Match", pm.overall_score),
        ("Skill Match", pm.skill_match_score),
        ("Experience Match", pm.experience_match_score),
        ("Education Match", pm.education_match_score),
    ]:
        color = "green" if score >= 70 else "yellow" if score >= 50 else "red"
        bar = "█" * (score // 10) + "░" * (10 - score // 10)
        table.add_row(dim, f"[{color}]{score}%[/{color}]", f"[{color}]{bar}[/{color}]")

    console.print(table)
    console.print(f"\nRecommendation: [bold]{pm.recommendation.upper()}[/bold]")
    console.print(f"Strengths: {pm.strengths_summary}")
    if pm.missing_skills:
        console.print(f"[yellow]Skill gaps:[/yellow] {', '.join(pm.missing_skills)}")

    # ATS score
    resume = result.tailored_resume
    console.print(f"\n[bold]Resume ATS Score:[/bold] {resume.ats_score_estimate}%")
    console.print(f"Keywords covered: {len(resume.keywords_included)}/{len(resume.keywords_included) + len(resume.keywords_missing)}")

    # Critic scores
    if result.resume_critique:
        console.print(f"[bold]Resume Critic Score:[/bold] {result.resume_critique.score}/10")
    if result.cover_letter_critique:
        console.print(f"[bold]Cover Letter Critic Score:[/bold] {result.cover_letter_critique.score}/10")

    # Output files
    output_dir = Path(os.getenv("DATA_DIR", "./data")) / "applications"
    console.print(f"\n[bold]📁 Output files saved to:[/bold] {output_dir}")
    if resume.docx_path:
        console.print(f"  Resume: [cyan]{Path(resume.docx_path).name}[/cyan]")
    if result.cover_letter.docx_path:
        console.print(f"  Cover letter: [cyan]{Path(result.cover_letter.docx_path).name}[/cyan]")

    # Show resume preview
    if opts.get("show_resume"):
        console.print("\n" + "─" * 60)
        console.print(Markdown(resume.markdown_content))

    # Show cover letter preview
    if opts.get("show_cover_letter"):
        console.print("\n" + "─" * 60)
        console.print(Markdown(result.cover_letter.markdown_content))

    # Show email
    if result.application_email:
        console.print("\n[bold]📧 Email Draft:[/bold]")
        console.print(f"Subject: {result.application_email.subject}")
        console.print(result.application_email.body)

    # Errors/warnings
    if result.errors:
        console.print(f"\n[yellow]⚠️  Warnings:[/yellow]")
        for err in result.errors:
            console.print(f"  • {err}")


def main():
    parser = argparse.ArgumentParser(
        description="AI Job Application Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py --demo
  python cli.py --url "https://greenhouse.io/jobs/123" --profile my_profile.json
  python cli.py --jd job.txt --profile my_profile.json --show-resume
        """
    )
    parser.add_argument("--demo", action="store_true", help="Run with built-in sample data")
    parser.add_argument("--url", type=str, help="Job posting URL to scrape")
    parser.add_argument("--jd", type=str, help="Path to job description text file")
    parser.add_argument("--profile", type=str, help="Path to candidate profile JSON file")
    parser.add_argument("--no-critic", action="store_true", help="Disable critic loop")
    parser.add_argument("--show-resume", action="store_true", help="Print resume to terminal")
    parser.add_argument("--show-cover-letter", action="store_true", help="Print cover letter to terminal")

    args = parser.parse_args()

    if not args.demo and not (args.url or args.jd):
        parser.error("Provide --demo, --url, or --jd")

    if not args.demo and not args.profile:
        parser.error("Provide --profile (JSON file) or use --demo")

    # Load inputs
    if args.demo:
        profile = DEMO_PROFILE
        job_input = DEMO_JOB_DESCRIPTION
        is_url = False
        console.print("[bold cyan]🎯 Demo mode — using built-in sample data[/bold cyan]\n")
    else:
        with open(args.profile) as f:
            profile = json.load(f)

        if args.url:
            job_input = args.url
            is_url = True
        else:
            with open(args.jd) as f:
                job_input = f.read()
            is_url = False

    opts = {
        "critic": not args.no_critic,
        "show_resume": args.show_resume,
        "show_cover_letter": args.show_cover_letter,
    }

    asyncio.run(run_pipeline(job_input, is_url, profile, opts))


if __name__ == "__main__":
    main()
