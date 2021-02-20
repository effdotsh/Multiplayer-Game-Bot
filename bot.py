from websocket import WebSocketApp
import argparse

import time
import random
import json
import _thread as thread
import math
import requests
import json

import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--dash_foresight', '-df', default=15,
                    help='How many moves into the future the bot looks to dash (more for higher latency)', type=float)
parser.add_argument('--dodge_foresight', '-d', default=30, type=float)
parser.add_argument('--dash_thresh', default=1,
                    help='The amount of padding to give the collision area.', type=float)
parser.add_argument('--max_players', '-p', default=2,
                    help='How many players before bot leaves', type=int)
parser.add_argument('--min_players', default=0, type=int)

parser.add_argument('--fire_rate', '-f', default=0.4, type=float)

parser.add_argument('--bullet_speed', '-b', default=15, type=float)
parser.add_argument('--bullet_radius', '-rb', default=25, type=float)
parser.add_argument('--player_radius', '-rp', default=50, type=float)

parser.add_argument('--boom_thresh', '-bt', default=20, type=float)
parser.add_argument('--boom_scaler', '-bs', default=4, type=float)
parser.add_argument('--boom_base', '-bb', default=100, type=float)

parser.add_argument('--name', '-n', default='BotBoio', type=str)
parser.add_argument('--reset_score', '-rs', default='100', type=float)

parser.add_argument('--url', '-u', default='localhost:3000', type=str)
parser.add_argument('--poll_time', '-pt', default=3, type=int)

args = parser.parse_args()

radius = (args.player_radius + args.bullet_radius) * args.dash_thresh

fire_timer: float = 0
x = 0
y = 0
px = 0
py = 0
id = ''

z = 0

dodging = False
dashing = False

def set_boom(health):
    return args.boom_base + (args.boom_base - health) * args.boom_scaler


def random_dash(x, y, px, py):
    connecting_slope = (y - py) / (x - px)
    slope = -1 / connecting_slope

    mid_point = ((x + px) / 2)
    diff = abs(x - px)
    dash_x = mid_point + (diff / 4 + random.randint(int(diff / 6), int(diff / 2))) * random.choice((-1, 1))

    dash_y = slope * (dash_x - mid_point) + (py + y) / 2

    return dash_x - x, dash_y - y


def check_incoming(bullets, x, y, px, py):
    global dodging
    global dashing

    for b in bullets:
        if b['fired_by'] != id and 0 < b['x'] < 3000 and 0 < b['y'] < 3000 and b != bullets[0]:
            new_x = b['x']
            new_y = b['y']

            collide = False
            dashing = False
            for i in range(args.dodge_foresight):
                new_x += b['angle'][0]
                new_y += b['angle'][1]
                if math.dist((x, y), (new_x, new_y)) <= radius * args.dash_thresh:
                    collide = True
                    if i < args.dash_foresight:
                        dashing = True
                    break

            if collide:
                angle = random_dash(x, y, px, py)
                if not dodging:
                    dodging = True
                    ws.send(f'vel{angle[0]},{angle[1]}')
                if dashing:
                    ws.send('dash')
            else:
                dodging = False
                dashing = False


def fire(x, y, px, py, vel_x, vel_y):
    dist = math.dist((x, y), (px, py))
    travel_time = dist / args.bullet_speed
    target_x = px + vel_x * travel_time
    target_y = py + vel_y * travel_time
    # ws.send(f'fire{target_x - x}, {target_y - y}')


def filter_players(player):
    if player['spectating'] or not player['living']:
        return False
    else:
        return True


def ws_handler(ws, message):
    global fire_timer
    global x
    global y
    global px
    global py
    global id

    msg = json.loads(message)
    if msg['type'] == 'sync_player':
        this_player = msg['you_are']
        players = msg['info'][0]
        if not check_join(players):
            ws.close()
            os.execl(sys.executable, sys.executable, *sys.argv)

        bx = players[this_player]['x']
        by = players[this_player]['y']
        id = players[this_player]['id']
        x = bx
        y = by

        filtered = filter(filter_players, players)

        other = 0
        p_counter = 0
        dist = 10000
        other_id = players[this_player]['id']
        for p in filtered:
            if p['id'] != id and math.dist((p['x'], p['y']), (x, y)) < dist:
                other_id = p['id']
                dist = math.dist((p['x'], p['y']), (x, y))

        for p in players:
            if p['id'] == other_id:
                other = p_counter
            p_counter += 1

        px = players[other]['x']
        py = players[other]['y']

        if args.reset_score > 0 and players[this_player]['score'] >= args.reset_score:
            ws.close()
            os.execl(sys.executable, sys.executable, *sys.argv)

        if players[other]['living'] and other != this_player:
            if time.time() - fire_timer >= args.fire_rate:
                fire(bx, by, px, py, players[other]['vel_x'], players[other]['vel_y'])
                fire_timer = time.time()

            boom = set_boom(players[this_player]['health'])

            vel_x = 0
            vel_y = 0
            if math.dist((px, py), (bx, by)) > boom + args.boom_thresh:
                vel_x = px - bx
                vel_y = py - by
            elif math.dist((px, py), (bx, by)) < boom - args.boom_thresh:
                vel_x = bx - px
                vel_y = by - py

            # vel = legalize_move(vel_x, vel_y)
            # if not dodging:
            #     ws.send(f'vel{vel[0]},{vel[1]}')


        else:
            vel = legalize_move(2144 / 2 - bx, 1047 / 2 - by)
            ws.send(f'vel{vel[0]},{vel[1]}')

            ws.send(f'fire{random.randint(-1000, 1000)}, {random.randint(-1000, 1000)}')

    if msg['type'] == 'sync_bullet':
        bullets = msg['info'][0]
        check_incoming(bullets, x, y, px, py)


def on_error(ws, error):
    print(error)
    os.execl(sys.executable, sys.executable, *sys.argv)


def legalize_move(vel_x, vel_y):
    possible = [0, 1, -1]

    correct = bind_vector(vel_x, vel_y)
    vel = (0, 0)
    # Turn direction into 8 directional
    for dir_x in possible:
        for dir_y in possible:
            new = bind_vector(dir_x, dir_y)
            if math.dist(new, correct) < math.dist(correct, vel):
                vel = new
    return vel


def on_open(ws):
    def run(*args):
        while True:
            time.sleep(0.1)
            ws.send('sync')

    ws.send(f'name{args.name}')
    thread.start_new_thread(run, ())


def check_join(players):
    num_players = 0
    for p in players:
        if not p['spectating'] and p['name'] not in [args.name, '']:
            num_players += 1

    if args.min_players <= num_players < args.max_players:
        return True
    else:
        return False


def should_join():
    while True:
        try:
            site = requests.get(f'https://{args.url}/info', timeout=1)
            break
        except:
            pass
    decoded = json.loads(site.content.decode('utf8'))
    return check_join(decoded)


def bind_vector(x, y, magnitude=99999999):
    if x != 0 or y != 0:
        scaler = magnitude / math.sqrt(pow(x, 2) + pow(y, 2))
        x *= scaler
        y *= scaler
    else:
        x = -magnitude if x <= -magnitude else (magnitude if x >= magnitude else x)
        y = -magnitude if y <= -magnitude else (magnitude if y >= magnitude else y)
    return x, y


start_running = should_join()
while not start_running:
    time.sleep(args.poll_time)
    start_running = should_join()

ws = WebSocketApp(f'ws://{args.url}/ws', on_message=ws_handler, on_error=on_error)
ws.on_open = on_open
ws.run_forever()
