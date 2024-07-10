#%%
"""
Make_CAPPI_NEXRAD.py ver 1.0 coded by A.NISHII
NEXRAD Level-IIデータからPyartを用いてCAPPIを作成する
偏波パラメータ(Kdp、Zdr、ρhv)の出力にも対応
*偏波間位相差変化率(Kdp)は偏波間位相差(psidp)から算出したものを使用 (kdp_vulpianiを使用)
*緯度経度座標系への投影はレーダーを中心とした正距方位図法を使用
*反射強度0 dBZ未満のグリッドは内挿に用いない点に注意

HISTORY(yyyy.mm.dd)
ver 1.0 First created 2023.05.15 A.NISHII
ver 1.1 Bug fixed (fill_valueの設定ミス) ドップラー速度出力をフラグ化 2024.07.09 A.NISHII
ver 1.2 Bug fixed (gatefilter設定ミス) 2024.07.10 A.NISHII
"""

import numpy as np
import pyart
from os.path import basename
import datetime
import locale
from os import makedirs
from sys import argv
import netCDF4

#%%
##パラメータ設定
#fname = '../data/RODN/RODN20220831_032654_V06'
fname = argv[1] #入力ファイル(NEXRAD Level-IIデータorLevel-IIデータのファイルリストを指定)
flist = False #Ture:fnameはNEXRADレベル2のファイルリスト(1行1ファイル。相対パスでも絶対パスでも可)、False:fnameはNEXRAD LEVEL2ファイルのパス
ppi_use = (0, 2, 4, 6, 7, 8, 9, 10, 11, 12, 13) #CAPPIに使用するPPI仰角番号

outdir = './out_cappi_ver20240709'     #出力ディレクトリ
flag_nc = True             #True:NetCDFファイルを出力(推奨。GrADSで読みだすにはctlファイルが必要)
flag_gradsbin = True       #True:grads 4byteバイナリとctlファイルを出力

#各方向の解像度は(limit[1]-limit[0])/(grid_shape-1) [m]となる
grid_shape = (21,601,601)  #(z方向Grid数,南北方向Grid数,東西方向Grid数)
limit_z = (0,20000)        #CAPPI作成高度(m)
limit_y = (-300000,300000) #南北方向のCAPPI作成範囲(m)
limit_x = (-300000,300000) #東西方向のCAPPI作成範囲(m)

interp_method = 'Cressman' #内挿方法(Cressman, Barnes2推奨、他にBarnes, Nearestが選択可)
roi_const = 2000.          #内挿の影響円半径(meter,このスクリプトでは半径を固定させて内挿を実施する)

flag_v     = False        #True:ドップラー速度も出力
flag_dupol = False        #True:偏波パラメータ(Zdr,Kdp,ρhv)も出力
zdrbias    = None         #Zdrバイアス(未知の場合はNoneと入力)

##パラメータ設定ここまで
#%%
#extract_4bytes(GrADSデータの作成とctlファイル向け移動経度情報の計算)
def extract_4bytes(grid, latlon, varname):
    #latlon = grid.get_point_longitude_latitude()
    lons = latlon[0]
    lats = latlon[1]
    slon = lons[int(len(lons)/2),0]
    slat = lats[0, int(len(lats)/2)]
    dlon = abs(lons[int(len(lons)/2),-1] - slon) / (len(lons[0]) - 1.)
    dlat = abs(lats[-1, int(len(lats)/2)] - slat) / (len(lats[0]) - 1.)

    data = grid.fields[varname]['data'].filled(-9999.).astype('float32')

    return data, slon, dlon, slat, dlat


# %%
#define_time_fromNEXRAD: NEXRAD Level-IIデータから時刻情報を抽出
def define_time_fromNEXRAD(fname):

    fname_base = basename(fname)
    fname_split = fname_base.split('_')
    date = fname_split[0][4:]
    time = fname_split[1]

    time_dt = datetime.datetime.strptime(date+time,'%Y%m%d%H%M%S')

    return time_dt

