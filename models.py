# models.py

from database import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    web_address = db.Column(db.String(150), nullable=False)
    items = db.relationship('UserItem', backref='user', lazy=True)

class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    items = db.relationship('Item', backref='package', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('package.id'), nullable=False)
    user_items = db.relationship('UserItem', backref='item', lazy=True)

    def __repr__(self):
        return f'<Item {self.name}>'

class UserItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    has_card = db.Column(db.Boolean, default=False)  # Novo campo para indicar se o usuário possui a carta

    def __repr__(self):
        return f'<UserItem user_id={self.user_id} item_id={self.item_id}>'
