from flask import Flask, render_template, request, redirect, url_for, session
from database import db
from models import User, Package, Item, UserItem

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dados.db'
app.config['SECRET_KEY'] = 'supersecretkey'
db.init_app(app)

with app.app_context():
    db.create_all()
    # Inicializa os pacotes e itens se não existirem
    if Package.query.count() == 0:
        for i in range(1, 19):
            package = Package(name=f'Pacote {i}')
            db.session.add(package)
            db.session.commit()
            for j in range(1, 10):
                item = Item(name=f'Carta {j}', package_id=package.id)
                db.session.add(item)
            db.session.commit()
    # Adiciona usuários de exemplo
    if User.query.count() == 0:
        users = [("Paulo Roberto", "https://www.facebook.com/pauloroberto.lopessousa/"), ("André Valença", "https://www.facebook.com/andrevalenca/")]
        for username, web_address in users:
            new_user = User(username=username, web_address=web_address)
            db.session.add(new_user)
        db.session.commit()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('select_user'))
    
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    packages = Package.query.all()
    user_items = UserItem.query.filter_by(user_id=user_id).all()
    user_items_dict = {user_item.item_id: user_item for user_item in user_items}
    
    current_package_id = session.get('current_package_id') or request.args.get('current_package_id')
    if current_package_id:
        current_package_id = int(current_package_id)
    else:
        current_package_id = packages[0].id if packages else None

    return render_template('index.html', user=user, packages=packages, user_items=user_items_dict, current_package_id=current_package_id)

@app.route('/set_user', methods=['POST'])
def set_user():
    user_id = request.form['user_id']
    session['user_id'] = user_id
    return redirect(url_for('index'))

@app.route('/add_user', methods=['POST'])
def add_user():
    username = request.form['username']
    web_address = request.form['web_address']
    if username and web_address:
        new_user = User(username=username, web_address=web_address)
        db.session.add(new_user)
        db.session.commit()
    return redirect(url_for('select_user'))

@app.route('/get_user', methods=['POST'])
def get_user():
    user_id = request.form['user_id']
    user = User.query.get(user_id)
    if user:
        return f"{user.username}: {user.web_address}"
    return "Usuário não encontrado"

@app.route('/update_user', methods=['POST'])
def update_user():
    user_id = request.form['user_id']
    username = request.form['username']
    web_address = request.form['web_address']
    user = User.query.get(user_id)
    if user:
        user.username = username
        user.web_address = web_address
        db.session.commit()
    return redirect(url_for('select_user'))

@app.route('/delete_user', methods=['POST'])
def delete_user():
    user_id = request.form['user_id']
    user = db.session.get(User, user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('select_user'))

@app.route('/update_package/<int:package_id>', methods=['POST'])
def update_package(package_id):
    if 'user_id' not in session:
        return redirect(url_for('select_user'))
    
    user_id = session['user_id']
    package = db.session.get(Package, package_id)
    if not package:
        return redirect(url_for('index'))  # Redireciona de volta para a página principal se o pacote não existir

    for item in package.items:
        item_id = item.id
        has_card = request.form.get(f'has_card_{item_id}') == 'on'
        quantity = int(request.form.get(f'quantity_{item_id}', 0))
        
        user_item = UserItem.query.filter_by(user_id=user_id, item_id=item_id).first()
        
        if user_item:
            user_item.has_card = has_card or quantity > 0
            user_item.quantity = quantity
        else:
            user_item = UserItem(user_id=user_id, item_id=item_id, has_card=has_card or quantity > 0, quantity=quantity)
            db.session.add(user_item)
    
    db.session.commit()
    
    session['current_package_id'] = package_id
    return redirect(url_for('index'))

@app.route('/statistics')
def statistics():
    return render_template('statistics.html')

@app.route('/missing_cards_per_album_person')
def missing_cards_per_album_person():
    users = User.query.all()
    packages = Package.query.all()
    missing_cards_data = []

    for user in users:
        user_data = {'username': user.username, 'packages': []}
        for package in packages:
            missing_cards = []
            for item in package.items:
                user_item = UserItem.query.filter_by(user_id=user.id, item_id=item.id).first()
                if not user_item or not user_item.has_card:
                    missing_cards.append(item.name)
            user_data['packages'].append({
                'package_name': package.name,
                'missing_cards': missing_cards
            })
        missing_cards_data.append(user_data)

    return render_template('missing_cards_per_album_person.html', missing_cards_data=missing_cards_data)

@app.route('/total_cards_per_person')
def total_cards_per_person():
    users = User.query.all()
    total_cards_data = []

    for user in users:
        total_cards = UserItem.query.filter_by(user_id=user.id, has_card=True).count()
        total_cards_data.append({'username': user.username, 'total_cards': total_cards})

    return render_template('total_cards_per_person.html', total_cards_data=total_cards_data)

@app.route('/possible_card_donations')
def possible_card_donations():
    users = User.query.all()
    packages = Package.query.all()
    donations = []

    for user in users:
        user_total_cards = sum(ui.quantity for ui in UserItem.query.filter_by(user_id=user.id).all())
        for package in packages:
            for item in package.items:
                user_item = UserItem.query.filter_by(user_id=user.id, item_id=item.id).first()
                if user_item and user_item.quantity > 1:
                    for other_user in users:
                        if other_user.id != user.id:
                            other_user_total_cards = sum(ui.quantity for ui in UserItem.query.filter_by(user_id=other_user.id).all())
                            if other_user_total_cards < user_total_cards:
                                other_user_item = UserItem.query.filter_by(user_id=other_user.id, item_id=item.id).first()
                                if not other_user_item or not other_user_item.has_card:
                                    priority_position = get_priority_position(other_user.id)
                                    donations.append({
                                        'donor': user.username,
                                        'recipient': other_user.username,
                                        'card_name': item.name,
                                        'package_name': package.name,
                                        'priority_position': priority_position
                                    })

    return render_template('possible_card_donations.html', donations=donations)

@app.route('/priority')
def priority():
    users = User.query.all()
    packages = Package.query.all()
    priority_data = []

    for package in packages:
        package_priority = {'package_name': package.name, 'users': []}
        for user in users:
            user_items = UserItem.query.filter_by(user_id=user.id).all()
            total_cards = sum(1 for ui in user_items if ui.has_card and ui.item.package_id == package.id)
            missing_cards = 9 - total_cards  # 9 é o total de cartas em cada pacote
            if missing_cards == 1:
                missing_item = next(item for item in package.items if not any(ui.item_id == item.id and ui.has_card for ui in user_items))
                package_priority['users'].append({'username': user.username, 'missing_card': missing_item.name})
        priority_data.append(package_priority)

    return render_template('priority.html', priority_data=priority_data)


def get_priority_position(user_id):
    users = User.query.all()
    user_totals = [(user.id, sum(ui.quantity for ui in UserItem.query.filter_by(user_id=user.id).all())) for user in users]
    user_totals.sort(key=lambda x: x[1])
    for position, (uid, total) in enumerate(user_totals):
        if uid == user_id:
            return position + 1
    return -1

@app.route('/select_user')
def select_user():
    users = User.query.all()
    return render_template('select_user.html', users=users)

if __name__ == "__main__":
    app.run(debug=True)
