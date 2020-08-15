#!/usr/bin/env python
from threading import Lock
from flask import Flask, render_template, session, request, \
    copy_current_request_context, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
import os
import redis
from flask_cors import CORS  # 追加

cache = redis.Redis(host='redis', port=6379)
# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = "eventlet"

app = Flask(__name__)
CORS(app)
# app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins="*")
thread = None
thread_lock = Lock()


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

# methods=['POST', 'OPTIONS']


@app.route('/join', methods=['POST', 'OPTIONS'])
def sets():
    if request.method != 'POST':
        return jsonify({'message': 'option'}), 200
    # cache.set("room_name", )
    print(request.get_data())
    rawData = request.get_data()
    if not rawData:
        print('no raw data')
        return jsonify({'message': 'no data was given'}), 400
    rawBody = dict(request.get_json())
    if not rawBody["roomName"]:
        print('no room name')
        return jsonify({'message': 'no room name was given'}), 400
    print('roomname was: ' + rawBody["roomName"])
    # 送られた roomname↓
    room_name = rawBody["roomName"]

    # DBに問い合わせてそのroomがあるか確かめる
    # 無かったら登録して、 {isFirst: true} で返す
    # 二人目だったら 登録しつつ {isFirst: false} で返す
    # 既に二人いたら、だめだよって返す
    if True:
        # if able to play
        return jsonify({'message': 'success', 'isFirst': 'true'}), 200
    else:
        # too many people
        return jsonify({'message': 'too many people'}), 200


@app.route('/get')
def get_room():
    room_name = str(cache.get("price"))
    return f"The price is {room_name}."


@socketio.on('my_event')
def test_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})


@socketio.on('my_broadcast_event')
def test_broadcast_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         broadcast=True)


@socketio.on('join')
def join(message):
    print('someone want to join')
    print(message)
    # join_room(message['room'])
    # session['receive_count'] = session.get('receive_count', 0) + 1
    return
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('leave')
def leave(message):
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('close_room')
def close(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
                         'count': session['receive_count']},
         room=message['room'])
    close_room(message['room'])


@socketio.on('my_room_event')
def send_room_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         room=message['room'])


@socketio.on('disconnect_request')
def disconnect_request():
    @copy_current_request_context
    def can_disconnect():
        disconnect()

    session['receive_count'] = session.get('receive_count', 0) + 1
    # for this emit we use a callback function
    # when the callback function is invoked we know that the message has been
    # received and it is safe to disconnect
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']},
         callback=can_disconnect)


@socketio.on('my_ping')
def ping_pong():
    emit('my_pong')


@socketio.on('connect')
def test_connect():
    print('someone has connected')
    # with thread_lock:
    #     if thread is None:
    #         thread = socketio.start_background_task(background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected', request.sid)


# if __name__ == '__main__':
    # socketio.run(app, debug=True)
