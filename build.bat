py setup.py sdist bdist_wheel
pyinstaller -y --name kingsquit --icon graham.ico --onefile main.py
