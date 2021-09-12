"""
Clean the csv files and produce a JSON file for use in javascript.

I'd rather not introduce any new python dependencies (like pandas) so attempting to do this
natively.
"""

import csv
import os
import json


DATA_DIR = "raw/"


# We have two files for mercedes which cannot be named the same but have different columns, so
# we'll map it manually.
FILENAME_TO_MAKE = {"merc": "mercedes"}

INTEGER_FIELDS = ["tax", "price", "mileage", "year"]


def process():
    data = []

    for filename in os.listdir(DATA_DIR):
        with open(f"raw/{filename}", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = row
                item["make"] = _get_make(filename)

                for fieldname in INTEGER_FIELDS:
                    value = item.get(fieldname, None)
                    if value is not None:
                        item[fieldname] = int(value)

                data.append(item)

    with open("cars.json", "w") as file:
        json.dump(data, file)


def _get_make(filename):
    """
    Remove .csv from file name and maybe map it to another name and then capitalise it.
    """
    clean_name = filename.replace(".csv", "")
    return FILENAME_TO_MAKE.get(clean_name, clean_name).capitalize()


if __name__ == "__main__":
    process()
