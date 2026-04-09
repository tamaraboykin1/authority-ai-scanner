"""Generate client-facing AI Visibility Report HTML."""


def generate_report_html(scan_data: dict, results: dict, full_report: bool = False, scan_id: str = "") -> str:
    """Generate a polished client-facing report.

    If full_report=False (default), shows only first 3 issues across all categories
    and blurs the rest with a paywall ($99 unlock or book a free call).
    If full_report=True, shows everything.
    """
    business_name = results.get("business_name", "Your Business")
    overall_score = results.get("overall_score", 0)
    grade = results.get("grade", "N/A")
    categories = results.get("categories", [])
    ai_rec = results.get("ai_recommendation", {})
    website_url = results.get("website_url", "")

    # Calculate projected score (always show improvement potential)
    projected_score = min(95, overall_score + 35 + (95 - overall_score) // 3)

    # Score color
    if overall_score >= 80:
        score_color = "#22c55e"
        status_text = "Good"
    elif overall_score >= 60:
        score_color = "#f59e0b"
        status_text = "Needs Improvement"
    elif overall_score >= 40:
        score_color = "#f97316"
        status_text = "At Risk"
    else:
        score_color = "#ef4444"
        status_text = "Critical"

    # Count total issues
    total_issues = sum(len(c.get("issues", [])) for c in categories)
    critical_issues = sum(1 for c in categories for i in c.get("issues", []) if i.get("impact") in ("critical", "high"))

    # How many free issues to show total across all categories
    MAX_FREE_ISSUES = 3
    free_issues_shown = 0
    hidden_issues_count = 0

    # Generate category cards
    category_html = ""
    for cat in categories:
        cat_name = cat.get("category", "")
        cat_score = cat.get("score", 0)
        issues = cat.get("issues", [])

        if cat_score >= 80:
            cat_color = "#22c55e"
            cat_icon = "&#10003;"
        elif cat_score >= 60:
            cat_color = "#f59e0b"
            cat_icon = "&#9888;"
        else:
            cat_color = "#ef4444"
            cat_icon = "&#10007;"

        issues_html = ""
        for issue in issues:
            impact = issue.get("impact", "medium")
            if impact == "critical":
                badge_color = "#ef4444"
                badge_text = "CRITICAL"
            elif impact == "high":
                badge_color = "#f97316"
                badge_text = "HIGH"
            elif impact == "medium":
                badge_color = "#f59e0b"
                badge_text = "MEDIUM"
            else:
                badge_color = "#6b7280"
                badge_text = "LOW"

            # Partial report: show first MAX_FREE_ISSUES, blur the rest
            if not full_report and free_issues_shown >= MAX_FREE_ISSUES:
                hidden_issues_count += 1
                issues_html += """
            <div style="padding:12px 16px;border-left:3px solid #374151;margin-bottom:8px;background:rgba(255,255,255,0.02);border-radius:0 8px 8px 0;filter:blur(5px);user-select:none;pointer-events:none;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="color:#e2e8f0;font-size:14px;">Issue details hidden - unlock full report to view</span>
                    <span style="background:#374151;color:#9ca3af;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">LOCKED</span>
                </div>
            </div>
            """
            else:
                free_issues_shown += 1
                issues_html += f"""
            <div style="padding:12px 16px;border-left:3px solid {badge_color};margin-bottom:8px;background:rgba(255,255,255,0.03);border-radius:0 8px 8px 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="color:#e2e8f0;font-size:14px;">{issue.get('issue', '')}</span>
                    <span style="background:{badge_color};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">{badge_text}</span>
                </div>
            </div>
            """

        category_html += f"""
        <div style="background:#111827;border-radius:12px;padding:24px;margin-bottom:16px;border:1px solid #1f2937;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="color:{cat_color};font-size:24px;">{cat_icon}</span>
                    <h3 style="color:#f8fafc;margin:0;font-size:18px;">{cat_name}</h3>
                </div>
                <div style="text-align:right;">
                    <span style="color:{cat_color};font-size:28px;font-weight:700;">{cat_score}</span>
                    <span style="color:#94a3b8;font-size:14px;">/100</span>
                </div>
            </div>
            <div style="background:#1f2937;height:8px;border-radius:4px;overflow:hidden;margin-bottom:16px;">
                <div style="background:{cat_color};height:100%;width:{cat_score}%;border-radius:4px;transition:width 1s;"></div>
            </div>
            {issues_html if issues else '<p style="color:#64748b;font-size:14px;margin:0;">No issues found in this category.</p>'}
        </div>
        """

    # AI Recommendation section
    ai_html = ""
    if ai_rec.get("checked"):
        found = ai_rec.get("found", False)
        ai_color = "#22c55e" if found else "#ef4444"
        ai_icon = "&#10003;" if found else "&#10007;"
        ai_html = f"""
        <div style="background:#111827;border-radius:12px;padding:24px;margin-bottom:16px;border:1px solid {ai_color}40;">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <span style="color:{ai_color};font-size:24px;">{ai_icon}</span>
                <h3 style="color:#f8fafc;margin:0;font-size:18px;">AI Recommendation Status</h3>
            </div>
            <p style="color:#cbd5e1;font-size:15px;margin:0;">{ai_rec.get('message', '')}</p>
        </div>
        """

    # Partial report unlock section (only show if NOT full report and there are hidden issues)
    unlock_html = ""
    if not full_report and hidden_issues_count > 0:
        unlock_html = f"""
        <div class="animate d4" style="background:linear-gradient(135deg,#1a1033,#0f172a);border-radius:16px;padding:40px;margin:32px 0;border:2px solid #7c3aed;text-align:center;">
            <div style="font-size:48px;margin-bottom:12px;">&#128274;</div>
            <h2 style="color:#f8fafc;font-size:24px;margin-bottom:8px;">{hidden_issues_count} More Issues Found</h2>
            <p style="color:#94a3b8;font-size:15px;margin-bottom:28px;line-height:1.6;">
                Your free scan revealed <strong style="color:#f97316;">{total_issues} total issues</strong>.
                You've seen {MAX_FREE_ISSUES} &mdash; unlock the remaining <strong style="color:#7c3aed;">{hidden_issues_count} issues</strong> to get the complete picture.
            </p>
            <div style="display:flex;flex-direction:column;gap:16px;max-width:400px;margin:0 auto;">
                <a href="mailto:info@authorityaisystems.com?subject=Schedule%20a%20Call%20-%20Review%20My%20AI%20Visibility%20Report&body=Hi%2C%20I%20just%20completed%20my%20free%20AI%20visibility%20scan%20and%20I%27d%20like%20to%20schedule%20a%20call%20to%20go%20over%20my%20full%20results.%0A%0ABusiness%3A%20{business_name}%0A%0AThank%20you!"
                   style="display:block;background:linear-gradient(135deg,#ff6b35,#e85d2a);color:#fff;font-weight:700;padding:16px 32px;border-radius:50px;font-size:16px;text-decoration:none;box-shadow:0 4px 15px rgba(255,107,53,0.4);text-align:center;">
                    &#128197; Schedule a Call to Review Results
                </a>
                <p style="color:#94a3b8;font-size:13px;margin:0;">We'll go over your full report together &mdash; no obligation</p>
                <div style="display:flex;align-items:center;gap:12px;margin:8px 0;">
                    <div style="flex:1;height:1px;background:#374151;"></div>
                    <span style="color:#64748b;font-size:13px;">OR</span>
                    <div style="flex:1;height:1px;background:#374151;"></div>
                </div>
                <a href="/report/{scan_id}?unlock=true"
                   style="display:block;background:#7c3aed;color:#fff;font-weight:700;padding:16px 32px;border-radius:50px;font-size:16px;text-decoration:none;box-shadow:0 4px 15px rgba(124,58,237,0.4);text-align:center;">
                    &#128275; Unlock Full Report &mdash; $99
                </a>
                <p style="color:#94a3b8;font-size:13px;margin:0;">Instant access to all {total_issues} issues without a call</p>
            </div>
        </div>
        """

    # Back to Home button
    back_home_html = """
        <div style="text-align:center;margin-bottom:24px;">
            <a href="https://authorityaisystems.com"
               style="display:inline-flex;align-items:center;gap:8px;color:#94a3b8;font-size:14px;text-decoration:none;padding:8px 16px;border:1px solid #374151;border-radius:8px;"
               onmouseover="this.style.color='#ff6b35';this.style.borderColor='#ff6b35';"
               onmouseout="this.style.color='#94a3b8';this.style.borderColor='#374151';">
                &#8592; Back to Authority AI Systems
            </a>
        </div>
    """

    # Badge for report type
    if not full_report:
        badge_html = '<div style="margin-top:12px;"><span style="background:#7c3aed;color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">FREE PREVIEW</span></div>'
    else:
        badge_html = '<div style="margin-top:12px;"><span style="background:#22c55e;color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">FULL REPORT</span></div>'

    # Section heading
    if full_report:
        analysis_heading = "Detailed Analysis"
    else:
        analysis_heading = f"Issue Preview ({MAX_FREE_ISSUES} of {total_issues} shown)"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Visibility Report - {business_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0f1c;
            color: #e2e8f0;
            min-height: 100vh;
        }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 24px 16px; }}
        @keyframes scoreIn {{
            from {{ stroke-dashoffset: 440; }}
        }}
        @keyframes fadeUp {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .animate {{ animation: fadeUp 0.6s ease-out forwards; opacity: 0; }}
        .d1 {{ animation-delay: 0.1s; }}
        .d2 {{ animation-delay: 0.2s; }}
        .d3 {{ animation-delay: 0.3s; }}
        .d4 {{ animation-delay: 0.4s; }}
        .d5 {{ animation-delay: 0.5s; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Back to Home -->
        {back_home_html}

        <!-- Header -->
        <div class="animate d1" style="text-align:center;padding:32px 0;border-bottom:1px solid #1f2937;margin-bottom:32px;">
            <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:8px;">
                <div style="width:40px;height:40px;border-radius:50%;border:2px solid #ff6b35;display:flex;align-items:center;justify-content:center;">
                    <div style="width:8px;height:8px;border-radius:50%;background:#ff6b35;"></div>
                </div>
                <span style="color:#ff6b35;font-weight:700;font-size:16px;letter-spacing:1px;">AUTHORITY AI SYSTEMS</span>
            </div>
            <h1 style="font-size:28px;color:#f8fafc;margin-bottom:4px;">AI Visibility Report</h1>
            <p style="color:#94a3b8;">Prepared for <strong style="color:#f8fafc;">{business_name}</strong></p>
            {f'<p style="color:#64748b;font-size:13px;margin-top:4px;">{website_url}</p>' if website_url else ''}
            {badge_html}
        </div>

        <!-- Score Circle -->
        <div class="animate d2" style="text-align:center;margin-bottom:40px;">
            <svg width="200" height="200" viewBox="0 0 200 200" style="margin-bottom:16px;">
                <circle cx="100" cy="100" r="85" fill="none" stroke="#1f2937" stroke-width="12"/>
                <circle cx="100" cy="100" r="85" fill="none" stroke="{score_color}" stroke-width="12"
                    stroke-linecap="round" stroke-dasharray="{2 * 3.14159 * 85}"
                    stroke-dashoffset="{2 * 3.14159 * 85 * (1 - overall_score/100)}"
                    transform="rotate(-90 100 100)"
                    style="animation: scoreIn 1.5s ease-out forwards;"/>
                <text x="100" y="90" text-anchor="middle" fill="{score_color}" font-size="48" font-weight="700">{overall_score}</text>
                <text x="100" y="115" text-anchor="middle" fill="#94a3b8" font-size="14">{grade} - {status_text}</text>
            </svg>
            <h2 style="font-size:22px;color:#f8fafc;margin-bottom:8px;">Your AI Visibility Score</h2>
            <p style="color:#94a3b8;font-size:15px;">
                We found <strong style="color:#f97316;">{total_issues} issues</strong> affecting your AI visibility
                {f', including <strong style="color:#ef4444;">{critical_issues} critical</strong> items' if critical_issues else ''}.
            </p>
        </div>

        <!-- Before / After Projection -->
        <div class="animate d3" style="background:linear-gradient(135deg,#111827,#1a1f35);border-radius:16px;padding:32px;margin-bottom:32px;border:1px solid #ff6b3540;text-align:center;">
            <h3 style="color:#ff6b35;font-size:14px;letter-spacing:2px;margin-bottom:20px;">YOUR POTENTIAL</h3>
            <div style="display:flex;justify-content:center;align-items:center;gap:40px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:14px;color:#94a3b8;margin-bottom:4px;">Current Score</div>
                    <div style="font-size:48px;font-weight:700;color:{score_color};">{overall_score}</div>
                </div>
                <div style="font-size:32px;color:#ff6b35;">&#10132;</div>
                <div>
                    <div style="font-size:14px;color:#94a3b8;margin-bottom:4px;">Projected Score</div>
                    <div style="font-size:48px;font-weight:700;color:#22c55e;">{projected_score}</div>
                </div>
            </div>
            <p style="color:#cbd5e1;font-size:14px;margin-top:16px;">
                With our optimization, businesses typically see a <strong style="color:#22c55e;">{projected_score - overall_score}-point improvement</strong> in AI visibility.
            </p>
        </div>

        <!-- AI Recommendation -->
        <div class="animate d3">
            {ai_html}
        </div>

        <!-- Category Breakdown -->
        <div class="animate d4">
            <h2 style="font-size:22px;color:#f8fafc;margin-bottom:20px;">{analysis_heading}</h2>
            {category_html}
        </div>

        <!-- Unlock section (partial report only) -->
        {unlock_html}

        <!-- CTA Section -->
        <div class="animate d5" style="background:linear-gradient(135deg,#ff6b35,#e85d2a);border-radius:16px;padding:40px;text-align:center;margin:40px 0;">
            <h2 style="color:#fff;font-size:26px;margin-bottom:12px;">Ready to Fix These Issues?</h2>
            <p style="color:rgba(255,255,255,0.9);font-size:16px;margin-bottom:24px;line-height:1.6;">
                Don't let your competitors steal your customers.<br>
                Our team can optimize your AI visibility and get you recommended by ChatGPT, Siri, and Google AI.
            </p>
            <a href="https://authorityaisystems.com/#pricing" style="display:inline-block;background:#fff;color:#ff6b35;font-weight:700;padding:16px 40px;border-radius:50px;font-size:18px;text-decoration:none;box-shadow:0 4px 15px rgba(0,0,0,0.3);">
                Choose Your Plan
            </a>
            <p style="color:rgba(255,255,255,0.7);font-size:13px;margin-top:16px;">
                Or call us: <a href="tel:" style="color:#fff;">Schedule a Free Consultation</a>
            </p>
        </div>

        <!-- Back to Home (bottom) -->
        {back_home_html}

        <!-- Footer -->
        <div style="text-align:center;padding:24px 0;border-top:1px solid #1f2937;color:#64748b;font-size:13px;">
            <p>Generated by <strong style="color:#ff6b35;">Authority AI Systems</strong></p>
            <p style="margin-top:4px;">authorityaisystems.com | info@authorityaisystems.com</p>
        </div>
    </div>
</body>
</html>"""

    return html
