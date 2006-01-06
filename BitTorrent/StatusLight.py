from BitTorrent.platform import bttime

class StatusLight(object):

    initial_state = 'stopped'

    states = {
        # state     : (stock icon name, tool tip),
        'stopped'   : ('bt-status-stopped',
                       _("Paused")),
        'empty'     : ('bt-status-stopped',
                       _("No torrents")),
        'starting'  : ('bt-status-starting',
                       _("Starting download")),
        'pre-natted': ('bt-status-pre-natted',
                       _("Starting download")),
        'running'   : ('bt-status-running',
                       _("Running normally")),
        'natted'    : ('bt-status-natted',
                       _("Downloads may be slow:\nProbably firewalled/NATted")),
        'broken'    : ('bt-status-broken',
                       _("Check network connection")),
        }

    messages = {
        # message           : default new state,
        'stop'              : 'stopped'   ,
        'empty'             : 'empty'     ,
        'start'             : 'starting'  ,
        'seen_peers'        : 'pre-natted',
        'seen_remote_peers' : 'running'   ,
        'broken'            : 'broken'    ,
        }
    
    transitions = {
        # state      : { message            : custom new state, },
        'pre-natted' : { 'start'            : 'pre-natted',
                         'seen_peers'       : 'pre-natted',},
        'running'    : { 'start'            : 'running'   ,
                         'seen_peers'       : 'running'   ,},
        'natted'     : { 'start'            : 'natted'    ,
                         'seen_peers'       : 'natted'    ,},
        'broken'     : { 'start'            : 'broken'    ,},
        #TODO: add broken transitions
        }

    time_to_nat = 60 * 5 # 5 minutes

    def __init__(self):
        self.mystate = self.initial_state
        self.start_time = None

    def send_message(self, message):
        if message not in self.messages.keys():
            #print 'bad message', message
            return
        new_state = self.messages[message]
        if self.transitions.has_key(self.mystate):
            if self.transitions[self.mystate].has_key(message):
                new_state = self.transitions[self.mystate][message]

        # special pre-natted timeout logic
        if new_state == 'pre-natted':
            if (self.mystate == 'pre-natted' and
                bttime() - self.start_time > self.time_to_nat):
                # go to natted state after a while
                new_state = 'natted'
            elif self.mystate != 'pre-natted':
                # start pre-natted timer
                self.start_time = bttime()

        if new_state != self.mystate:
            #print 'changing state from', self.mystate, 'to', new_state
            self.mystate = new_state
            self.change_state()

    def change_state(self):
        pass


import gtk

class GtkStatusLight(gtk.EventBox, StatusLight):

    def __init__(self, main):
        gtk.EventBox.__init__(self)
        StatusLight.__init__(self)
        self.main = main
        self.image = None
        self.images = {}
        for k,(s,t) in self.states.items():
            i = gtk.Image()
            i.set_from_stock(s, gtk.ICON_SIZE_LARGE_TOOLBAR)
            i.show()
            self.images[k] = i        
        self.set_size_request(24,24)
        self.main.tooltips.set_tip(self, 'tooltip')
        self.send_message('stop')

    def change_state(self):
        state = self.mystate
        assert self.states.has_key(state)
        if self.image is not None:
            self.remove(self.image)
        self.image = self.images[state]
        self.add(self.image)
        stock, tooltip = self.states[state]
        self.main.tooltips.set_tip(self, tooltip)
