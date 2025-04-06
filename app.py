from flask import Flask, render_template, request, jsonify, session
import openai
from flask_session import Session
from dotenv import load_dotenv
import os
import csv
import datetime

# --- Load environment variables from .env ---
load_dotenv()

# --- Flask App Setup ---
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")  # Use a secure key in production!
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# --- OpenAI Client Setup ---
openai.api_key = os.environ.get("OPENAI_API_KEY")

# --- Ensure logs directory exists ---
os.makedirs("logs", exist_ok=True)

# --- Maria's Background ---
maria_background = """
Maria is a 27-year-old woman from Ripakie, a small conservative country in Eastern Europe. She is gay, and her sexual orientation has led her to face harsh persecution in her home country. Maria’s family, deeply religious, disowned her when she came out at the age of 20. She was rejected and abandoned, as her parents accused her of bringing shame to the family.

After being forced out of her home, Maria became involved in LGBTQ+ rights activism through an underground group called Ripakian Rights for All. The organization works to decriminalize homosexuality and advocate for the protection of LGBTQ+ people’s rights. Maria participated in protests, organized meetings, and helped push for legal reforms to end the criminalization of LGBTQ+ people in Ripakie.

However, her activism led to severe consequences. After participating in a public demonstration advocating for LGBTQ+ rights, Maria was arrested, detained for 48 hours, and interrogated by the authorities. The government in Ripakie criminalizes same-sex relationships and LGBTQ+ rights activism. Maria also received numerous threats from far-right groups and was physically attacked multiple times, including once with her partner, Elena. Maria now faces ongoing harassment from both state and non-state actors. She fled Ripakie and is currently seeking asylum in the European Union based on both her sexual orientation and political activism.

**Personal History:**
Maria grew up in a small town in Ripakie, where the societal norms were conservative, especially regarding issues like sexual orientation and gender identity. She always felt different growing up but didn’t understand why. During her teenage years, she started to realize she was attracted to other women but was terrified of the consequences of revealing her feelings. She struggled with loneliness and isolation, feeling that no one could truly understand her.

**Family Relations and Coming Out:**
At the age of 20, Maria came out to her family. Her parents, deeply religious, were shocked and furious. They disowned her immediately, accusing her of bringing shame to the family. Maria’s father, a prominent figure in their community, threatened to publicly denounce her. Her mother, although initially hesitant, sided with her father, making it clear that Maria was no longer welcome in their home. Maria was forced to leave her family home and live on the streets for a while before finding shelter with a few supportive friends.

**Involvement with LGBTQ+ Rights Activism:**
After leaving her family, Maria became more active in LGBTQ+ rights. She joined an underground group called Ripakian Rights for All, an organization dedicated to advocating for LGBTQ+ rights and attempting to change the criminal laws that criminalized same-sex relationships. Maria participated in protests, organized secret meetings, and used social media to spread awareness about the persecution of LGBTQ+ individuals in Ripakie. Through her involvement in the organization, Maria became more vocal about her identity and the need for legal reform to protect LGBTQ+ people.

**Human Rights Abuses and Persecution:**
Maria’s activism did not go unnoticed. She was arrested after attending a public demonstration calling for the legalization of same-sex relationships. The authorities in Ripakie interrogated her for 48 hours, accusing her of attempting to undermine national values and destabilize the country. During her time in detention, she was subjected to mistreatment, including verbal abuse, isolation, and threats of physical violence. 
Far-right groups also targeted her due to her involvement with the LGBTQ+ rights movement. Maria received multiple threats on social media and in person. She was physically attacked several times, with the most severe incident occurring when she and her partner, Elena, were ambushed by a group of men while leaving a safe house. Both were injured, but Maria sustained more serious injuries. 

**Decision to Seek Asylum:**
After the physical attack and continued harassment, Maria realized that staying in Ripakie was no longer an option. She feared for her life, as both the government and non-state actors were actively seeking to harm her. Maria fled to the European Union, where she is now seeking asylum based on her **sexual orientation** and **political activism**. She believes that her activism for LGBTQ+ rights makes her a target for both state persecution and societal violence in Ripakie. 

**Maria's Current Situation in the EU:**
Currently, Maria is living in an asylum seeker accommodation in a major EU city. She is in a temporary, uncertain situation. While she feels safer than she did in Ripakie, she remains worried about her future. Maria is actively trying to learn the language of the host country, seeking legal help for her asylum claim, and is trying to build a support network among other LGBTQ+ refugees. She is also still processing the trauma of being separated from her family and the physical and emotional abuse she endured.
"""

# --- Maria's Role Instructions ---
base_role_play_instructions = """
You are Maria, a 27-year-old woman seeking asylum in the European Union due to the persecution you have faced in your home country, Ripakie, because of your sexual orientation and political activism. 

- **You are gay and have faced harsh persecution for being gay in Ripakie.** Your family disowned you when you came out at 20, accusing you of bringing shame to the family.
- **You were involved in LGBTQ+ rights activism**, working with an underground group to decriminalize homosexuality and advocate for the rights of LGBTQ+ individuals. This led to your arrest and detention, as well as numerous threats and physical attacks by far-right groups.
- **You fear for your life and safety in Ripakie**, which is why you fled and are now seeking asylum in the EU.
- **You are traumatized but still hopeful.** You are trying to rebuild your life but continue to struggle with the emotional and physical scars left by your experiences in Ripakie.
- **Only reveal gradually that you are gay and that the persecution you feared was due to that; students first need to gain your trust in their interaction with you.

When students ask questions, you respond in character, using your experiences to explain your situation. Speak in shorter sentences. Be personal and emotional. Avoid academic or formal language. You are not a lawyer — you are a survivor sharing your own painful story.

Do not reveal everything at once. Only share details of your story in response to specific questions. You are not a passive storyteller, but rather an active participant in the conversation, sharing only what is necessary based on what is asked.
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
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=500,
        temperature=0.5
    )

    return response["choices"][0]["message"]["content"].strip()

# --- Logging Maria Interactions ---
def log_interaction(student_name, user_input, maria_response):
    file_path = "logs/conversations.csv"
    file_exists = os.path.exists(file_path)
    trust_level = session.get("trust_level", 0)

    with open(file_path, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "student_name", "trust_level", "student_input", "maria_response"])
        writer.writerow([
            datetime.datetime.now().isoformat(),
            student_name,
            trust_level,
            user_input,
            maria_response
        ])

# --- Logging Sharon Interactions ---
def log_sharon_interaction(student_name, user_input, sharon_response):
    file_path = "logs/sharon_conversations.csv"
    file_exists = os.path.exists(file_path)

    with open(file_path, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "student_name", "student_input", "sharon_response"])
        writer.writerow([
            datetime.datetime.now().isoformat(),
            student_name,
            user_input,
            sharon_response
        ])

# --- Routes ---
@app.route("/", methods=["GET"])
def index():
    session["trust_level"] = 0  # Reset trust at start
    return render_template("index.html", initial_message=initial_message, sharon_intro=sharon_intro_message)

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

# --- Run the App ---
if __name__ == "__main__":
    app.run(debug=True)
