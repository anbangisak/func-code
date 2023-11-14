import requests
import time
#resp = requests.get("http://mce-vod-am-svc.vmp-vode.astro-vmp-staging.vmpastroev.net/workflows/vode/assets/3ff7fb5f-fb15-5a26-98da-6fef23fe1cb1", verify=False)
# data = {'mediaSource': {'streams': [{'name': 'fc03d380-60bf-11e9-a5db-c70878d9d913-0', 'sourceUrl': 'https://s3-ap-southeast-1.amazonaws.com/ivpcontributionstaging/fullasset/PACK0000000000145024/PACK0000000000145024_Layer1.ts'}, {'name': 'fc03d380-60bf-11e9-a5db-c70878d9d913-9', 'sourceUrl': 'https://s3-ap-southeast-1.amazonaws.com/ivpcontributionstaging/fullasset/PACK0000000000145024/PACK0000000000145024_Layer10.ts'}], 'ebpMode': False}, 'statusCallback': {'url': ''}, 'assetId': 'fc03d380-60bf-11e9-a5db-c70878d9d913'}
# postApiHeader = {"Content-type": "application/json"}
# url = "http://mce-vod-am-svc.vmp-vode.astro-vmp-staging.vmpastroev.net/workflows/vode/assets"
# resp = requests.post(url, data=data, headers=postApiHeader, verify=False)
# print(resp.status_code)
# print(resp.json())

#for idx in range(4500, 4700):
for idx in range(111, 112):
  # idx = 1
  assetId = "c56e2fa0-c6e1-4dd2-aa02-789184f5b8ff-astro-test{}".format(idx)
  data = {'assetId': assetId,
    'assetUrl': "http://mce-vod-am-svc:7001/workflows/gtd-vod-origin/assets/{}".format(assetId),
    'statusCallback': {'url': ''},
    'mediaSource': {'streams': [{'name': '{}-0'.format(assetId),
        'sourceUrl': 'https://s3-us-east-1.amazonaws.com/chn-mf-vmp-source-1/PACK0000000000100004/PACK0000000000100004_Layer1.ts'},
      {'name': '{}-1'.format(assetId),
        'sourceUrl': 'https://s3-us-east-1.amazonaws.com/chn-mf-vmp-source-1/PACK0000000000100004/PACK0000000000100004_Layer2.ts'},
      {'name': '{}-2'.format(assetId),
        'sourceUrl': 'https://s3-us-east-1.amazonaws.com/chn-mf-vmp-source-1/PACK0000000000100004/PACK0000000000100004_Layer3.ts'},
      {'name': '{}-3'.format(assetId),
        'sourceUrl': 'https://s3-us-east-1.amazonaws.com/chn-mf-vmp-source-1/PACK0000000000100004/PACK0000000000100004_Layer4.ts'},
      {'name': '{}-4'.format(assetId),
        'sourceUrl': 'https://s3-us-east-1.amazonaws.com/chn-mf-vmp-source-1/PACK0000000000100004/PACK0000000000100004_Layer5.ts'},
      {'name': '{}-5'.format(assetId),
        'sourceUrl': 'https://s3-us-east-1.amazonaws.com/chn-mf-vmp-source-1/PACK0000000000100004/PACK0000000000100004_Layer6.ts'},
      {'name': '{}-6'.format(assetId),
        'sourceUrl': 'https://s3-us-east-1.amazonaws.com/chn-mf-vmp-source-1/PACK0000000000100004/PACK0000000000100004_Layer7.ts'},
      {'name': '{}-7'.format(assetId),
        'sourceUrl': 'https://s3-us-east-1.amazonaws.com/chn-mf-vmp-source-1/PACK0000000000100004/PACK0000000000100004_Layer8.ts'}],
      'ebpMode': True}}

  postApiHeader = {"Content-type": "application/json"}
  url = "http://mce-vod-am-svc.gtd-vod-origin.mf5.astroeng.net/workflows/gtd-vod-origin/assets"
  print(data)
  # resp = requests.post(url, data=data, headers=postApiHeader, verify=False)
  resp = requests.post(url, json=data, headers=postApiHeader, verify=False)
  print(resp.status_code)
  print(resp.json())

#for idx in range(1000, 2000):
#for idx in range(3005, 3015):
  # idx = 1
#  assetId = "c56e2fa0-c6e1-4dd2-aa02-789184f5b8ff-astro-test{}".format(idx)
#  time.sleep(1)
#  getUrl = "http://mce-vod-am-svc.auto-vod-origin.mf5.astroeng.net/workflows/auto-vod-origin/assets/{}".format(assetId)
#  get_resp = requests.get(getUrl, verify=False)
#  print(get_resp.status_code)
#  print(get_resp.json())