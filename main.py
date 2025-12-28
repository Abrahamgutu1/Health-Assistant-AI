import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI

# Create OpenAI client (reads OPENAI_API_KEY from environment)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Your Assistant ID from the OpenAI dashboard
ASSISTANT_ID = "asst_55iZs4Uxtgt0JmWxJwYWYOMD"

app = FastAPI()


class Question(BaseModel):
    question: str


# ----------------------------------------
# Call your Health Assistant (Assistants API)
# ----------------------------------------
def call_health_assistant(user_question: str) -> str:
    """
    Send the user's question to your Health Assistant via the Assistants API.
    The assistant is configured to be warm, detailed, and educational,
    but not to diagnose or give medical advice.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return (
            "The online AI assistant is not configured because the API key is missing.\n\n"
            "Please set the OPENAI_API_KEY on the server.\n\n"
            "For personal health concerns, please talk to a licensed healthcare professional."
        )

    if not ASSISTANT_ID or not ASSISTANT_ID.startswith("asst_"):
        return (
            "The Health Assistant ID is not set correctly in the server code.\n\n"
            "Please update ASSISTANT_ID in main.py with your real assistant ID from the OpenAI dashboard."
        )

    try:
        # 1) Create a thread with a rich, warm prompt including the user's question
        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are a warm, supportive health education assistant.\n"
                        "The user is asking the following health-related question:\n\n"
                        f"\"{user_question}\"\n\n"
                        "Respond in a detailed, clear, and comforting way.\n"
                        "- Explain what might generally be going on in educational terms.\n"
                        "- You may describe common possible causes in GENERAL (not for this specific user).\n"
                        "- Normalize their feelings and reassure them that it is okay to feel worried or confused.\n"
                        "- Suggest healthy, safe next steps (like rest, hydration, note-taking, or asking a doctor questions).\n"
                        "- Encourage them to seek professional medical evaluation for personal or persistent symptoms.\n\n"
                        "Do NOT:\n"
                        "- Diagnose the user.\n"
                        "- Say they have a specific condition.\n"
                        "- Give prescriptions, dosages, or specific treatment plans.\n\n"
                        "Use phrases like:\n"
                        "- \"In general, doctors say this symptom can sometimes be related to...\"\n"
                        "- \"People may experience this for a variety of reasons, including...\"\n"
                        "- \"Only a clinician who examines you can say what is actually going on in your case.\"\n\n"
                        "End with something like:\n"
                        "\"I hope this helps. This is general educational information only, not medical advice. "
                        "For personal medical concerns, please talk to a doctor or licensed healthcare professional.\""
                    ),
                }
            ]
        )

        # 2) Run the assistant on that thread and wait for completion
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
        )

        if run.status != "completed":
            return (
                "The Health Assistant could not complete the request right now.\n\n"
                f"Status: {run.status}\n\n"
                "Please try again later, and for medical concerns, talk to a doctor or "
                "licensed healthcare professional."
            )

        # 3) Retrieve messages from the thread
        messages = client.beta.threads.messages.list(thread_id=thread.id)

        # Look for the assistant's reply
        for msg in messages.data:
            if msg.role == "assistant":
                parts = [
                    part.text.value
                    for part in msg.content
                    if part.type == "text"
                ]
                if parts:
                    return "\n".join(parts)

        # Fallback if no assistant text found
        return (
            "I'm here for you, but I couldn't generate a full response this time.\n\n"
            "Please try asking again, and for health questions about your own body, "
            "talk directly with a licensed healthcare professional."
        )

    except Exception as e:
        # Log error to server console and show a gentle message to the user
        print("Error calling Assistants API:", e)
        return (
            "There was a problem contacting the Health Assistant service.\n\n"
            "Please try again later, and for personal health concerns, "
            "talk to a doctor or licensed healthcare professional."
        )


# ----------------------------------------
# Home Page UI (black theme + health icon)
# ----------------------------------------
@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Health Assistant AI</title>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <style>
            :root {
                --bg-main: #05060a;
                --accent: #32e0a1;
                --text-primary: #f5f5f7;
                --text-muted: #9ea2b3;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                background: radial-gradient(circle at top, #151823 0, #05060a 45%, #020308 100%);
                font-family: system-ui, sans-serif;
                color: var(--text-primary);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }

            /* ⭐️ Centered Header Like ChatGPT */
            .navbar {
                text-align: center;
                padding: 25px 0;
                color: var(--text-primary);
                font-size: 1.7rem;
                font-weight: 600;
                letter-spacing: 0.5px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            }

            .navbar span {
                background: linear-gradient(135deg, #32e0a1, #1aa36f);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            .content {
                max-width: 900px;
                margin: 40px auto;
                padding: 20px;
            }

            .assistant-box {
                background: rgba(10, 12, 20, 0.85);
                padding: 25px;
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 0.06);
                box-shadow: 0 0 25px rgba(0,0,0,0.6);
            }

            textarea {
                width: 100%;
                height: 120px;
                background: #0b0d15;
                border: 1px solid #2a2f42;
                border-radius: 10px;
                color: var(--text-primary);
                padding: 10px;
                font-size: 1rem;
                margin-bottom: 10px;
            }

            button {
                background: linear-gradient(135deg, #32e0a1, #1aa36f);
                color: #000;
                border: none;
                padding: 12px 24px;
                font-weight: 600;
                border-radius: 10px;
                cursor: pointer;
                font-size: 1rem;
                width: 100%;
            }

            #answer {
                margin-top: 25px;
                padding-top: 15px;
                white-space: pre-wrap;
                font-size: 1rem;
                line-height: 1.5;
                border-top: 1px solid rgba(255,255,255,0.08);
            }

            /* Small, quiet safety note (not in-your-face) */
            .footer {
                margin-top: auto;
                text-align: center;
                padding: 20px 10px;
                font-size: 0.73rem;
                color: var(--text-muted);
                opacity: 0.55;
            }
        </style>
    </head>
    <body>

        <!-- ⭐️ Center Title Like ChatGPT -->
        <header class="navbar">
            <span>Health Assistant AI</span>
        </header>

        <main class="content">
            <div class="assistant-box">
                <textarea id="question" placeholder="Ask anything... 'Why do I feel lightheaded when standing up?'"></textarea>
                <button onclick="ask()">Ask</button>
                <div id="answer"></div>
            </div>
        </main>

        <!-- Minimal safety note (quiet, not visible like before) -->
        <footer class="footer">
            Educational information only • Not medical advice • Not a diagnosis
        </footer>

        <script>
            async function ask() {
                const question = document.getElementById('question').value.trim();
                const answerDiv = document.getElementById('answer');
                if (!question) {
                    answerDiv.textContent = "Please enter a question.";
                    return;
                }

                answerDiv.textContent = "Thinking...";

                try {
                    const res = await fetch('/ask', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ question })
                    });
                    const data = await res.json();
                    answerDiv.textContent = data.answer;
                } catch {
                    answerDiv.textContent = "Error contacting server.";
                }
            }
        </script>
    </body>
    </html>
    """


# ----------------------------------------
# Q&A Endpoint (emergency filter + AI)
# ----------------------------------------
@app.post("/ask")
def ask_health_question(q: Question):
    user_q = q.question.strip()
    user_q_lower = user_q.lower()

    # Basic emergency / crisis keywords
    emergencies = [
        "chest pain",
        "can't breathe",
        "cannot breathe",
        "not breathing",
        "bleeding a lot",
        "overdose",
        "suicidal",
        "kill myself",
        "want to hurt myself",
        "stroke",
        "heart attack",
        "passed out",
        "unconscious"
    ]

    if any(term in user_q_lower for term in emergencies):
        return {
            "type": "emergency_warning",
            "answer": (
                "⚠️ Your question sounds like it could involve a medical emergency.\n\n"
                "Please call 911 or your local emergency number, or go to the nearest emergency room "
                "or urgent care immediately.\n\n"
                "This assistant cannot evaluate, diagnose, or respond to emergencies."
            )
        }

    # Otherwise, call the warm, educational Health Assistant
    answer = call_health_assistant(user_q)
    return {"type": "general_info", "answer": answer}
