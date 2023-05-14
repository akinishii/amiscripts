#!/bin/bash

sdate="202208310000"
edate="202208310005"
outdir="./RODN/20220831"

mkdir -p ${outdir}

python3 Get_Level2_fromAWS.py
mv *_V06 ${outdir}

ls ${outdir}/*_V06 > flist
python3 Draw_NEXRAD_Level2.py flist
rm flist
