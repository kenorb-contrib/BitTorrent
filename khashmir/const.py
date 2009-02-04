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

# magic id to use before we know a peer's id
NULL_ID =  20 * '\0'

# Kademlia "K" constant, this should be an even number
K = 8

# SHA1 is 160 bits long
HASH_LENGTH = 160

# checkpoint every this many seconds
CHECKPOINT_INTERVAL = 60 * 5 # five minutes

# how often to find our own nodes
FIND_CLOSE_INTERVAL = 60 * 15 # fifteen minutes

### SEARCHING/STORING
# concurrent krpc calls per find node/value request!
CONCURRENT_REQS = K

# how many hosts to post to
STORE_REDUNDANCY = 3


###  ROUTING TABLE STUFF
# how many times in a row a node can fail to respond before it's booted from the routing table
MAX_FAILURES = 3

# never ping a node more often than this
MIN_PING_INTERVAL = 60 * 15 # fifteen minutes

# refresh buckets that haven't been touched in this long
BUCKET_STALENESS = 60 * 15 # fifteen minutes


###  KEY EXPIRER
# time before expirer starts running
KEINITIAL_DELAY = 15 # 15 seconds - to clean out old stuff in persistent db

# time between expirer runs
KE_DELAY = 60 * 5 # 5 minutes

# expire entries older than this
KE_AGE = 60 * 30 # 30 minutes


## krpc errback codes
KRPC_TIMEOUT = 20

KRPC_ERROR = 1
KRPC_ERROR_METHOD_UNKNOWN = 2
KRPC_ERROR_RECEIVED_UNKNOWN = 3
KRPC_ERROR_TIMEOUT = 4
KRPC_SOCKET_ERROR = 5

KRPC_CONNECTION_CACHE_TIME = KRPC_TIMEOUT * 2


## krpc erorr response codes
KERR_ERROR = (201, "Generic Error")
KERR_SERVER_ERROR = (202, "Server Error")
KERR_PROTOCOL_ERROR = (203, "Protocol Error")
KERR_METHOD_UNKNOWN = (204, "Method Unknown")
KERR_INVALID_ARGS = (205, "Invalid Argements")
KERR_INVALID_TOKEN = (206, "Invalid Token")
