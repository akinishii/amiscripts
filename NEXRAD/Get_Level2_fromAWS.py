#%%
"""
Get_Level2_fromAWS.py coded by A.NISHII
Get NEXRAD Level-II data from AWS by using nexradaws
"""
import nexradaws
from datetime import datetime

#%%
site="RODN" #RODN: Kadena air base in Japan
sdate = datetime(2022,8,31,00,0) #(year,month,day,hour,minute)
edate = datetime(2022,8,31,23,59)

#%%
conn = nexradaws.NexradAwsInterface()
files = conn.get_avail_scans_in_range(sdate,edate,site)
# %%
conn.download(files,'.')
