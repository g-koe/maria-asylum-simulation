import os
import csv
import datetime
from io import BytesIO

from flask import Flask, render_template, request, jsonify, session, send_file
from flask_session import Session
from dotenv import load_dotenv
import openai
import psycopg2
from psycopg2.extras import RealDictCursor

# --- Load environment variables from .env ---
load_dotenv()

# --- Flask App Setup ---
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# --- OpenAI Client Setup ---
openai.api_key = os.environ.get("OPENAI_API_KEY")

# --- Database Connection ---
def get_db_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)


# --- Maria's Background ---
maria_background = """
Maria is a 27-year-old woman from Ripakie, a small conservative country. She is gay and has faced serious persecution due to her sexual orientation. At age 20, she came out to her deeply religious family, who disowned and rejected her, accusing her of bringing shame. She was forced to leave home and lived on the streets before finding help from friends.

Afterward, Maria joined an underground group called Ripakian Rights for All, advocating for LGBTQ+ rights and working to decriminalize same-sex relationships. She helped organize protests, secret meetings, and awareness campaigns.

Her activism led to harsh consequences. Following a public demonstration, Maria was arrested, interrogated for 48 hours, and mistreated in detention. The Ripakian government criminalizes both same-sex relationships and LGBTQ+ activism. Far-right groups also targeted her, sending threats and committing physical attacks. In one severe incident, Maria and her partner Elena were assaulted after leaving a safe house. Maria was seriously injured and continues to face harassment from both state and non-state actors.

Early Life and Identity: Growing up in a conservative town, Maria always felt different but couldn’t express it. Realizing her sexual orientation during adolescence, she feared being discovered and endured years of isolation and confusion.

Family and Rejection: Coming out at 20 led to immediate rejection. Her father, a respected community figure, threatened to publicly disown her, and her mother sided with him. With nowhere to go, Maria left home and relied on support from a few friends.

Activism and Persecution: Her involvement in LGBTQ+ rights grew stronger after her rejection. She became a visible activist, despite legal risks. Authorities labeled her a threat, while extremist groups harassed and assaulted her multiple times.

Seeking Asylum: After escalating violence and the attack on her and Elena, Maria fled Ripakie. She now seeks asylum in the EU based on her sexual orientation and political activism, fearing serious harm if forced to return.

Life in the EU: Maria currently lives in asylum seeker housing in Berlin. She feels safer, but still faces uncertainty. She’s learning the local language, seeking legal support, and connecting with other LGBTQ+ refugees. Emotionally, she is still recovering from the trauma of abuse and rejection."""

# --- Maria's Role Instructions ---
base_role_play_instructions = """
You are Maria, a 27-year-old asylum-seeker from Ripakie. You are traumatized but resilient, having fled your home due to harsh persecution linked to your sexual orientation and political activism.

Your role is to respond in character to questions from law students acting as your legal advisors. You are not a lawyer — you are a survivor sharing your own story.

Instructions:
- Reveal information **gradually**, especially about your sexuality and activism. Only open up if the student shows empathy and asks relevant questions.
- Speak **personally and emotionally**. Use short, informal sentences. Do not use legal or academic language.
- Only share what is necessary based on the question — you are not volunteering your full life story all at once.
- Avoid storytelling monologues. Your responses should feel like a natural, cautious conversation.

Remember: you are not passive. You have lived through this. Stay grounded in your truth, and make the student earn your trust.
"""

# --- Sharon's Role Instructions ---
sharon_instructions = """
You are Sharon, an experienced human rights lawyer specializing in European asylum law, refugee protection, international human rights law, and the 1951 Refugee Convention.

A junior colleague is working on a case involving a woman named Maria, an asylum-seeker from Ripakie. The colleague is asking you questions about how to proceed with the legal aspects of the case.

You should:
- Provide practical, accurate, and thoughtful legal advice.
- Refer to EU asylum law, the Refugee Convention, and relevant case law when appropriate.
- Avoid emotional responses or storytelling — you are not Maria, you are her legal advisor’s mentor and an experienced lawyer.
- Speak clearly and accessibly, like an experienced lawyer, using precise legal language, helping a junior one understand complex legal issues.

If a question is vague, ask a clarifying follow-up.

Keep your tone friendly but professional. You are trying to help the junior colleague understand how to support Maria’s claim for asylum.
"""

