# The contents of this file are subject to the Python Software Foundation
# License Version 2.3 (the License).  You may not copy or use this file, in
# either source code or executable form, except in compliance with the License.
# You may obtain a copy of the License at http://www.python.org/license.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.
#
# author: David Harrison
try:
   from CMap import CMap, CIndexedMap
   Map = CMap
   IndexedMap = CIndexedMap
   
except:
   from PMap import PMap, PIndexedMap
   Map = PMap
   IndexedMap = PIndexedMap
   print "Using pure python version of Map.  Please compile CMap.\n"

try:
   from CMultiMap import CMultiMap, CIndexedMultiMap
   MultiMap = CMultiMap
   IndexedMultiMap = CIndexedMultiMap
except:
   print "Warning!! Please compile CMultiMap.  There is no pure "
   print "python version of MultiMap.\n"
