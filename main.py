from flask import Flask, render_template, request, jsonify
import openai
import os
import json
import sqlite3

user_data = {}
app = Flask(__name__, static_url_path='/static')

def init_database():
    conn = sqlite3.connect("user_data.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_data (
        username TEXT PRIMARY KEY,
        messages TEXT
    )
    """)
    conn.commit()
    conn.close()

init_database()

def update_important_info(important_info, message, max_items=5):
    categories = ["lieux", "objets", "personnages", "actions", "missions"]

    for category in categories:
        if category not in important_info:
            important_info[category] = []

    for category in categories:
        if category in message.lower():
            if message not in important_info[category]:
                important_info[category].append(message)
                if len(important_info[category]) > max_items:
                    important_info[category].pop(0)

    return important_info

def generate_prompt(important_info):
    prompt = "Informations importantes:\n"
    for category, items in important_info.items():
        for item in items:
            prompt += f"- {item}\n"
        prompt += "\n"
    return prompt


def interact_with_gpt(messages, initial_info, character_info, universe_info):

    openai.api_key = os.getenv("OPENAI_API_KEY")

    important_info = {"lieux": [], "objets": [], "personnages": [], "actions": [], "missions": []}
    for message in messages:
        important_info = update_important_info(important_info, message["content"])

    prompt = generate_prompt(important_info)

    prompt += "\nVous êtes le maître d'un jeu immersif. Vous aidez le joueur à progresser dans l'histoire en posant des questions et en donnant des options. En tant que maître du jeu, vous pouvez décrire les scènes, créer des défis et proposer des choix aux joueurs. Vous êtes responsable de l'histoire et devez vous assurer que le joueur reste engagé et intéressé. Intégrez un système de statistiques, il y en a 4 : force, charisme, intelligence, dextérité, elles évoluent avec les actions du joueur et agissent sur les actions du joueur. Ajoute des émojis quand c'est pertinent et ne fais pas de réponse trop longues. Souvenez-vous que les informations importantes sur le personnage et l'univers ont déjà été fournies. Concentrez-vous sur les questions et les choix pour le joueur sans répéter les informations déjà partagées."

    # Construire un nouvel ensemble de messages avec le message système ajouté
    input_messages = [{"role": "system", "content": prompt}] + messages

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0301",
        messages=input_messages,
        temperature=0.9,
        max_tokens=400
    )

    return completion.choices[0].message["content"]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/talk", methods=["POST"])
def talk():
    user_message = request.form["message"]
    username = request.form["username"]
    character_info = request.form["characterInfo"]
    universe_info = request.form["universeInfo"]

    if username not in user_data:
        user_data[username] = {"messages": [{"role": "user", "content": user_message}]}
    else:
        user_data[username]["messages"].append({"role": "user", "content": user_message})

    response_message = interact_with_gpt(user_data[username]["messages"], user_data[username].get("initial_info", ""), character_info, universe_info)
    user_data[username]["messages"].append({"role": "assistant", "content": response_message})

    return jsonify({"response": response_message, "messages": user_data[username]["messages"]})

@app.route("/save_game", methods=["POST"])
def save_game():
    username = request.form["username"]
    messages = request.form["messages"]

    conn = sqlite3.connect("user_data.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_data (username, messages) VALUES (?, ?)", (username, messages))
    conn.commit()
    conn.close()

    return jsonify({"message": "Partie sauvegardée avec succès."})

@app.route("/load_game", methods=["GET"])
def load_game():
    username = request.args.get("username")

    conn = sqlite3.connect("user_data.db")
    c = conn.cursor()
    c.execute("SELECT messages FROM user_data WHERE username = ?", (username,))
    messages = c.fetchone()
    conn.close()

    if messages:
        return jsonify({"messages": messages[0]})
    else:
        return jsonify({"messages": None})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)