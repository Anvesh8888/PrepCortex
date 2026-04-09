import os
from flask import Flask, render_template, request
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("AI_API_KEY"))

@app.route('/', methods=['GET', 'POST'])
def home():
    planner = ""
    if request.method == 'POST':
        # Get the 4 parameters from the form
        days = request.form.get('days')
        subjects = request.form.get('subjects')
        difficulty = request.form.get('difficulty')
        hours = request.form.get('hours')

        # The AI Prompt
        prompt = f"Create a study planner for {days} days. Subjects: {subjects}. Difficulty level: {difficulty}. I can study {hours} hours per day."
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        planner = response.choices[0].message.content

    return render_template('index.html', planner=planner)

if __name__ == "__main__":
    app.run(debug=True)
