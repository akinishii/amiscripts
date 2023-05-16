#%%
"""
Get_ELinfo_NEXRAD.py ver 1.0 coded by A.NISHII
NEXRAD Level-IIデータからPyartを用いて仰角情報を取得し標準出力に出力する。
savetxt(23行目)をTrueにした場合テキストに仰角情報を保存する。

Useage
python3 Get_ELinfo_NEXRAD.py path/to/level-ii

HISTORY(yyyy.mm.dd)
ver 1.0 First created 2023.05.16 A.NISHII
"""

import pyart
from sys import argv
from os import makedirs
from os.path import basename

#%%
##Parameters

#fname = './RODN/maysak/RODN20200831_180549_V06'
fname = argv[1]
radar = pyart.io.read_nexrad_archive(fname)
savetxt = True #True:Save elevation info to txt file
txtdir = './elinfo'

##End of params

#%%
#Read Elevation info from data
print(f'Input file: {fname}')
els = radar.fixed_angle['data']
print('scnum el[deg.]')
for e in range(len(els)):
    print(f'{e:02d} {els[e]:4.01f}')

# %%
#Save Elevations to a txt file if savetxt is true.
if savetxt:
    makedirs(txtdir,exist_ok=True)
    txtname = txtdir + '/elinfo_' + basename(fname) + '.txt'
    with open(txtname,'w') as fp:
        fp.write('scnum el[deg.]\n')
        for e in range(len(els)):
            fp.write(f'{e:02d} {els[e]:4.01f}\n')
    print('Elevation info saved to '+txtname)
