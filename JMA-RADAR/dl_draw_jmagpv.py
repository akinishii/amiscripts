"""
dl_draw_jmagpv.py ver 1.0 coded by A.NISHII 

京大生存圏データベースからJMA-GPVデータをダウンロードして
降雨強度データを描画するスクリプト
A scirpt to download JMA-GPV data from RISH (Kyoto Univ.) and
draw composite rainfall intensity data

Useage
45~60行目辺りのパラメータを指定し，以下のコマンドを実行
Set variables around Line 45-60 and run
python3 dl_draw_jmagpv.py

NOTE
wgirb2のpathが通っている必要がある
You need wgrib2 to use this script
Get wgrib2: https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2/

HISTORY(yyyy.mm.dd)
Ver 1.0: Code Created 2022.12.14 by A.NISHII

"""

# In[72]:
import numpy as np
import subprocess
import tarfile
import datetime
import matplotlib.pyplot as plt
import glob
import requests
from os.path import exists
from os import makedirs, remove
from shutil import move
import matplotlib.ticker as mticker
from matplotlib.colors import ListedColormap, BoundaryNorm
import cartopy.crs as ccrs
from cartopy.mpl.ticker import LatitudeFormatter,LongitudeFormatter


#%% 
##Set Parameters
sdate = '201807030800' ##UTCで指定 (yyyymmddHHMM). しかし画像はJSTにより出力される。
edate = '201807030830' ##UTCで指定 (yyyymmddHHMM)

##Cutting range
cutrange = [120,150,22,45]            #表示範囲([lon1, lon2, lat1, lat2]) lon1<lon2, lat1<lat2を満たすこと 
xtick_info = np.arange(120,150.1,10.0) #表示する経度ラベルをリスト or ndarrayで指定
ytick_info = np.arange(25,45.01,5.0)   #表示する緯度ラベルを指定

DL_rish = True #True: 京大生存圏データベースからダウンロードする
savebin = False #True: wgrib2で変換したバイナリファイルを保存する(現段階ではFalse推奨)
savefig = True #True: 画像を保存するかどうか

rawd_path = './jmagpv_raw'    #京大生存圏からDLしたデータを保存するディレクトリ
outdir_bin = './jmagpv_bin'   #変換したバイナリファイルを保存するディレクトリ(savebin=Trueのとき有効)
outdir_fig = './fig_rint' #変換した画像を保存するディレクトリ(savefig=Trueのとき有効)

#plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = 14 #フォントサイズ
plt.rcParams['xtick.labelsize'] = 12 #経度ラベルのフォントサイズ
plt.rcParams['ytick.labelsize'] = 12 #緯度ラベルのフォントサイズ

##End of set parameters

# In[77]: Definision of functions
def DL_RawGPV(path,date):
    url = 'http://database.rish.kyoto-u.ac.jp/arch/jmadata/data/jma-radar/synthetic/original/'+date[0:4]+'/'+date[4:6]+'/'+date[6:8]
    #print(url)
    fname = 'Z__C_RJTD_'+date+'00_RDR_JMAGPV__grib2.tar'
    file = requests.get(url+'/'+fname)
    
    dlpath = path+'/'+date[0:4]+'/'+date[4:6]+'/'+date[6:8]+'/'
    #print(dlpath)
    makedirs(dlpath,exist_ok=True)
        
    with open(dlpath + fname, 'wb') as f:
        f.write(file.content)


# In[78]:


def Unzip_Decode(tarpath,binname, date):
    ##tarファイルを展開
    with tarfile.open(tarpath,'r') as tf:
        tf.extractall(path='.')
    
    ##1km 解像度のgrib2ファイルのpathを取得
    gribpath = 'Z__C_RJTD_{0}00_RDR_JMAGPV_Ggis1km_Prr10lv_ANAL_grib2.bin'.format(date)
        
    ##Decode grib2 by wgrib2 (4-byte浮動小数点型バイナリに変換)
    commands = ['wgrib2',gribpath,'-no_header','-bin',binname]
    subprocess.run(commands)


# In[79]:
def Get_Rint(fname, xnum, ynum):
    print(fname)
    rint = np.fromfile(fname, dtype=np.float32)
    rint = rint.reshape((ynum, xnum))
    return rint

# In[103]:
def Create_Cmap(clevs):
    ##0,5,10,20,30,50,80,120
    cmap_rgb=np.array(
             [[160,210,255],
              [33,140,255],
              [0,65,255],
              [250,245,0],
              [255,153,0],
              [255,40,0],
              [181,0,91],
              [204,0,160]]
              ) / 256.
    #cmap = ListedColormap(['green','skyblue','deepskyblue','yellow','red','tomato','darkred','darkviolet'])
    cmap = ListedColormap(cmap_rgb)
    #cmap = LinearSegmentedColormap(cmap_rgb)
    cmap.set_under('white')
    cmap.set_over(np.array([218,112,214])/256.)
    cmap.set_bad(np.array([220,220,220])/256.)
    #cmap.set_extremes(bad=np.array([200,200,200])/256.,under='white',over=np.array([218,112,214])/256.)
    norm = BoundaryNorm(clevs,cmap.N)
    return cmap, norm
 

