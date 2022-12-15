#%%
"""
Draw_NEXRAD_Level2.py ver 1.0 coded by A.NISHII
NEXRAD Level-IIデータ(反射強度とドップラー速度)をPy-ARTを用いて描画する
デフォルトではファイルに入っているスキャン全てを描画する

HISTORY(yyyy.mm.dd)
ver 1.0 First created 2022.12.15 A.NISHII

"""
import pyart
from matplotlib import colors
import matplotlib.pyplot as plt
from os.path import basename
from os import makedirs
import numpy as np
#from sys import argv

#%%
##パラメータ設定

fname = './RODN/RODN20220831_044832_V06' #NEXRAD Level-IIデータを指定
figdir = './rodn_zv' #画像を出力するディレクトリ
xmin = -250 #描画範囲の西端 (レーダを中心とした座標で東が正。kmで指定)
xmax = 250  #東端 (km)
ymin = -250 #南端 (レーダを中心とした座標で北が正。kmで指定)
ymax = 250  #北端 (km)
circle_range = np.arange(50,251,50) #レーダから半径circle_range kmの円を描く(リスト or ndarrayで指定)
hair_length = 25 #レーダ中心を示す十字の長さ(km)

##パラメータ設定ここまで

#%%
print(f'Inputfile: {fname}')
makedirs(figdir,exist_ok=True)

#%%
radar = pyart.io.read_nexrad_archive(fname)
display = pyart.graph.RadarDisplay(radar)

#%%
#反射強度用カラーマップの作製
clevs_z = np.arange(0,61,5)
cmap_z = plt.get_cmap('pyart_NWSRef').copy()
cmap_z.set_under('white')
norm_z = colors.BoundaryNorm(clevs_z,cmap_z.N,extend='both')

# %%
#描画
for e in range(len(radar.sweep_number['data'])):
    fig = plt.figure(figsize=(13,5.5))
    ax = fig.add_subplot(121)
    ax.set_aspect(1)
    display.plot('reflectivity',e, cmap=cmap_z, norm=norm_z, colorbar_label='ZH [dBZ]',ax=ax)
    display.set_limits((xmin, xmax), (ymin, ymax), ax=ax)
    display.plot_cross_hair(hair_length,ax=ax)

    ax2 = fig.add_subplot(122)
    ax2.set_aspect(1)
    display.plot('velocity',e,vmin=-24.78,vmax=24.78,colorbar_label='V [m/s]',ax=ax2)
    display.set_limits((xmin, xmax), (ymin, ymax),ax=ax2)
    display.plot_cross_hair(hair_length,ax=ax2)


    for r in circle_range:
        display.plot_range_ring(r,ax=ax, ls='-', col='k', lw=1)
        display.plot_range_ring(r,ax=ax2, ls='-', col='k', lw=1)

    angle = int(radar.fixed_angle['data'][e].round(1) * 10.)

    figname = figdir + '/' + basename(fname) + f'_ZV_scnum{e:02d}_el{angle:04d}.jpg'
    plt.savefig(figname,bbox_inches='tight',dpi=200)
    print(f'Fig saved to {figname}')
    #break
