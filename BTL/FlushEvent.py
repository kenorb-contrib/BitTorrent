# A producer buffer that calls a callback when the
# send buffer is completely flushed.
#
# usage:
#
# self.buffer = FlushEventBuffer(onflushed)
#
# then when you write data:
# self.buffer.write(data)
#
# then when you have a transport:
# self.buffer.attachConsumer(self.transport)
#
# by Greg Hazel


class FlushEventBuffer(object):
    """ Proxy object so either buffer can be used """

    def __init__(self, onflushed):
        buffer = OutputBuffer(onflushed)
        self._attachBuffer(buffer)

    def _attachBuffer(self, buffer):
        self.buffer = buffer
        self.write = self.buffer.write
        self.stopWriting = self.buffer.stopWriting
        self.isFlushed = self.buffer.isFlushed

    def attachConsumer(self, transport):
        if hasattr(transport, 'addBufferCallback'):
            buffer = PassBuffer(transport, self.buffer)
            self._attachBuffer(buffer)
        elif hasattr(transport, 'registerProducer'):
            # Multicast uses sendto, which does not buffer.
            # It has no producer api
            self.buffer.attachConsumer(transport)

    def cleanup(self):
        self.buffer.consumer = None
        

class PassBuffer(object):
    """ Hint: not actually a buffer. Used for IOCP or reactors
        with a flush event already. """

    def __init__(self, consumer, old_buffer):
        self.consumer = consumer
        self.callback_onflushed = old_buffer.callback_onflushed
        self._is_flushed = False
        self.consumer.addBufferCallback(self._flushed, "buffer empty")
        # swallow the data written to the old buffer
        if old_buffer._buffer_list:
            print 'consumed', len(old_buffer._buffer_list)
            self.consumer.writeSequence(old_buffer._buffer_list)
            old_buffer._buffer_list[:] = []

    def write(self, b):
        self._is_flushed = False
        self.consumer.write(b)

    def stopWriting(self):
        """ maybe broken """
        pass
    
    def isFlushed(self):
        return self._is_flushed
    
    def _flushed(self):
        self._is_flushed = True
        self.callback_onflushed()

        
class OutputBuffer(object):

    """ This is an IPullProducer which has an unlimited buffer size,
        and calls a callback when the buffer is completely flushed. """

    def __init__(self, callback_onflushed):
        self.consumer = None
        self.registered = False
        self.callback_onflushed = callback_onflushed
        self._buffer_list = []

    def isFlushed(self):
        return (len(self._buffer_list) == 0)

    def attachConsumer(self, consumer):
        self.consumer = consumer
        if not self.registered:
            self.beginWriting()

    def write(self, b):
        self._buffer_list.append(b)

        if self.consumer and not self.registered:
            self.beginWriting()

    def beginWriting(self):
        if not self.consumer:
            raise ValueError("You must attachConsumer before "
                             "you beginWriting")
        self.stopWriting()
        self.registered = True
        self.consumer.registerProducer(self, False)

    def stopWriting(self):
        if not self.registered:
            return

        self.registered = False
        if self.consumer:
            try:
                self.consumer.unregisterProducer()
            except KeyError:
                # bug in iocpreactor: http://twistedmatrix.com/trac/ticket/1657
                pass

    def resumeProducing(self):
        if not self.registered:
            return
        if not self.consumer:
            raise ValueError("You must attachConsumer before "
                             "you resumeProducing")

        if self._buffer_list:
            self.consumer.writeSequence(self._buffer_list)
            del self._buffer_list[:]
            self.callback_onflushed()
        else:
            self.stopWriting()

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

