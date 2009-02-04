#!/bin/bash

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

# written by Matt Chisholm
APP_NAME="bittorrent"
LANGUAGES=`python language_codes.py -a`
MESSAGES_PO="messages.pot"

rm -f $APP_NAME.lis
rm -f *~

# create .pot file with most important strings first so that people
# who start but don't finish translations end up translating the most
# important parts
ls BitTorrent/GUI_wx/*py        >> $APP_NAME.lis
ls bittorrent.py maketorrent.py >> $APP_NAME.lis
ls BitTorrent/StatusLight.py    >> $APP_NAME.lis
ls BitTorrent/defaultargs.py    >> $APP_NAME.lis
ls *py                          >> $APP_NAME.lis
# find everything else
find . -name \*.py -type f | egrep -v '/(build)|(dist)|(test)/' >> $APP_NAME.lis

xgettext -f $APP_NAME.lis -L Python -o -                        |\
    sed -e 's/CHARSET/UTF-8/'                                   |\
    sed -e 's/SOME DESCRIPTIVE TITLE./BitTorrent/'              |\
    sed -e 's/YEAR/2006/'                                       |\
    sed -e "s/THE PACKAGE'S COPYRIGHT HOLDER/BitTorrent, Inc./" |\
    sed -e 's/PACKAGE/BitTorrent/'                              |\
    sed -e 's/VERSION/5.0/'                                     |\
    sed -e 's/FIRST AUTHOR/BitTorrent Development Team/'        |\
    sed -e 's/EMAIL@ADDRESS/translations (at) bittorrent (dot) com/' |\
    sed -e 's/FULL NAME/BitTorrent Development Team/' > $MESSAGES_PO.nonunique


msguniq $MESSAGES_PO.nonunique > $MESSAGES_PO
rm -f $MESSAGES_PO.nonunique

for lang in $LANGUAGES ; do 
    echo "making $lang"
    mkdir -p locale/$lang/LC_MESSAGES
    msgmerge --no-fuzzy-matching po/$lang.po $MESSAGES_PO \
        | egrep -v '^#~' \
        > locale/$lang/LC_MESSAGES/$APP_NAME.po
    msgfmt -o locale/$lang/LC_MESSAGES/$APP_NAME.mo \
        locale/$lang/LC_MESSAGES/$APP_NAME.po
done

## Don't do this always:
#for lang in $LANGUAGES ; do
#    cp locale/${lang}/LC_MESSAGES/bittorrent.po po/$lang.po
#    echo 'cp', $lang
#done

