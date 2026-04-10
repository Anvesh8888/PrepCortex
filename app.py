import gevent.monkey
gevent.monkey.patch_all()
import os
import random
import json
import PyPDF2
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from google import genai
import markdown
from markupsafe import Markup

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-prepcortex-key'
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='gevent', 
    engineio_logger=False, 
    always_connect=True
)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"), http_options={'api_version': 'v1'})
FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-1.5-flash"]

# --- GAME STATE ---
games = {} 

# --- HTTP ROUTES ---
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
            error_message = "All AI servers are currently full! Please wait 30 seconds and try again."

    return render_template('index.html', planner=planner_html, error=error_message)
    
@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['pdf']
    num_questions = request.form.get('num_questions', 5)
    
    try:
        # Extract text from PDF
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
            if len(text) > 30000: break # Limit text so AI isn't overwhelmed

        # Ask Gemini to generate JSON
        prompt = (
            f"Generate exactly {num_questions} multiple-choice questions from this text. "
            f"Output ONLY a raw JSON array. No markdown formatting, no backticks. "
            f"Format: [{{\"q\": \"Question?\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"answer\": 0}}]\n\n"
            f"Text: {text}"
        )

        for model in FALLBACK_MODELS:
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                raw_text = response.text.strip().removeprefix('```json').removesuffix('```').strip()
                questions = json.loads(raw_text)
                return jsonify({'questions': questions})
            except Exception as e:
                continue
                
        return jsonify({'error': 'AI failed to generate questions.'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- WEBSOCKETS ---
@socketio.on('create_room')
def handle_create(data):
    username = data['username']
    room_code = str(random.randint(1000, 9999))
    
    games[room_code] = {
        "host": request.sid,
        "players": {request.sid: {"username": username, "score": 0}},
        "questions": [], # Will be loaded from host's PDF
        "current_question": 0,
        "answers_this_round": set(), # Tracks who has answered
        "started": False
    }
    
    join_room(room_code)
    emit('room_created', {'room_code': room_code, 'players': get_players(room_code), 'is_host': True})

@socketio.on('join_room')
def handle_join(data):
    username = data['username']
    room_code = data['room_code']
    
    if room_code in games and not games[room_code]['started']:
        games[room_code]['players'][request.sid] = {"username": username, "score": 0}
        join_room(room_code)
        socketio.emit('player_joined', {'players': get_players(room_code)}, room=room_code)
        emit('join_success', {'room_code': room_code, 'is_host': False})
    else:
        emit('error', {'message': 'Room not found or game has already started!'})

@socketio.on('start_game')
def handle_start(data):
    room_code = data['room_code']
    questions = data['questions']
    
    if room_code in games and games[room_code]['host'] == request.sid:
        games[room_code]['questions'] = questions
        games[room_code]['started'] = True
        send_question(room_code)

@socketio.on('submit_answer')
def handle_answer(data):
    room_code = data['room_code']
    answer_idx = data['answer']
    
    room = games.get(room_code)
    if not room or request.sid in room['answers_this_round']: return

    # Record answer
    room['answers_this_round'].add(request.sid)
    correct_ans = room['questions'][room['current_question']]['answer']
    
    if answer_idx == correct_ans:
        room['players'][request.sid]['score'] += 3
    else:
        room['players'][request.sid]['score'] -= 1

    # Tell this specific player they are waiting
    emit('waiting_for_others')

    # Check if EVERYONE has answered
    if len(room['answers_this_round']) >= len(room['players']):
        # Send scores to everyone
        socketio.emit('round_results', {'players': get_players(room_code)}, room=room_code)
        
        # Wait 3 seconds so people can see the leaderboard, then next question
        socketio.sleep(3) 
        
        room['answers_this_round'].clear() # Reset for next round
        room['current_question'] += 1
        
        if room['current_question'] < len(room['questions']):
            send_question(room_code)
        else:
            socketio.emit('game_over', {'players': get_players(room_code)}, room=room_code)

def get_players(room_code):
    return [p_data for sid, p_data in games[room_code]['players'].items()]

def send_question(room_code):
    room = games[room_code]
    q_data = room['questions'][room['current_question']]
    
    safe_q = {
        "q": q_data["q"], 
        "options": q_data["options"], 
        "current": room['current_question'] + 1, 
        "total": len(room['questions'])
    }
    socketio.emit('new_question', safe_q, room=room_code)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
