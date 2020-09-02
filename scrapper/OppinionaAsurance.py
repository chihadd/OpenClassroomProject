
import time
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup as soup
import requests
import pandas as pd
from pymongo import MongoClient


from utils.mongoDB import send_data_opininion_assurance_to_mongo
# ------------###------------------###------------------------###-------------------------------###--------------------------
# Il faut installer selenium --> pip install selenium
# il faut téléchrger " ChromeDriver " et le mettre là ou se trouve le script python
# ------------###------------------###------------------------###-------------------------------###--------------------------

class OpinionAssurance:
    def __init__(self):
        print("Class Object Created..!")

    def get_all_category_links(self):
        main_page_url = "https://www.opinion-assurances.fr"
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option(
            'excludeSwitches', ['enable-logging'])
        chrome_options.add_argument("--log-level=3")
        driver = webdriver.Chrome(
            options=chrome_options, executable_path="../chromedriver.exe")
        driver.get(main_page_url)
        try:
            WebDriverWait(driver, 5).until(
                EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "#FilterHeadBandProductTypeId")))
            print("Success In Opening Main Page..!")
        except:
            print("Page Taking To Much Time To Load.!")

        Main_Category = Select(driver.find_element_by_css_selector(
            "#FilterHeadBandProductTypeId"))
        options = Main_Category.options
        print(len(options))
        URL = []
        for index in range(2, len(options) + 1):
            driver.find_element_by_css_selector(
                "#FilterHeadBandProductTypeId > option:nth-child(" + str(index) + ")").click()
            time.sleep(2)
            try:
                WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "#FilterHeadBandCarrierId > option:nth-child(2)")))
            except:
                continue
            current_page_source = driver.page_source
            page_soup = soup(current_page_source, "html5lib")
            sub_category_options = page_soup.find("select", {"id": "FilterHeadBandCarrierId"}).findAll("option",
                                                                                                       {
                                                                                                           "value": True})
            sub_category_options.pop(0)
            for category in sub_category_options:
                url = "https://www.opinion-assurances.fr" + \
                    category["value"].replace(".html", "-page1.html")
                print("Scraped Link :", url)
                URL.append(url)
        URL = list(set(URL))
        print("Total Linked Scraped :", len(URL))
        driver.quit()
        return URL

    def get_page_soup(self, url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36'}
        try:
            page_html = requests.get(url, headers=headers)
            print("Current URL :", url)
            page_soup = soup(page_html.content, features="lxml")
            return page_soup
        except:
            print("On Soup Sleep")
            time.sleep(10)
            return get_page_soup(url)

    def Scrape_Data(self, soup):
        Auteur = []
        Campany = []
        Dates = []
        Commentaires = []
        Etoiles = []

        # results = soup.find('div', class_='row oa_reactionBlock')
        avis = soup.findAll('div', class_='row oa_reactionBlock')
        for avi in avis:
            rDiv = avi.find('div', class_='oa_stackLevel')
            avi = avi.find(
                "div", {"class": "col-xs-12 col-sm-9 oa_reactionUser"})
            auteur_avi = avi.find('span', itemprop='author')
            auteur_avi_1 = auteur_avi.text.strip()
            Auteur.append(auteur_avi_1)

            camp_avi = avi.find('a')
            camp_avi_1 = camp_avi.text.strip()
            Campany.append(camp_avi_1)

            date_avi = avi.find('div', class_='col-md-12 oa_date')
            date_avi_1 = date_avi.text.replace('à', ',').strip()
            Dates.append(date_avi_1)

            description_avi = avi.find('h4', class_='oa_reactionText')
            description_avi_1 = description_avi.text.strip()
            Commentaires.append(description_avi_1)

            if None in (auteur_avi, date_avi, description_avi):
                continue

            icons = rDiv.find_all('i')
            num = 0
            for i in icons:
                if 'active' in i['class']:
                    num += 1
                    v = str(num)
            Etoiles.append(v)

        return Auteur, Campany, Dates, Commentaires, Etoiles

    def Iterate_Through_ALL_The_LINKS_AND_GET_Data(self, URL):
        Final_Auteur = []
        Final_Campany = []
        Final_Dates = []
        Final_Commentaires = []
        Final_Etoiles = []

        for url in URL:
            previous_page_number = 1
            next_page_number = 2
            while 1:
                page_soup = self.get_page_soup(url)
                Auteur, Campany, Dates, Commentaires, Etoiles = self.Scrape_Data(page_soup)
                Final_Auteur = Final_Auteur + Auteur
                Final_Campany = Final_Campany + Campany
                Final_Dates = Final_Dates + Dates
                Final_Commentaires = Final_Commentaires + Commentaires
                Final_Etoiles = Final_Etoiles + Etoiles
                try:
                    check = page_soup.find("div", {"class": "oa_right"}).find(
                        "a", {"title": "Page suivante"})["href"]
                    url = url.replace(
                        "-page" + str(previous_page_number), "-page" + str(next_page_number))
                    previous_page_number += 1
                    next_page_number += 1
                except:
                    break
        Data_Frame = pd.DataFrame(
            {'Auteur': Final_Auteur, 'Campany': Final_Campany, 'Date': Final_Dates,
                'Commentaire': Final_Commentaires,
                'Etoile': Final_Etoiles})

        print(Data_Frame)
        Data_Frame.reset_index(inplace=True)
        data_to_dict = Data_Frame.to_dict("records")
        #print(data_dict)
        send_data_opininion_assurance_to_mongo(data_to_dict)
        return data_to_dict


if __name__ == "__main__":
    Object = OpinionAssurance()
    print("Executing First Function.!")
    # ALL_URLS = Object.get_all_category_links()
    ALL_URLS = ['https://www.opinion-assurances.fr/assureur-axa-assurance-vie-page1.html']  # Pour tester le script
    print("Executing Second Function.!")
    Complete_Data_Frame = Object.Iterate_Through_ALL_The_LINKS_AND_GET_Data(ALL_URLS)


