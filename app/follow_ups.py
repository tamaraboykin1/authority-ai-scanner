"""Follow-up email sequence templates and management."""

FOLLOW_UP_SEQUENCES = {
    "chatbot_lead": [
        {
            "step": 1,
            "delay_hours": 0,
            "subject": "Your AI Visibility Consultation — Next Steps",
            "body": """Hi {name},

Thanks for chatting with us about {business_name}! I wanted to follow up personally.

You mentioned that {challenge} is your biggest challenge right now. That's exactly what our {recommended_package} is designed to solve.

Here's the thing — every day your business isn't optimized for AI assistants like ChatGPT and Google AI, your competitors are capturing customers that should be yours.

I'd love to walk you through exactly how we'd fix this for {business_name}. Would you be open to a quick 15-minute call this week?

You can also run your free AI Visibility Score here to see exactly where you stand: {scanner_url}

Looking forward to connecting,
Authority AI Systems Team"""
        },
        {
            "step": 2,
            "delay_hours": 48,
            "subject": "Quick question about {business_name}",
            "body": """Hi {name},

I wanted to share something interesting — we just ran a quick check on businesses in your area, and most of them aren't showing up in AI recommendations at all.

This means there's a massive first-mover advantage for {business_name} right now. The businesses that optimize for AI visibility first will lock in their position as the go-to recommendation.

Our {recommended_package} would position {business_name} to be the #1 recommendation when customers ask AI assistants for help in your industry.

Would you like to see a demo of how this works? Just reply to this email and I'll set it up.

Best,
Authority AI Systems Team"""
        },
        {
            "step": 3,
            "delay_hours": 120,
            "subject": "Last chance: Special offer for {business_name}",
            "body": """Hi {name},

I know you're busy running {business_name}, so I'll keep this short.

We're offering a limited-time discount on our {recommended_package} for businesses in your area. This won't last long — we only take on a limited number of clients per month to ensure quality results.

Here's what you'd get:
- Complete AI visibility audit of {business_name}
- Competitor analysis showing who AI currently recommends over you
- Custom optimization roadmap
- Implementation support

The window for early-mover advantage in AI visibility is closing fast. Businesses that wait will find it exponentially harder to compete.

Ready to get started? Reply to this email or book a call here.

Best,
Authority AI Systems Team"""
        },
        {
            "step": 4,
            "delay_hours": 240,
            "subject": "We found something about {business_name}...",
            "body": """Hi {name},

I wanted to give you a heads-up — we've been tracking AI recommendation trends in your industry, and the competition is heating up.

Businesses that have already optimized for AI visibility are seeing:
- 5x more AI recommendations
- 73% increase in qualified leads
- Significant revenue growth from AI-driven traffic

{business_name} has real potential here. I'd hate to see your competitors lock in this advantage while you're still deciding.

If you'd like a no-obligation walkthrough of exactly how we'd position {business_name} for AI dominance, just reply "interested" and I'll set up a time.

No pressure — but don't sleep on this.

Best,
Authority AI Systems Team"""
        },
        {
            "step": 5,
            "delay_hours": 480,
            "subject": "Final follow-up: {business_name} + AI Visibility",
            "body": """Hi {name},

This will be my last email about this — I don't want to be that person who won't stop emailing you.

Here's the bottom line: AI is rapidly becoming how customers find businesses. ChatGPT, Google AI, Claude, Perplexity — they're all recommending businesses to millions of people every day.

If {business_name} isn't optimized for these platforms, you're invisible to a growing segment of your potential customers.

We've helped businesses like yours go from completely invisible to being the #1 AI recommendation in their market. The results speak for themselves.

If you ever want to explore this, we're here. Just reply to this email anytime.

Wishing you all the best,
Authority AI Systems Team

P.S. You can always check your current AI visibility score for free at {scanner_url}"""
        }
    ],
    "scanner_lead": [
        {
            "step": 1,
            "delay_hours": 1,
            "subject": "Your AI Visibility Score Results — Here's What to Do Next",
            "body": """Hi there,

Thanks for running your AI Visibility Score! Here's a quick summary of what we found for {business_name}:

Score: {score}/100 (Grade: {grade})

{score_summary}

The good news? Every issue we found is fixable. The bad news? Every day these issues remain, AI assistants are recommending your competitors instead of you.

Want us to fix everything for you? Our team can:
1. Implement all the recommendations from your scan
2. Optimize your business for every major AI platform
3. Monitor and improve your AI visibility monthly

Reply to this email or book a call to get started.

Best,
Authority AI Systems Team"""
        },
        {
            "step": 2,
            "delay_hours": 72,
            "subject": "Your competitors are already doing this...",
            "body": """Hi,

Quick update — since you ran your AI Visibility Score for {business_name}, we've seen more businesses in your area starting to optimize for AI.

The first-mover advantage won't last forever. Businesses that position themselves now will be exponentially harder to overtake later.

Your scan showed several critical areas for improvement. Want us to handle the fixes? We have packages starting at $497 for a complete audit and action plan.

Reply "interested" and I'll send you the details.

Best,
Authority AI Systems Team"""
        },
        {
            "step": 3,
            "delay_hours": 168,
            "subject": "One last thing about your AI visibility...",
            "body": """Hi,

Just a final note — your AI Visibility Score for {business_name} showed areas that need attention.

We only reach out like this when we see real potential. Your business has what it takes to dominate AI recommendations in your market, but the optimization needs to happen soon.

If you'd like help, we're here. If not, no worries — you can always re-run your free scan at {scanner_url} to track your progress.

Best,
Authority AI Systems Team"""
        }
    ]
}


OUTREACH_TEMPLATES = {
    "cold_email_initial": {
        "subject": "I found something about {business_name} that you should see",
        "body": """Hi {name},

I was researching {industry} businesses in {city} and came across {business_name}. I noticed something that could be costing you customers.

I ran a quick AI visibility check on your business, and here's what I found: when people ask AI assistants like ChatGPT or Google AI for a {industry} recommendation in {city}, your business doesn't come up.

This matters because more and more customers are using AI to find businesses — and if you're not showing up, your competitors are getting those customers instead.

I help businesses like yours become the #1 AI recommendation in their market. Would you be open to a quick chat about how this works?

I can also send you a free AI Visibility Score report for {business_name} — no strings attached.

Best,
Authority AI Systems"""
    },
    "cold_email_followup": {
        "subject": "Re: AI visibility for {business_name}",
        "body": """Hi {name},

Just following up on my previous email. I wanted to share a quick stat:

Businesses optimized for AI visibility see an average 73% increase in leads from AI-driven recommendations. That's customers who are actively looking for exactly what you offer.

I'd love to show you what's possible for {business_name}. Would a 15-minute call work this week?

Best,
Authority AI Systems"""
    },
    "cold_sms_initial": "Hi {name}, I'm from Authority AI Systems. I noticed {business_name} isn't showing up in AI recommendations (ChatGPT, Google AI). This could be costing you customers. Want me to send you a free AI visibility report? No strings attached.",
    "cold_sms_followup": "Hi {name}, just following up — I have that free AI visibility report ready for {business_name}. Want me to send it over? It shows exactly where you stand vs competitors."
}


def render_template(template: str, variables: dict) -> str:
    """Render a template string with variables."""
    result = template
    for key, value in variables.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def get_follow_up_sequence(lead_type: str) -> list:
    """Get the follow-up sequence for a lead type."""
    return FOLLOW_UP_SEQUENCES.get(lead_type, [])


def get_outreach_template(template_name: str) -> dict | str:
    """Get an outreach template by name."""
    return OUTREACH_TEMPLATES.get(template_name, {})
