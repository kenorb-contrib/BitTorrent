#!/usr/local/bin/bash

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

# Author : MichaelBibby ( michaelbibby # gmail.com )
# Date : 2005/12/15 
# Purpose : To start '/usr/local/bin/bttrack.py' at system startup.

BTTRACK='/usr/local/bin/bittorrent-tracker.py'
BTTRACK_PID_FILE='/var/run/bittorrent-tracker.pid'
BTTRACK_PID=$(cat $BTTRACK_PID_FILE)

BTTRACK_ARGS='--port 6969 --dfile /var/log/bittorrent-tracker/dlinfo --allowed_dir /home/torrents --show_infopage 0 --logfile /var/log/bittorrent-tracker/bittorrent-tracker.log'

function USAGE()
{
    echo -e "\n\t Usage : $0 [start|stop]"
}

# ---- Main ------
if [ X$# == X0 ]
then
    $BTTRACK $BTTRACK_ARGS &
elif [ X$# == X1 ]
then
    case $1 in
        start) echo -ne "Starting BT tracker ..."
            $BTTRACK $BTTRACK_ARGS &
            echo -ne "\t Done." 
        ;;
        stop) echo -ne "Stop BT tracker ..."
            kill $BTTRACK_PID
            echo -ne "\t Done."
        ;;
        *) USAGE
        ;;
        esac
else 
    USAGE
fi
# ----- Done ----