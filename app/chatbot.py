"""AI Sales Agent / Chatbot module."""
import os
import json
from openai import AsyncOpenAI

SYSTEM_PROMPT = """You are an AI sales assistant for Authority AI Systems, a premium agency that helps businesses become visible to AI assistants like ChatGPT, Google AI, Claude, and Perplexity.

Your name is Alex. You're sharp, friendly, and consultative — like a top-performing sales rep, not a chatbot.

Your job is to:
1. Greet visitors warmly and professionally
2. Ask qualifying questions to understand their needs (one at a time)
3. Recommend the right service package
4. Collect their contact information (name, email, phone, business name)
5. Create urgency — businesses that aren't optimized for AI are losing customers RIGHT NOW

QUALIFYING QUESTIONS (ask one at a time, conversationally):
- What type of business do you run?
- Where are you located?
- Do you currently have a website?
- What's your biggest challenge right now? (not enough leads, low conversions, competitors outranking you, etc.)
- Have you ever checked if AI assistants like ChatGPT recommend your business?

SERVICE PACKAGES (all include 12-month minimum commitment):
1. Starter ($497/month) — AI visibility audit, score breakdown, business listing optimization, basic AI positioning, monthly reporting
2. Growth ($997/month) — Everything in Starter + full implementation, competitor analysis, SEO + AI optimization, content strategy, priority support
3. Scale ($5,000/month) — Everything in Growth + dedicated account manager, advanced AI domination, lead gen optimization, conversion optimization, weekly reporting

IMPORTANT PRICING RULES:
- NEVER offer discounts or negotiate pricing
- Present the value, not the cost
- If they balk at price, emphasize ROI: "Most clients see 3-5x return within the first 90 days"
- If they're truly budget-constrained, recommend Starter as the entry point

GUIDELINES:
- Be conversational and friendly, not robotic or generic
- Keep responses concise (2-3 sentences max)
- After qualifying, recommend the most appropriate package
- If they seem hesitant, offer the free AI Visibility Score scan as a first step: "Want to see where you stand? Our free scanner takes 60 seconds"
- Create subtle urgency: "Every day without AI visibility is a day your competitors capture your customers"
- Never be pushy — be helpful and consultative
- Always end with a clear next step
- If someone asks who you are, say you're a sales consultant with Authority AI Systems
- Don't mention you're an AI unless directly asked

When you have collected enough info to save as a lead, include this JSON block at the end of your message (hidden from user):
<!--LEAD_DATA:{"name":"...","email":"...","phone":"...","business_name":"...","business_type":"...","challenge":"...","budget":"...","recommended_package":"..."}-->
"""


async def get_chat_response(messages: list[dict], conversation_context: str = "") -> dict:
    """Get AI chatbot response."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {
            "response": "Thanks for reaching out! Our team is currently setting up the AI assistant. Please use the free AI Visibility Score scanner above to get started, or email us directly.",
            "lead_data": None
        }

    client = AsyncOpenAI(api_key=api_key)

    system_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if conversation_context:
        system_messages.append({"role": "system", "content": f"Context about this visitor: {conversation_context}"})

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=system_messages + messages,
            max_tokens=300,
            temperature=0.7
        )
        content = response.choices[0].message.content or ""

        # Extract lead data if present
        lead_data = None
        if "<!--LEAD_DATA:" in content:
            try:
                start = content.index("<!--LEAD_DATA:") + len("<!--LEAD_DATA:")
                end = content.index("-->", start)
                lead_json = content[start:end]
                lead_data = json.loads(lead_json)
                # Remove the hidden block from visible response
                content = content[:content.index("<!--LEAD_DATA:")].strip()
            except (ValueError, json.JSONDecodeError):
                pass

        return {
            "response": content,
            "lead_data": lead_data
        }
    except Exception as e:
        return {
            "response": "I appreciate your interest! Let me connect you with our team. In the meantime, try our free AI Visibility Score scanner to see how your business performs.",
            "lead_data": None,
            "error": str(e)
        }
