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

from BTL.defer import Deferred, defer_to_thread

class ThreadProxy(object):
    __slots__ = ('obj', 'local_queue_task', 'thread_queue_task')
    def __init__(self, obj, local_queue_task, thread_queue_task):
        self.obj = obj
        self.local_queue_task = local_queue_task
        self.thread_queue_task = thread_queue_task

    def __gen_call_wrapper__(self, f):
        def call_wrapper(*a, **kw):
            return defer_to_thread(self.local_queue_task, self.thread_queue_task,
                                   f, *a, **kw)
        return call_wrapper

    def __getattr__(self, attr):
        a = getattr(self.obj, attr)
        if callable(a):
            return self.__gen_call_wrapper__(a)
        return a

    def call_with_obj(self, _f, *a, **k):
        w = self.__gen_call_wrapper__(_f)
        return w(self.obj, *a, **k)


