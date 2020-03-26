import monpa
import pandas as pd
from fhir.resources.patient import Patient
from fhir.resources.address import Address
from fhir.resources.humanname import HumanName
from ckip import CkipSegmenter
import json
import jieba
import re

def get_human_name(patient, human_name, name_dict):
	name = HumanName()

	name.text = human_name
	name.use = "usual"

	if human_name[:2] in name_dict or len(human_name) == 4:
		name.family = human_name[0:2]
		name.given = [(human_name[2:])]

	else:
		name.family = human_name[0]
		name.given = [(human_name[1:])]

	patient.name = [name]
	return patient

def get_address(patient, addr_1, city_dict, district_dict, postalcode_dict, city_district_dict):
	if addr_1 == '""':
		return patient
	if addr_1 == '不詳':
		address = Address()
		address.text = addr_1
		patient.address.append(address)
		return patient

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

	for i in range(3):
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
				if addr_1[:2] in district_dict:
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

	address.district = district
	address.city = city
	address.line = [addr_1]
	try:
		address.postalCode = str(postalcode_dict[district[:-1]])
	except:
		address.postalCode = None

	patient.address.append(address)
	

	return patient

def main():

	data = pd.read_csv("./patient.csv", encoding = "utf-8")
	data = data.iloc[:, 0]
	human_name = []
	addr1 = []
	addr2 = []
	for i in data:
		human_name.append(i.split("\x06")[0])
		addr1.append(i.split("\x06")[1].replace("\u3000", "").replace("台", "臺").replace("市", "巿"))
		addr2.append(i.split("\x06")[2].replace("\u3000", "").replace("台", "臺").replace("市", "巿"))

	map = pd.read_csv("./map.csv", encoding = "utf-8")
	name = pd.read_csv("./name-2.csv", encoding = "utf-8")
	name_dict = {}
	city_dict = {}
	district_dict = {}
	postalcode_dict = {}
	city_district_dict = {}
	for i in range(len(map.index)):
		if map.iloc[i, 0][:2] not in city_dict:
			city_dict[map.iloc[i, 0][:2]] = map.iloc[i, 0][:3].replace("市", "巿")
		if map.iloc[i, 0][3:-1] not in district_dict:
			district_dict[map.iloc[i, 0][3:-1]] = map.iloc[i, 0][3:].replace("市", "巿")
			postalcode_dict[map.iloc[i, 0][3:-1]] = map.iloc[i, 7]
			city_district_dict[map.iloc[i, 0][3:-1]] = map.iloc[i, 0][:3].replace("市", "巿")

	for i in range(name.shape[0]):
		if name.iloc[i, 0] not in name_dict:
			name_dict[name.iloc[i, 0]] = i


	for id, i in enumerate(human_name):
		patient = Patient()
		patient.id = "patient-" + str(id)
		patient = get_human_name(patient, human_name[id], name_dict)
		patient.address = []
		patient = get_address(patient, addr1[id], city_dict, district_dict, postalcode_dict, city_district_dict)
		patient = get_address(patient, addr2[id], city_dict, district_dict, postalcode_dict, city_district_dict)
		print(patient.as_json())


if __name__ == '__main__':
	main()