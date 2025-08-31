# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.d (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot module containing commands related to android"""

import asyncio
import json
import math
import os
import re
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from requests import get

from userbot import CMD_HELP, TEMP_DOWNLOAD_DIRECTORY, trgg
from userbot.events import register
from userbot.utils import chrome, human_to_bytes, humanbytes, md5, time_formatter

GITHUB = "https://github.com"


@register(outgoing=True, pattern="^\.magisk$".format(trg=trgg))
async def magisk(request):
    magisk_dict = {
        "Stable": "https://raw.githubusercontent.com/topjohnwu/magisk-files/master/stable.json",
        "Beta": "https://raw.githubusercontent.com/topjohnwu/magisk-files/master/beta.json",
        "Canary": "https://raw.githubusercontent.com/topjohnwu/magisk-files/master/canary.json",
    }
    releases = "Latest Magisk Releases:\n"
    for name, release_url in magisk_dict.items():
        data = get(release_url).json()
        releases += (
            f'{name}: [APK v{data["magisk"]["version"]}]({data["magisk"]["link"]}) | '
            f'[Changelog]({data["magisk"]["note"]})\n'
        )
    await request.edit(releases)


@register(outgoing=True, pattern=r"^\.device(?: |$)(\S*)".format(trg=trgg))
async def device_info(request):
    """ get android device basic info from its codename """
    textx = await request.get_reply_message()
    codename = request.pattern_match.group(1)
    if codename:
        pass
    elif textx:
        codename = textx.text
    else:
        await request.edit("`Usage: .device <codename> / <model>`")
        return
    data = json.loads(
        get(
            "https://raw.githubusercontent.com/androidtrackers/"
            "certified-android-devices/master/by_device.json"
        ).text
    )
    results = data.get(codename)
    if results:
        reply = f"**Search results for {codename}**:\n\n"
        for item in results:
            reply += (
                f"**Brand**: {item['brand']}\n"
                f"**Name**: {item['name']}\n"
                f"**Model**: {item['model']}\n\n"
            )
    else:
        reply = f"`Couldn't find info about {codename}!`\n"
    await request.edit(reply)


@register(outgoing=True, pattern=r"^\.codename(?: |)([\S]*)(?: |)([\s\S]*)".format(trg=trgg))
async def codename_info(request):
    """ search for android codename """
    textx = await request.get_reply_message()
    brand = request.pattern_match.group(1).lower()
    device = request.pattern_match.group(2).lower()

    if brand and device:
        pass
    elif textx:
        brand = textx.text.split(" ")[0]
        device = " ".join(textx.text.split(" ")[1:])
    else:
        await request.edit("`Usage: .codename <brand> <device>`")
        return

    data = json.loads(
        get(
            "https://raw.githubusercontent.com/androidtrackers/"
            "certified-android-devices/master/by_brand.json"
        ).text
    )
    devices_lower = {k.lower(): v for k, v in data.items()}  # Lower brand names in JSON
    devices = devices_lower.get(brand)
    results = [
        i
        for i in devices
        if i["name"].lower() == device.lower() or i["model"].lower() == device.lower()
    ]
    if results:
        reply = f"**Search results for {brand} {device}**:\n\n"
        if len(results) > 8:
            results = results[:8]
        for item in results:
            reply += (
                f"**Device**: {item['device']}\n"
                f"**Name**: {item['name']}\n"
                f"**Model**: {item['model']}\n\n"
            )
    else:
        reply = f"`Couldn't find {device} codename!`\n"
    await request.edit(reply)


