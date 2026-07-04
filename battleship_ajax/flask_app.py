from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import json

app = Flask(__name__)

def get_codes():
    with open('games.txt', 'r') as f:
        codes = []
        for line in f.readlines():
            codes.extend(line.strip().split(','))
        return codes

def get_opponent_code(player_code):
    if not os.path.exists('games.txt'):
        return None
    with open('games.txt', 'r') as f:
        for line in f:
            players = line.strip().split(',')
            if len(players) == 2:
                if players[0] == player_code:
                    return players[1]
                elif players[1] == player_code:
                    return players[0]
    return None

def save_board(player_code, board_data):
    cleaned_board = {k: int(v) for k, v in board_data.items()}
    with open(f'board_{player_code}.json', 'w') as f:
        json.dump(cleaned_board, f)

def load_board(player_code):
    filename = f'board_{player_code}.json'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return None


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/play')
def join():
    return render_template('join.html')

@app.route('/create')
def create():
    return render_template('create.html')

@app.post('/new')
def create_game():
    player1_code = request.form.get('p1_code')
    player2_code = request.form.get('p2_code')
    if player1_code and player2_code:
        with open('games.txt', 'a') as f:
            f.write(f'{player1_code},{player2_code}\n')
    return redirect(url_for('home'))

@app.post('/place')
def place_ships():
    code = request.form.get('game_code')
    if code in get_codes():
        return render_template('place_ships.html', game_code=code)
    else:
        return redirect(url_for('join'))

@app.route('/game', methods=['GET', 'POST'])
def game():
    player_code = request.args.get('id')
    opponent_code = get_opponent_code(player_code) 
    if not player_code or not opponent_code:
        return "Invalid game or player code setup.", 400
    if request.method == 'POST' and 'board_data' in request.form:
        board_data_raw = request.form.get('board_data')
        if board_data_raw:
            save_board(player_code, json.loads(board_data_raw))
        return redirect(url_for('game', id=player_code))
    my_board = load_board(player_code)
    opp_board = load_board(opponent_code)
    if not my_board:
        return redirect(url_for('place_ships')) 
    if not opp_board:
        return render_template('waiting.html', player_code=player_code, opp_code=opponent_code)
    
    tracking_board = {}
    for cell, status in opp_board.items():
        if status in [2, 3]:
            tracking_board[cell] = status
        else:
            tracking_board[cell] = 0
    return render_template('game.html', player_code=player_code, opponent_code=opponent_code, my_board=my_board, tracking_board=tracking_board)

@app.post('/fire')
def fire_shot():
    player_code = request.json.get('player_code')
    target_cell = request.json.get('cell')    
    opponent_code = get_opponent_code(player_code)
    opp_board = load_board(opponent_code)    
    if not opp_board or target_cell not in opp_board:
        return jsonify({"success": False, "message": "Invalid target"})
    current_status = opp_board[target_cell]    
    if current_status == 1:
        opp_board[target_cell] = 3
        result = "hit"
    elif current_status == 0:
        opp_board[target_cell] = 2
        result = "miss"
    else:
        return jsonify({"success": False, "message": "Already attacked this cell!"})
    
    save_board(opponent_code, opp_board)
    won = 1 not in opp_board.values()
    return jsonify({"success": True, "result": result, "won": won})

@app.route('/state')
def game_state():
    player_code = request.args.get('id')
    opponent_code = get_opponent_code(player_code)
    my_board = load_board(player_code)
    opp_board = load_board(opponent_code)
    
    tracking_board = {}
    if opp_board:
        for cell, status in opp_board.items():
            tracking_board[cell] = status if status in [2, 3] else 0
    
    has_won = opp_board is not None and 1 not in opp_board.values()
    has_lost = my_board is not None and 1 not in my_board.values()
    winner = "you" if has_won else ("opponent" if has_lost else None)

    return jsonify({
        "my_board": my_board,
        "tracking_board": tracking_board,
        "opp_ready": opp_board is not None,
        "winner": winner
    })

@app.route('/cleanup')
def cleanup_game():
    player_code = request.args.get('id')
    opponent_code = get_opponent_code(player_code)    
    try:
        for code in [player_code, opponent_code]:
            if code:
                filename = f'board_{code}.json'
                if os.path.exists(filename):
                    os.remove(filename)
        if os.path.exists('games.txt') and player_code and opponent_code:
            with open('games.txt', 'r') as f:
                lines = f.readlines()           
            with open('games.txt', 'w') as f:
                for line in lines:
                    parts = line.strip().split(',')
                    if len(parts) == 2 and (
                        (parts[0] == player_code and parts[1] == opponent_code) or
                        (parts[0] == opponent_code and parts[1] == player_code)
                    ):
                        continue
                    f.write(line)                    
    except Exception as e:
        pass
    return redirect(url_for('home'))
   

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
