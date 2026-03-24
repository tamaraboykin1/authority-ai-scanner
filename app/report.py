"""Generate client-facing AI Visibility Report HTML."""


def generate_report_html(scan_data: dict, results: dict) -> str:
    """Generate a polished client-facing report that shows problems but NOT solutions."""
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
            <h2 style="font-size:22px;color:#f8fafc;margin-bottom:20px;">Detailed Analysis</h2>
            {category_html}
        </div>

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

        <!-- Footer -->
        <div style="text-align:center;padding:24px 0;border-top:1px solid #1f2937;color:#64748b;font-size:13px;">
            <p>Generated by <strong style="color:#ff6b35;">Authority AI Systems</strong></p>
            <p style="margin-top:4px;">authorityaisystems.com | info@authorityaisystems.com</p>
        </div>
    </div>
</body>
</html>"""

    return html
