# Universal helper functions: Logistics, Micro...etc
# Player state: Timing, Loops, Pause/Play status etc
# loads in a generic state implicitly for things like home menu state and common

# Possibly: Statistics like delay increase and such function

from helper.fsm import Machine
from helper.context import Context
from helper.config import Config

import os
import sys
import json
import time
import random
import helper.util as util
import helper.mouse as mouse
import importlib
import threading

config_path = 'helper/config/'


class Controller:
    state = {
        'logistic': [time.time()] * 4,
        'waiting': 0,
        'repairLoop': 0,
        'repairLoopComplete': 0,
        'bigLoop': 1,
        'bigLoopComplete': 0,
        'smallLoop': 10,
        'smallLoopComplete': 0,
        'runtime': time.time(),
        'sequence': 0
    }

    def __init__(self, files):
        self.scripts = {}

        for f in files:
            name, path = f.split('=')
            self.scripts[name] = Machine(self.getData(path)) if os.path.exists(path) else path
        self.scripts['common'] = Machine(self.getData(config_path + 'common.json'))
        self.scripts['fight'] = Machine(self.getData(config_path + 'commonBattle.json'))
        self.scripts['seq1'] = Machine(self.getData(config_path + 'teamSelectSeq1.json'))
        self.scripts['seq2'] = Machine(self.getData(config_path + 'teamSelectSeq2.json'))
        self.scripts['logi'] = Machine(self.getData(config_path + 'logistic.json'))
        self.scripts['end'] = Machine(self.getData(config_path + 'end.json'))

        runner = importlib.import_module(self.scripts['runner'], package=None)
        self.runner = runner.Runner(self)

        tr = threading.Thread(None, self.loopLogi, 'logi')
        tr.start()

    def getData(self, jsonPath):
        o = {}
        with open(jsonPath, 'r') as cfg:
            o = json.load(cfg)
        return o

    def play(self):
        tr = threading.Thread(None, self.playThread, 'play')
        tr.start()
        Controller.state['runtime'] = time.time()
        print('PLAY')

    def playThread(self):
        # do the big loops
        self.runner.play()
        t = time.time() - Controller.state['runtime']
        print('RUNTIME: ' + str(round(t, 1)) + 's (' + str(round(t / 60, 1)) + ' min)')
        util.alert()

    def pauseToggle(self):
        # this only works while a fsm is being run normally though (not forced)
        Machine.blocked = not Machine.blocked
        print('PAUSE' if Machine.blocked else 'RESUME')

    def kill(self):
        Machine.dead = True

    def clickAway(self, toMain=False):
        mEnd = self.scripts['end']
        ri = random.randint(0, 9)
        while not mEnd.checkState('loading'):
            if toMain:
                mEnd.forceRun('end big loop')
            else:
                mEnd.forceRun('rc' + str(ri))
            util.wait(0.25)

    def loopLogi(self):
        m = self.scripts['logi']
        while True:
            if Machine.dead:
                sys.exit()

            if m.checkState('logi1') or m.checkState('logi2'):
                Controller.state['waiting'] = max(0, Controller.state['waiting'] - 1)
                while m.checkState('logi1') or m.checkState('logi2'):
                    m.forceRun('logi2')
                    if m.checkState('logi1'):
                        util.wait(0.4)
                    elif m.checkState('logi2'):
                        util.wait(0.2)
            util.wait(0.4)

    def openLogi(self):
        m = self.scripts['common']
        while not m.checkState('logi opened'):
            m.forceRun('open logi')
            util.wait(2)

    def closeLogi(self):
        m = self.scripts['common']
        while not m.checkState('home'):
            m.forceRun('logi opened')
            util.wait(2)

    def getLogisticTimer(self):
        # maybe make this mult
        m = self.scripts['common']
        m.waitState('home')

        self.openLogi()
        ts = []
        for i in range(4):
            tr = threading.Thread(None, self.getSingleLogisticTimer, 'logi' + str(i), args=[i])
            ts.append(tr)
            tr.start()

        for t in ts:
            t.join()

        Controller.state['waiting'] = sum(1 for t in Controller.state['logistic'] if round(t - time.time()) < Config.i.data['min_time'])
        self.closeLogi()

    def getSingleLogisticTimer(self, i):
        # do ocr
        coord = [833, 148, 998, 187]    # TL and BR of first box
        offset = [0, 113, 225, 338]     # y offsets from top location

        xoff = Context.i.x
        yoff = Context.i.y + offset[i]
        convertedRegion = (
            coord[0] + xoff,
            coord[1] + yoff,
            coord[2] + xoff,
            coord[3] + yoff
        )
        remaining = util.getTimer(util.getScreenText(convertedRegion))
        while remaining is None:
            self.openLogi()
            remaining = util.getTimer(util.getScreenText(convertedRegion))
        remaining = round(time.time() + remaining)
        Controller.state['logistic'][i] = remaining

    def withdraw(self, grid):
        m = self.scripts['fight']
        m.forceRun('g' + str(grid))
        util.wait(0.2)
        m.forceRun('withdraw')
        util.wait(0.2)

    def swap(self, gFrom, gTo):
        m = self.scripts['fight']
        pFrom = m.state['g' + str(gFrom)].function['data']['points']
        pTo = m.state['g' + str(gTo)].function['data']['points']
        mouse.rDrag(*pFrom, *pTo, delay=0.15)
        util.wait(0.2)

    def increment(self, name, amount=1):
        Controller.state[name] += amount

    def decrement(self, name, amount=1):
        Controller.state[name] = max(0, Controller.state[name] - amount)

    def toggleSequence(self):
        Controller.state['sequence'] = (Controller.state['sequence'] + 1) % 2
