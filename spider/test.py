import requests
from lxml import etree
divs_xpath = '//div[@class="row"]//div'
url = 'http://glidedsky.com/level/web/crawler-basic-2?page={}'
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36",
    "Referer":"http://glidedsky.com/submission/crawler-basic-1",
    "Cookie":"__ga=GA1.2.709410983.1589167367; Hm_lvt_dde6ba2851f3db0ddc415ce0f895822e=1589245194; footprints=eyJpdiI6ImpUXC9wa1FSVldLRllacVhHY0lENzFBPT0iLCJ2YWx1ZSI6IjdwdzVnVzA5bFwvYWN0VHR1NW93RXU5aGp4RXJSK05QZ1d2ZVJRSzFLTEVUOWxkeUpmb1J5WGJ2SWJVYlE1NExLIiwibWFjIjoiMDI3NWY1ZmI1OGQxNjFhNDhiZjY4ZTEzZjk5Y2NmOTdiNTE5NWU5MjM1YTI0MzE2NzFkNjgzOGFiN2IzMWZlYyJ9; Hm_lvt_020fbaad6104bcddd1db12d6b78812f6=1589167367,1589245188,1589418935; _gid=GA1.2.1918191875.1589418935; remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d=eyJpdiI6Im9IMGRSXC9BS09NWTRJMmY4K3lETkp3PT0iLCJ2YWx1ZSI6Ik1icTJBU3ZldXJsaXpLZkFWclJOUm5zRTM1OEdnclJVb0c3UlVpMGFTNWZwWGxMaGFUOHNYZUxQanoyMzN5c3RHRGxPdXZyc3JXbkk2UVlKSW9XbUpNVTd4OEdMVEFZTjU2NUN4MDNweVlLU2JYWEY2SFwvVis5TFA3YlBQdmluWFVTejlhQUZ1bTNPaEMrSHRuRnRhTW1wMzZsTWZJZ1NGR0ZERkFPb1crRG89IiwibWFjIjoiMzAwM2JjOWUxY2FmNmExMGNiMTBlZmFhNGFmM2VhM2QzZWM5ODMwZGEzNjNjNjVlZjk2MTJiYTg0MTg4Yjc2ZiJ9; XSRF-TOKEN=eyJpdiI6Ik1YUm5mOHl0dEM0SjVMTVJcLzBiempRPT0iLCJ2YWx1ZSI6Ik5iRENmUUcrS3NwMTZNbzJEXC9VSnRMWUN4RTdGNUlmdHJDdGhSV3ZvQkVHcnNJcmZ2OXNoTXhOellpSWN3cTFDIiwibWFjIjoiY2UyMThmNDFjY2NiZjU1YmIyNDc1YjMyODgyY2Y5NzY3OTU5ZjU5NDdmMjgwYWE3ZGYxN2UzMTljNzNiNmM2NiJ9; glidedsky_session=eyJpdiI6IjdwY3o2WUdENE50VCtHUDcra0VVbGc9PSIsInZhbHVlIjoiME02cjkwU2NqV0VKTzFmeHRRckV5S2tqT2djVVFKcHRvenV5R0kxcUhnQkRcL1dGVWZUZXBGRkFjQ1dBNzZhVnQiLCJtYWMiOiIzNmM2MjVlODFkM2Y0MDk3NTIwYTQwMGU5YzkzMWEzZDliMWU5ZDNiZjk5NzI4YTNlYzIzZDNmNTgwYmUxYmMyIn0%3D; Hm_lpvt_020fbaad6104bcddd1db12d6b78812f6=1589436234; _gat_gtag_UA_75859356_3=1"
}
sums = 0
for x in range(1,1001):
    resp = requests.get(url.format(x),headers=headers)
    html = etree.HTML(resp.content)
    divs = html.xpath(divs_xpath)
    num = 0
    for div in divs:
        num += int(div.text)
    sums +=num
    print sums