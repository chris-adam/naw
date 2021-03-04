from cx_Freeze import setup, Executable


includefiles = ["client_secret.json"]
includes = []
excludes = []
packages = ["gspread", "pandas", "requests", "bs4", "oauth2client", "httplib2", "browser_cookie3", "urllib3", "keyring"]

setup(
    name='naw_releve_auto',
    version='0',
    description="Relève automatiquement le tdc de l'alliance pour le mettre dans un Google Sheet",
    author='Chris ADAM',
    author_email='adam.chris@live.be',
    options={'build_exe': {'includes': includes,
                           'excludes': excludes,
                           'packages': packages,
                           'include_files': includefiles}},
    executables=[Executable('naw_copy.py')]
)
