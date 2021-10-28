#!/usr/bin/env python
# In[ ]:
#  coding: utf-8

from itertools import product
from collections import defaultdict

###### Searching and Downloading Google Images to the local disk ######
# Import Libraries
import sys
import aiohttp
import asyncio
import urllib.request
from urllib.request import Request, urlopen
from urllib.request import URLError, HTTPError
import http.client
from http.client import IncompleteRead, BadStatusLine

http.client._MAXHEADERS = 1000

import time  # Importing the time library to check the time of code execution
import os
import ssl
import datetime
import json
import re
import codecs
import socket

from .arg_parser import args_list, user_input
from .utils import (
    _extract_data_pack,
    _extract_data_pack_extended,
    _extract_data_pack_ajax,
    _image_objects_from_pack,
    format_object,
    create_image_name,
    build_url_parameters,
    build_search_url,
    create_directories,
    GOOGLE_URL,
)


class googleimagesdownload:
    def __init__(self):
        pass

    # Downloading entire Web Document (Raw Page Content)
    async def download_page(self, url):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36"
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req)
            respData = str(resp.read())
        except:
            print(
                "Could not open URL. Please check your internet connection and/or ssl settings \n"
                "If you are using proxy, make sure your proxy settings is configured correctly"
            )
            raise
        try:
            return _image_objects_from_pack(_extract_data_pack(respData))
        except Exception as e:
            print(e)
            print(
                "Image objects data unpacking failed. Please leave a comment with the above error at https://github.com/hardikvasa/google-images-download/pull/298"
            )
            raise

    # Download Page for more than 100 images
    async def download_extended_page(self, url, chromedriver):
        from selenium import webdriver
        from selenium.webdriver.common.keys import Keys

        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--headless")

        try:
            browser = webdriver.Chrome(chromedriver, chrome_options=options)
        except Exception as e:
            print(
                "Looks like we cannot locate the path the 'chromedriver' (use the '--chromedriver' "
                "argument to specify the path to the executable.) or google chrome browser is not "
                "installed on your machine (exception: %s)" % e
            )
            raise
        browser.set_window_size(1024, 768)

        # Open the link
        browser.get(url)
        browser.execute_script(
            """
            (function(XHR){
                "use strict";
                var open = XHR.prototype.open;
                var send = XHR.prototype.send;
                var data = [];
                XHR.prototype.open = function(method, url, async, user, pass) {
                    this._url = url;
                    open.call(this, method, url, async, user, pass);
                }
                XHR.prototype.send = function(data) {
                    var self = this;
                    var url = this._url;
                    function stateChanged() {
                        if (self.readyState == 4) {
                            console.log("data available for: " + url)
                            XHR.prototype._data.push(self.response);
                        }
                    }
                    if (url.includes("/batchexecute?")) {
                        this.addEventListener("readystatechange", stateChanged, false);
                    }
                    send.call(this, data);
                };
                XHR.prototype._data = [];
            })(XMLHttpRequest);
        """
        )

        await asyncio.sleep(1)
        print("Getting you a lot of images. This may take a few moments...")

        element = browser.find_element_by_tag_name("body")
        # Scroll down
        for i in range(50):
            element.send_keys(Keys.PAGE_DOWN)
            await asyncio.sleep(0.3)

        try:
            browser.find_element_by_xpath('//input[@value="Show more results"]').click()
            for i in range(50):
                element.send_keys(Keys.PAGE_DOWN)
                await asyncio.sleep(0.3)  # bot id protection
        except:
            for i in range(50):
                element.send_keys(Keys.PAGE_DOWN)
                await asyncio.sleep(0.3)  # bot id protection

        print("Reached end of Page.")
        await asyncio.sleep(0.5)

        source = browser.page_source  # page source
        images = _image_objects_from_pack(_extract_data_pack_extended(source))

        ajax_data = browser.execute_script("return XMLHttpRequest.prototype._data")
        for chunk in ajax_data:
            images += _image_objects_from_pack(_extract_data_pack_ajax(chunk))

        # close the browser
        browser.close()

        return images

    # Format the object in readable format

    async def similar_images(self, similar_images):
        try:
            searchUrl = (
                f"https://{GOOGLE_URL}/searchbyimage?site=search&sa=X&image_url="
                + similar_images
            )
            headers = {}
            headers[
                "User-Agent"
            ] = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"

            req1 = urllib.request.Request(searchUrl, headers=headers)
            resp1 = urllib.request.urlopen(req1)
            content = str(resp1.read())
            l1 = content.find("AMhZZ")
            l2 = content.find("&", l1)
            urll = content[l1:l2]

            newurl = (
                f"https://{GOOGLE_URL}/search?tbs=sbi:" + urll + "&site=search&sa=X"
            )
            req2 = urllib.request.Request(newurl, headers=headers)
            resp2 = urllib.request.urlopen(req2)
            l3 = content.find("/search?sa=X&amp;q=")
            l4 = content.find(";", l3 + 19)
            urll2 = content[l3 + 19 : l4]
            return urll2
        except:
            return "Cloud not connect to Google Images endpoint"

    # Building URL parameters

    # building main search URL

    # measures the file size
    def file_size(self, file_path):
        if os.path.isfile(file_path):
            file_info = os.stat(file_path)
            size = file_info.st_size
            for x in ["bytes", "KB", "MB", "GB", "TB"]:
                if size < 1024.0:
                    return "%3.1f %s" % (size, x)
                size /= 1024.0
            return size

    # keywords from file
    def keywords_from_file(self, file_name):
        search_keyword = []
        with codecs.open(file_name, "r", encoding="utf-8-sig") as f:
            if ".csv" in file_name:
                for line in f:
                    if line in ["\n", "\r\n"]:
                        pass
                    else:
                        search_keyword.append(line.replace("\n", "").replace("\r", ""))
            elif ".txt" in file_name:
                for line in f:
                    if line in ["\n", "\r\n"]:
                        pass
                    else:
                        search_keyword.append(line.replace("\n", "").replace("\r", ""))
            else:
                print(
                    "Invalid file type: Valid file types are either .txt or .csv \n"
                    "exiting..."
                )
                raise KeyError()
        return search_keyword

    async def fetch(self, client, url):
        async with client.get(url, timeout=10) as resp:
            resp.raise_for_status()
            return await resp.read(), resp.content_type

    # Download Images
    async def download_image(
        self, image_url, main_directory, dir_name, count, semaphore
    ):
        async with semaphore:
            try:
                async with aiohttp.ClientSession(
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.27 Safari/537.17"
                    }
                ) as client:
                    data, image_type = await self.fetch(client, image_url)
                try:
                    # timeout time to download an image
                    try:
                        image_name = (
                            str(count) + "_" + create_image_name(image_url, image_type)
                        )
                    except ValueError as e:
                        return (
                            "fail",
                            f"Invalid image format '{image_type}'. Skipping...",
                            "",
                            "",
                        )

                    path = os.path.join(main_directory, dir_name, image_name)
                    try:
                        with open(path, "wb") as output_file:
                            output_file.write(data)
                            absolute_path = os.path.abspath(path)
                    except OSError as e:
                        return (
                            "fail",
                            "OSError on an image...trying next one..."
                            + " Error: "
                            + str(e),
                            "",
                            "",
                        )

                    # return image name back to calling method to use it for thumbnail downloads
                    download_status = "success"
                    download_message = (
                        "Completed Image ====> " + str(count) + "." + image_name
                    )
                    return_image_name = str(count) + "." + image_name

                except UnicodeEncodeError as e:
                    download_status = "fail"
                    download_message = (
                        "UnicodeEncodeError on an image...trying next one..."
                        + " Error: "
                        + str(e)
                    )
                    return_image_name = ""
                    absolute_path = ""

                except URLError as e:
                    download_status = "fail"
                    download_message = (
                        "URLError on an image...trying next one..."
                        + " Error: "
                        + str(e)
                    )
                    return_image_name = ""
                    absolute_path = ""

                except BadStatusLine as e:
                    download_status = "fail"
                    download_message = (
                        "BadStatusLine on an image...trying next one..."
                        + " Error: "
                        + str(e)
                    )
                    return_image_name = ""
                    absolute_path = ""
            except (
                HTTPError,
                aiohttp.client_exceptions.ClientResponseError,
                asyncio.exceptions.TimeoutError,
                aiohttp.client_exceptions.ClientPayloadError,
                aiohttp.client_exceptions.InvalidURL,
                aiohttp.client_exceptions.ServerDisconnectedError,
            ) as e:  # If there is any HTTPError
                download_status = "fail"
                download_message = (
                    "HTTPError on an image...trying next one..." + " Error: " + str(e)
                )
                return_image_name = ""
                absolute_path = ""

            except URLError as e:
                download_status = "fail"
                download_message = (
                    "URLError on an image...trying next one..." + " Error: " + str(e)
                )
                return_image_name = ""
                absolute_path = ""

            except ssl.CertificateError as e:
                download_status = "fail"
                download_message = (
                    "CertificateError on an image...trying next one..."
                    + " Error: "
                    + str(e)
                )
                return_image_name = ""
                absolute_path = ""

            except IOError as e:  # If there is any IOError
                download_status = "fail"
                download_message = (
                    "IOError on an image...trying next one..." + " Error: " + str(e)
                )
                return_image_name = ""
                absolute_path = ""

            except IncompleteRead as e:
                download_status = "fail"
                download_message = (
                    "IncompleteReadError on an image...trying next one..."
                    + " Error: "
                    + str(e)
                )
                return_image_name = ""
                absolute_path = ""

        return download_status, download_message, return_image_name, absolute_path

    async def _get_all_items(self, image_objects, main_directory, dir_name, semaphore):
        formated_objects = list(map(format_object, image_objects))
        res = await asyncio.gather(
            *[
                self.download_image(
                    object["image_link"], main_directory, dir_name, count, semaphore
                )
                for count, object in enumerate(formated_objects)
            ]
        )
        items = []
        abs_path = []
        errorCount = 0
        for object, (
            download_status,
            download_message,
            return_image_name,
            absolute_path,
        ) in zip(formated_objects, res):
            if download_status != "success":
                errorCount += 1
                continue
            object["image_filename"] = return_image_name
            items.append(object)
            abs_path.append(absolute_path)

        return items, errorCount, abs_path

    async def get_image_urls(self, arguments):
        for arg in args_list:
            if arg not in arguments:
                arguments[arg] = None
        ######Initialization and Validation of user arguments
        if arguments["keywords"]:
            search_keyword = [str(item) for item in arguments["keywords"].split(",")]

        # Additional words added to keywords
        if arguments["suffix_keywords"]:
            suffix_keywords = [
                " " + str(sk) for sk in arguments["suffix_keywords"].split(",")
            ]
        else:
            suffix_keywords = [""]

        # Additional words added to keywords
        if arguments["prefix_keywords"]:
            prefix_keywords = [
                str(sk) + " " for sk in arguments["prefix_keywords"].split(",")
            ]
        else:
            prefix_keywords = [""]

        # Setting limit on number of images to be downloaded
        if arguments["limit"]:
            limit = int(arguments["limit"])
        else:
            limit = 100

        # If this argument is present, set the custom output directory
        images_groups = defaultdict(list)
        ######Initialization Complete
        for pky, sky, kw in product(prefix_keywords, suffix_keywords, search_keyword):
            search_term = pky + kw + sky

            params = build_url_parameters(arguments)  # building URL with params

            url = build_search_url(search_term, params)

            if limit < 101:
                images = await self.download_page(url)  # download page
            else:
                images = await self.download_extended_page(
                    url, arguments["chromedriver"]
                )
            dir_name = arguments.get("image_directory", search_term)
            images_groups[dir_name].extend(images)
        return images_groups

    async def download(self, images, main_directory="downloads", limit=None):
        paths = {dir_name: [] for dir_name in images}
        total_errors = 0
        for dir_name in images:
            create_directories(main_directory, dir_name)
        semaphore = asyncio.Semaphore(500)
        download_args = [
            (images, main_directory, dir_name, semaphore)
            for dir_name, images in images.items()
        ]
        paths_list = await asyncio.gather(
            *[self._get_all_items(*download_arg) for download_arg in download_args]
        )

        for (items, errorCount, abs_path), (_, _, dir_name, _) in zip(
            paths_list, download_args
        ):
            paths[dir_name].extend(
                [item | {"file_path": path} for path, item in zip(abs_path, items)]
            )
            total_errors = total_errors + errorCount
        return paths, total_errors
