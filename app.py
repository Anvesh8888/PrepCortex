import os
from flask import Flask
from openai import OpenAI

app = Flask(__name__)
# Render will provide this key automatically once we set it up in their dashboard
client = OpenAI(api_key=os.environ.get("AI_API_KEY"))

@app.route('/')
def home():
    return "AI Website is Running!"

if __name__ == "__main__":
    app.run()