@register(outgoing=True, pattern="^\.pixeldl(?: |$)(.*)".format(trg=trgg))
async def download_api(dl):
    await dl.edit("`Collecting information...`")
    URL = dl.pattern_match.group(1)
    URL_MSG = await dl.get_reply_message()
    if URL:
        pass
    elif URL_MSG:
        URL = URL_MSG.text
    else:
        await dl.edit("`Empty information...`")
        return
    if not re.findall(r"\bhttps?://download.*pixelexperience.*\.org\S+", URL):
        await dl.edit("`Invalid information...`")
        return
    driver = await chrome()
    await dl.edit("`Getting information...`")
    driver.get(URL)
    error = driver.find_elements_by_class_name("swal2-content")
    if len(error) > 0:
        if error[0].text == "File Not Found.":
            await dl.edit(f"`FileNotFoundError`: {URL} is not found.")
            return
    datas = driver.find_elements_by_class_name("download__meta")
    """ - enumerate data to make sure we download the matched version - """
    md5_origin = None
    i = None
    for index, value in enumerate(datas):
        for data in value.text.split("\n"):
            if data.startswith("MD5"):
                md5_origin = data.split(":")[1].strip()
                i = index
                break
        if md5_origin is not None and i is not None:
            break
    if md5_origin is None and i is None:
        await dl.edit("`There is no match version available...`")
    if URL.endswith("/"):
        file_name = URL.split("/")[-2]
    else:
        file_name = URL.split("/")[-1]
    file_path = TEMP_DOWNLOAD_DIRECTORY + file_name
    download = driver.find_elements_by_class_name("download__btn")[i]
    download.click()
    await dl.edit("`Starting download...`")
    file_size = human_to_bytes(download.text.split(None, 3)[-1].strip("()"))
    display_message = None
    complete = False
    start = time.time()
    while complete is False:
        if os.path.isfile(file_path + ".crdownload"):
            try:
                downloaded = os.stat(file_path + ".crdownload").st_size
                status = "Downloading"
            except OSError:  # Rare case
                await asyncio.sleep(1)
                continue
        elif os.path.isfile(file_path):
            downloaded = os.stat(file_path).st_size
            file_size = downloaded
            status = "Checking"
        else:
            await asyncio.sleep(0.3)
            continue
        diff = time.time() - start
        percentage = downloaded / file_size * 100
        speed = round(downloaded / diff, 2)
        eta = round((file_size - downloaded) / speed)
        prog_str = "`{0}` | [{1}{2}] `{3}%`".format(
            status,
            "".join(["█" for i in range(math.floor(percentage / 10))]),
            "".join(["░" for i in range(10 - math.floor(percentage / 10))]),
            round(percentage, 2),
        )
        current_message = (
            "`[DOWNLOAD]`\n\n"
            f"`{file_name}`\n"
            f"`Status`\n{prog_str}\n"
            f"`{humanbytes(downloaded)} of {humanbytes(file_size)}"
            f" @ {humanbytes(speed)}`\n"
            f"`ETA` -> {time_formatter(eta)}"
        )
        if (
            round(diff % 15.00) == 0
            and display_message != current_message
            or (downloaded == file_size)
        ):
            await dl.edit(current_message)
            display_message = current_message
        if downloaded == file_size:
            if not os.path.isfile(file_path):  # Rare case
                await asyncio.sleep(1)
                continue
            MD5 = await md5(file_path)
            if md5_origin == MD5:
                complete = True
            else:
                await dl.edit("`Download corrupt...`")
                os.remove(file_path)
                driver.quit()
                return
    await dl.respond(f"`{file_name}`\n\n" f"Successfully downloaded to `{file_path}`.")
    await dl.delete()
    driver.quit()
    return




@register(outgoing=True, pattern=r"^\.twrp(?: |$)(\S*)".format(trg=trgg))
async def twrp(request):
    """ get android device twrp """
    textx = await request.get_reply_message()
    device = request.pattern_match.group(1)
    if device:
        pass
    elif textx:
        device = textx.text.split(" ")[0]
    else:
        await request.edit("`Usage: .twrp <codename>`")
        return
    url = get(f"https://dl.twrp.me/{device}/")
    if url.status_code == 404:
        reply = f"`Couldn't find twrp downloads for {device}!`\n"
        await request.edit(reply)
        return
    page = BeautifulSoup(url.content, "lxml")
    download = page.find("table").find("tr").find("a")
    dl_link = f"https://dl.twrp.me{download['href']}"
    dl_file = download.text
    size = page.find("span", {"class": "filesize"}).text
    date = page.find("em").text.strip()
    reply = (
        f"**Latest TWRP for {device}:**\n"
        f"[{dl_file}]({dl_link}) - __{size}__\n"
        f"**Updated:** __{date}__\n"
    )
    await request.edit(reply)

