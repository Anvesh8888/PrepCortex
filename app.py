import os
from flask import Flask, render_template, request
from google import genai
import markdown # Add this
from markupsafe import Markup # Add this

app = Flask(__name__)

client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY"),
    http_options={'api_version': 'v1'}
)

@app.route('/', methods=['GET', 'POST'])
def home():
    planner_html = "" # Changed to track HTML output
    error_message = ""
    
    if request.method == 'POST':
        days = request.form.get('days')
        subjects = request.form.get('subjects')
        difficulty = request.form.get('difficulty')
        hours = request.form.get('hours')

        # Updated Prompt: Specific instructions for no "fluff"
        prompt = (
            f"Generate a professional study plan for {days} days. "
            f"Subjects: {subjects}. Difficulty: {difficulty}. Time: {hours}hrs/day. "
            f"Instructions: Use a clean Markdown table for the daily schedule. "
            f"Use headers for sections. Do not include introductory or concluding conversational text. "
            f"Focus only on the schedule and actionable goals."
        )
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt
            )
            # Convert the AI's Markdown text into clean HTML
            raw_markdown = response.text
            planner_html = Markup(markdown.markdown(raw_markdown, extensions=['tables']))
            
        except Exception as e:
            error_message = "Server busy. Please try again in a moment."

    return render_template('index.html', planner=planner_html, error=error_message)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
