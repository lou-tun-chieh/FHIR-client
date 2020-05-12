CREATE OR REPLACE FUNCTION parseAddr(in addr_input varchar, out addr_text varchar, out addr_country varchar, out addr_city varchar, out addr_district varchar, out addr_line varchar, out addr_type varchar, out addr_postalcode varchar, out addr_use varchar) RETURNS RECORD AS $$
from sys import path
path.append( '/usr/local/lib/python3.7/site-packages/' )
import pandas as pd
from fhir.resources.patient import Patient
from fhir.resources.address import Address
from fhir.resources.humanname import HumanName
import json
import csv
import re

def Get_addr(addr_1, city_dict, district_dict, postalcode_dict, city_district_dict):
    if addr_1 == '""':
        address = Address()
        address.text = None
        address.type = None
        address.use = None
        address.country = None
        district = None
        city = None
        line = None
        postalcode = None
        return address
    if addr_1 == "不詳":
        address = Address()
        address.text = addr_1
        address.type = None
        address.use = None
        address.country = None
        district = None
        city = None
        line = None
        postalcode = None
        return address

    allPttrn={'countyPat': '.[^巿區]縣',
            'cityPat': '[^是在於及、，]{1,2}巿',
            'districtPat': '那瑪夏區|[^巿及、，]?.社?區|[^是在於及、，]{1,2}巿|(阿里山|三地門|太麻里)鄉|..鄉|..鎮',
            'roadPat': '(?<=[縣市區鄉鎮里村])[^巿區鄉鎮村路及、，]{1,}([路街]|大道)',
            'sectionPat': '\\s?[\\d零一二三四五六七八九十百千１２３４５６７８９０]*?\\s?段',
            'townshipPat': '(阿里山|三地門|太麻里)鄉|..[鄉里]',
            'townPat': '..鎮',
            'villagePat': '..村',
            'neighborhoodPat': '(\\s?[\\d零一二三四五六七八九十百千１２３４５６７８９０]*?\\s?鄰)',
            'alleyPat': '(國中|([^縣市區鄉鎮里村路段]{1,2}|鐵路)[\\d零一二三四五六七八九十百千１２３４５６７８９０]*?|\\s?>',
            'numberPat': '(\\s?[\\d零一二三四五六七八九十百千１２３４５６７８９０]*?\\s?[之\\-]\\s?)?\\s?[\\d零一二三四五 >',
            'floorPat': '\\s?[\\d零一二三四五六七八九十百千１２３４５６７８９０]*?\\s?[fF樓]\\s?([之\\-]\\s?[\\d零一二三四>',
            'roomPat': '\\s?[a-zA-Z]*?\\d*?([a-zA-Z]*?)?(\\d*?)?\\s?室',
            }

    address = Address()
    address.text = addr_1
    address.type = "physical"
    address.use = "home"
    address.country = "ROC"
    district = None
    city = None
    line = None
    postalcode = None

    for i in range(2):
        if i == 0:
            addPat = re.compile(allPttrn["countyPat"])
            result = addPat.match(addr_1)
            if result != None:
                city = result.group(0)
                addr_1 = re.sub(city, '', addr_1)
            else:
                if addr_1[:2] in city_dict:
                    city = city_dict[addr_1[:2]]
                    if addr_1[:3] == city:
                        addr_1 = addr_1 = addr_1[3:]
                    else:
                        addr_1 = addr_1 = addr_1[2:]

        elif i == 1:
            addPat = re.compile(allPttrn["districtPat"])
            result = addPat.match(addr_1)

            if result != None:
                district = result.group(0)
                addr_1 = re.sub(district, '', addr_1)
            else:
                if addr_1[:2] in district_dict and ( len(addr_1) > 2 and addr_1[2] != "路"):
                    district = district_dict[addr_1[:2]]
                    addr_1 = addr_1[2:]
                elif addr_1[:3] in district_dict:
                    district = district_dict[addr_1[:3]]
                    addr_1 = addr_1[2:]

    
    if district == city:
        district = None
    if city == "新竹巿":
        if district != "東區" or district != "北區" or district != "香山區":
            city = "新竹縣"

    # plpy.notice(city)
    address.district = district
    address.city = city

    address.line = addr_1
    try:
        address.postalCode = str(postalcode_dict[district[:-1]])
    except:
        address.postalCode = None

    
    return address


from sqlalchemy import create_engine
engine = create_engine('postgresql://postgres:smart@localhost:5432/fhir')
csv_data = pd.read_csv("./map.csv", "rb")

city_dict = {}
district_dict = {}
postalcode_dict = {}
city_district_dict = {}

for i in range(4, len(csv_data.index)):
    city = csv_data.iloc[i][0].split(",")[0]
    code = csv_data.iloc[i][0].split(",")[7]
    district = csv_data.iloc[i][0].split(",")[1]

    if city[:2] not in city_dict:
        city_dict[city[:2]] = city[:3].replace("市", "巿")
    if city[3:-1] not in district_dict:
        district_dict[city[3:-1]] = city[3:].replace("市", "巿")
        postalcode_dict[city[3:-1]] = code
        city_district_dict[city[3:-1]] = city[:3].replace("市", "巿")

# plpy.notice(district_dict)

addr = addr_input.replace("\u3000", "").replace("台", "臺").replace("市", "巿")

address = Get_addr(addr, city_dict, district_dict, postalcode_dict, city_district_dict)


return address.text, address.country, address.city, address.district, address.line, address.type, address.postalCode, address.use

$$ LANGUAGE plpython3u;