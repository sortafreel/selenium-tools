#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Selenium Tools
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import os
from datetime import datetime
from selenium import webdriver
from secrets import token_urlsafe
from pytils import translit
from PIL import Image
from random import randint
from dotenv import load_dotenv
from time import sleep
import string
import zipfile

# Load env variables
load_dotenv()


# check_load types
# ID = "id"
# XPATH = "xpath"
# LINK_TEXT = "link text"
# PARTIAL_LINK_TEXT = "partial link text"
# NAME = "name"
# TAG_NAME = "tag name"
# CLASS_NAME = "class name"
# CSS_SELECTOR = "css selector"


# Check element load
def check_load(check_type, check_id, driver, timeout=10):
    try:
        # Проверяю наличие элемента
        element_present = EC.presence_of_element_located(
            (getattr(By, check_type), check_id)
        )
        WebDriverWait(driver, timeout).until(element_present)
    except TimeoutException:
        print(check_type)
        print(check_id)
        print(
            'Timed out waiting for page to load: {} ({})'.format(check_type, check_id)
        )


# Slow typing to simulate human
def slow_type(print_text, sl_element):
    for char in print_text:
        sl_element.send_keys(char)
        sleep(0.05 + (randint(0, 150) / 1000))


# Short break
def short_sleep():
    sleep(0.1 + (randint(0, 200) / 1000))


# "Long" break
def long_sleep():
    sleep(0.5 + (randint(0, 500) / 1000))


# Chrome extension to use https
def create_proxyauth_extension(
    proxy_name,
    proxy_host,
    proxy_port,
    proxy_username,
    proxy_password,
    scheme='http',
    plugin_path=None,
):

    # Generate plugin name if needed
    if plugin_path is None:
        plugin_path = 'chrome_proxyauth_plugin_{}.zip'.format(proxy_name)

    # Extension manifest
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    # JS to use proxy
    background_js = string.Template(
        """
    var config = {
            mode: "fixed_servers",
            rules: {
              singleProxy: {
                scheme: "${scheme}",
                host: "${host}",
                port: parseInt(${port})
              },
              bypassList: ["foobar.com"]
            }
          };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "${username}",
                password: "${password}"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {urls: ["<all_urls>"]},
                ['blocking']
    );
    """
    ).substitute(
        host=proxy_host,
        port=proxy_port,
        username=proxy_username,
        password=proxy_password,
        scheme=scheme,
    )

    # Zip data to extension
    with zipfile.ZipFile(plugin_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)
    return plugin_path


# Screenshot function with scrolling
def fullpage_screenshot(driver, keyword=None, margin_left=None, margin_right=None):

    # Calculate base parameters
    total_width = driver.execute_script("return document.body.offsetWidth")
    total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
    viewport_width = driver.execute_script("return document.body.clientWidth")
    viewport_height = driver.execute_script("return window.innerHeight")

    # List to hold screenshot parts
    rectangles = []

    # Divide the screen into rectangles
    # Determine how many pixels of height I have already collected
    used_height = 0
    # Until the entire height is processed
    while used_height < total_height:
        # Determine how many pixels of width I have collected
        used_width = 0
        # Determine how many pixels I will collect with this rectangle
        top_height = used_height + viewport_height
        # If reached the limit - collect to the edge of the page
        if top_height > total_height:
            top_height = total_height
        # If the width is not fully covered
        while used_width < total_width:
            # Summarize the processed pixels with visible width
            top_width = used_width + viewport_width
            # If more than the maximum width - collect to the edge of the page
            if top_width > total_width:
                top_width = total_width
            # Determine the coordinates of the square
            current_rectangle = (used_width, used_height, top_width, top_height)
            # Add a rectangle to the list
            rectangles.append(current_rectangle)
            # Updating processed pixel widths
            used_width = used_width + viewport_width
        # Updating processed height pixels
        used_height = used_height + viewport_height

    # Create blank image and technical variables
    stitched_image = Image.new('RGB', (total_width, total_height))
    part = 0
    previous = None

    # Scroll the page
    for rectangle in rectangles:

        # Start scrolling with the second rectangle
        if previous is not None:
            # Scrolling
            driver.execute_script(
                "window.scroll({0}, {1})".format(rectangle[0], rectangle[1])
            )
            sleep(0.5)

        # Prepare screenshot part name
        file_name = "part_{0}.png".format(part)

        # Save screenshot part
        driver.get_screenshot_as_file(file_name)
        screenshot = Image.open(file_name)

        # If need to scroll more than page height - trimmed
        if rectangle[1] + viewport_height > total_height:
            # Determine the coordinates of the placement to the overall image
            offset = (rectangle[0], total_height - viewport_height)
        else:
            # Determine the coordinates of the placement to the overall image
            offset = (rectangle[0], rectangle[1])

        # Insert part of the screenshot on the overall image
        stitched_image.paste(screenshot, offset)

        # Delete the screenshot from the memory
        del screenshot
        os.remove(file_name)

        # Update screenshot parts indexes
        part = part + 1
        previous = rectangle

    # Checking whether to trim
    if margin_left and margin_right:
        # Crop image to adequate size
        si_height = stitched_image.size[1]
        final_image = stitched_image.crop(
            (int(margin_left), 0, int(margin_right), si_height)
        )
    # If no need to trim
    else:
        final_image = stitched_image

    # Check if the folder for temporary images is created
    images_temp_folder = os.environ.get('IMAGES_TEMP_FOLDER', 'Temp_Images')
    if not os.path.exists(images_temp_folder):
        os.makedirs(images_temp_folder)

    # Creating an unique file name and saving file
    # If the keyword is specified
    if keyword:
        # Translify the keyword
        # Add date and unique id
        file_local = '{}_{}_{}.png'.format(
            translit.translify(keyword).replace(' ', '_'),
            datetime.strftime(datetime.now(), '%Y-%m-%d_%H-%M-%S'),
            token_urlsafe(8),
        )
    # If not
    else:
        # Add date and unique id
        file_local = '{}_{}.png'.format(
            datetime.strftime(datetime.now(), '%Y-%m-%d_%H-%M-%S'), token_urlsafe(8)
        )

    # Save the image
    final_image.save(os.path.join(images_temp_folder, file_local))

    # Return the name of the image
    return file_local


