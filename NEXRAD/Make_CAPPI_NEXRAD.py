#%%
"""
Make_CAPPI_NEXRAD.py ver 1.0 coded by A.NISHII
NEXRAD Level-IIデータからPyartを用いてCAPPIを作成する
偏波パラメータ(Kdp、Zdr、ρhv)の出力にも対応
*偏波間位相差変化率(Kdp)は偏波間位相差(psidp)から算出したものを使用
*緯度経度座標系への投影はレーダーを中心とした正距方位図法を使用
*反射強度0 dBZ未満のグリッドは内挿に用いない点に注意

HISTORY(yyyy.mm.dd)
ver 1.0 First created 2023.05.15 A.NISHII
"""

import numpy as np
import pyart
from os.path import basename
import datetime
import locale
from os import makedirs
from sys import argv

#%%
##パラメータ設定
#fname = './RODN/maysak/RODN20200831_180549_V06'
fname = argv[1] #入力ファイル(NEXRAD Level-IIデータorLevel-IIデータのファイルリストを指定)
flist = True #Ture:fnameはファイルリスト、False:fnameはNEXRAD LEVEL2ファイル
ppi_use = (0, 2, 4, 6, 7, 8, 9, 10, 11, 12, 13) #CAPPIに使用するPPI仰角番号

outdir = './out_cappi'     #出力ディレクトリ
flag_nc = True             #True:NetCDFファイルを出力(推奨。GrADSで読みだすにはctlファイルが必要)
flag_gradsbin = True       #True:grads 4byteバイナリとctlファイルを出力

#各方向の解像度は(limit[1]-limit[0])/(grid_shape-1) [m]となる
grid_shape = (21,601,601)  #(z方向Grid数,南北方向Grid数,東西方向Grid数)
limit_z = (0,20000)        #CAPPI作成高度(m)
limit_y = (-300000,300000) #南北方向のCAPPI作成範囲(m)
limit_x = (-300000,300000) #東西方向のCAPPI作成範囲(m)

interp_method = 'Cressman' #内挿方法(Cressman, Barnes2推奨、他にBarnes, Nearestが選択可)
roi_const = 2000.          #内挿の影響円半径(meter,このスクリプトでは半径を固定させて内挿を実施する)

flag_dupol = True          #True:偏波パラメータ(Zdr,Kdp,ρhv)を出力、False:ZhとVのみ出力
zdrbias = None             #Zdrバイアス(未知の場合はNoneと入力)

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

    data = grid.fields[varname]['data'].__array__()
    data_nonan = np.nan_to_num(data,nan=-9999.).astype('float32')
    return data_nonan, slon, dlon, slat, dlat


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
def save_ncvariable(nc,var,undef,vname,vname_long,vunits,vdtype,vdim):
    ncvar = nc.createVariable(vname,vdtype,vdim)
    ncvar.long_name = vname_long
    ncvar.standatd_name = vname_long
    ncvar.units = vunits
    if undef != None: ncvar.missing_value = undef
    ncvar[:] = var

#out_nc: netCDFファイルに解析結果を出力する
def out_nc(ncname,undef,xnum,sx,dx,lons,ynum,sy,dy,lats,znum,sz,dz,
           date_str,vars,varnames,meta):
    import netCDF4
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

    save_ncvariable(nc,lats,None,'lat','latitude','degrees_north',np.dtype('float32').char,('y','x'))
    save_ncvariable(nc,lons,None,'lon','longitude','degrees_east',np.dtype('float32').char,('y','x'))

    for v in range(len(varnames)):
        save_ncvariable(nc,vars[v],undef,varnames[v],meta[v][0],meta[v][1],np.dtype('float32').char,('time','z','y','x'))

    nc.title ='CAPPI created from NEXRAD PPIs'
    nc.history = 'Created by Make_CAPPI_NEXRAD.py'

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
                                    roi_func='constant', constant_roi = roi_const, gatefilter=gatefilter)
    latlon = grid.get_point_longitude_latitude()
    display = pyart.graph.GridMapDisplay(grid)

    #Save data to 4-byte binary
    df_z, slon, dlon, slat, dlat = extract_4bytes(grid,latlon,'reflectivity')
    df_v, _, _, _, _ = extract_4bytes(grid,latlon,'velocity')
    if flag_dupol:
        df_zdr, _, _, _, _ = extract_4bytes(grid,latlon,'differential_reflectivity')
        df_kdp, _, _, _, _ = extract_4bytes(grid,latlon,'specific_differential_phase')
        df_rhv, _, _, _, _ = extract_4bytes(grid,latlon,'cross_correlation_ratio')
        df = np.array([df_z,df_v,df_zdr,df_kdp,df_rhv],dtype='float32')
        vnames = ['ref','vel','zdr','kdp','rhv']
        
    else:
        df = np.array([df_z,df_v],dtype='float32')
        vnames = ['ref','vel']
    date_dt  = define_time_fromNEXRAD(f)

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
        print('CAPPI (GrADS binary) saved to ' + outdir + '/' + binfname)

    #netCDF形式で保存
    if flag_nc:
        #メタデータの抽出(list([standard_name,units] for _ in range(len(vnames))))
        meta = []
        meta.append([grid.fields['reflectivity']['long_name'],grid.fields['reflectivity']['units']]) 
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
            datestr_nc,df,vnames,meta)
        print('CAPPI (nc) saved to ' + ncdir + '/' + ncname)