def Set_Map_Ticks(ax,xticks,yticks):
    gl = ax.gridlines(crs=ccrs.PlateCarree(),draw_labels=False,linewidth=0)
    gl.xlocator = mticker.FixedLocator(xticks)
    gl.ylocator = mticker.FixedLocator(yticks)
    ax.set_xticks(xticks,crs=ccrs.PlateCarree())
    ax.set_yticks(yticks,crs=ccrs.PlateCarree())  
    ax.xaxis.set_major_formatter(LongitudeFormatter())
    ax.yaxis.set_major_formatter(LatitudeFormatter())
    #ax.set_xlabel('Longitude')
    #ax.set_ylabel('Latitude')


def Draw_JMAGPV(rint, lons, lats, xticks, yticks, date,savepath,save=False):
    levels = [0,5,10,20,30,50,80,120]
    extent = [lons[0],lons[-1],lats[0],lats[-1]]
    fig = plt.figure()
    ax = fig.add_subplot(111,projection=ccrs.PlateCarree())
    ax.coastlines(resolution='10m',linewidth=0.5)
    ax.set_extent(extent,ccrs.PlateCarree())
    rint_draw = np.where(rint>0.01,rint,-1.)
    rint_draw = np.where(rint_draw<999,rint_draw,np.nan)
    cmap, norm = Create_Cmap(levels)
    print(rint_draw.shape)
    cm = ax.imshow(rint_draw, cmap=cmap, norm=norm, extent=extent, origin='lower')
    #cm = ax.contourf(lons,lats,rint_draw,cmap=cmap, norm=norm)
    cbar = fig.colorbar(cm, ax=ax, ticks=levels,extend='both',shrink=0.8)
    cbar.set_label('[mm/h]')
    Set_Map_Ticks(ax,xticks, yticks)
    ax.set_title('JMA-GPV Rainfall Intensity [mm/h]\n{0}/{1}/{2} {3}:{4} JST'.format(
                 date[0:4],date[4:6],date[6:8],date[8:10],date[10:12]))
    if savefig:
        savedir = '{0}/{1}/'.format(savepath, date[0:8])
        makedirs(savedir,exist_ok=True)
        ofname = savedir + 'jmagpv_{0}jst.jpg'.format(date)
        plt.savefig(ofname,dpi=300,bbox_inches='tight')
    else:
        plt.show()
    plt.close()


def Move_Clear(savebin, outdir_bin, date):
    flist = glob.glob('Z__C_RJTD*.bin')
    if savebin:
        savedir = '{0}/{1}/'.format(outdir_bin,date[0:8])
        makedirs(savedir,exist_ok=True)
        flist_bin = glob.glob('jmagpv_*.bin')
        for f in flist_bin:
            move(f,savedir)
    else:
        flist.extend(glob.glob('jmagpv_*.bin'))
        
    for f in flist:
        remove(f)
        #print(f+' removed.')


# In[102]: Main
raw_xmax = 2560
raw_ymax = 3360
lats = np.arange(0,raw_ymax,dtype=np.float64) * 0.008333 +  20.004167
lons = np.arange(0,raw_xmax,dtype=np.float64) * 0.012500 + 118.006250
dint = 10

cutlon = lons[(cutrange[0]<=lons)&(lons<=cutrange[1])]
cutlat = lats[(cutrange[2]<=lats)&(lats<=cutrange[3])]
clon_midx = np.argmax(lons>cutrange[0])
clat_midx = np.argmax(lats>cutrange[2])
clon_idx = np.array([clon_midx,clon_midx+len(cutlon)],dtype=np.int32)
clat_idx = np.array([clat_midx,clat_midx+len(cutlat)],dtype=np.int32)

sdate_dt = datetime.datetime.strptime(sdate,'%Y%m%d%H%M')
edate_dt = datetime.datetime.strptime(edate,'%Y%m%d%H%M')
hours =  int((edate_dt - sdate_dt).seconds / 3600.)

rints = np.zeros((hours*int(60/dint),len(cutlat),len(cutlon)))

date_dt = sdate_dt
date = date_dt.strftime("%Y%m%d%H%M")

while True:
    tpath = rawd_path + '/{0}/{1}/{2}/Z__C_RJTD_{3}00_RDR_JMAGPV__grib2.tar'.format(
            date[0:4],date[4:6],date[6:8],date)

    #print(cum_count,tpath)
    if not exists(tpath):
        if DL_rish:
            print('Download data from Internet')
            DL_RawGPV(rawd_path, date)
        else:
            print(tpath + 'Not found! Skip this time')
            date_dt = date_dt+datetime.timedelta(minutes=dint)
            date = date_dt.strftime("%Y%m%d%H%M")
            continue

    binname = './jmagpv_'+date+'00.bin'
    Unzip_Decode(tpath,binname,date)

    rint_full = Get_Rint(binname,raw_xmax,raw_ymax)
    crint = rint_full[clat_idx[0]:clat_idx[1],clon_idx[0]:clon_idx[1]]
    date_jst = (date_dt+datetime.timedelta(hours=9)).strftime("%Y%m%d%H%M")
    Draw_JMAGPV(crint, cutlon, cutlat, xtick_info, ytick_info, date_jst, outdir_fig, savefig)

    Move_Clear(savebin, outdir_bin, date)
            
    if date == edate:
        break
    
    date_dt = date_dt+datetime.timedelta(minutes=dint)
    date = date_dt.strftime("%Y%m%d%H%M")