#%%
#Make_GradsCtl: GrADSコントロールファイルを作成
def Make_GradsCtl(ctlfname, binfname, undef, xnum, slon, dlon, ynum, slat, dlat, znum, sz, dz, date_str, vars):
    with open(ctlfname,'w') as f:
        f.write(f'dset ^{binfname}\n')
        f.write('title\n')
        f.write('options little_endian\n')
        f.write(f'undef {undef}\n')
        f.write(f'xdef {xnum} linear {slon:.6f} {dlon:.6f}\n')
        f.write(f'ydef {ynum} linear {slat:.6f} {dlat:.6f}\n')
        f.write(f'zdef {znum} linear {sz} {dz:.3f}\n')
        f.write(f'tdef 1 linear ' + date_str + ' 5mn\n')
        f.write(f'vars {len(vars)}\n')
        for n in range(len(vars)):
            f.write(f'{vars[n]} {znum} 0 {vars[n]}\n')
        f.write('endvars\n')
        f.write('\n')

#%%
#save_ncvariable: netCDFに変数情報を保存する
def save_ncvariable(nc,var,undef,vname,vname_long,vunits,vdtype,vdim,comment=None):
    ncvar = nc.createVariable(vname,vdtype,vdim)
    ncvar.long_name = vname_long
    ncvar.standatd_name = vname_long
    ncvar.units = vunits
    if undef != None: ncvar.missing_value = undef
    ncvar[:] = var
    if comment is not None: ncvar.comment = comment

#out_nc: netCDFファイルに解析結果を出力する
def out_nc(ncname,undef,xnum,sx,dx,lons,ynum,sy,dy,lats,znum,sz,dz,
           date_str,vars,varnames,meta,origfname,ppi_use,interp_method,roi_const):
    nc = netCDF4.Dataset(ncname,'w',format='NETCDF3_CLASSIC')
    nc.createDimension('time',1)
    nc.createDimension('z',znum)
    nc.createDimension('y',ynum)
    nc.createDimension('x',xnum)
    time = np.array([0],dtype=np.float32)
    z = sz   + np.arange(znum) * dz
    y = sy   + np.arange(ynum) * dy
    x = sx   + np.arange(xnum) * dx
    time_unit = 'seconds since ' + date_str
    save_ncvariable(nc,time,None,'time','time',time_unit,np.dtype('float32').char,('time',))

    save_ncvariable(nc,z,None,'z','height_above_sea_level','m',np.dtype('float32').char,('z',))
    save_ncvariable(nc,y,None,'y','y coord from radar','m',np.dtype('float32').char,('y',))
    save_ncvariable(nc,x,None,'x','x coord from radar','m',np.dtype('float32').char,('x',))

    save_ncvariable(nc,lats,None,'lat','latitude','degrees_north',np.dtype('float32').char,('y','x'),
                    "Projection: Azimuthal equidistant centered at radar")
    save_ncvariable(nc,lons,None,'lon','longitude','degrees_east',np.dtype('float32').char,('y','x'),
                    "Projection: Azimuthal equidistant centered at radar")

    for v in range(len(varnames)):
        save_ncvariable(nc,vars[v],undef,varnames[v],meta[v][0],meta[v][1],np.dtype('float32').char,('time','z','y','x'))

    nc.title    = 'CAPPI created from NEXRAD Level-II PPIs using Py-ART'
    nc.history  = 'Created by Make_CAPPI_NEXRAD.py ver 1.1 (author: A.NISHII)'
    nc.source   = f'{origfname} Used scum numbers: ({" ".join([str(p) for p in ppi_use])})'
    nc.comment  = f'PPIs are interpolated using {interp_method} method with {roi_const:.0f} m radius'

    nc.close()

#%%
if flag_nc:  makedirs(outdir+'/nc/', exist_ok=True)
if flag_gradsbin: makedirs(outdir+'/bin/', exist_ok=True)
print('Input file: '+fname)
if flist:
    with open(fname,'r') as f:
        files = f.readlines()
        files = [s.replace('\n','') for s in files]
else:
    files = [fname,]

