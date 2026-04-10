import os
import random
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from google import genai
import markdown
from markupsafe import Markup

# --- APP INITIALIZATION ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-prepcortex-key' # Required for secure WebSockets
socketio = SocketIO(app)

# --- AI SETUP ---
# Initialize client with stable v1 API
client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY"),
    http_options={'api_version': 'v1'}
)

# The Waterfall List for high-demand fallback
FALLBACK_MODELS = [
    "gemini-2.5-flash",         # 1. Primary choice (Smartest)
    "gemini-2.5-flash-lite",    # 2. Backup 1 (Fast & high capacity)
    "gemini-1.5-flash",         # 3. Backup 2 (Older but very stable)
    "gemini-1.5-flash-8b"       # 4. Backup 3 (Smallest, almost never busy)
]


# --- MULTIPLAYER GAME STATE ---
# Dictionary to store active rooms, players, and scores
games = {} 

# Sample Mock Questions (You can replace this with AI-generated ones later!)
QUIZ_QUESTIONS = [
    {"q": "What does CPU stand for?", "options": ["Central Process Unit", "Computer Personal Unit", "Central Processing Unit", "Central Processor Unit"], "answer": 2},
    {"q": "Which language is used for styling web pages?", "options": ["HTML", "JQuery", "CSS", "XML"], "answer": 2},
    {"q": "What is 8 + 5?", "options": ["12", "13", "14", "15"], "answer": 1}
]


# --- FLASK ROUTES (HTTP) ---
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
                response = client.models.generate_content(
                    model=model_name, 
                    contents=prompt
                )
                
                # Convert AI Markdown to clean HTML
                raw_markdown = response.text
                planner_html = Markup(markdown.markdown(raw_markdown, extensions=['tables']))
                success = True
                print(f"Success using model: {model_name}")
                break 
                
            except Exception as e:
                print(f"Model {model_name} failed or busy. Trying next...")
                continue
        
        if not success:
            error_message = "Wow, all AI servers are currently full! Please wait 30 seconds and try again."

    return render_template('index.html', planner=planner_html, error=error_message)

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')


# --- SOCKET.IO EVENTS (WEBSOCKETS) ---
@socketio.on('create_room')
def handle_create(data):
    username = data['username']
    # Generate a random 4-digit room code
    room_code = str(random.randint(1000, 9999))
    
    # Initialize the room memory
    games[room_code] = {
        "host": request.sid,
        "players": {request.sid: {"username": username, "score": 0}},
        "current_question": 0,
        "started": False
    }
    
    join_room(room_code)
    emit('room_created', {'room_code': room_code, 'players': get_players(room_code)})

@socketio.on('join_room')
def handle_join(data):
    username = data['username']
    room_code = data['room_code']
    
    if room_code in games and not games[room_code]['started']:
        games[room_code]['players'][request.sid] = {"username": username, "score": 0}
        join_room(room_code)
        # Blast updated player list to everyone in the room
        socketio.emit('player_joined', {'players': get_players(room_code)}, room=room_code)
        emit('join_success', {'room_code': room_code})
    else:
        emit('error', {'message': 'Room not found or game has already started!'})

@socketio.on('start_game')
def handle_start(data):
    room_code = data['room_code']
    if room_code in games and games[room_code]['host'] == request.sid:
        games[room_code]['started'] = True
        send_question(room_code)

@socketio.on('submit_answer')
def handle_answer(data):
    room_code = data['room_code']
    answer_idx = data['answer']
    
    room = games.get(room_code)
    if not room: return

    # Check answer (+3 for correct, -1 for wrong)
    correct_ans = QUIZ_QUESTIONS[room['current_question']]['answer']
    if answer_idx == correct_ans:
        room['players'][request.sid]['score'] += 3
    else:
        room['players'][request.sid]['score'] -= 1

    # Blast updated scores to everyone
    socketio.emit('update_scores', {'players': get_players(room_code)}, room=room_code)

    # Move to next question (simplification: we move on when the host answers)
    if request.sid == room['host']:
        room['current_question'] += 1
        if room['current_question'] < len(QUIZ_QUESTIONS):
            send_question(room_code)
        else:
            socketio.emit('game_over', {'players': get_players(room_code)}, room=room_code)


# --- HELPER FUNCTIONS ---
def get_players(room_code):
    return [p_data for sid, p_data in games[room_code]['players'].items()]

def send_question(room_code):
    q_data = QUIZ_QUESTIONS[games[room_code]['current_question']]
    # Send only the question and options, KEEP THE ANSWER SECRET on the server!
    safe_q = {"q": q_data["q"], "options": q_data["options"]}
    socketio.emit('new_question', safe_q, room=room_code)


# --- RUNNER ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # CRITICAL: We use socketio.run instead of app.run for WebSockets!
    socketio.run(app, host='0.0.0.0', port=port)
