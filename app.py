from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_migrate import Migrate
from database import db
from models import User, Package, Item, UserItem, PriorityCard

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dados.db'
app.config['SECRET_KEY'] = 'supersecretkey'
db.init_app(app)
migrate = Migrate(app, db)

# Função para popular a tabela de cartas prioritárias
def populate_priority_cards():
    priority_cards = [
        {"card_name": "Carta 1", "package_id": 1},
        {"card_name": "Carta 2", "package_id": 2},
        # Adicione mais cartas conforme necessário
    ]
    for card in priority_cards:
        new_priority_card = PriorityCard(card_name=card["card_name"], package_id=card["package_id"])
        db.session.add(new_priority_card)
    db.session.commit()

# Função para inicializar cartas para um usuário
def initialize_user_cards(user_id):
    packages = Package.query.all()
    for package in packages:
        for item in package.items:
            user_item = UserItem(user_id=user_id, item_id=item.id, has_card=False, quantity=0)
            db.session.add(user_item)
    db.session.commit()

with app.app_context():
    db.create_all()
    # Inicializa os pacotes e itens se não existirem
    if Package.query.count() == 0:
        for i in range(1, 19):
            package = Package(name=f'Pacote {i}')
            db.session.add(package)
            for j in range(1, 10):
                item = Item(name=f'Carta {j}', package_id=package.id)
                db.session.add(item)
        db.session.commit()

    # Adiciona usuários de exemplo
    if User.query.count() == 0:
        users = [("Paulo Roberto", "https://gettraveltowngame.net/b3fdfae3-c815-4bbf-9b72-b4e4869975c2/"), ("Letícia", "https://gettraveltowngame.net/42670bf5-e231-4a00-ab30-4a4c8ff0d480/")]
        for username, web_address in users:
            new_user = User(username=username, web_address=web_address)
            db.session.add(new_user)
            db.session.commit()
            initialize_user_cards(new_user.id)  # Inicializa cartas para o novo usuário

    # Popula a tabela de cartas prioritárias
    if PriorityCard.query.count() == 0:
        populate_priority_cards()

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

    # Passando o número do álbum para o template
    album_number = current_package_id

    return render_template('index.html', user=user, packages=packages, user_items=user_items_dict, current_package_id=current_package_id, album_number=album_number)

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
        initialize_user_cards(new_user.id)  # Inicializa cartas para o novo usuário
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
    data = request.get_json()
    user_id = data['user_id']
    username = data.get('username')
    web_address = data.get('web_address')
    is_premium = data.get('is_premium')

    user = User.query.get(user_id)
    if user:
        if username:
            user.username = username
        if web_address:
            user.web_address = web_address
        if is_premium is not None:
            user.is_premium = is_premium
        db.session.commit()

    return jsonify({"status": "success"}), 200

@app.route('/delete_user', methods=['POST'])
def delete_user():
    user_id = request.form['user_id']
    user = User.query.get(user_id)

    if user:
        UserItem.query.filter_by(user_id=user_id).delete()
        db.session.delete(user)
        db.session.commit()

    return redirect(url_for('select_user'))

@app.route('/update_package/<int:package_id>', methods=['POST'])
def update_package(package_id):
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Usuário não autenticado"}), 403

    user_id = session['user_id']
    package = db.session.get(Package, package_id)
    if not package:
        return jsonify({"status": "error", "message": "Pacote não encontrado"}), 404

    updated = False
    for item in package.items:
        item_id = item.id
        has_card = request.form.get(f'has_card_{item_id}') == 'on'
        is_golden = request.form.get(f'is_golden_{item_id}') == 'on'
        quantity = 0 if is_golden else int(request.form.get(f'quantity_{item_id}', 0))

        user_item = UserItem.query.filter_by(user_id=user_id, item_id=item_id).first()
        if user_item:
            user_item.has_card = has_card
            user_item.is_golden = is_golden
            user_item.quantity = quantity
            updated = True
        else:
            user_item = UserItem(user_id=user_id, item_id=item_id, has_card=has_card, is_golden=is_golden, quantity=quantity)
            db.session.add(user_item)
            updated = True

    if updated:
        db.session.commit()

    return jsonify({"status": "success"}), 200

@app.route('/statistics')
def statistics():
    return render_template('statistics.html')

