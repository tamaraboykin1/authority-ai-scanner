"""AI Sales Agent / Chatbot module."""
import os
import json
from openai import AsyncOpenAI

SYSTEM_PROMPT = """You are an AI sales assistant for Authority AI Systems, a premium agency that helps businesses become visible to AI assistants like ChatGPT, Google AI, Claude, and Perplexity.

Your job is to:
1. Greet visitors warmly and professionally
2. Ask qualifying questions to understand their needs
3. Recommend the right service package
4. Collect their contact information
5. Create urgency — businesses that aren't optimized for AI are losing customers RIGHT NOW

QUALIFYING QUESTIONS (ask one at a time, conversationally):
- What type of business do you run?
- Do you currently have a website?
- What's your biggest challenge right now? (not enough leads, low conversions, competitors outranking you, etc.)
- Have you ever checked if AI assistants like ChatGPT recommend your business?
- What's your approximate monthly marketing budget?

SERVICE PACKAGES:
1. AI Visibility Audit ($497 one-time) - Full scan, score breakdown, competitor comparison, missed opportunities, actionable recommendations
2. AI Growth System ($1,500-$2,500/month) - Everything in Audit + implementation, business listing optimization, SEO + AI positioning, monthly tracking
3. Done-For-You AI Domination ($5,000+/month) - Everything in Growth + full management, advanced positioning, lead gen optimization, conversion optimization, priority support

GUIDELINES:
- Be conversational and friendly, not robotic
- Keep responses concise (2-3 sentences max)
- After qualifying, recommend the most appropriate package
- Always try to collect: name, email, phone, business name
- If they seem hesitant, offer the free AI Visibility Score scan as a first step
- Create subtle urgency: "Every day without AI visibility is a day your competitors capture your customers"
- Never be pushy — be helpful and consultative
- If asked about pricing, be transparent and emphasize ROI
- Always end with a clear next step

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
