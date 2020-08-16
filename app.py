#!/usr/bin/env python
# from threading import Lock
from flask import Flask, render_template, session, request, \
    copy_current_request_context, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
import os
import redis
import random
import json
import initial_board
# from flask_cors import CORS  # 追加

cache = redis.Redis(host='redis', port=6379)
# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = "eventlet"

app = Flask(__name__)
# CORS(app)
# app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins="*")
# thread = None
# thread_lock = Lock()


# @app.after_request
# def after_request(response):
#     response.headers.add("Access-Control-Allow-Origin", "*")
#     response.headers.add("Access-Control-Allow-Headers", "*")
# #    response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
#     response.headers.add('Access-Control-Allow-Methods',
#                          'GET,PUT,POST,DELETE,OPTIONS')
# #    response.headers.add("allow", "GET,OPTIONS,HEAD")
#     return response


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit('my_response',
                      {'data': 'Server generated event', 'count': count},
                      )


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/img'), 'favicon.ico', )


@app.route('/')
def index():
    return render_template('test.html', async_mode=socketio.async_mode)


@app.route('/data')
def data():
    data = cache.keys('*')
    return jsonify({'data': str(list(map(bytes.decode, list(data))))}), 200


@app.route('/get/<room_name>')
def get(room_name):
    data = cache.hgetall(f'room:{room_name}')
    return jsonify({'data': str(data)}), 200


@ socketio.on('room')
def room(message):
    if not message.get('roomName'):
        print('no raw data')
        emit('room', {'status': 'error',
                      'message': 'no room name was given'})
        return
    # 送られた roomname↓
    room_name = message["roomName"]
    room_name_key = f'room:{message["roomName"]}'

    # 部屋が無かったら登録して、部屋に参加
    if not cache.hlen(room_name_key):
        print(f'{room_name_key} を登録したよ！')
        color = "white" if int(random.random() * 2) else "black"
        cache.hset(room_name_key, color, str(request.sid))
        cache.expire(room_name_key, 1800)
        join_room(room_name_key)
        emit('room', {"status": "waiting",
                      "room": room_name_key}, room=room_name_key)
        return

    # 既に二人いたら、だめだよって返す
    if cache.hexists(room_name_key, 'white') and cache.hexists(room_name_key, 'black'):
        print('既に存在してるよ')
        emit('room', {"status": "fail", "room": room_name})
        return
    # 二人目だったら 登録しつつ部屋に入る
    print('２人目だよ')
    items = {key.decode(): val.decode()
             for key, val in cache.hgetall(room_name_key).items()}
    if not (items.get('white') or items.get('black')):
        print('変ですねえ')
        emit('room', {"status": "fail", "room": room_name, "message": "変ですねえ"})
        return
    yourColor = ''
    if items.get('black'):
        # print('おまえは白')
        yourColor = 'white'
    else:
        # print('お前は黒')
        yourColor = 'black'
    join_room(room_name_key)
    cache.hset(room_name_key, yourColor, str(request.sid))
    # ここでプレイヤーの登録Done、初期ボードを登録
    cache.hset(room_name_key, 'board', json.dumps(initial_board.initial_board))
    cache.hset(room_name_key, 'next', "white")
    # ready to begin game
    # 1番さんに知らせる
    enemyColor = "black" if yourColor == 'white' else "white"
    emit("room", {
        "room": room_name_key,
        "status": "play",
        "color": enemyColor
    }, room=items[enemyColor])
    # 2番さんに知らせる
    emit("room", {
        "room": room_name_key,
        "status": "play",
        "color": yourColor
    })
    cache.expire(room_name_key, 1800)
    # gameチャンネルに どーん する
    generated_board = generate_board_to_send(initial_board.initial_board)
    emit('game', {"board": generated_board,
                  "turn": "black"}, room=room_name_key)
    # session['receive_count'] = session.get('receive_count', 0) + 1
    # emit('my_response',
    #      {'data': 'In rooms: ' + ', '.join(rooms()),
    #       'count': session['receive_count']})
    # emit('my_response', {"hello": "hello...?"})
    return


