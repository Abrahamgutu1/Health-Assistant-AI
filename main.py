import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = "asst_55iZs4Uxtgt0JmWxJwYWYOMD"

app = FastAPI()

class Question(BaseModel):
    question: str


def call_health_assistant(user_question: str) -> str:
    try:
        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"You are a warm, educational, supportive health assistant.\n"
                        f"User question: \"{user_question}\"\n"
                        "Respond kindly, clearly, and with non-diagnostic information.\n"
                    ),
                }
            ]
        )

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
        )

        if run.status != "completed":
            return "The assistant is still thinking. Try again in a moment."

        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for msg in messages.data:
            if msg.role == "assistant":
                parts = [p.text.value for p in msg.content if p.type == "text"]
                if parts:
                    return "\n".join(parts)

        return "I couldn’t generate a response. Try again."
    except Exception as e:
        print("ERROR:", e)
        return "There was an issue contacting the AI. Try again."


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
            body {
                background: radial-gradient(circle at top, #151823, #05060a 40%, #020308 100%);
                color: #f5f5f7;
                font-family: system-ui, sans-serif;
                margin: 0;
            }
            .navbar {
                text-align: center;
                padding: 25px 0;
                font-size: 1.7rem;
                font-weight: 600;
                letter-spacing: 0.5px;
                border-bottom: 1px solid rgba(255,255,255,0.05);
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 10px;
            }
            .content {
                max-width: 850px;
                margin: 40px auto;
                padding: 20px;
            }
            .assistant-box {
                background: rgba(10, 12, 20, 0.85);
                padding: 25px;
                border-radius: 14px;
                border: 1px solid rgba(255,255,255,0.06);
                box-shadow: 0 0 25px rgba(0,0,0,0.6);
            }
            textarea {
                width: 100%;
                height: 120px;
                background: #0b0d15;
                border-radius: 10px;
                padding: 10px;
                border: 1px solid #2a2f42;
                color: #fff;
                margin-bottom: 10px;
                resize: vertical;
            }
            button {
                width: 100%;
                padding: 12px;
                border-radius: 10px;
                border: none;
                background: linear-gradient(135deg,#32e0a1,#1aa36f);
                color: #000;
                font-size: 1rem;
                font-weight: bold;
                cursor: pointer;
            }
            #answer {
                margin-top: 20px;
                white-space: pre-wrap;
                border-top: 1px solid rgba(255,255,255,0.08);
                padding-top: 15px;
            }
            .footer {
                text-align: center;
                font-size: 0.75rem;
                color: #8a8f9e;
                margin-top: 40px;
                opacity: 0.6;
            }
        </style>
    </head>

    <body>
        <header class="navbar">
            <span>Health Assistant AI</span>
        </header>

        <main class="content">
            <div class="assistant-box">
                <textarea id="question" placeholder="Ask anything health-related..."></textarea>
                <button onclick="ask()">Ask</button>
                <div id="answer"></div>
            </div>
        </main>

        <footer class="footer">
            Educational information only — not medical advice
        </footer>

        <script>
            async function ask() {
                const question = document.getElementById('question').value.trim();
                const answerDiv = document.getElementById('answer');
                if (!question) return answerDiv.textContent = "Please enter a question.";

                answerDiv.textContent = "Thinking...";

                const res = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question })
                });

                const data = await res.json();
                answerDiv.textContent = data.answer;
            }
        </script>
    </body>
    </html>
    """


@app.post("/ask")
def ask_health_question(q: Question):
    emergencies = ["not breathing","overdose","heart attack","stroke","chest pain","suicidal","bleeding a lot"]
    if any(word in q.question.lower() for word in emergencies):
        return {"answer": "⚠️ This may be serious. Contact emergency care or a medical professional immediately."}
    
    return {"answer": call_health_assistant(q.question)}
