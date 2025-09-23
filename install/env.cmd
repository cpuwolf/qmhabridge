set PYROOT=E:\Python310
set PATH=%PYROOT%;%PYROOT%\Scripts;%PATH%;

set MYROOT=%~dp0..\
pushd %MYROOT%

python.exe -m pip install --upgrade pip
pip.exe install -r requirements.txt


