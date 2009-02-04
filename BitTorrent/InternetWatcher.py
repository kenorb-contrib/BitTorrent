# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# by Greg Hazel

import random
from twisted.internet import task
from BTL.obsoletepythonsupport import set

class InternetSubscriber(object):

    def internet_active(self):
        pass

    def try_one_connection(self):
        pass

class InternetWatcher(object):
    
    def __init__(self, rawserver):

        self.rawserver = rawserver
        old_connectionMade = rawserver.connectionMade
        def connectionMade(s):
            if rawserver.connections == 0:
                self._first_connection()
            old_connectionMade(s)
        rawserver.connectionMade = connectionMade
        rawserver.internet_watcher = self

        self.subscribers = set()
        self.internet_watcher = task.LoopingCall(self._internet_watch)
        self.internet_watcher.start(5)

    def add_subscriber(self, s):
        self.subscribers.add(s)

    def remove_subscriber(self, s):
        self.subscribers.remove(s)

    def _internet_watch(self):
        if self.rawserver.connections != 0 or not self.subscribers:
            return
        l = list(self.subscribers)
        random.shuffle(l)
        for s in l:
            if s.try_one_connection():
                break

    def _first_connection(self):
        for s in self.subscribers:
            s.internet_active()


def get_internet_watcher(rawserver):
    if not hasattr(rawserver, "internet_watcher"):
        InternetWatcher(rawserver)    
    return rawserver.internet_watcher

