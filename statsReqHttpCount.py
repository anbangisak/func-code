import json

def httpCodeCount(clientCodeCount, overallCodeCount):
    for key, val in clientCodeCount.items():
        print(key, val)
        if key in overallCodeCount and overallCodeCount[key] > 0:
            overallCodeCount[key] += val
        else:
            overallCodeCount[key] = val

def getDictJson(jsonSrc="stats4ReqCount.json"):
    # jsonSrc = "stats.json"
    dictObj = dict()
    with open(jsonSrc) as fileObj:
        dictObj = json.load(fileObj)
    # if dictObj:
    #     print(dictObj)
    return dictObj

def loopDict(dictObj):
    manifestHttpCodeCount = {}
    segmentHttpCodeCount = {}
    partHttpCodeCount =  {}
    OverallHttpCodeCount = {}
    for key, val in dictObj["metrics"].items():
        # if manifestHttpCodeCount:
        #     print(manifestHttpCodeCount)
        manifestHttpCodeCount = httpCodeCount(val["mediaPlReqHttpCode"], manifestHttpCodeCount)
        segmentHttpCodeCount = httpCodeCount(val["segmentHttpCode"], segmentHttpCodeCount)
        partHttpCodeCount = httpCodeCount(val["partHttpCode"], partHttpCodeCount)
        print(manifestHttpCodeCount, val["mediaPlReqHttpCode"])

dictObj = getDictJson()
loopDict(dictObj)