@register(outgoing=True, pattern=r"^\.specs(?: |)([\s\S]*)".format(trg=trgg))
async def devices_specifications(request):
    textx = await request.get_reply_message()
    device_query = request.pattern_match.group(1).strip()
    if device_query:
        pass
    elif textx:
        device_query = textx.text.strip()
    else:
        await request.edit("`Usage: .specs <phone name>`\n`Example: .specs iPhone 15 Pro`")
        return
    if not device_query:
        await request.edit("`Please provide a phone name`\n`Example: .specs Samsung Galaxy S24`")
        return
    await request.edit(f"`🔍 Searching specifications for {device_query}...`")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        search_url = f"https://www.gsmarena.com/results.php3?sQuickSearch=yes&sName={quote(device_query)}"
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code != 200:
            await request.edit(f"`⚠ Error searching for {device_query}`")
            return
        soup = BeautifulSoup(response.content, 'html.parser')
        device_links = []
        makers_div = soup.find('div', class_='makers')
        if makers_div:
            links = makers_div.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href and href.endswith('.php'):
                    device_links.append(f"https://www.gsmarena.com/{href}")
        if not device_links:
            await request.edit(f"`⚠ No results found for {device_query}`")
            return
        phone_url = None
        device_query_lower = device_query.lower().replace(' ', '')
        for link in device_links:
            link_name = link.split('/')[-1].replace('.php', '').replace('_', ' ').replace('-', ' ')
            link_name_clean = link_name.lower().replace(' ', '')
            if link_name_clean == device_query_lower:
                phone_url = link
                break
        if not phone_url:
            best_match = None
            best_score = 0
            for link in device_links:
                link_name = link.split('/')[-1].replace('.php', '').replace('_', ' ').replace('-', ' ')
                link_name_clean = link_name.lower().replace(' ', '')
                score = 0
                query_words = device_query.lower().split()
                link_words = link_name.lower().split()
                matching_words = sum(1 for word in query_words if word in link_words)
                score = matching_words / len(query_words) if query_words else 0
                if device_query_lower in link_name_clean:
                    score += 0.5
                extra_words = len(link_words) - len(query_words)
                if extra_words > 0:
                    score -= (extra_words * 0.1)
                if score > best_score:
                    best_score = score
                    best_match = link
            phone_url = best_match if best_match else device_links[0]
        phone_response = requests.get(phone_url, headers=headers, timeout=10)
        if phone_response.status_code != 200:
            await request.edit(f"`⚠ Error loading device page`")
            return
        phone_soup = BeautifulSoup(phone_response.content, 'html.parser')
        phone_name = None
        name_elem = phone_soup.find('h1', class_='specs-phone-name-title')
        if name_elem:
            phone_name = name_elem.get_text().strip()
        if not phone_name:
            phone_name = device_query.title()
        all_specs = {}
        specs_div = phone_soup.find('div', {'id': 'specs-list'})
        if specs_div:
            tables = specs_div.find_all('table', {'cellspacing': '0'})
            for table in tables:
                current_category = None
                rows = table.find_all('tr')
                for row in rows:
                    th = row.find('th', {'scope': 'row'})
                    if th:
                        current_category = th.get_text().strip()
                        if current_category not in all_specs:
                            all_specs[current_category] = {}
                    ttl_cell = row.find('td', {'class': 'ttl'})
                    nfo_cell = row.find('td', {'class': 'nfo'})
                    if ttl_cell and nfo_cell:
                        spec_name_elem = ttl_cell.find('a')
                        if spec_name_elem:
                            spec_name = spec_name_elem.get_text().strip()
                        else:
                            spec_name = ttl_cell.get_text().strip()
                        spec_value = nfo_cell.get_text().strip()
                        spec_value = re.sub(r'\s+', ' ', spec_value).strip()
                        if spec_name and spec_value and spec_value != '-' and current_category:
                            if len(spec_value) > 200:
                                spec_value = spec_value[:200] + "..."
                            all_specs[current_category][spec_name] = spec_value
        if all_specs:
            reply = f"**📱 {phone_name}**\n\n"
            important_order = ['Network', 'Launch', 'Body', 'Display', 'Platform', 'Memory', 'Main Camera', 'Selfie Camera', 'Battery']
            shown_categories = []
            for category in important_order:
                for cat_name, specs in all_specs.items():
                    if category.lower() in cat_name.lower() and specs:
                        reply += f"**{cat_name.upper()}**\n"
                        count = 0
                        for spec_name, spec_value in specs.items():
                            if count < 5:
                                if len(spec_value) > 100:
                                    spec_value = spec_value[:100] + "..."
                                reply += f"• **{spec_name}**: {spec_value}\n"
                                count += 1
                        reply += "\n"
                        shown_categories.append(cat_name)
                        break
            for cat_name, specs in all_specs.items():
                if cat_name not in shown_categories and len(reply) < 3500:
                    if specs:
                        reply += f"**{cat_name.upper()}**\n"
                        count = 0
                        for spec_name, spec_value in specs.items():
                            if count < 3:
                                if len(spec_value) > 100:
                                    spec_value = spec_value[:100] + "..."
                                reply += f"• **{spec_name}**: {spec_value}\n"
                                count += 1
                        reply += "\n"
            if len(reply) > 4000:
                reply = reply[:3900] + "\n\n`...truncated`"
            await request.edit(reply)
        else:
            await request.edit(f"**📱 {phone_name}**\n\n`⚠ Could not extract specifications`\n`Try checking manually:` {phone_url}")
    except requests.exceptions.Timeout:
        await request.edit(f"`⏱️ Timeout searching for {device_query}`")
    except Exception as e:
        await request.edit(f"`⚠ Error processing {device_query}`")


