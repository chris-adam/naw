import os
import traceback
from datetime import timedelta, datetime
from time import sleep
from time import time

import gspread
import pandas as pd
import requests
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

UPDATE_DELAY_SHEET = 8*60*60  # seconds


def update_google_sheet(print_log=False):
    if print_log:
        log("Mise à jour du Google sheet en cours ...")

    # set up permissions
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1Al31wRrld2nGviQyFiPG_O6ec37qW5QRbcFX3dkikpw").worksheet('Relevés tdc')
    # my copy: 15wgTEWgj0qKEEE_7uM7WbXgk22_XKRZPQuBAXdAGLcY

    # Add new row
    new_row = build_new_row()
    print(new_row.set_index("Date"))

    row_to_replace = 7
    dates = sheet.get("B7:B75")
    for previous_date, date in zip(dates[:-1], dates[1:]):
        row_to_replace += 1
        if previous_date == date:
            break

    # update date
    sheet.update_cell(row_to_replace, 2, new_row.at[0, "Date"].to_pydatetime().strftime('%Y-%m-%d %H:%M'))

    # update tdc
    colonies = sheet.get("F6:DL6")[0]
    for col in new_row.columns[1:]:
        try:
            index = search(col, colonies)
            sheet.update_cell(row_to_replace, index+6, int(new_row.at[0, col]))
        except TypeError:
            log("La colonie \"{}\" n'a pas été trouvé dans le tableur Google sheet".format(col))
            continue

    if print_log:
        log("Mise à jour terminée")


def search(key, lst):
    key = key.lower().replace(" ", "")
    for i, elem in enumerate(lst):
        elem = elem.lower().replace("*", "").replace(" ", "")
        if elem != "" and (elem.endswith(key) or key.endswith(elem)):
            return i


def get_releve(url="https://www.natureatwar.fr/descriptionalliance-LA",
               cookies={'PHPSESSID': 'ggdihv5rkrtcoevlc0d67ir6t6'}):

    r = requests.get(url, cookies=cookies)
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find_all("table", {"class": "table-striped"})[1]
    rows = table.find_all("tr")

    titles = ["Tdc", "Rank", "Pseudo", "Colonie", "Total", "Bat", "Tech", "Etat"]
    releve = pd.DataFrame(columns=titles)
    for row in rows:
        lst = []
        for cell in row.find_all("td"):
            for sub_cell in cell:
                lst.append(sub_cell)
        if len(lst) == len(titles):
            releve = releve.append(pd.DataFrame({i: [a] for i, a in zip(titles, lst)}))

        releve = releve.reset_index(drop=True)

    return format_releve(releve)


def format_releve(releve):
    releve["Tdc"] = [int(tdc.replace(" ", "")) for tdc in releve["Tdc"]]
    releve["Rank"] = [str(rank.replace(" ", "")) for rank in releve["Rank"]]
    releve["Pseudo"] = [str(pseudo.find("b"))[3:-4] for pseudo in releve["Pseudo"]]
    releve["Colonie"] = [str(colonie.find("b"))[3:-4] for colonie in releve["Colonie"]]
    releve["Total"] = [int(total.replace(" ", "")) for total in releve["Total"]]
    releve["Bat"] = [int(bat.replace(" ", "")) for bat in releve["Bat"]]
    releve["Tech"] = [int(tech.replace(" ", "")) for tech in releve["Tech"]]
    releve["Etat"] = [str(etat)[10:str(etat)[10:].find("\"")+10] for etat in releve["Etat"]]
    return releve


def build_new_row():
    disconnected = True
    releve = None
    while disconnected:
        try:
            releve = get_releve()
        except (AttributeError, IndexError):
            log("Récupération des données échouées, nouvel essai. Si ce problème persiste, reconnecte-toi sur NAW.")
            sleep(15)
        except requests.exceptions.ConnectionError:
            log("Pas de connection internet, nouvel essai dans 15 secondes")
            sleep(15)
        else:
            disconnected = False

    new_row = pd.DataFrame({**{"Date": [round_datetime(datetime.today())]},
                            **{colonie: [tdc] for colonie, tdc in zip(releve["Colonie"], releve["Tdc"])}})

    return new_row


def round_datetime(tm):
    return tm - timedelta(seconds=tm.second, microseconds=tm.microsecond)


def log(*message, date=True):
    if date:
        print(datetime.today().strftime('%d-%m-%Y %H:%M:%S'), end=" : ")
    print(*message)


if __name__ == "__main__":
    try:
        pd.set_option("display.max_columns", 12)
        pd.set_option("display.width", 200)
        pd.set_option('display.float_format', lambda x: '%.f' % x)

        time_sheet = time()-UPDATE_DELAY_SHEET

        while True:
            if time()-time_sheet >= UPDATE_DELAY_SHEET:
                time_sheet = time()
                update_google_sheet(print_log=True)
            else:
                build_new_row()

            sleep(120)

    except Exception:
        traceback.print_exc()
        os.system("pause")