# この部屋、この色、このマスに置きたいよ！っていうのが飛んでくる
@ socketio.on('game')
def game(message):
    if not (message.get('piece') and message.get('room')):
        return
    piece = message["piece"]
    room_name = message["room"]
    room_name_key = f'room:{message["room"]}'
    # その部屋のボードを取りに行く
    board = json.loads(cache.hget(room_name_key, 'board').decode())
    current_color = cache.hget(room_name_key, 'next').decode()
    if current_color != message["color"]:
        print("変です")
    # print(dict(board))
    new_next = "white" if current_color == "black" else "black"
    # update_board()する
    new_board = update_board(board, message.get('piece'), message["color"])
    # print(new_board)
    cache.hset(room_name_key, "next", new_next)
    cache.hset(room_name_key, "board", json.dumps(new_board))
    generated_board = generate_board_to_send(new_board)
    # can_place() (ボードを渡すと、「両方の色」が置ける場所を配列で返してくれるくん)でどこに置けるかを知る
    # can_place(board) == {"white":[...], "black": [...]}
    # どっちも空配列だったらゲーム終了のお知らせ
    # 自分の置ける場所がなければパスです
    # この時点でDBを更新
    # update_board_with_can_place()して、boardオブジェクトにcan_placeを挿入
    # 送り返して終了
    emit('game', {"board": generated_board,
                  "turn": current_color}, room=room_name_key)


@ socketio.on('connect')
def test_connect():
    print(f'{request.sid} has connected')
    emit('my_response', {'data': 'Connected', 'count': 0})


# @ socketio.on('disconnect')
# def test_disconnect():
    # DBからdisconnectした人のデータを抹消する
    # 一人目でwaitingだった場合は、部屋を抹消
    # ゲーム中だった場合は、もうひとりに知らせてから、部屋を抹消
    # print('Client disconnected', request.sid)


def update_board(board, piece, color):
    col = 1 if color == "white" else 0
    enemyCol = 0 if color == "white" else 1
    # print(f'col:{col} enemy:{enemyCol}')

    for i in range(-1, 2):
        for j in range(-1, 2):
            for k in range(-1, 2):
                if(i == j == k == 0):
                    continue
                # piece から [i, j, k] 方向を向いてる
                next_place = False
                try:
                    next_place = board["board"][piece[0] +
                                                i][piece[1]+j][piece[2]+k]["piece"] != col
                    pass
                except:
                    continue
                if board["board"][piece[0]+i][piece[1]+j][piece[2]+k]["piece"] == enemyCol:
                    board["board"][piece[0]][piece[1]
                                             ][piece[2]] = {"piece": col}
                    # print('変わりそう')
                    step = 0  # WIP
                    if [i, j, k].count(0) == 0:
                        # print('３じげん')
                        if i == 1 and j == 1 and k == 1:
                            step = min(6-piece[i], 6-piece[j], 6-piece[k])
                        elif i == 1 and j == 1 and k == -1:
                            step = min(6-piece[i], 6-piece[j], piece[k])
                        elif i == 1 and j == -1 and k == 1:
                            step = min(6-piece[i], piece[j], 6-piece[k])
                        elif i == 1 and j == -1 and k == -1:
                            step = min(6-piece[i], piece[j], piece[k])
                        elif i == -1 and j == 1 and k == 1:
                            step = min(piece[i], 6-piece[j], 6-piece[k])
                        elif i == -1 and j == 1 and k == -1:
                            step = min(piece[i], 6-piece[j], piece[k])
                        elif i == -1 and j == -1 and k == 1:
                            step = min(piece[i], piece[j], 6-piece[k])
                        elif i == -1 and j == -1 and k == -1:
                            step = min(piece[i], piece[j], piece[k])
                            # step = min(1, 2, 3)
                    elif [i, j, k].count(0) == 1:
                        # print('２じげん')
                        if i == 1 and j == 1:
                            step = min(6-piece[i], 6-piece[j])
                        elif i == -1 and j == 1:
                            step = min(piece[i], 6-piece[j])
                        elif i == 1 and j == -1:
                            step = min(6-piece[i], piece[j])
                        elif i == -1 and j == -1:
                            step = min(piece[i], piece[j])
                            #
                        elif i == 1 and k == 1:
                            step = min(6-piece[i], 6-piece[k])
                        elif i == -1 and k == 1:
                            step = min(piece[i], 6-piece[k])
                        elif i == 1 and k == -1:
                            step = min(6-piece[i], piece[k])
                        elif i == -1 and k == -1:
                            step = min(piece[i], piece[k])
                            #
                        elif j == 1 and k == 1:
                            step = min(6-piece[j], 6-piece[k])
                        elif j == -1 and k == 1:
                            step = min(piece[j], 6-piece[k])
                        elif j == 1 and k == -1:
                            step = min(6-piece[j], piece[k])
                        elif j == -1 and k == -1:
                            step = min(piece[j], piece[k])
                        step = min(1, 2)
                    else:
                        # print('１じげん')
                        if i == 1:
                            step = 6 - piece[i]
                        elif i == -1:
                            step = piece[i]
                        elif j == 1:
                            step = 6 - piece[j]
                        elif j == -1:
                            step = piece[j]
                        elif k == 1:
                            step = 6 - piece[k]
                        elif k == -1:
                            step = piece[k]
                    # print(step)
                    for l in range(1, step):
                        if board["board"][piece[0]+l*i][piece[1]+l*j][piece[2]+l*k]["piece"] == -1:
                            # print(f'ないよ')
                            break
                        elif board["board"][piece[0]+l*i][piece[1]+l*j][piece[2]+l*k]["piece"] == col:
                            # print('あるよ')
                            for m in range(l):
                                # print('かえたよ')
                                board["board"][piece[0]+m*i][piece[1] +
                                                             m*j][piece[2]+m*k] = {"piece": col}
                            break
    return board


