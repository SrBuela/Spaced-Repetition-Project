# auth.py - Complete working version
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta

def register_auth_routes(app):
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = User.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password, password):
                login_user(user)
                
                # Update streak on login (FIXED)
                today = date.today()
                last_study = user.last_study_date
                
                if last_study:
                    try:
                        if isinstance(last_study, str):
                            last_study = datetime.fromisoformat(last_study).date()
                    except:
                        last_study = None
                
                if last_study == today:
                    pass
                elif last_study == today - timedelta(days=1):
                    user.streak = (user.streak or 0) + 1
                elif last_study is None:
                    user.streak = 1
                else:
                    user.streak = 1
                
                user.last_study_date = today.isoformat()
                db.session.commit()
                
                flash(f'Welcome back, {username}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
        
        return render_template('login.html')
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if not username or not email or not password:
                flash('All fields are required!', 'error')
                return render_template('register.html')
            
            if password != confirm_password:
                flash('Passwords do not match!', 'error')
                return render_template('register.html')
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists!', 'error')
                return render_template('register.html')
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered!', 'error')
                return render_template('register.html')
            
            new_user = User(
                username=username,
                email=email,
                password=generate_password_hash(password),
                total_points=0,
                total_studied=0,
                streak=0,
                unlocked_decks=999,
                stars=0
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        
        return render_template('register.html')
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))