import urllib.request
import re

req = urllib.request.Request('https://skilltrack.web.onrender.com', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    html = response.read().decode('utf-8')
    print('Index fetched')
    
    scripts = re.findall(r'<script type="module" crossorigin src="(.*?)"></script>', html)
    if scripts:
        js_url = 'https://skilltrack.web.onrender.com' + scripts[0]
        print('Fetching JS:', js_url)
        js_req = urllib.request.Request(js_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(js_req) as js_response:
            js_text = js_response.read().decode('utf-8')
            match = re.search(r'"(https?://skilltrack-api.*?)"', js_text)
            if match:
                print('Found API URL in JS:', match.group(1))
            else:
                print('Did not find skilltrack-api in JS')