def can_place(board):
    res = {0: [], 1: []}
    colors = [0, 1]
    for col in colors:
        enemyCol = 1 if col == 0 else 0
        for x in range(6):
            for y in range(6):
                for z in range(6):
                    # print(f'{[x,y,z]}')
                    if board["board"][x][y][z] != -1:
                        continue
                    for i in range(-1, 2):
                        for j in range(-1, 2):
                            for k in range(-1, 2):
                                if(i == j == k == 0):
                                    continue
                                # [x,y,z] から [i, j, k] 方向を向いてる
                                next_place = False
                                try:
                                    next_place = board["board"][x +
                                                                i][y+j][z+k]["piece"] != col
                                    pass
                                except:
                                    continue
                                if board["board"][x+i][y+j][z+k]["piece"] == enemyCol:
                                    # print('置けるかも')
                                    step = 0  # WIP
                                    if [i, j, k].count(0) == 0:
                                        # print('３じげん')
                                        if i == 1 and j == 1 and k == 1:
                                            step = min(6-x, 6-y, 6-z)
                                        elif i == 1 and j == 1 and k == -1:
                                            step = min(
                                                6-x, 6-y, z)
                                        elif i == 1 and j == -1 and k == 1:
                                            step = min(
                                                6-x, y, 6-z)
                                        elif i == 1 and j == -1 and k == -1:
                                            step = min(
                                                6-x, y, z)
                                        elif i == -1 and j == 1 and k == 1:
                                            step = min(
                                                x, 6-y, 6-z)
                                        elif i == -1 and j == 1 and k == -1:
                                            step = min(
                                                x, 6-y, z)
                                        elif i == -1 and j == -1 and k == 1:
                                            step = min(
                                                x, y, 6-z)
                                        elif i == -1 and j == -1 and k == -1:
                                            step = min(
                                                x, y, z)
                                            # step = min(1, 2, 3)
                                    elif [i, j, k].count(0) == 1:
                                        print('２じげん')

                                        if i == 1 and j == 1:
                                            step = min(6-x, 6-y)
                                        elif i == -1 and j == 1:
                                            step = min(x, 6-y)
                                        elif i == 1 and j == -1:
                                            step = min(6-x, y)
                                        elif i == -1 and j == -1:
                                            step = min(x, y)
                                            #
                                        elif i == 1 and k == 1:
                                            step = min(6-x, 6-y)
                                        elif i == -1 and k == 1:
                                            step = min(x, 6-z)
                                        elif i == 1 and k == -1:
                                            step = min(6-x, z)
                                        elif i == -1 and k == -1:
                                            step = min(x, z)
                                        elif j == 1 and k == 1:
                                            step = min(6-y, 6-z)
                                        elif j == -1 and k == 1:
                                            step = min(y, 6-z)
                                        elif j == 1 and k == -1:
                                            step = min(6-y, z)
                                        elif j == -1 and k == -1:
                                            step = min(y, z)
                                        step = min(1, 2)
                                    else:
                                        print('１じげん')

                                        if i == 1:
                                            step = 6 - x
                                        elif i == -1:
                                            step = x
                                        elif j == 1:
                                            step = 6 - y
                                        elif j == -1:
                                            step = y
                                        elif k == 1:
                                            step = 6 - z
                                        elif k == -1:
                                            step = z
                                    print(step)
                                    for l in range(step):
                                        if board["board"][x+l*i][y+l*j][z+l*k]["piece"] == -1:
                                            print(f'')
                                            break
                                        elif board["board"][x+l*i][y+l*j][z+l*k]["piece"] == col:
                                            res[col].append([x, y, z])
    return res


def generate_board_to_send(board):
    # print(type(board))
    for i in range(6):
        for j in range(6):
            for k in range(6):
                # print(type(board["board"][i][j][k]))
                board["board"][i][j][k]["can_place"] = True
    return board
