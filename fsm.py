import util
import mouse

from config import Config
from context import Context
# multiple machines can be kept at the highest level and swapped between
# these can be controlled by another config that can tell what states scripts to load


class Machine:
    # The driver for the states

    # Map of custom functions
    # Map of names to states (this owns all steps)
    # Current/Previous state kept and updating
    # Check the current pixels to match against state
    # executes step functionality
    # supports pause
    # To/From json
    def __init__(self, data):
        self.state = {}
        for k, v in data['fsm'].items():
            self.state[k] = Step(v)
        self.cur = data['start']
        self.pre = None

    def run(self):
        cur = self.state[self.cur]
        while cur.next or cur.pixelCheck():
            if not cur.function:
                return
            self.execute()
            cur = self.state[self.cur]

    def checkForStates(self, states):
        for name in states:
            if self.state[name].pixelCheck():
                return name
        return None

    def checkNext(self):
        cur = self.state[self.cur]
        nextStep = self.checkForStates(cur.next)
        if nextStep:
            self.pre = self.cur
            self.cur = nextStep
            return True
        return False

    # runs the current step/state
    # wait to enter current pixel state (check if the wait is too long)
    # makes sure that it's still on current state while retrying if needed
    # does the action
    def execute(self):
        cur = self.state[self.cur]

        while not cur.pixelCheck():
            util.wait(0)
            self.checkNext()
            return

        # print(self.cur)
        # print(cur.function)
        cur.run()

        functionData = cur.function['data']
        util.wait(functionData['wait'], 0.15)
        if self.checkNext():
            return

        # retry loop, otherwise notify
        while cur.pixelCheck():
            cur.run()
            util.wait(functionData['retry'], 0.15)
            if self.checkNext():
                return


class Step:
    # Each state/node that can be controlled by the fsm

    # Custom machine function name (for complex steps that can't be described well using json like cv and data stuff)
    # List of Step names (can be empty indicating termination of fsm)
    # List of Pixel ((x, y), (r, g, b))
    # Function (click action, drag action)
    # Timing (initial wait, retry wait, )
    # To/From json

    def __init__(self, data):
        self.pixel = data['pixel']
        self.function = data['function']
        self.next = data['next']

    # this should be modified to a conditional check that allows customization
    # which can give it the ability to check other variables
    # or just allow the controller to pause and do other checks (then the controller will be specific but separate scripts should not need to reimplement the same stuff)
    def pixelCheck(self):
        return all([util.matchColor(pix['rgb'], Context.i.getColor(*(pix['pos'])), Config.i.data['pixel_threshold']) for pix in self.pixel])

    def run(self):
        # does the actual action
        data = self.function['data']
        action = self.function['action']
        if action == 'rect':
            mouse.click(util.irpoint(*data['points']))
        elif action == 'circle':
            mouse.click(util.icpoint(*data['points']))
        elif action == 'middle':
            mouse.middleClick()
        elif action == 'drag':
            mouse.rDrag(*data['points'])
        else:
            pass
