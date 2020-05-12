CREATE OR REPLACE FUNCTION HumanName(in h_name varchar, out text varchar, out family varchar, out given varchar, out use varchar) RETURNS RECORD AS $$
from sys import path
path.append( '/usr/local/lib/python3.7/site-packages/' )


import pandas as pd
from fhir.resources.patient import Patient
from fhir.resources.humanname import HumanName
import json
import csv
from sqlalchemy import create_engine


name_dict = {}
engine = create_engine('postgresql://postgres:smart@localhost:5432/fhir')
csv_data = pd.read_csv("./name-2.csv", "rb")

for i in range(csv_data.shape[0]):
    if csv_data.iloc[i, 0] not in name_dict:
        name_dict[csv_data.iloc[i, 0]] = i

name = HumanName()
if h_name != None:
    name.text = h_name
    name.use = "usual"

    if name.text[:2] in name_dict or len(name.text) == 4:
        name.family = name.text[0:2]
        name.given = (name.text[2:])

    else:
        name.family = name.text[0]
        name.given = (name.text[1:])

return name.text, name.family, name.given, name.use
$$ LANGUAGE plpython3u;