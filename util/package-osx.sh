#!/usr/bin/env bash
VERSION=$(python -c 'import beem; print(beem.__version__)')
COMM_TAG=$(git describe --tags $(git rev-list --tags --max-count=1))
COMM_COUNT=$(git rev-list --count HEAD)
BUILD="steemmonsters-${COMM_TAG}-${COMM_COUNT}_osx.dmg"

rm -rf dist build locale
pip install 
python setup.py clean
python setup.py build_ext
# python setup.py build_locales
pip install pyinstaller
pyinstaller steemmonsters-onedir.spec

cd dist
ditto -rsrc --arch x86_64 'steemmonsters.app' 'steemmonsters.tmp'
rm -r 'steemmonsters.app'
mv 'steemmonsters.tmp' 'steemmonsters.app'
hdiutil create -volname "steemmonsters $VERSION" -srcfolder 'steemmonsters.app' -ov -format UDBZ "$BUILD"
if [ -n "$UPLOAD_OSX" ]
then
    curl --upload-file "$BUILD" https://transfer.sh/
    # Required for a newline between the outputs
    echo -e "\n"
    md5 -r "$BUILD"
    echo -e "\n"
    shasum -a 256 "$BUILD"
fi
