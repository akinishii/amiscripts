"""
Get_CWBradarimg.py ver 1.1 coded by A.NISHII
台湾中央気象局の合成レーダー画像(反射強度)と落雷分布図を入手する
約24時間前のデータまで取得可能
Scraping Taiwan Central Weather Bureau's radar composite images
and lightning map images.

Requirements
Python>=3.8, requests, tqdm, pandas

Useage
python3 Get_CWDradarimg.py
*Line 20~26のparameterを設定してから実行すること

HISTORY(yyyy.mm.dd)
ver 1.0 First created 2023.06.12 A.NISHII
ver 1.1 Bug fixed 2023.09.04 A.NISHII

"""
###Parameter settings###
sdate = '202309030700' #Start date of dl (yyyymmddHHMM, TST(UTC+8))
edate = '202309040700' #End date of dl (yyyymmddHHMM, TST(UTC+8))
freq  = 10 #DL inverbal of images (in minutes)
region = 1 #0:Broad area 1:Limited area(around Taiwan only)
lighting = False #True: Lightning map also downloaded

outdir = './zoom' #Saving directory of figures
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
if region == 0:
    head = 'CV1_3600_'
elif region == 1:
    head = 'CV1_TW_3600_'
else:
    raise ValueError('"region" variable shold be set 0 or 1')

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
    
    rfigname = f'{head}{dt_str}.png'
    rfigurl  = f'https://www.cwb.gov.tw/Data/radar/{rfigname}'
    rfigpath = f'{rfigdir}/{rfigname}'
    print(rfigurl)
    dl_file(rfigurl,rfigpath)

    if lighting:
        lgtfigname = f'{dt_str}00_lgts.jpg'
        lgturl = f'https://www.cwb.gov.tw/Data/lightning/{lgtfigname}'
        lgtfigpath = f'{lgtdir}/{lgtfigname}'
        print(lgturl)
        dl_file(lgturl,lgtfigpath)
    
print('Finish')