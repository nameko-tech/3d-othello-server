#!/usr/bin/env python
from flask import Flask, render_template, session, request, \
    copy_current_request_context, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
import os
import redis
import time
import random
import json
import initial_board
from flask_cors import CORS  # 追加
import board as board_manager

if os.environ.get("REDIS_URL"):
    url = os.environ.get("REDIS_URL")
    host_port = url[url.index("@") + 1:]
    host = host_port[:host_port.rindex(":")]
    port = int(url[url.rindex(":")+1:])
    i = url[url.rindex("/")+1:]
    password = i[i.index(":")+1:url.index("@")-8]
    print(url, host, port, password)
    cache = redis.Redis(host=host, port=port, password=password)
else:
    cache = redis.Redis(host='redis', port=6379)

app = Flask(__name__)
# CORS(app)
# app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/img'), 'favicon.ico', )


@app.route('/')
def index():
    return render_template('test.html')


@app.route('/data')
def data():
    data = cache.keys('*')
    return jsonify({'data': str(list(map(bytes.decode, list(data))))}), 200


@app.route('/get/<room_name>')
def get(room_name):
    data = cache.hgetall(f'room:{room_name}')
    return jsonify({'data': str(data)}), 200


@socketio.on('room')
def room(message):
    print('message arrived to room')
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
    generated_board = board_manager.generate_board_to_send(
        initial_board.initial_board)
    emit('game', {"board": generated_board,
                  "turn": "black"}, room=room_name_key)
    return


# この部屋、この色、このマスに置きたいよ！っていうのが飛んでくる
@socketio.on('game')
def game(message):
    if not (message.get('piece') and message.get('room') and message.get('color')):
        # send message that tells invalid
        return
    room_name_key = f'room:{message["room"]}'
    # その部屋のボードを取りに行く
    board = json.loads(cache.hget(room_name_key, 'board').decode())
    current_color = cache.hget(room_name_key, 'next').decode()
    if current_color != message["color"]:
        print("変です")
    # print(dict(board))
    new_next = "white" if current_color == "black" else "black"
    # update_board()する
    new_board = board_manager.update_board(
        board, message.get('piece'), message["color"])
    # print(new_board)
    cache.hset(room_name_key, "next", new_next)
    cache.hset(room_name_key, "board", json.dumps(new_board))
    generated_board = board_manager.generate_board_to_send(new_board)
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


@socketio.on_error()
def error_handler(e):
    print('error occurred: ' + str(e))


@socketio.on('message')
def handle_message(message):
    print('received message: ' + message)


@ socketio.on('disconnect')
def test_disconnect():
    # DBからdisconnectした人のデータを抹消する
    # 一人目でwaitingだった場合は、部屋を抹消
    # ゲーム中だった場合は、もうひとりに知らせてから、部屋を抹消
    print('Client disconnected', request.sid)
