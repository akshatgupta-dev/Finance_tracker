from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_email_password'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

db = SQLAlchemy(app)
login_manager = LoginManager(app)
mail = Mail(app)

# Models

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    expenses = db.relationship('Expense', backref='owner', lazy=True)
    budget = db.relationship('Budget', backref='owner', lazy=True)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# Routes

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    # Redirect to login or dashboard based on user's authentication status
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Login failed. Check your username and password')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', expenses=expenses, budgets=budgets)

@app.route('/add_expense', methods=['POST'])
@login_required
def add_expense():
    amount = float(request.form['amount'])
    category = request.form['category']
    expense = Expense(amount=amount, category=category, user_id=current_user.id)
    db.session.add(expense)
    db.session.commit()
    check_budget_alerts(current_user)
    return redirect(url_for('dashboard'))

@app.route('/set_budget', methods=['POST'])
@login_required
def set_budget():
    category = request.form['category']
    amount = float(request.form['amount'])
    budget = Budget(category=category, amount=amount, user_id=current_user.id)
    db.session.add(budget)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def check_budget_alerts(user):
    expenses = Expense.query.filter_by(user_id=user.id).all()
    budgets = Budget.query.filter_by(user_id=user.id).all()
    
    for budget in budgets:
        total_spent = sum([expense.amount for expense in expenses if expense.category == budget.category])
        if total_spent >= budget.amount * 0.8:
            send_email_alert(user.email, budget.category, budget.amount, total_spent)

def send_email_alert(user_email, category, budget_amount, total_spent):
    msg = Message('Budget Alert', recipients=[user_email])
    msg.body = f"You're approaching your budget for {category}. You have spent {total_spent} out of {budget_amount}."
    mail.send(msg)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure this is within the app context
    app.run(debug=True)
