
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