# Driver preparation function
def prepare_driver(
    description=None,
    task_proxy=None,
    vnc=False,
    selenium_url='http://localhost:4444/wd/hub',
    screen_resolution='1920x1080',
    page_load_strategy='normal',
):

    # Configure driver properties
    capabilities = {
        'browserName': 'chrome',
        'version': '69.0',
        'enableVNC': vnc,
        'enableVideo': False,
        'screenResolution': '{}x24'.format(screen_resolution),
        'pageLoadStrategy': page_load_strategy,
        'env': ['LANG=ru_RU.UTF-8', 'LANGUAGE=ru:en', 'LC_ALL=ru_RU.UTF-8'],
        'chromeOptions': {
            #     'args': [
            #         '--disable-infobars',
            # '--disable-features=EnableEphemeralFlashPermission',
            # ],
            # 'prefs': {
            #     'profile.default_content_setting_values.plugins': 1,
            #     'profile.content_settings.plugin_whitelist.adobe-flash-player': 1,
            #     'profile.content_settings.exceptions.plugins.*,'
            #     '*.per_resource.adobe-flash-player': 1,
            #     'profile.default_content_settings.state.flash': 1,
            #     'profile.content_settings.exceptions.plugins.*,*.setting': 1,
            # },
        },
    }

    # Configure the proxy
    if task_proxy:
        # Prepare extension
        extension_path = create_proxyauth_extension(
            proxy_name=token_urlsafe(8),
            proxy_host=task_proxy.get('proxy_host'),
            proxy_port=task_proxy.get('proxy_port'),
            proxy_username=task_proxy.get('proxy_username'),
            proxy_password=task_proxy.get('proxy_password'),
        )
        # Encode extension to base64
        options = ChromeOptions()
        options.add_extension(extension_path)
        # Add to Chrome properties
        capabilities['chromeOptions'] = {
            **capabilities['chromeOptions'],
            **options.to_capabilities()['goog:chromeOptions'],
        }
        # Delete local extension
        os.remove(extension_path)

    # Add args
    capabilities['chromeOptions']['args'] = ['--disable-infobars']

    # Configure test name
    if description and task_proxy:
        capabilities['name'] = '{} | {} ({}:{})'.format(
            datetime.utcnow().strftime('%d.%m.%y %H:%M:%S'),
            description,
            task_proxy['proxy_host'],
            task_proxy['proxy_port'],
        )
    elif description:
        capabilities['name'] = '{} {}'.format(
            datetime.utcnow().strftime('%d.%m.%y %H:%M:%S'), description
        )

    # Connect Selenoid/Selenium Grid
    driver = webdriver.Remote(
        # Get url from ENV or working locally
        command_executor=os.environ.get('SELENIUM_URL', selenium_url),
        desired_capabilities=capabilities,
    )

    # Expand the browser to full window
    driver.set_window_size(1920, 1080)

    # Return driver
    return driver
