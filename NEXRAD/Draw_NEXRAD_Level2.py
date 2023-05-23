#%%
"""
Draw_NEXRAD_Level2.py ver 2.2 coded by A.NISHII
NEXRAD Level-IIデータ(反射強度とドップラー速度)をPy-ARTを用いて描画する
デフォルトではファイルに入っているスキャン全てを描画する

HISTORY(yyyy.mm.dd)
ver 1.0 First created 2022.12.15 A.NISHII
ver 2.0 Implimented filelist mode 2023.05.14 A.NISHII
ver 2.1 Bug fixed 2023.05.23 A.NISHII
ver 2.2 Implimented drawing height circles 2023.05.23 A.NISHII
"""

import pyart
from matplotlib import colors
import matplotlib.pyplot as plt
from os.path import basename
from os import makedirs
import numpy as np
from sys import argv

#%%
##パラメータ設定
#fname = './PGUA/PGUA20230522_150343_V06' #NEXRAD Level-IIデータorLevel-IIデータのファイルリストを指定
fname = argv[1]
flist = True #Ture:fnameはファイルリスト、False:fnameはNEXRAD LEVEL2ファイル
figdir = '../fig/pgua_zv' #画像を出力するディレクトリ
xmin = -400 #描画範囲の西端 (レーダーを中心とした座標で東が正。kmで指定)
xmax = 400  #東端 (km)
ymin = -400 #南端 (レーダーを中心とした座標で北が正。kmで指定)
ymax = 400  #北端 (km)
c_dis_or_alt = 'alt' #'dis':レーダーからの距離を円で表示、'alt':ビーム高度を円で表示、'non':円を描かない
circle_range = np.array([2,4.5,8]) #dis:レーダーから半径circle_range kmの円を描く(リスト or ndarrayで指定)
                                  #alt:ビーム高度がcircle_range kmになる距離に円を描く
circle_label = True  #True:円にレーダーからの距離orビーム高度を表示する
labelpad = 15 #labelと円の距離 [km](半径400 km表示なら15,200 km表示なら5を推奨)
hair_length = 15 #レーダー中心を示す十字の長さ(km)('non'のときは描かない)
##パラメータ設定ここまで

#%%
#入力ファイル情報の取得
print(f'Inputfile: {fname}')
makedirs(figdir,exist_ok=True)
if flist:
    with open(fname,'r') as f:
        files = f.readlines()
        files = [s.replace('\n','') for s in files]
else:
    files = [fname,]

#%%
#反射強度用カラーマップの作成
clevs_z = np.arange(0,61,5)
cmap_z = plt.get_cmap('pyart_NWSRef').copy()
cmap_z.set_under('white')
norm_z = colors.BoundaryNorm(clevs_z,cmap_z.N,extend='both')

#%%
#ビーム高度がh_tofid kmになる、レーダーからの距離を計算
def find_dis_atalt(h_tofid,anthgt,el,farthest,prec=0.1):
    ##dis: distance from the radar [km] (numpy 1d-array)
    ##anthgt: Anntena height [km] (velue)
    ##el: elevation angle [deg.] (value)
    ##prec: precision of height [km] (value)
    ##farthest: distance from a radar to the farthest gate [km]
    ##Return: Beam altitude [km] (numpy 1d-array)
    er_km = 8493.3121 ##Equivalent Earth radious [km] (~4/3 of the Earth radious)
    elrad = np.deg2rad(el)
    sinel = np.sin(elrad)
    cosel = np.cos(elrad)

    #Compute central beam altitude every prec km.
    dis = np.arange(0,farthest,prec,dtype='float')
    c = dis * cosel / (er_km+dis*sinel)
    c = elrad + np.arctan(c)
    height = dis * np.sin(c) - np.power(dis*np.cos(c),2.0) / (2 * er_km) + anthgt

    #Find distance which have the nearest altitude.
    dis_atalt = []
    ap = dis_atalt.append
    for h in h_tofid:
        diff = np.abs(height-h)
        ap(dis[np.argmin(diff)])

    return dis_atalt
#%%
#描画
for f in files:
    radar = pyart.io.read_nexrad_archive(f)
    display = pyart.graph.RadarDisplay(radar)
    print(f,' is opened')

    antenna_h = radar.altitude['data'][0] / 1000.

    for e in range(len(radar.sweep_number['data'])):
        fig = plt.figure(figsize=(13,5.5))
        ax = fig.add_subplot(121)
        ax.set_aspect(1)
        display.plot('reflectivity',e, cmap=cmap_z, norm=norm_z, colorbar_label='ZH [dBZ]',ax=ax)
        display.set_limits((xmin, xmax), (ymin, ymax), ax=ax)
        if c_dis_or_alt != 'non': display.plot_cross_hair(hair_length,ax=ax)

        ax2 = fig.add_subplot(122)
        ax2.set_aspect(1)
        display.plot('velocity',e,vmin=-24.78,vmax=24.78,colorbar_label='V [m/s]',ax=ax2)
        display.set_limits((xmin, xmax), (ymin, ymax),ax=ax2)
        if c_dis_or_alt != 'non': display.plot_cross_hair(hair_length,ax=ax2)

        #円を描く
        el = radar.fixed_angle['data'][e].round(1)
        if c_dis_or_alt == 'dis':
            draw_crange = circle_range
        elif c_dis_or_alt == 'alt':
            draw_crange = find_dis_atalt(circle_range,antenna_h,el,
                                         radar.range['data'][-1]/1000.)
        
        if c_dis_or_alt == 'dis' or c_dis_or_alt == 'alt':
            for r in draw_crange:
                display.plot_range_ring(r,ax=ax, ls='-', col='k', lw=1)
                display.plot_range_ring(r,ax=ax2, ls='-', col='k', lw=1)
            
            if circle_label:
                for r in range(len(draw_crange)):
                    ax.text(0,draw_crange[r]+hair_length,f'{circle_range[r]:.1f} km',
                            horizontalalignment='center',transform=ax.transData,
                            clip_on=True)
                    ax2.text(0,draw_crange[r]+hair_length,f'{circle_range[r]:.1f} km',
                            horizontalalignment='center',transform=ax2.transData,
                            clip_on=True)
            
        angle = int(el * 10.)
        figname = figdir + '/' + basename(f) + f'_ZV_scnum{e:02d}_el{angle:04d}.jpg'
        plt.savefig(figname,bbox_inches='tight',dpi=200)
        print(f'Fig saved to {figname}')
        plt.close()
        #break

# %%
