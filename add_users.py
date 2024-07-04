from database import db
from models import User
from werkzeug.security import generate_password_hash
from app import app

with app.app_context():
    db.create_all()
    
    # Adicionando usuários de teste
    users = [
        {"username": "PauloRoberto", "password": "senha123"},
        {"username": "Fernando", "password": "senha123"}
    ]
    
    for user_data in users:
        username = user_data['username']
        password = user_data['password']
        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
    
    db.session.commit()
    print("Usuários adicionados com sucesso.")
