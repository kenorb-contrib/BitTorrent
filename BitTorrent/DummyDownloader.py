# Written by Bram Cohen
# this file is public domain

class DummyDownloader:
    def __init__(self):
        self.downloads = {}

    def connection_made(self, connection):
        self.downloads[connection.get_id()] = connection

    def connection_lost(self, connection):
        del self.downloads[connection.get_id()]

    def got_message(self, connection, message):
        pass
