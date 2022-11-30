#!/bin/bash

for pyfile in ../samples/*.py;
do
    echo "Running demo <$pyfile>..."
    python $pyfile
    if [[ $? -ne 0 ]] ; then
        echo
        echo "Demo <$pyfile> failed."
        exit 1
    fi
done

echo "All demos passed."
exit 0
