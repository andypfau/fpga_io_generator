#!/bin/bash

for pyfile in *.py;
do
    python $pyfile
    if [[ $? -ne 0 ]] ; then
        echo
        echo "Demo <$pyfile> failed."
        exit 1
    fi
done

echo "All demos passed."
exit 0
