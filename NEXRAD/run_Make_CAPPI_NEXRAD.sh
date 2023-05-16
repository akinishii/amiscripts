#!/bin/bash
#ディレクトリ内のNEXRADファイルからCAPPIデータを作る処理を一括で実施する
#注意：実行前にMake_CAPPI_NEXRAD.pyの設定を確認すること
#(flistはTrueになっているか、ppi_useは適切か、等)

datadir="RODN/20220831"

ls ${datadir}/*_V06 > flist
python3 Make_CAPPI_NEXRAD.py flist
rm flist
