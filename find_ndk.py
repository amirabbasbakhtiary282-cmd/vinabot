import urllib.request
import re

url = 'https://dl.google.com/android/repository/repository2-1.xml'
try:
    response = urllib.request.urlopen(url)
    content = response.read().decode()
    
    ndk_urls = re.findall(r'https://[^"\']*ndk[^"\']*linux[^"\']*\.zip', content)
    for u in set(ndk_urls):
        print(u)
        
except Exception as e:
    print('Error:', e)