#%%
for f in files:
    #データ読み出し
    radar = pyart.io.read_nexrad_archive(f)
    print(f,' is opened')
    radar_4ppi = radar.extract_sweeps(ppi_use)

    if flag_dupol:
        kdp,pdp = pyart.retrieve.kdp_vulpiani(radar=radar_4ppi,psidp_field='differential_phase',
                                              band='S',prefilter_psidp=True)
        radar_4ppi.add_field('specific_differential_phase',kdp)
        print('Kdp retrieved')
        if zdrbias != None:
            radar.fields['differential_reflectivity']['data'] -= zdrbias
            print('Zdr bias corrected')

    #Set filter
    gatefilter = pyart.filters.GateFilter(radar_4ppi)
    gatefilter.exclude_below('reflectivity',0) #反射強度0 dBZ未満のデータはマスクする

    #CAPPI作成
    grid = pyart.map.grid_from_radars(radar_4ppi,grid_shape=grid_shape,grid_limits=(limit_z,limit_y,limit_x), weighting_function='Cressman',
                                    roi_func='constant', constant_roi = roi_const, gatefilters=gatefilter)
    latlon = grid.get_point_longitude_latitude()
    display = pyart.graph.GridMapDisplay(grid)

    #保存のために4-byteバイナリデータを抽出
    #Reflevtivity (デフォルト)
    df = []
    vnames = ['ref']
    df_z, slon, dlon, slat, dlat = extract_4bytes(grid,latlon,'reflectivity')
    df.append(df_z)

    #ドップラー速度(flag_vがTrueの場合)
    if flag_v:
        df_v, _, _, _, _ = extract_4bytes(grid,latlon,'velocity')
        df.append(df_v)
        vnames.append('vel')

    #偏波パラメータ(flag_dupolがTrueの場合)
    if flag_dupol:
        df_zdr, _, _, _, _ = extract_4bytes(grid,latlon,'differential_reflectivity')
        df_kdp, _, _, _, _ = extract_4bytes(grid,latlon,'specific_differential_phase')
        df_rhv, _, _, _, _ = extract_4bytes(grid,latlon,'cross_correlation_ratio')
        df.append(df_zdr)
        df.append(df_kdp)
        df.append(df_rhv)
        vnames.append('zdr')
        vnames.append('kdp')
        vnames.append('rhv')

    df = np.array(df,dtype='float32')
    date_dt  = define_time_fromNEXRAD(f)

    #GrADSバイナリ形式で保存
    if flag_gradsbin:
        locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')
        date_str = date_dt.strftime("%H:%MZ%d%b%Y")
        ctlfname = basename(f) + '_3D_xy.ctl'
        ctlfname_ll = basename(f) + '_3D_latlon.ctl'
        binfname = basename(f) + '_3D.bin'
        Make_GradsCtl(outdir + '/bin/' + ctlfname, binfname, -9999., df_z.shape[2], -300, 1.0, df_z.shape[1], -300, 1.0, 
                    df_z.shape[0], limit_z[0], (limit_z[1]-limit_z[0])/(grid_shape[0]-1)/1000., date_str, vnames)
        Make_GradsCtl(outdir + '/bin/' + ctlfname_ll, binfname, -9999., df_z.shape[2], slon, dlon, df_z.shape[1], slat, dlat, 
                    df_z.shape[0], limit_z[0], (limit_z[1]-limit_z[0])/(grid_shape[0]-1)/1000., date_str, vnames)
        df.tofile(outdir + '/bin/' + binfname,format='<f4')
        print('CAPPI (GrADS binary) saved to ' + outdir + '/bin/' + binfname)

    #netCDF形式で保存
    if flag_nc:
        #メタデータの抽出(list([standard_name,units] for _ in range(len(vnames))))
        meta = []
        meta.append([grid.fields['reflectivity']['long_name'],grid.fields['reflectivity']['units']])
        if flag_v:
            meta.append([grid.fields['velocity']['long_name'],grid.fields['velocity']['units']]) 
        if flag_dupol:
            meta.append([grid.fields['differential_reflectivity']['long_name'],grid.fields['differential_reflectivity']['units']]) 
            meta.append([grid.fields['specific_differential_phase']['long_name'],grid.fields['specific_differential_phase']['units']]) 
            meta.append([grid.fields['cross_correlation_ratio']['long_name'],grid.fields['cross_correlation_ratio']['units']]) 
        datestr_nc = date_dt.strftime('%Y-%m-%d %H:%M:%S+00:00')
        ncname = basename(f) +'_3D.nc'
        ncdir = outdir+'/nc/'
        out_nc(ncdir+ncname,-9999.,
            df_z.shape[2], limit_x[0],(limit_x[1]-limit_x[0])/(grid_shape[2]-1),latlon[0], 
            df_z.shape[1], limit_y[0],(limit_y[1]-limit_y[0])/(grid_shape[1]-1),latlon[1],
            df_z.shape[0], limit_z[0],(limit_z[1]-limit_z[0])/(grid_shape[0]-1),
            datestr_nc,df,vnames,meta,basename(f),ppi_use,interp_method,roi_const)
        print('CAPPI (nc) saved to ' + ncdir + ncname)
