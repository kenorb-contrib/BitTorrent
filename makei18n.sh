APP_NAME="bittorrent"
LANGUAGES="fr he_IL it no pt_BR" 
MESSAGES_PO="messages.po"

find . -name \*.py -type f | egrep -v '/(build)|(dist)|(test)/' > $APP_NAME.lis
xgettext -f $APP_NAME.lis -L Python -o - | \
    sed -e 's/CHARSET/UTF-8/' > $MESSAGES_PO

for lang in $LANGUAGES ; do 
    echo "making $lang"
    mkdir -p locale/$lang/LC_MESSAGES
    msgmerge --no-fuzzy-matching po/$lang.po $MESSAGES_PO \
        > locale/$lang/LC_MESSAGES/$APP_NAME.po
    msgfmt -o locale/$lang/LC_MESSAGES/$APP_NAME.mo \
        locale/$lang/LC_MESSAGES/$APP_NAME.po
done

rm -f $APP_NAME.lis