@app.route('/missing_cards_per_album_person', methods=['GET', 'POST'])
def missing_cards_per_album_person():
    users = User.query.order_by(User.username).all()
    selected_user_id = None
    missing_cards_data = []

    if request.method == 'POST':
        selected_user_id = request.form.get('user_id')
        if selected_user_id:
            selected_user = User.query.get(selected_user_id)
            packages = Package.query.all()
            user_data = {'username': selected_user.username, 'packages': []}
            for package in packages:
                missing_cards = []
                for item in package.items:
                    user_item = UserItem.query.filter_by(user_id=selected_user.id, item_id=item.id).first()
                    if not user_item or not user_item.has_card:
                        missing_cards.append(item.name)
                user_data['packages'].append({
                    'package_name': package.name,
                    'missing_cards': missing_cards
                })
            missing_cards_data.append(user_data)

    return render_template('missing_cards_per_album_person.html', users=users, missing_cards_data=missing_cards_data, selected_user_id=selected_user_id)

@app.route('/total_cards_per_person')
def total_cards_per_person():
    users = User.query.all()
    total_cards_data = []

    for user in users:
        total_cards = UserItem.query.filter_by(user_id=user.id, has_card=True).count()
        total_cards_data.append({'username': user.username, 'total_cards': total_cards})

    return render_template('total_cards_per_person.html', total_cards_data=total_cards_data)

@app.route('/possible_card_donations', methods=['GET', 'POST'])
def possible_card_donations():
    users = User.query.order_by(User.username).all()  # Ordena os usuários pelo nome de usuário
    packages = Package.query.all()
    possible_donations = []
    priority_donations = []
    other_donations = []
    donor = None  # Inicializar a variável donor como None

    if request.method == 'POST':
        donor_id = request.form['recipient_id']  # O usuário selecionado é o doador, não o destinatário
        donor = User.query.get(donor_id)

        if donor:
            for package in packages:
                for item in package.items:
                    donor_item = UserItem.query.filter_by(user_id=donor.id, item_id=item.id).first()
                    if donor_item and donor_item.quantity > 1:
                        for user in users:
                            if user.id != donor.id:
                                recipient_item = UserItem.query.filter_by(user_id=user.id, item_id=item.id).first()
                                if not recipient_item or not recipient_item.has_card:
                                    donation_data = {
 'donor': donor.username,
 'recipient': user.username,
 'card_name': item.name,
 'package_name': package.name,
 'priority_position': get_priority_position(donor.id)
                                    }
                                    possible_donations.append(donation_data)

            # Filtrar doações prioritárias
            for donation in possible_donations:
                package_id = Package.query.filter_by(name=donation['package_name']).first().id
                if is_priority_card(donation['card_name'], package_id):
                    priority_donations.append(donation)
                else:
                    other_donations.append(donation)

            # Ordenar as doações de prioridade pela posição de prioridade
            priority_donations.sort(key=lambda x: x['priority_position'])

    return render_template('possible_card_donations.html', priority_donations=priority_donations, other_donations=other_donations, users=users, recipient=donor)

def is_priority_card(card_name, package_id):
    return PriorityCard.query.filter_by(card_name=card_name, package_id=package_id).first() is not None

def get_priority_position(user_id):
    users = User.query.all()
    user_totals = [(user.id, sum(ui.quantity for ui in UserItem.query.filter_by(user_id=user.id).all()), user.is_premium, user.id) for user in users]
    user_totals.sort(key=lambda x: (x[2], x[1], x[3]))  # Prioridade: premium, total de cartas, ordem de chegada
    for position, (uid, total, is_premium, user_id) in enumerate(user_totals):
        if uid == user_id:
            return position + 1
    return -1

@app.route('/select_recipient', methods=['GET', 'POST'])
def select_recipient():
    if request.method == 'POST':
        recipient_id = request.form['recipient_id']
        return redirect(url_for('possible_card_donations', recipient_id=recipient_id))

    users = User.query.all()
    return render_template('select_recipient.html', users=users)

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

@app.route('/select_user')
def select_user():
    users = User.query.order_by(User.username).all()  # Ordena os usuários pelo nome de usuário
    return render_template('select_user.html', users=users)

@app.route('/reset_user_cards', methods=['POST'])
def reset_user_cards():
    data = request.get_json()
    if not data or 'user_id' not in data:
        return {"status": "error", "message": "Dados inválidos"}, 400

    user_id = data['user_id']

    # Remove todos os UserItems do usuário
    UserItem.query.filter_by(user_id=user_id).delete()
    db.session.commit()

    # Inicializa novamente com has_card=False e quantity=0
    initialize_user_cards(user_id)

    return {"status": "success"}, 200

if __name__ == "__main__":
    app.run(debug=True)
    
