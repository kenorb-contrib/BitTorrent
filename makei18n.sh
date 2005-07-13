APP_NAME="bittorrent"
LANGUAGES='af ar da de es fi fr he_IL hu it ja ko nl no pt_BR ro ru sk sl sq sv tr zh_CN zh_TW'
MESSAGES_PO="messages.pot"

rm -f $APP_NAME.lis

# create .pot file with most important strings first so that people
# who start but don't finish translations end up translating the most
# important parts
ls bt*gui.py                  >> $APP_NAME.lis
ls BitTorrent/GUI.py          >> $APP_NAME.lis
ls BitTorrent/TorrentQueue.py >> $APP_NAME.lis
ls BitTorrent/defaultargs.py  >> $APP_NAME.lis
ls bt*.py                     >> $APP_NAME.lis
ls *py                        >> $APP_NAME.lis
# find everything else
find . -name \*.py -type f | egrep -v '/(build)|(dist)|(test)/' >> $APP_NAME.lis

xgettext -f $APP_NAME.lis -L Python -o - | \
    sed -e 's/CHARSET/UTF-8/' > $MESSAGES_PO.nonunique

msguniq $MESSAGES_PO.nonunique > $MESSAGES_PO
rm -f $MESSAGES_PO.nonunique

for lang in $LANGUAGES ; do 
    echo "making $lang"
    mkdir -p locale/$lang/LC_MESSAGES
    msgmerge po/$lang.po $MESSAGES_PO \
        > locale/$lang/LC_MESSAGES/$APP_NAME.po
    msgfmt -o locale/$lang/LC_MESSAGES/$APP_NAME.mo \
        locale/$lang/LC_MESSAGES/$APP_NAME.po
done

## Don't do this always:
#for lang in $LANGUAGES ; do
#    cp locale/${lang}/LC_MESSAGES/bittorrent.po po/$lang.po
#done

