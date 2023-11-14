import requests
import time

for idx in range(1, 100):
    assetId = "8cd27454-4be6-5077-a872-98a91a3c1357-test{}".format(idx)
    data = {'assetId': assetId,
 'assetUrl': 'http://mce-vod-am-svc:7001/workflows/vode/assets/{0}'.format(assetId),
 'statusCallback': {'url': ''},
 'mediaSource': {'streams': [{'name': '{0}-0'.format(assetId),
    'sourceUrl': 'https://s3-ap-southeast-1.amazonaws.com/ivpcontributionstaging/fullasset/JAEZI01HM01AA/JAEZI01HM01AA_1/Profile_Layer1.ts'},
   {'name': '{0}-1'.format(assetId),
    'sourceUrl': 'https://s3-ap-southeast-1.amazonaws.com/ivpcontributionstaging/fullasset/JAEZI01HM01AA/JAEZI01HM01AA_1/Profile_Layer2.ts'},
   {'name': '{0}-2'.format(assetId),
    'sourceUrl': 'https://s3-ap-southeast-1.amazonaws.com/ivpcontributionstaging/fullasset/JAEZI01HM01AA/JAEZI01HM01AA_1/Profile_Layer3.ts'},
   {'name': '{0}-3'.format(assetId),
    'sourceUrl': 'https://s3-ap-southeast-1.amazonaws.com/ivpcontributionstaging/fullasset/JAEZI01HM01AA/JAEZI01HM01AA_1/Profile_Layer4.ts'},
   {'name': '{0}-4'.format(assetId),
    'sourceUrl': 'https://s3-ap-southeast-1.amazonaws.com/ivpcontributionstaging/fullasset/JAEZI01HM01AA/JAEZI01HM01AA_1/Profile_Layer5.ts'},
   {'name': '{0}-5'.format(assetId),
    'sourceUrl': 'https://s3-ap-southeast-1.amazonaws.com/ivpcontributionstaging/fullasset/JAEZI01HM01AA/JAEZI01HM01AA_1/Profile_Layer6.ts'},
   {'name': '{0}-6'.format(assetId),
    'sourceUrl': 'https://s3-ap-southeast-1.amazonaws.com/ivpcontributionstaging/fullasset/JAEZI01HM01AA/JAEZI01HM01AA_1/Profile_Layer7.ts'},
   {'name': '{0}-7'.format(assetId),
    'sourceUrl': 'https://s3-ap-southeast-1.amazonaws.com/ivpcontributionstaging/fullasset/JAEZI01HM01AA/JAEZI01HM01AA_1/Profile_Layer8.ts'},
   {'name': '{0}-8'.format(assetId),
    'sourceUrl': 'https://s3-ap-southeast-1.amazonaws.com/ivpcontributionstaging/fullasset/JAEZI01HM01AA/JAEZI01HM01AA_1/Profile_Layer9.ts'},
   {'name': '{0}-9'.format(assetId),
    'sourceUrl': 'https://s3-ap-southeast-1.amazonaws.com/ivpcontributionstaging/fullasset/JAEZI01HM01AA/JAEZI01HM01AA_1/Profile_Layer10.ts'}],
  'ebpMode': True}}
    postApiHeader = {"Content-type": "application/json"}
    # url = "http://mce-vod-am-svc.auto-vod-origin.mf5.astroeng.net/workflows/auto-vod-origin/assets"
    url = "http://mce-vod-am-svc.vmp-vode.astro-vmp-staging.vmpastroev.net/workflows/vode/assets"
    print(data)
    # resp = requests.post(url, data=data, headers=postApiHeader, verify=False)
    resp = requests.post(url, json=data, headers=postApiHeader, verify=False)
    print(resp.status_code)
    print(resp.json())

