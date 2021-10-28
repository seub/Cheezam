import json
import re
from urllib.parse import quote
import os
import time

GOOGLE_URL = "www.google.fr"


def _extract_data_pack(page):
    start_line = page.find("AF_initDataCallback({key: \\'ds:1\\'") - 10
    start_object = page.find("[", start_line + 1)
    end_object = page.rfind("]", 0, page.find("</script>", start_object + 1)) + 1
    object_raw = str(page[start_object:end_object])
    return bytes(object_raw, "utf-8").decode("unicode_escape")


def _extract_data_pack_extended(page):
    start_line = page.find("AF_initDataCallback({key: 'ds:1'") - 10
    start_object = page.find("[", start_line + 1)
    end_object = page.rfind("]", 0, page.find("</script>", start_object + 1)) + 1
    return str(page[start_object:end_object])


def _extract_data_pack_ajax(data):
    lines = data.split("\n")
    return json.loads(lines[3])[0][2]


def _image_objects_from_pack(data):
    image_objects = json.loads(data)[31][-1][12][2]
    image_objects = [x for x in image_objects if x[0] == 1]
    return image_objects


def replace_with_byte(match):
    return chr(int(match.group(0)[1:], 8))


def repair(brokenjson):
    invalid_escape = re.compile(
        r"\\[0-7]{1,3}"
    )  # up to 3 digits for byte values up to FF
    return invalid_escape.sub(replace_with_byte, brokenjson)


def format_object(object):
    data = object[1]
    main = data[3]
    info = data[9]
    if info is None:
        info = data[11]
    formatted_object = {}
    try:
        formatted_object["image_height"] = main[2]
        formatted_object["image_width"] = main[1]
        formatted_object["image_link"] = main[0]
        formatted_object["image_format"] = main[0][
            -1 * (len(main[0]) - main[0].rfind(".") - 1) :
        ]
        formatted_object["image_description"] = info["2003"][3]
        formatted_object["image_host"] = info["2003"][17]
        formatted_object["image_source"] = info["2003"][2]
        formatted_object["image_thumbnail_url"] = data[2][0]
    except Exception as e:
        print(e)
        return None
    return formatted_object


def create_image_name(image_url, image_type):
    qmark = image_url.rfind("?")
    if qmark == -1:
        qmark = len(image_url)
    slash = image_url.rfind("/", 0, qmark) + 1
    image_name = str(image_url[slash:qmark]).lower()

    if image_type == "image/jpeg" or image_type == "image/jpg":
        if not image_name.endswith(".jpg") and not image_name.endswith(".jpeg"):
            image_name += ".jpg"
    elif image_type == "image/png":
        if not image_name.endswith(".png"):
            image_name += ".png"
    elif image_type == "image/webp":
        if not image_name.endswith(".webp"):
            image_name += ".webp"
    elif image_type == "image/gif":
        if not image_name.endswith(".gif"):
            image_name += ".gif"
    elif image_type == "image/bmp" or image_type == "image/x-windows-bmp":
        if not image_name.endswith(".bmp"):
            image_name += ".bmp"
    elif image_type == "image/x-icon" or image_type == "image/vnd.microsoft.icon":
        if not image_name.endswith(".ico"):
            image_name += ".ico"
    elif image_type == "image/svg+xml":
        if not image_name.endswith(".svg"):
            image_name += ".svg"
    else:
        raise ValueError("Invalid image format '")
    return image_name


