import os
import re
import smtplib
import json
from typing import List, Dict, Optional

import openai
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Load API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("Set OPENAI_API_KEY environment variable before running.")

# Optional sales handoff configuration
SALES_EMAIL = os.getenv("SALES_EMAIL")  # e.g. sales@neurofive.com
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else None
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
ENABLE_SALES_HANDOFF = os.getenv("ENABLE_SALES_HANDOFF", "false").lower() in ("1", "true", "yes")

SYSTEM_PROMPT = """
You are "Ava", a friendly and helpful Sales Assistant for Neurofive Solutions.
You help customers learn about Neurofive products, answer questions, and guide them to the right product.

Products:
1) Neurofive App - Productivity and AI tools for teams
2) Neurofive Store - Tech gadgets (headphones, smart watches, laptops)
3) Neurofive Cloud - Secure cloud storage and backup for businesses

Conversation rules you MUST follow:
- Be enthusiastic, helpful, and never pushy.
- Always ask 1-2 clarifying questions before making a product recommendation when user intent is to buy or evaluate.
- When recommending, highlight 2-3 key benefits.
- Always include a clear next step: "Would you like a demo / link / pricing?"
- Keep replies under 120 words.
- If asked something off-topic, politely steer back to Neurofive products.
- Never invent exact pricing. If the user asks for exact pricing, reply: "Let me connect you to sales@neurofive.com for exact pricing."
"""

PRICING_PATTERNS = re.compile(r"\b(price|cost|how much|pricing|per month|subscription|monthly|rate)\b", re.I)
OFF_TOPIC_PATTERNS = re.compile(r"\b(recipe|cooking|how to cook|movie|sports|lyrics|poem)\b", re.I)
BUY_INTENT_PATTERNS = re.compile(r"\b(buy|demo|trial|pricing|subscribe|evaluate|team|for my team|looking for)\b", re.I)

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

app = FastAPI(title="Ava - Neurofive Sales Assistant")

# Allow local frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend file from the repository root (we'll add static/index.html)

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict]] = None
    contact: Optional[Dict] = None  # optional contact info for handoff (name, email, phone)


def is_pricing_query(text: str) -> bool:
    return bool(PRICING_PATTERNS.search(text))


def is_off_topic(text: str) -> bool:
    return bool(OFF_TOPIC_PATTERNS.search(text))


def appears_to_want_to_buy(text: str) -> bool:
    return bool(BUY_INTENT_PATTERNS.search(text))


def send_sales_email(user_message: str, contact: Optional[Dict] = None) -> bool:
    """Attempt to send an email to SALES_EMAIL using SMTP env vars. Returns True if sent."""
    if not (ENABLE_SALES_HANDOFF and SALES_EMAIL and SMTP_HOST and SMTP_USER and SMTP_PASS and SMTP_PORT):
        return False

    subject = "Neurofive Sales Handoff - Pricing Request"
    body = f"A user requested pricing or handoff.\n\nMessage:\n{user_message}\n\nContact:\n{json.dumps(contact or {}, indent=2)}\n"
    message = f"From: {SMTP_USER}\nTo: {SALES_EMAIL}\nSubject: {subject}\n\n{body}"

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [SALES_EMAIL], message)
        server.quit()
        return True
    except Exception as e:
        print("Failed to send sales email:", e)
        return False


@app.post("/chat")
async def chat(req: ChatRequest):
    user_message = req.message.strip()

    # Pre-checks for off-topic
    if is_off_topic(user_message):
        return JSONResponse({
            "reply": (
                "I can help with Neurofive products and services — for recipes or other topics I recommend a cooking resource. "
                "Would you like to hear about the Neurofive App or Store instead?"
            ),
            "handed_off": False,
        })

    # Pricing - do not hallucinate prices. Offer handoff to sales if configured
    if is_pricing_query(user_message):
        handed_off = False
        if ENABLE_SALES_HANDOFF:
            success = send_sales_email(user_message, req.contact)
            handed_off = success

        return JSONResponse({
            "reply": (
                "I don't have exact pricing information. Let me connect you to sales@neurofive.com for exact pricing. "
                "Would you like me to arrange a demo or send product tiers instead?"
            ),
            "handed_off": handed_off,
        })

    # Build messages for OpenAI
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if req.history:
        messages.extend(req.history)
    messages.append({"role": "user", "content": user_message})

    if appears_to_want_to_buy(user_message):
        messages.append({
            "role": "system",
            "content": "If the user shows intent to buy/evaluate, ask 1-2 brief clarifying questions (team size, use-case, budget range) before recommending."
        })

    try:
        resp = openai.ChatCompletion.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7,
            max_tokens=180,
        )
        reply = resp.choices[0].message.content.strip()

        # Post-check length
        if len(reply.split()) > 130:
            trimmed = " ".join(reply.split()[:120]).rstrip() + "..."
            trimmed += " Would you like a demo / link / pricing?"
            reply = trimmed

        return JSONResponse({"reply": reply, "handed_off": False})

    except Exception as e:
        print("OpenAI call failed:", e)
        return JSONResponse({"reply": "Sorry, I'm having trouble accessing the assistant right now. Please try again later.", "handed_off": False}, status_code=500)


@app.get("/")
async def index():
    return FileResponse("static/index.html")
