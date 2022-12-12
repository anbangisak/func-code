import sys
import re
import m3u8
from mpegdash.parser import MPEGDASHParser
from math import gcd
from functools import reduce

def getM3u8UrlBwList(manifestObj):
    bwlist = list()
    audlist = list()
    for plylt in manifestObj.playlists:
        for plymedia in plylt.media:
            audlist.append(plymedia.language)
        bwlist.append(plylt.stream_info.bandwidth)
    bwlist = list(set(bwlist))
    audlist = list(set(audlist))
    return bwlist, audlist

def getMatchingBwAudDict(urls_with_bw_aud, url):
    for key, val in urls_with_bw_aud.items():
        if val.get("url") == url:
            return val

def formatUrlLine(urls_with_bw_aud, urlPack):
    lineList = list()
    for key, urlObj in urlPack.items():
        pause = ""
        pack = ""
        urlBwAudDict = getMatchingBwAudDict(urls_with_bw_aud, urlObj["url"])
        # print("urlObj: ", urlObj)
        if urlObj:
            pack = urlObj.get("pack") if urlObj.get("pack") else "linear"
            pause = urlObj.get("pause") if urlObj.get("pause") else ""
        else:
            pack = "linear"
            pause = ""
        for bw in urlBwAudDict["bwList"]:
            urlVal = "url=" + urlBwAudDict["url"]
            urlVal += " bw={0}".format(bw)
            if(urlBwAudDict["audList"]):
                for lang in urlBwAudDict["audList"]:
                    urlVal2 = urlVal
                    urlVal2 += " lang={0}".format(lang)
                    urlVal2 += " pack={0}".format(pack)
                    urlVal2 += " pause={0}".format(pause) if pause else ""
                    lineList.append(urlVal2)
            else:
                urlVal += " pack={0}".format(pack)
                urlVal += " pause={0}".format(pause) if pause else ""
                lineList.append(urlVal)
    return lineList

def reqM3u8Url(url):
    print(url)
    m3u8Obj = m3u8.load(url, verify_ssl=False)
    return m3u8Obj

def getMpdBwAudList(manifestObj):
    bwlist = list()
    audlist = list()
    for period in manifestObj.periods:
        for adpt_set in period.adaptation_sets:
            if adpt_set.mime_type == "video/mp4":
                for rep in adpt_set.representations:
                    print(rep.bandwidth)
                    bwlist.append(rep.bandwidth)
            if adpt_set.mime_type == "audio/mp4":
                print(adpt_set.lang)
                audlist.append(adpt_set.lang)
    return bwlist, audlist

def reqMpdUrl(url):
    # unable to verify ssl
    mpdObj = MPEGDASHParser.parse(url)
    return mpdObj

def create_percent_urls(urlPack):
    for key, spec in urlPack.items():
        # for spec in val:
        print(spec)
    percent_list = [spec.get("percent") for key, spec in urlPack.items()]
    if(sum(percent_list) != 100):
        print("exiting since percentage is not 100%")
        exit(1)

    gcd_val = reduce(gcd, percent_list)
    # print(gcd_val)

    urls = []
    for key, spec in urlPack.items():
        print(spec)
        percent = spec.get("percent")
        loop_count = int(percent / gcd_val)
        for x in range(loop_count):
            urlVal = "url=" + spec.get("url")
            urlVal += " bw={0}".format(spec.get("bw")) if spec.get("bw") else ""
            urlVal += " lang={0}".format(spec.get("lang")) if spec.get("lang") else ""
            urlVal += " pack={0}".format(spec.get("pack")) if spec.get("pack") else ""
            urlVal += " pause={0}".format(spec.get("pause")) if spec.get("pause") else ""
            urls.append(urlVal)

    return urls

def getUrlList():
    fileObj = open("urls.txt", "r")
    urlList = list()
    urlPack = dict()
    counter = 0
    while True:
        line = fileObj.readline()
        if not line:
            break
        line = line.strip()
        if len(line) == 0 or (len(line) > 0 and line[0] == "#"):
            continue
        compRegex = re.compile("[^\\s]+")
        urlAttrList = compRegex.findall(line)
        # print(urlAttrList)
        url = ""
        pack = ""
        pause = ""
        percent = ""
        bw = ""
        lang = ""
        for val in urlAttrList:
            if url == "" and val.startswith("url="):
                url = val.replace("url=", "")
                urlList.append(url)
                urlPack[counter] = {"url": url}
            if pack == "" and val.startswith("pack="):
                pack = val.replace("pack=", "")
                urlPack[counter]["pack"] = pack
            if pause == "" and val.startswith("pause="):
                pause = val.replace("pause=", "")
                urlPack[counter]["pause"] = pause
            if percent == "" and val.startswith("percent="):
                percent = val.replace("percent=", "")
                urlPack[counter]["percent"] = int(percent) if percent else 0
            if bw == "" and val.startswith("bw="):
                percent = val.replace("bw=", "")
                urlPack[counter]["bw"] = int(bw) if bw else 0
            if lang == "" and val.startswith("lang="):
                lang = val.replace("lang=", "")
                urlPack[counter]["lang"] = lang

        if url == "":
            print("invalid urls.txt file")
            exit(0)
        counter += 1
    fileObj.close()
    return urlList, urlPack

if __name__ == "__main__":
    urlList, urlPack = getUrlList()
    print("urlPack: ", urlPack)

    if len(sys.argv) == 2 and sys.argv[1] == "-enable-all-stream":
        # print(sys.argv[1])
        urls_with_bw_aud = dict()
        for idx, url in enumerate(urlList):
            urls_with_bw_aud[idx] = {"url": url}
            if url.endswith(".m3u8"):
                manifestObj = reqM3u8Url(url)
                urls_with_bw_aud[idx]["bwList"], urls_with_bw_aud[idx]["audList"] = getM3u8UrlBwList(manifestObj)
            if url.endswith(".mpd"):
                manifestObj = reqMpdUrl(url)
                urls_with_bw_aud[idx]["bwList"], urls_with_bw_aud[idx]["audList"] = getMpdBwAudList(manifestObj)
        # print(urls)
        lineList = formatUrlLine(urls_with_bw_aud, urlPack)
    else:
        lineList = create_percent_urls(urlPack)

    textfile = open("urls10.txt", "w")
    for line in lineList:
        print(line)
        textfile.write(line + "\n")
    textfile.close()
