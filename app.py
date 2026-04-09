import os
from flask import Flask, render_template, request
from google import genai
from google.genai import types

app = Flask(__name__)

# 1. Initialize Gemini Client using the Stable v1 API
# This helps avoid '404 Not Found' errors common in beta versions
client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY"),
    http_options={'api_version': 'v1'}
)

@app.route('/', methods=['GET', 'POST'])
def home():
    planner = ""
    error_message = ""
    
    if request.method == 'POST':
        # Get parameters from the HTML form
        days = request.form.get('days')
        subjects = request.form.get('subjects')
        difficulty = request.form.get('difficulty')
        hours = request.form.get('hours')

        # Craft the prompt for the AI
        prompt = (
            f"Act as an expert academic coach. Create a detailed study planner for {days} days. "
            f"Subjects to cover: {subjects}. Difficulty level: {difficulty}. "
            f"Available study time: {hours} hours per day. "
            f"Provide the plan in a clean Markdown table with columns for Day, Focus Topic, and Goal."
        )
        
        try:
            # 2. Try the primary model (Gemini 2.5 Flash)
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt
            )
            planner = response.text
            
        except Exception as e:
            # 3. Handle 503 Service Unavailable (High Demand) with a Fallback
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                try:
                    # Switch to the Lite version which usually has more capacity
                    response = client.models.generate_content(
                        model="gemini-2.5-flash-lite", 
                        contents=prompt
                    )
                    planner = response.text
                except Exception as fallback_error:
                    error_message = "All AI lanes are full. Please wait 30 seconds and try again."
            else:
                error_message = f"An error occurred: {str(e)}"

    return render_template('index.html', planner=planner, error=error_message)

if __name__ == "__main__":
    # Use the port Render assigns, or default to 5000 for local testing
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
