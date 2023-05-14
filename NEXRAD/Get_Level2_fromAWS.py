#%%
"""
Get_Level2_fromAWS.py coded by A.NISHII 2023.05.14
Get NEXRAD Level-II data from AWS by using nexradaws
Data is downloaded in the current directory.

Useage 1:
python3 Get_Level2_fromAWS.py
*site, sdate, and edate variables in this script must be specified.

Useage 2:
python3 Get_Level2_fromAWS.py yyyymmddHHMM yyyymmddHHMM
                             (start DL time) (end DL time) *UTC
*site variable must be specified.
                             
Useage 3:
python3 Get_Level2_fromAWS.py yyyymmddHHMM yyyymmddHHMM SITE
"""

from sys import argv,exit
import nexradaws
from datetime import datetime

#%%
site="RODN" #RODN: Kadena air base in Japan
sdate = datetime(2022,8,31,00,00) #(year,month,day,hour,minute) in UTC
edate = datetime(2022,8,31,00,10)

#%%
#Check site and date settings
if len(argv) == 3 or len(argv) ==4:
    sdstr = argv[1]
    sdate = datetime(int(sdstr[0:4]),int(sdstr[4:6]),int(sdstr[6:8]),int(sdstr[8:10]),int(sdstr[10:12]))
    edstr = argv[2]
    edate = datetime(int(edstr[0:4]),int(edstr[4:6]),int(edstr[6:8]),int(edstr[8:10]),int(edstr[10:12]))
elif len(argv) != 1:
    print('Invalid number of argments!')
    exit(-1)

if len(argv) == 4: site = argv[3]

#%%
#Download data from AWS
print('Data from {0} to {1}Z will be donwloaded'.format(
      sdate.strftime('%y-%m-%d %H:%M'),edate.strftime('%y-%m-%d %H:%M')))
conn = nexradaws.NexradAwsInterface()
files = conn.get_avail_scans_in_range(sdate,edate,site)
conn.download(files,'.')
print('Finish')