def build_url_parameters(arguments):
    if arguments["language"]:
        lang = "&lr="
        lang_param = {
            "Arabic": "lang_ar",
            "Chinese (Simplified)": "lang_zh-CN",
            "Chinese (Traditional)": "lang_zh-TW",
            "Czech": "lang_cs",
            "Danish": "lang_da",
            "Dutch": "lang_nl",
            "English": "lang_en",
            "Estonian": "lang_et",
            "Finnish": "lang_fi",
            "French": "lang_fr",
            "German": "lang_de",
            "Greek": "lang_el",
            "Hebrew": "lang_iw ",
            "Hungarian": "lang_hu",
            "Icelandic": "lang_is",
            "Italian": "lang_it",
            "Japanese": "lang_ja",
            "Korean": "lang_ko",
            "Latvian": "lang_lv",
            "Lithuanian": "lang_lt",
            "Norwegian": "lang_no",
            "Portuguese": "lang_pt",
            "Polish": "lang_pl",
            "Romanian": "lang_ro",
            "Russian": "lang_ru",
            "Spanish": "lang_es",
            "Swedish": "lang_sv",
            "Turkish": "lang_tr",
        }
        lang_url = lang + lang_param[arguments["language"]]
    else:
        lang_url = ""

    if arguments["exact_size"]:
        size_array = [x.strip() for x in arguments["exact_size"].split(",")]
        exact_size = (
            ",isz:ex,iszw:" + str(size_array[0]) + ",iszh:" + str(size_array[1])
        )
    else:
        exact_size = ""

    built_url = "&tbs="
    counter = 0
    params = {
        "color": [
            arguments["color"],
            {
                "red": "ic:specific,isc:red",
                "orange": "ic:specific,isc:orange",
                "yellow": "ic:specific,isc:yellow",
                "green": "ic:specific,isc:green",
                "teal": "ic:specific,isc:teel",
                "blue": "ic:specific,isc:blue",
                "purple": "ic:specific,isc:purple",
                "pink": "ic:specific,isc:pink",
                "white": "ic:specific,isc:white",
                "gray": "ic:specific,isc:gray",
                "black": "ic:specific,isc:black",
                "brown": "ic:specific,isc:brown",
            },
        ],
        "color_type": [
            arguments["color_type"],
            {
                "full-color": "ic:color",
                "black-and-white": "ic:gray",
                "transparent": "ic:trans",
            },
        ],
        "usage_rights": [
            arguments["usage_rights"],
            {
                "labeled-for-reuse-with-modifications": "sur:fmc",
                "labeled-for-reuse": "sur:fc",
                "labeled-for-noncommercial-reuse-with-modification": "sur:fm",
                "labeled-for-nocommercial-reuse": "sur:f",
            },
        ],
        "size": [
            arguments["size"],
            {
                "large": "isz:l",
                "medium": "isz:m",
                "icon": "isz:i",
                ">400*300": "isz:lt,islt:qsvga",
                ">640*480": "isz:lt,islt:vga",
                ">800*600": "isz:lt,islt:svga",
                ">1024*768": "visz:lt,islt:xga",
                ">2MP": "isz:lt,islt:2mp",
                ">4MP": "isz:lt,islt:4mp",
                ">6MP": "isz:lt,islt:6mp",
                ">8MP": "isz:lt,islt:8mp",
                ">10MP": "isz:lt,islt:10mp",
                ">12MP": "isz:lt,islt:12mp",
                ">15MP": "isz:lt,islt:15mp",
                ">20MP": "isz:lt,islt:20mp",
                ">40MP": "isz:lt,islt:40mp",
                ">70MP": "isz:lt,islt:70mp",
            },
        ],
        "type": [
            arguments["type"],
            {
                "face": "itp:face",
                "photo": "itp:photo",
                "clipart": "itp:clipart",
                "line-drawing": "itp:lineart",
                "animated": "itp:animated",
            },
        ],
        "time": [
            arguments["time"],
            {
                "past-24-hours": "qdr:d",
                "past-7-days": "qdr:w",
                "past-month": "qdr:m",
                "past-year": "qdr:y",
            },
        ],
        "aspect_ratio": [
            arguments["aspect_ratio"],
            {
                "tall": "iar:t",
                "square": "iar:s",
                "wide": "iar:w",
                "panoramic": "iar:xw",
            },
        ],
        "format": [
            arguments["format"],
            {
                "jpg": "ift:jpg",
                "gif": "ift:gif",
                "png": "ift:png",
                "bmp": "ift:bmp",
                "svg": "ift:svg",
                "webp": "webp",
                "ico": "ift:ico",
                "raw": "ift:craw",
            },
        ],
    }
    for key, value in params.items():
        if value[0] is not None:
            ext_param = value[1][value[0]]
            # counter will tell if it is first param added or not
            if counter == 0:
                # add it to the built url
                built_url = built_url + ext_param
                counter += 1
            else:
                built_url = built_url + "," + ext_param
                counter += 1
    built_url = lang_url + built_url + exact_size
    return built_url


def build_search_url(search_term, params):
    return (
        f"https://{GOOGLE_URL}/search?q="
        + quote(search_term.encode("utf-8"))
        + "&espv=2&biw=1366&bih=667&site=webhp&source=lnms&tbm=isch"
        + params
        + "&sa=X&ei=XosDVaCXD8TasATItgE&ved=0CAcQ_AUoAg"
    )

    # make directories


def create_directories(main_directory, dir_name):
    try:
        if not os.path.exists(main_directory):
            os.makedirs(main_directory)
            time.sleep(0.15)
        path = dir_name
        sub_directory = os.path.join(main_directory, path)
        if not os.path.exists(sub_directory):
            os.makedirs(sub_directory)
    except OSError as e:
        if e.errno != 17:
            raise
        pass
