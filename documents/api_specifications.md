# 3D OTHELLO API 仕様

を記述していきます

---

## HTTP エンドポイント

### GET `/`

### GET `/data`

### GET `/get/<room_name>`

---

## Socketio エンドポイント

### `on connect`

特に何もしない

### `on disconnect`

- DB から disconnect した人のデータを抹消する
- 一人目で waiting だった場合は、部屋を抹消
- ゲーム中だった場合は、もうひとりに知らせてから、部屋を抹消

などを検討中

- ### `room`

部屋に関するあれこれを行う

<!-- <br/> -->

##### payload

```Json
{
	"roomName": "<あいことば>"
}
```

### `game`