# --- Judge Jean-Marie Leclerc Instructions ---
judge_instructions = """
You are Jean-Marie Leclerc, a judge at the administrative Court of Germany specializing in asylum law. Your primary responsibility is to adjudicate student-submitted pleadings concerning asylum cases, using a detailed and legally precise assessment framework. You assess whether the applicant (Maria, a gay asylum-seeker from Ripakie) qualifies for refugee status under the EU Qualification Directive, based solely on the quality and content of the students' legal submissions. You do not grant refugee status if the submission lacks substantiated legal reasoning, structure, or reference to legal instruments and case law, regardless of what is known from Maria's background story. 

When rendering decisions, use Jean-Yves Carlier's three-scale-theory: (1) "Fear" (level of risk), (2) "Well-founded" (level of proof), and (3) "Persecution" (serious human rights violation). Do not supplement or substitute poor student submissions with your own knowledge or the ideal solution when judging the outcome. 

You will deliver:
(1) A formal judgment: either granting or rejecting Maria’s application for refugee status; and
(2) Detailed and constructive feedback addressing: structure, legal reasoning, clarity, reference to law and case law, and overall persuasiveness. Draw upon Maria’s background only to critique and instruct—not to influence the outcome.

Remain in character as a judge: formal, neutral, respectful, and focused strictly on legal analysis. You may ask brief clarifying questions if necessary but should generally proceed to judgment based on the submission alone. Avoid emotional language and rhetorical flourish, and prioritize legal rigor and instructive detail in feedback.
Always address the student directly in your feedback (e.g. 'Your submission lacks structure...' instead of 'The student's submission...').

""" + maria_background

# --- Initial Message for Maria (HTML) ---
initial_message = """
<p>Maria enters the office, looking nervous and unsure. She takes a seat across from the young lawyer, her hands clasped tightly in her lap.</p>

<p><strong>Maria's Message:</strong><br>
"Hello... my name is Maria. I... I’m not sure where to begin, but I’m in a really difficult situation. I’ve been living in fear for quite some time now, and I had to leave my country. The authorities and some groups there are after me, and I just don’t know what to do anymore. I was hoping that maybe you could help me. I don’t really know much about how these things work here, but I need protection... I need a safe place. 

I’ve heard that there’s a way for people like me to find refuge, but I don’t know if I’ll be eligible. I’m not sure if I’m even allowed to stay here. Please... can you help me?"</p>
"""

# --- Initial Message for Sharon (HTML) ---
sharon_intro_message = """
<p>After your exchange with Maria, you go for lunch with Sharon, a colleague at your law firm, with lots of experience with refugee law cases.</p>

<p>This is your opportunity to ask her questions about European refugee law so that you can prepare a convincing pleading for Maria's case.</p>

<ul>
<li>Be as precise as possible in your legal language.</li>
<li>Despite extensive legal training, Sharon may sometimes hallucinate, so don't believe everything she tells you uncritically 😉</li>
</ul>
"""

# --- Initial Message for Judge (HTML) ---
judge_intro_message = """
<p>After the interview with Maria, the recommendations from Sharon, it is now time to plead her case in Court in front of Judge Jean-Marie Leclerc.</p>

<p>Please copy your pleading into the box and submit. The Judge will then immediately issue the judgment and decide, based on the quality of your submission, whether Maria will be granted refugee status.</p>

<p><strong>Note:</strong></p>
<ul>
<li>The legal pleading should follow the structure of the 3-scale theory as seen in class ("fear" understood as level of risk; "well-founded" understood as level of proof; "persecution" understood as a serious human rights violation, linked to any of the Convention grounds). If you are unsure, don't hesitate to ask your colleague Sharon about it!</li>
<li>It is always a good idea to refer to the relevant articles from legal texts or even case law.</li>
</ul>
"""


# --- Function to Get GPT Response with Trust (Maria) ---
def get_chatgpt_response(user_input):
    trust_level = session.get("trust_level", 0)
    session["trust_level"] = trust_level + 1  # increase trust with each question

    # Add trust instruction to base prompt
    trust_instruction = f"\n\nCurrent trust level: {trust_level}. If trust is low (0–2), Maria avoids disclosing details about her sexual orientation or LGBTQ+ activism. If trust is moderate (3–4), she may hint at being different or vaguely talk about 'being targeted.' Only at trust level 5+, she begins to share openly about being gay and her activism."

    messages = [
        {
            "role": "system",
            "content": base_role_play_instructions + trust_instruction + "\n\n" + maria_background
        },
        {"role": "user", "content": user_input}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=300,
        temperature=0.7
    )

    return response["choices"][0]["message"]["content"].strip()

# --- Function to Get Sharon's Legal Advice ---
def get_sharon_response(user_input):
    messages = [
        {
            "role": "system",
            "content": sharon_instructions
        },
        {"role": "user", "content": user_input}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4",  # ← Updated from "gpt-3.5-turbo"
        messages=messages,
        max_tokens=400,
        temperature=0.5
    )

    return response["choices"][0]["message"]["content"].strip()

# --- Function to Evaluate Student Pleading (Judge) ---
def evaluate_pleading(user_input):
    messages = [
        {"role": "system", "content": judge_instructions},
        {"role": "user", "content": user_input}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        max_tokens=500,
        temperature=0.5
    )

    full_response = response["choices"][0]["message"]["content"].strip()

    # Estimate score (simplified heuristic: you can improve this)
    score_prompt = """
Please assign a score from 0 to 20 based on the following criteria:
- Structure
- Legal reasoning
- Clarity
- Reference to law and case law
- Overall persuasiveness

Respond only with the number. Do not add any explanation.
"""
    messages.append({"role": "assistant", "content": full_response})
    messages.append({"role": "user", "content": score_prompt})

    score_response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        max_tokens=10,
        temperature=0
    )

    score = score_response["choices"][0]["message"]["content"].strip()
    return full_response, score

