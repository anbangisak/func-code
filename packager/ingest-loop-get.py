import requests
import time

for idx in range(1, 10):
    assetId = "8cd27454-4be6-5077-a872-98a91a3c1357-test{}".format(idx)
    url = "http://mce-vod-am-svc.vmp-vode.astro-vmp-staging.vmpastroev.net/workflows/vode/assets/{}".format(assetId)
    resp = requests.get(url, verify=False)
    print(resp.status_code)
    print(resp.json())
