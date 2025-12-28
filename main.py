import os
import sqlite3
import hashlib
from typing import Optional, List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI

# ---------- OpenAI Client & Assistant ----------
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
ASSISTANT_ID = "asst_55iZs4Uxtgt0JmWxJwYWYOMD"

app = FastAPI()

DB_PATH = "health_ai.db"


# ---------- Database Setup ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Users table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
        """
    )

    # Messages table (chat/history)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,        -- "user" or "assistant"
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """
    )

    conn.commit()
    conn.close()


init_db()


def get_db():
    return sqlite3.connect(DB_PATH)


# ---------- Pydantic Models ----------
class Question(BaseModel):
    question: str
    user_id: Optional[int] = None


class AuthRequest(BaseModel):
    username: str
    password: str


class Message(BaseModel):
    role: str
    message: str


# ---------- OpenAI Call ----------
def call_health_assistant(user_question: str) -> str:
    """
    Call your OpenAI Health Assistant and return a warm, educational answer.
    """
    try:
        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are a warm, educational, supportive health assistant.\n"
                        "You give general health information only, not medical advice.\n\n"
                        f"User question: \"{user_question}\""
                    ),
                }
            ]
        )

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
        )

        if run.status != "completed":
            return "The assistant is still thinking. Please try again in a moment."

        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for msg in messages.data:
            if msg.role == "assistant":
                parts = [p.text.value for p in msg.content if p.type == "text"]
                if parts:
                    return "\n".join(parts)

        return "I couldn’t generate a full response this time. Please try again."
    except Exception as e:
        print("ERROR calling assistant:", e)
        return "There was an issue contacting the AI service. Please try again."


# ---------- Auth Endpoints ----------
@app.post("/signup")
def signup(auth: AuthRequest):
    username = auth.username.strip()
    password = auth.password

    if not username or not password:
        return {"success": False, "message": "Username and password are required."}

    pw_hash = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, pw_hash),
        )
        conn.commit()
        user_id = c.lastrowid
        return {
            "success": True,
            "message": "Account created.",
            "user_id": user_id,
            "username": username,
        }
    except sqlite3.IntegrityError:
        return {"success": False, "message": "Username already taken."}
    finally:
        conn.close()


@app.post("/login")
def login(auth: AuthRequest):
    username = auth.username.strip()
    password = auth.password

    if not username or not password:
        return {"success": False, "message": "Username and password are required."}

    pw_hash = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id, password_hash FROM users WHERE username = ?",
        (username,),
    )
    row = c.fetchone()
    conn.close()

    if row is None:
        return {"success": False, "message": "User not found."}

    user_id, stored_hash = row
    if stored_hash != pw_hash:
        return {"success": False, "message": "Incorrect password."}

    return {
        "success": True,
        "message": "Login successful.",
        "user_id": user_id,
        "username": username,
    }


# ---------- History Endpoint ----------
@app.get("/history")
def get_history(user_id: int) -> List[Message]:
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """
        SELECT role, message
        FROM messages
        WHERE user_id = ?
        ORDER BY id ASC
        """,
        (user_id,),
    )
    rows = c.fetchall()
    conn.close()

    return [{"role": role, "message": msg} for (role, msg) in rows]