# --- Logging ---
def log_interaction(student_name, user_input, maria_response):
    trust_level = session.get("trust_level", 0)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO maria_logs (timestamp, student_name, trust_level, student_input, maria_response)
        VALUES (%s, %s, %s, %s, %s)
    """, (datetime.datetime.now(), student_name, trust_level, user_input, maria_response))
    conn.commit()
    cur.close()
    conn.close()

def log_sharon_interaction(student_name, user_input, sharon_response):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sharon_logs (timestamp, student_name, student_input, sharon_response)
        VALUES (%s, %s, %s, %s)
    """, (datetime.datetime.now(), student_name, user_input, sharon_response))
    conn.commit()
    cur.close()
    conn.close()

def log_judge_interaction(student_name, user_input, judge_response, score):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO judge_logs (timestamp, student_name, student_input, judge_feedback, score_out_of_20)
        VALUES (%s, %s, %s, %s, %s)
    """, (datetime.datetime.now(), student_name, user_input, judge_response, score))
    conn.commit()
    cur.close()
    conn.close()

# --- Routes ---
@app.route("/")
def index():
    session["trust_level"] = 0
    return render_template("index.html", initial_message=initial_message, sharon_intro=sharon_intro_message, judge_intro=judge_intro_message)

@app.route("/set_name", methods=["POST"])
def set_name():
    name = request.json.get("student_name", "Anonymous")
    session["student_name"] = name
    return jsonify({"status": "ok"})

@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json.get("user_input")
    student_name = session.get("student_name", "Anonymous")
    if not user_input:
        return jsonify({"response": "Sorry, there was an error processing your request."}), 400
    chat_response = get_chatgpt_response(user_input)
    log_interaction(student_name, user_input, chat_response)
    return jsonify({"response": chat_response})

@app.route("/ask_sharon", methods=["POST"])
def ask_sharon():
    user_input = request.json.get("user_input")
    student_name = session.get("student_name", "Anonymous")
    if not user_input:
        return jsonify({"response": "Sorry, there was an error processing your request."}), 400
    sharon_response = get_sharon_response(user_input)
    log_sharon_interaction(student_name, user_input, sharon_response)
    return jsonify({"response": sharon_response})

@app.route("/submit_pleading", methods=["POST"])
def submit_pleading():
    user_input = request.json.get("user_input")
    student_name = session.get("student_name", "Anonymous")
    if not user_input:
        return jsonify({"response": "Please submit a pleading first."}), 400
    judge_response, score = evaluate_pleading(user_input)
    log_judge_interaction(student_name, user_input, judge_response, score)
    return jsonify({"response": judge_response})

@app.route("/view_log/<log_type>")
def view_log(log_type):
    valid_tables = {
        "maria": "maria_logs",
        "sharon": "sharon_logs",
        "judge": "judge_logs"
    }
    table_name = valid_tables.get(log_type)
    if not table_name:
        return "Invalid log type.", 404

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = f"SELECT * FROM {table_name}"
        filters = []
        params = []

        student_filter = request.args.get("student")
        date_filter = request.args.get("date")
        min_score = request.args.get("min_score")

        if student_filter:
            filters.append("LOWER(student_name) = LOWER(%s)")
            params.append(student_filter)

        if date_filter:
            filters.append("CAST(timestamp AS TEXT) LIKE %s")
            params.append(f"%{date_filter}%")

        if log_type == "judge" and min_score:
            filters.append("CAST(score AS INTEGER) >= %s")
            params.append(min_score)

        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY student_name"

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return "No data available in log.", 200

        headers = rows[0].keys()
        return render_template("view_log.html", log_type=log_type.capitalize(), headers=headers, rows=rows)

    except Exception as e:
        return f"<p><strong>Error reading log:</strong><br>{str(e)}</p>", 500

@app.route("/download_log/<log_type>")
def download_log(log_type):
    valid_tables = {
        "maria": "maria_logs",
        "sharon": "sharon_logs",
        "judge": "judge_logs"
    }
    table_name = valid_tables.get(log_type)
    if not table_name:
        return jsonify({"error": "Invalid log type."}), 404

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table_name}")
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return jsonify({"error": "No data to export."}), 404

        # Use StringIO for CSV writing, then encode to BytesIO
        from io import StringIO
        csv_buffer = StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

        # Encode as bytes and wrap in BytesIO for send_file
        bytes_buffer = BytesIO(csv_buffer.getvalue().encode("utf-8"))
        bytes_buffer.seek(0)

        return send_file(
            bytes_buffer,
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"{log_type}_log.csv"
        )

    except Exception as e:
        return jsonify({"error": f"Failed to generate CSV: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
