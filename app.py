from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import requests
import logging
from config import config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Загрузка конфигурации
env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[env])

# Настройка базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'cfd6245c36bd276cff4769d9fce4cf0dbc056f4e1a014c912cb9d23507bb3efe'
app.config['UPLOAD_FOLDER'] = 'static/avatars'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Проверка и создание папки для аватаров
avatars_folder = os.path.join(os.getcwd(), 'static', 'avatars')
if not os.path.exists(avatars_folder):
    os.makedirs(avatars_folder)

# Настройка Socket.IO
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode=None,
    logger=True,
    engineio_logger=True,
    ping_timeout=5000,
    ping_interval=25000
)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class UserReaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tutor_id = db.Column(db.Integer, db.ForeignKey('tutor.id'), nullable=False)
    reaction_type = db.Column(db.String(10), nullable=False)  # 'like' или 'dislike'
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'tutor_id', name='unique_user_tutor_reaction'),
    )

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.Float, nullable=True)
    avatar = db.Column(db.String(100), nullable=True)
    reactions = db.relationship('UserReaction', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Tutor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    subjects = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(100), nullable=False)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    reactions = db.relationship('UserReaction', backref='tutor', lazy=True)

tutors = [
    {"name": "Иван Иванов", "rating": 4.9, "subjects": "Математика, Физика", "image": "tutor1.jpg"},
    {"name": "Мария Петрова", "rating": 4.7, "subjects": "Английский язык", "image": "tutor2.jpg"},
    {"name": "Алексей Сидоров", "rating": 4.8, "subjects": "Информатика", "image": "tutor3.jpg"},
]

BOT_TOKEN = '8186615018:AAENdDsVYsPPCQHfdeG17t7kENBrblWXupU'
CHAT_ID = '689163231'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def home():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    # Отправляем текущие данные при подключении
    try:
        tutors = Tutor.query.all()
        for tutor in tutors:
            emit('reaction_update', {
                'tutor_id': tutor.id,
                'likes': tutor.likes,
                'dislikes': tutor.dislikes
            })
    except Exception as e:
        logger.error(f'Error sending initial data: {str(e)}')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('reaction')
def handle_socket_reaction(data):
    logger.info(f'Received reaction: {data}')
    try:
        tutor_id = data.get('tutor_id')
        reaction_type = data.get('type')
        user_id = data.get('user_id')
        
        if not all([tutor_id, reaction_type, user_id]):
            logger.error('Missing required data')
            return
        
        tutor = Tutor.query.get(tutor_id)
        user = User.query.get(user_id)
        
        if not tutor or not user:
            logger.error('Tutor or user not found')
            return
            
        # Проверяем, есть ли уже реакция от этого пользователя
        existing_reaction = UserReaction.query.filter_by(
            user_id=user_id,
            tutor_id=tutor_id
        ).first()
        
        if existing_reaction:
            logger.info('User already reacted')
            return
            
        # Создаем новую реакцию
        new_reaction = UserReaction(
            user_id=user_id,
            tutor_id=tutor_id,
            reaction_type=reaction_type
        )
        
        # Обновляем счетчики
        if reaction_type == 'like':
            tutor.likes += 1
        elif reaction_type == 'dislike':
            tutor.dislikes += 1
        
        db.session.add(new_reaction)
        db.session.commit()
        
        # Отправляем обновление всем клиентам
        emit('reaction_update', {
            'tutor_id': tutor_id,
            'likes': tutor.likes,
            'dislikes': tutor.dislikes,
            'user_id': user_id
        }, broadcast=True)
        
    except Exception as e:
        logger.error(f'Error handling socket reaction: {str(e)}')
        db.session.rollback()

@app.route('/tutors')
def tutors_page():
    try:
        tutors = Tutor.query.all()
        user_reactions = {}
        if 'user_id' in session:
            reactions = UserReaction.query.filter_by(user_id=session['user_id']).all()
            user_reactions = {r.tutor_id: r.reaction_type for r in reactions}
        return render_template('tutors.html', tutors=tutors, user_reactions=user_reactions)
    except Exception as e:
        logger.error(f'Error in tutors_page: {str(e)}')
        return 'Произошла ошибка при загрузке страницы', 500

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        message = request.form['message']

        text = (f"Новая заявка:\nИмя: {name}\nТелефон: {phone}\n"
                f"Email: {email}\nСообщение: {message}")

        send_to_telegram(text)
        return redirect(url_for('contact'))

    return render_template('contact.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        if User.query.filter_by(email=email).first():
            flash('Этот email уже зарегистрирован.', 'danger')
            return redirect(url_for('register'))

        new_user = User(name=name, email=email, role=role)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Регистрация успешна!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Неверный email или пароль.', 'danger')

    return render_template('login.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if request.method == 'POST':
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    user.avatar = filename
                    db.session.commit()
                    flash('Аватар успешно обновлен!', 'success')
                    return redirect(url_for('profile'))

        return render_template('profile.html', user=user)
    return redirect(url_for('login'))

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('home'))

@app.route('/api/reaction', methods=['POST'])
def handle_reaction():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json()
    tutor_id = data.get('tutor_id')
    reaction_type = data.get('type')
    user_id = session['user_id']
    
    if not all([tutor_id, reaction_type]):
        return jsonify({'error': 'Missing data'}), 400
        
    try:
        tutor = Tutor.query.get(tutor_id)
        if not tutor:
            return jsonify({'error': 'Tutor not found'}), 404
            
        # Проверяем, есть ли уже реакция от этого пользователя
        existing_reaction = UserReaction.query.filter_by(
            user_id=user_id,
            tutor_id=tutor_id
        ).first()
        
        if existing_reaction:
            return jsonify({'error': 'Already reacted'}), 400
            
        # Создаем новую реакцию
        new_reaction = UserReaction(
            user_id=user_id,
            tutor_id=tutor_id,
            reaction_type=reaction_type
        )
        
        # Обновляем счетчики
        if reaction_type == 'like':
            tutor.likes += 1
        elif reaction_type == 'dislike':
            tutor.dislikes += 1
            
        db.session.add(new_reaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'likes': tutor.likes,
            'dislikes': tutor.dislikes
        })
        
    except Exception as e:
        logger.error(f'Error in handle_reaction: {str(e)}')
        db.session.rollback()
        return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    # Настройка порта для Railway
    port = int(os.environ.get('PORT', 5000))
    if os.environ.get('FLASK_ENV') == 'production':
        # В production используем gunicorn
        app.run(host='0.0.0.0', port=port)
    else:
        # В development используем встроенный сервер Flask с socket.io
        socketio.run(app, host='0.0.0.0', port=port, debug=True)