# ---------- Home Page (Simple UI + Auth + History) ----------
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
                display: flex;
                flex-direction: column;
                min-height: 100vh;
            }
            .navbar {
                text-align: center;
                padding: 20px 0;
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
                max-width: 900px;
                margin: 10px auto 20px auto;
                padding: 0 20px 20px 20px;
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 14px;
            }
            /* Auth bar */
            .auth-bar {
                background: rgba(10, 12, 20, 0.9);
                border-radius: 10px;
                padding: 10px 12px;
                border: 1px solid rgba(255,255,255,0.06);
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 8px;
                font-size: 0.85rem;
            }
            .auth-bar input {
                background: #0b0d15;
                border-radius: 8px;
                border: 1px solid #2a2f42;
                color: #fff;
                padding: 5px 8px;
                font-size: 0.85rem;
            }
            .auth-bar button {
                padding: 6px 10px;
                border-radius: 8px;
                border: none;
                background: linear-gradient(135deg,#32e0a1,#1aa36f);
                color: #000;
                font-size: 0.8rem;
                font-weight: 600;
                cursor: pointer;
            }
            .auth-message {
                color: #f5f5f7;
                font-size: 0.8rem;
            }
            .auth-muted {
                color: #9ea2b3;
            }
            .auth-logged {
                display: flex;
                align-items: center;
                gap: 10px;
            }

            /* Simple Q&A box */
            .assistant-box {
                background: rgba(10, 12, 20, 0.85);
                padding: 20px;
                border-radius: 14px;
                border: 1px solid rgba(255,255,255,0.06);
                box-shadow: 0 0 25px rgba(0,0,0,0.6);
            }
            .assistant-box h2 {
                margin-top: 0;
                margin-bottom: 10px;
                font-size: 1.1rem;
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
                font-size: 0.95rem;
            }
            .ask-button {
                width: 100%;
                padding: 10px;
                border-radius: 10px;
                border: none;
                background: linear-gradient(135deg,#32e0a1,#1aa36f);
                color: #000;
                font-size: 1rem;
                font-weight: bold;
                cursor: pointer;
            }
            #answer {
                margin-top: 15px;
                white-space: pre-wrap;
                border-top: 1px solid rgba(255,255,255,0.08);
                padding-top: 10px;
                font-size: 0.95rem;
            }

            /* History box */
            .history-box {
                background: rgba(5, 7, 14, 0.9);
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.04);
                padding: 10px 12px;
                font-size: 0.85rem;
                max-height: 220px;
                overflow-y: auto;
            }
            .history-entry {
                margin-bottom: 8px;
            }
            .history-entry strong {
                color: #32e0a1;
            }

            .footer {
                text-align: center;
                font-size: 0.75rem;
                color: #8a8f9e;
                margin: 10px 0 18px 0;
                opacity: 0.6;
            }
        </style>
    </head>
    <body>
        <header class="navbar">
            <span>Health Assistant AI</span>
        </header>

        <main class="content">
            <!-- Auth bar -->
            <div class="auth-bar">
                <div id="auth-logged-out">
                    <span class="auth-muted">Log in or sign up to save your questions and answers:</span>
                    <input id="authUsername" type="text" placeholder="Username" />
                    <input id="authPassword" type="password" placeholder="Password" />
                    <button onclick="signup()">Sign up</button>
                    <button onclick="login()">Log in</button>
                </div>
                <div id="auth-logged-in" style="display:none" class="auth-logged">
                    <span>Logged in as <strong id="currentUserLabel"></strong></span>
                    <button onclick="loadHistory()">Load history</button>
                    <button onclick="logout()">Log out</button>
                </div>
                <div id="authMessage" class="auth-message"></div>
            </div>

            <!-- Main Q&A box -->
            <div class="assistant-box">
                <h2>Ask a health-related question</h2>
                <textarea id="question" placeholder="Example: Why do I feel lightheaded when I stand up?"></textarea>
                <button class="ask-button" onclick="ask()">Ask</button>
                <div id="answer"></div>
            </div>

            <!-- History panel (when logged in + loaded) -->
            <div class="history-box" id="historyBox">
                <em>History will appear here after you log in and click "Load history".</em>
            </div>
        </main>

        <footer class="footer">
            Educational information only — not medical advice or diagnosis.
        </footer>

        <script>
            const authLoggedOut = document.getElementById('auth-logged-out');
            const authLoggedIn = document.getElementById('auth-logged-in');
            const authMsg = document.getElementById('authMessage');
            const currentUserLabel = document.getElementById('currentUserLabel');
            const historyBox = document.getElementById('historyBox');

            function getCurrentUser() {
                const userId = localStorage.getItem('health_user_id');
                const username = localStorage.getItem('health_username');
                if (userId && username) {
                    return { userId: parseInt(userId), username };
                }
                return null;
            }

            function setCurrentUser(userId, username) {
                localStorage.setItem('health_user_id', String(userId));
                localStorage.setItem('health_username', username);
                updateAuthUI();
            }

            function clearCurrentUser() {
                localStorage.removeItem('health_user_id');
                localStorage.removeItem('health_username');
                updateAuthUI();
            }

            function updateAuthUI() {
                const user = getCurrentUser();
                authMsg.textContent = '';
                if (user) {
                    authLoggedOut.style.display = 'flex';
                    authLoggedOut.style.visibility = 'hidden';
                    authLoggedOut.style.position = 'absolute';
                    authLoggedIn.style.display = 'flex';
                    currentUserLabel.textContent = user.username;
                } else {
                    authLoggedOut.style.display = 'flex';
                    authLoggedOut.style.visibility = 'visible';
                    authLoggedOut.style.position = 'static';
                    authLoggedIn.style.display = 'none';
                    currentUserLabel.textContent = '';
                    historyBox.innerHTML = '<em>History will appear here after you log in and click "Load history".</em>';
                }
            }

            function showAuthMessage(text) {
                authMsg.textContent = text;
            }

            async function signup() {
                const username = document.getElementById('authUsername').value.trim();
                const password = document.getElementById('authPassword').value;

                if (!username || !password) {
                    showAuthMessage("Please enter username and password.");
                    return;
                }

                try {
                    const res = await fetch('/signup', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username, password })
                    });
                    const data = await res.json();
                    showAuthMessage(data.message || '');
                    if (data.success) {
                        setCurrentUser(data.user_id, data.username);
                    }
                } catch (err) {
                    console.error(err);
                    showAuthMessage("Error during signup.");
                }
            }

            async function login() {
                const username = document.getElementById('authUsername').value.trim();
                const password = document.getElementById('authPassword').value;

                if (!username || !password) {
                    showAuthMessage("Please enter username and password.");
                    return;
                }

                try {
                    const res = await fetch('/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username, password })
                    });
                    const data = await res.json();
                    showAuthMessage(data.message || '');
                    if (data.success) {
                        setCurrentUser(data.user_id, data.username);
                    }
                } catch (err) {
                    console.error(err);
                    showAuthMessage("Error during login.");
                }
            }

            function logout() {
                clearCurrentUser();
                showAuthMessage("Logged out.");
            }

            async function loadHistory() {
                const user = getCurrentUser();
                if (!user) {
                    showAuthMessage("You must be logged in to load history.");
                    return;
                }

                try {
                    const res = await fetch('/history?user_id=' + user.userId);
                    const data = await res.json();

                    historyBox.innerHTML = "";
                    if (!data || data.length === 0) {
                        historyBox.innerHTML = "<em>No saved history yet. Ask a question and I'll start saving your chats.</em>";
                        return;
                    }

                    for (const entry of data) {
                        const div = document.createElement('div');
                        div.className = 'history-entry';
                        const who = entry.role === 'user' ? 'You' : 'Assistant';
                        div.innerHTML = "<strong>" + who + ":</strong> " + entry.message;
                        historyBox.appendChild(div);
                    }
                } catch (err) {
                    console.error(err);
                    showAuthMessage("Error loading history.");
                }
            }

            async function ask() {
                const questionEl = document.getElementById('question');
                const answerDiv = document.getElementById('answer');
                const text = questionEl.value.trim();

                if (!text) {
                    answerDiv.textContent = "Please type a question.";
                    return;
                }

                answerDiv.textContent = "Thinking...";
                const user = getCurrentUser();

                const body = user
                    ? { question: text, user_id: user.userId }
                    : { question: text };

                try {
                    const res = await fetch('/ask', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body)
                    });
                    const data = await res.json();
                    answerDiv.textContent = data.answer || "I couldn't generate a response. Please try again.";
                } catch (err) {
                    console.error(err);
                    answerDiv.textContent = "There was an error contacting the server. Please try again.";
                }
            }

            // Initialize auth UI on load
            updateAuthUI();
        </script>
    </body>
    </html>
    """


# ---------- Ask Endpoint (with history saving) ----------
@app.post("/ask")
def ask_health_question(q: Question):
    """
    Takes a question and returns an answer.
    If user_id is provided, saves the conversation in the database.
    """
    text_lower = q.question.lower()
    emergencies = [
        "not breathing",
        "can't breathe",
        "cannot breathe",
        "bleeding a lot",
        "overdose",
        "suicidal",
        "kill myself",
        "want to hurt myself",
        "heart attack",
        "stroke",
        "chest pain",
        "passed out",
        "unconscious",
    ]

    # Emergency check
    if any(word in text_lower for word in emergencies):
        answer = (
            "⚠️ Your message sounds like it could involve a serious or emergency situation.\n\n"
            "Please call 911 or your local emergency number, or go to the nearest emergency room or urgent care "
            "immediately. This assistant cannot evaluate or respond to emergencies."
        )
    else:
        answer = call_health_assistant(q.question)

    # Save history if we have a logged-in user
    if q.user_id is not None:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO messages (user_id, role, message) VALUES (?, ?, ?)",
            (q.user_id, "user", q.question),
        )
        c.execute(
            "INSERT INTO messages (user_id, role, message) VALUES (?, ?, ?)",
            (q.user_id, "assistant", answer),
        )
        conn.commit()
        conn.close()

    return {"answer": answer}