@register(outgoing=True, pattern=r"^\.ofox(?: |$)(\S*)")
async def ofox(request):
    """ get android device ofox """
    textx = await request.get_reply_message()
    device = request.pattern_match.group(1)
    if device:
        pass
    elif textx:
        device = textx.text.split(" ")[0]
    else:
        await request.edit("`Usage: .ofox <codename>`")
        return
    url = get(f"https://api.orangefox.download/v3/devices/get?codename={device}")
    if url.status_code == 404:
        await request.edit(f"`Couldn't find OrangeFox Recovery for {device}!`\n")
        return
    info = json.loads(url.text)
    if 'url' in info:
        ed = (
            f"**Latest OFOX Recovery for {info['full_name']}:**\n"
            f"[{device}]({info['url']})\n"
            f"Maintainer: {info['maintainer']['name']}"
        )
        await request.edit(ed)
    else:
        await request.edit("Mmmm... Some issue occured")


CMD_HELP.update(
    {
        "android": ".magisk\
\nGet latest Magisk releases\
\n\n.device <codename>\
\nUsage: Get info about android device codename or model.\
\n\n.codename <brand> <device>\
\nUsage: Search for android device codename.\
\n\n.pixeldl **<download.pixelexperience.org>**\
\nUsage: Download pixel experience ROM into your userbot server.\
\n\n.specs <brand> <device>\
\nUsage: Get device specifications info.\
\n\n.twrp <codename>\
\nUsage: Get latest twrp download for android device.\
\n\n.ofox <codename>\
\nUsage: Get latest ofox recovery download for android device."
    }
)
