#!/bin/bash

sdate="202305221500" #yyyymmddHHMM (UTC)
edate="202305221510"
sitename="PGUA"
outdir="./PGUA/"

mkdir -p ${outdir}

python3 Get_Level2_fromAWS.py ${sdate} ${edate} ${sitename}
mv *_V06 ${outdir}

ls ${outdir}/*_V06 > flist
python3 Draw_NEXRAD_Level2.py flist
rm flist
