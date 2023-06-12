"""
Get_KMAradarimg.py ver 1.0 coded by A.NISHII
韓国気象庁の合成レーダー画像(反射強度)と落雷分布図を入手する
レーダー画像は約4日前、落雷画像は約10日前まで取得可能
Scraping Korean Meteorological Administration's radar composite images
and lightning map images.

Requirements
Python>=3.8, requests, tqdm, pandas

Useage
python3 Get_KMAradarimg.py
*Line 20~25のparameterを設定してから実行すること

HISTORY(yyyy.mm.dd)
ver 1.0 First created 2023.06.12 A.NISHII

"""
###Parameter settings###
sdate = '202306011200' #Start date of dl (yyyymmddHHMM, KST(UTC+9))
edate = '202306011200' #End date of dl (yyyymmddHHMM, KST(UTC+9))
freq  = 5 #DL inverbal of images (in minutes, 5 is minimum)
lighting = True #True: Lightning map also downloaded

outdir = './rimg_kma' #Saving directory of figures
###End of Parameter settings###

#import libraries
import requests
from tqdm import tqdm
from pandas import date_range
from os import makedirs
from datetime import datetime

#Function for downloading images.
def dl_file(url,savepath):
    res = requests.get(url,stream=True,timeout=6.1)
    stc = res.status_code
    if stc == requests.codes.ok:
        fsize = int(res.headers['content-length'])
        if res.headers['Content-Type'] != 'image/png':
            print('Link is not an image. Skip downloading this file.')
            return -1
        pbar = tqdm(total=fsize,unit='B',unit_scale=True)
        with open(savepath,'wb') as f:
            for chunk in res.iter_content(chunk_size=1024):
                f.write(chunk)
                pbar.update(len(chunk))
        pbar.close()
    else:
        print(f'{res.status_code} error raised. Skip downloading this file.')
        return stc
    
    return 0

###Main###
#Define array of dates
sd_dt = datetime.strptime(sdate,'%Y%m%d%H%M')
ed_dt = datetime.strptime(edate,'%Y%m%d%H%M')
dts   = date_range(sd_dt,ed_dt,freq=f'{freq}min',inclusive='both')
if len(dts) == 0: raise ValueError('Invalid range of dates')

rfigdir=f'{outdir}/radar'
makedirs(rfigdir,exist_ok=True)
if lighting: 
    lgtdir = f'{outdir}/lightning'
    makedirs(lgtdir,exist_ok=True)

#Get images
for dt in dts:
    print(f'Downloading {dt}...')
    dt_str = dt.strftime('%Y%m%d%H%M')
    rfigname = f'RDR_CMP_WRC_{dt_str}.png'
    rfigurl  = f'https://web.kma.go.kr/repositary/image/rdr/img/{rfigname}'
    rfigpath = f'{rfigdir}/{rfigname}'
    print(rfigurl)
    dl_file(rfigurl,rfigpath)
    if lighting:
        lgtfigname = f'lgt_kma_{dt_str}.png'
        lgturl = f'https://web.kma.go.kr/repositary/image/lgt/img/{lgtfigname}'
        lgtfigpath = f'{lgtdir}/{lgtfigname}'
        print(lgturl)
        dl_file(lgturl,lgtfigpath)
    
print('Finish')
