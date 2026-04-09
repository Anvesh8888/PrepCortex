import os
from flask import Flask, render_template, request
from google import genai

app = Flask(__name__)

# Initialize Gemini Client
# It will automatically look for an environment variable named GEMINI_API_KEY
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route('/', methods=['GET', 'POST'])
def home():
    planner = ""
    if request.method == 'POST':
        days = request.form.get('days')
        subjects = request.form.get('subjects')
        difficulty = request.form.get('difficulty')
        hours = request.form.get('hours')

        # Updated prompt for Gemini
        prompt = (f"Create a study planner for {days} days. "
                  f"Subjects: {subjects}. Difficulty: {difficulty}. "
                  f"I have {hours} hours per day. Format the output clearly.")
        
        try:
            # Using the fast and free gemini-3-flash model
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt
            )
            planner = response.text
        except Exception as e:
            planner = f"Error: {str(e)}"

    return render_template('index.html', planner=planner)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
