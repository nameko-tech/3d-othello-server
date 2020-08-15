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
    # print(type(data))
    return jsonify({'data': str(list(map(bytes.decode, list(data))))}), 200


@app.route('/get/<room_name>')
def get(room_name):
    data = cache.hgetall(f'room:{room_name}')
    print(list(data))
    return jsonify({'data': str(data)}), 200


@ socketio.on('room')
def room(message):
    print()
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
        print(f'room creator joined to {room_name_key}')
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
    print(items)
    if not (items.get('white') or items.get('black')):
        print('変ですねえ')
        emit('room', {"status": "fail", "room": room_name, "message": "変ですねえ"})
        return
    yourColor = ''
    if items.get('black'):
        print('おまえは白')
        yourColor = 'white'
    else:
        print('お前は黒')
        yourColor = 'black'
    join_room(room_name_key)
    cache.hset(room_name_key, yourColor, str(request.sid))
    # ここでプレイヤーの登録Done、初期ボードを登録
    cache.hset(room_name_key, 'board', json.dumps(initial_board.initial_board))
    cache.hset(room_name_key, 'next', 'black')
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
    generated_board = generate_can_place(initial_board.initial_board)
    emit('game', {"board": generated_board, "count": "<何手目か>",
                  "turn": "black"}, room=room_name_key)
    # session['receive_count'] = session.get('receive_count', 0) + 1
    # emit('my_response',
    #      {'data': 'In rooms: ' + ', '.join(rooms()),
    #       'count': session['receive_count']})
    # emit('my_response', {"hello": "hello...?"})
    return


@ socketio.on('game')
def game(message):
    if not (message.get('piece') and message.get('room')):
        return
    print(message["piece"], message["room"])
    room_name_key = f'room:{message["room"]}'
    board = json.loads(cache.hget(room_name_key, 'board').decode())
    current = cache.hget(room_name_key, 'next')
    print(dict(board))
    new_next = "white" if current.decode() == "black" else "black"
    new_board = update_board(board, message.get('piece'))
    cache.hset(room_name_key, "next", new_next)
    cache.hset(room_name_key, "board", json.dumps(new_board))
    generated_board = generate_can_place(new_board)
    emit('game', {"board": generated_board, "count": "<何手目か>",
                  "turn": current.decode()}, room=room_name_key)


@ socketio.on('connect')
def test_connect():
    print(f'{request.sid} has connected')
    emit('my_response', {'data': 'Connected', 'count': 0})


@ socketio.on('disconnect')
def test_disconnect():
    # DBからdisconnectした人のデータを抹消する
    # 一人目でwaitingだった場合は、部屋を抹消
    # ゲーム中だった場合は、もうひとりに知らせてから、部屋を抹消
    print('Client disconnected', request.sid)


def update_board(board, piece):
    return board


def generate_can_place(board):
    for i in range(6):
        for j in range(6):
            for k in range(6):
                board["board"][i][j][k]["can_place"] = True
    return board


"""
"
" ここから下は未使用
"
"""


@ socketio.on('my_event')
def test_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})


@ socketio.on('my_broadcast_event')
def test_broadcast_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         broadcast=True)


@ socketio.on('leave')
def leave(message):
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@ socketio.on('close_room')
def close(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
                         'count': session['receive_count']},
         room=message['room'])
    close_room(message['room'])


@ socketio.on('my_room_event')
def send_room_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         room=message['room'])


@ socketio.on('disconnect_request')
def disconnect_request():
    @ copy_current_request_context
    def can_disconnect():
        disconnect()

    session['receive_count'] = session.get('receive_count', 0) + 1
    # for this emit we use a callback function
    # when the callback function is invoked we know that the message has been
    # received and it is safe to disconnect
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']},
         callback=can_disconnect)


@ socketio.on('my_ping')
def ping_pong():
    emit('my_pong')
