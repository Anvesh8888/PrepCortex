import os
from flask import Flask, render_template, request
from google import genai
import markdown
from markupsafe import Markup

app = Flask(__name__)

# Initialize client with stable v1 API
client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY"),
    http_options={'api_version': 'v1'}
)

# The Waterfall List: It will try these in order from top to bottom
FALLBACK_MODELS = [
    "gemini-2.5-flash",         # 1. Primary choice (Smartest)
    "gemini-2.5-flash-lite",    # 2. Backup 1 (Fast & high capacity)
    "gemini-1.5-flash",         # 3. Backup 2 (Older but very stable)
    "gemini-1.5-flash-8b"       # 4. Backup 3 (Smallest, almost never busy)
]

@app.route('/', methods=['GET', 'POST'])
def home():
    planner_html = ""
    error_message = ""
    
    if request.method == 'POST':
        days = request.form.get('days')
        subjects = request.form.get('subjects')
        difficulty = request.form.get('difficulty')
        hours = request.form.get('hours')

        # Clean prompt for Markdown tables
        prompt = (
            f"Generate a professional study plan for {days} days. "
            f"Subjects: {subjects}. Difficulty: {difficulty}. Time: {hours}hrs/day. "
            f"Instructions: Use a clean Markdown table for the daily schedule. "
            f"Use headers for sections. Do not include introductory or concluding conversational text. "
            f"Focus only on the schedule and actionable goals."
        )
        
        success = False
        
        # The Fallback Loop
        for model_name in FALLBACK_MODELS:
            try:
                # Try generating the response
                response = client.models.generate_content(
                    model=model_name, 
                    contents=prompt
                )
                
                # If successful, convert Markdown to HTML and break the loop
                raw_markdown = response.text
                planner_html = Markup(markdown.markdown(raw_markdown, extensions=['tables']))
                success = True
                print(f"Success using model: {model_name}") # This will show in Render Logs
                break 
                
            except Exception as e:
                # If it hits a 503 error, it silently ignores it and tries the next model
                print(f"Model {model_name} failed. Trying next...")
                continue
        
        # If it went through all 4 models and ALL were busy
        if not success:
            error_message = "Wow, all 4 AI servers are currently full! Please wait a minute and try again."

    return render_template('index.html', planner=planner_html, error=error_message)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
