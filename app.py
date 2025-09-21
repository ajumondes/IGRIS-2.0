# app.py

import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# --- App Initialization & Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-very-secret-key-that-you-should-change'

# Set up the database URI
basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
os.makedirs(instance_path, exist_ok=True) # Ensure the instance folder exists
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "igris.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Database & Login Manager Setup ---
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect here if user is not logged in

# --- Database Models (The "Blueprints") ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # For now, we'll store the raw JSON data. Later, this will be a trained model.
    model_data = db.Column(db.Text, nullable=True) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Web Page Routes ---
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/enroll')
@login_required
def enroll():
    profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    return render_template('enroll.html', profile_exists=(profile is not None))

# --- API Endpoint for Enrollment ---
@app.route('/api/enroll', methods=['POST'])
@login_required
def api_enroll():
    data = request.get_json()
    if not data or len(data) < 50: # Basic validation
        return jsonify({'status': 'error', 'message': 'Not enough data provided'}), 400

    # For now, just save the raw JSON. Later we'll train a model here.
    raw_json_data = json.dumps(data)
    profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    if profile:
        profile.model_data = raw_json_data
    else:
        profile = UserProfile(user_id=current_user.id, model_data=raw_json_data)
        db.session.add(profile)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Enrollment data saved!'})

# Add this new route to your app.py

# --- API Endpoint for Continuous Authentication ---
@app.route('/api/authenticate', methods=['POST'])
def api_authenticate():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data received'}), 400

    user_id = data.get('user_id')
    mouse_events = data.get('mouse_events', [])
    keyboard_events = data.get('keyboard_events', [])

    # --- THIS IS WHERE THE ML SCORING WILL HAPPEN IN THE FUTURE ---
    # For now, we'll just print what we received and return a dummy score.
    print(f"Received auth data for user: {user_id}")
    print(f"Mouse Events Count: {len(mouse_events)}")
    print(f"Keyboard Events Count: {len(keyboard_events)}")
    
    # In the future, you would load the user's model and calculate a real score.
    # For now, we'll pretend the user is always genuine.
    dummy_trust_score = 0.95
    decision = "Genuine"
    # ----------------------------------------------------------------

    return jsonify({
        'status': 'success',
        'trust_score': dummy_trust_score,
        'decision': decision
    })

# --- Main Execution ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # This creates the .db file and tables
    app.run(debug=True)