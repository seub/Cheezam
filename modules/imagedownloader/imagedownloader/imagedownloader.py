from google_images_download import google_images_download

import asyncio
from pathlib import Path
import os
import unidecode
import pandas as pd
import csv
from collections import defaultdict
import json
from PIL import Image
import PIL

DOWNLOAD_DIR = "fullsize"
RESIZE_DIR = "resized"
DOWNLOAD_PATH = Path(__file__).parent.parent / DOWNLOAD_DIR

# creating object
response = google_images_download.googleimagesdownload()

search_queries = map(
    unidecode.unidecode,
    [
        "Abondance",
        "Arome de Lyon",
        "Banon",
        "Beaufort",
        "Bethmale",
        "Bleu d'Auvergne",
        "Bleu de Gex",
        "Bleu de Laqueuille",
        "Bleu de Termignon",
        "Bleu des Causses",
        "Bleu du Vercors-Sassenage",
        "Bresse Bleu",
        "Brie de Meaux",
        "Brie de Melun",
        "Brocciu",
        "Brousse du Rove",
        "Cabecou",
        "Caillebotte",
        "Camembert de Normandie",
        "Cantal",
        "Chabichou du Poitou",
        "Chamberat",
        "Chaource",
        "Charolais",
        "Chevrotin",
        "Comte",
        "Coulommiers",
        "Crottin de Chavignol",
        "Emmenthal de Savoie",
        "Faisselle",
        "Fort de Bethune",
        "Foudjou",
        "Fourme d'Ambert",
        "Fourme de Montbrison",
        "Fromage aux Noix",
        "Fromage aux artisons du Velay",
        "Fromage fort",
        "Gruyere Francais",
        "Laguiole",
        "Langres",
        "Livarot",
        "Maconnais",
        "Maroilles",
        "Mimolette",
        "Mont dor",
        "Morbier",
        "Munster",
        "Neufchâtel",
        "Ossau-Iraty",
        "Ptit Basque",
        "Persille de Tignes",
        "Picodon",
        "Pont-leveque",
        "Pouligny-Saint-Pierre",
        "Pourri Bressan",
        "Pelardon",
        "Perail",
        "Petafine",
        "Raclette",
        "Ramequin",
        "Reblochon",
        "Rigotte de Condrieu",
        "Rocamadour",
        "Rollot",
        "Roquefort",
        "Saint-Marcellin",
        "Saint-Nectaire",
        "Sainte-maure-de-touraine",
        "Salers",
        "Selles-sur-cher",
        "Soumaintrain",
        "Tome de Savoie",
        "Tome des Bauges",
        "Tome du Champsaur",
        "Tome fraîche",
        "Tome noire des Pyrenees",
        "Truffe de Ventadour",
        "Vache qui rie",
        "Vacherin des Bauges",
        "Valencay",
        "epoisses",
    ],
)


async def get_urls_dict(query, count=100, semaphore=None):
    arguments = {
        "keywords": query,
        "suffix_keywords": "fromage",
        "format": "jpg",
        "limit": count,
        "print_urls": False,
        "size": "medium",
        "language": "French",
        "output_directory": DOWNLOAD_DIR,
        "image_directory": query,
        "chromedriver": "/usr/local/bin/chromedriver",
    }
    print(f"Getting url for query {query}")
    async with semaphore:
        return await response.get_image_urls(arguments)


async def downloadimages(image_urls, semaphore=None, download_limit=None):

    # keywords is the search query
    # format is the image file format
    # limit is the number of images to be downloaded
    # print urs is to print the image file url
    # size is the image size which can
    # be specified manually ("large, medium, icon")
    # aspect ratio denotes the height width ratio
    # of images to download. ("tall, square, wide, panoramic")
    async with semaphore:
        images = (
            await response.download(
                image_urls, main_directory=DOWNLOAD_DIR, limit=download_limit
            )
        )[0]
        cheeses = [
            image
            | {
                "fromage": fromage,
                "file_path": os.path.relpath(
                    image.get("file_path"), start=DOWNLOAD_PATH
                ),
            }
            for fromage in images
            for image in images[fromage]
            if image.get("file_path")
        ]
        return cheeses


async def main(
    limit=None,
    count=100,
    get_urls=True,
    download=True,
    url_path=None,
    download_limit=None,
):
    # Driver Code
    images = []
    queries = search_queries if not limit else list(search_queries)[:limit]
    semaphore = asyncio.Semaphore(100)
    if get_urls:
        image_urls_list = await asyncio.gather(
            *[get_urls_dict(query, count, semaphore) for query in queries]
        )
        image_urls = defaultdict(list)
        for l in image_urls_list:
            for k, v in l.items():
                image_urls[k].extend(v)
        with open(url_path, "w") as url_file:
            image_urls = json.dump(image_urls, url_file)
    else:
        with open(url_path) as url_file:
            image_urls = json.load(url_file)
    if download:
        images = await downloadimages(
            image_urls,
            semaphore,
            download_limit=download_limit,
        )
        pd.DataFrame(images).to_csv("./image_db.csv", quoting=csv.QUOTE_NONNUMERIC)


def list_images(folder):
    for dirpath, _, filenames in os.walk(folder):
        for filename in filenames:
            yield os.path.join(dirpath, filename)


def resize(old_folder, new_folder):

    for i, image_path in enumerate(list_images(old_folder)):
        print(i, end="\r")
        new_path = os.path.join(new_folder, os.path.relpath(image_path, old_folder))
        if os.path.exists(Path(new_path)):
            continue
        try:
            image = Image.open(image_path)
        except PIL.UnidentifiedImageError as e:
            continue

        width, height = image.size
        if width <= height:
            crop_coord = (0, (width - height) // 2, width, (width + height) // 2)
        else:
            crop_coord = ((width - height) // 2, 0, (width + height) // 2, height)
        new_image = image.crop(crop_coord).resize((256, 256))

        if not os.path.exists(Path(new_path).parent):
            os.makedirs(Path(new_path).parent)
        try:
            new_image.save(new_path)
        except OSError:
            continue
    print("")


if __name__ == "__main__":
    """
    asyncio.run(
        main(
            count=1000,
            get_urls=False,
            download=False,
            url_path="./urls.json",
        )
    )
    """
    resize(DOWNLOAD_PATH, Path(__file__).parent.parent / RESIZE_DIR)
