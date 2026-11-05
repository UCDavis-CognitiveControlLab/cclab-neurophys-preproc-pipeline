:: Demo script to run run supercat on output from pass1_for_supercat.bat, 
:: pass1 filters data and performs edge extractions
:: edit the supercat elements to match your data. See 'Building The Supercat Command Line' in the ReadMe for help.
:: change streams (add/remove ni, add lf) and probe string to match your data.
:: add any edge extractors (extractors for sync edges are added automatically).
:: If your data does not have any sync signal, remove -supercat_trim_edges.
:: set dest to your desired output directory
::


@echo off
@setlocal enableextensions
@cd /d "%~dp0"


echo Starting CatGT supercat run
set LOCALARGS=-supercat={D:\Wenqing\040125\raw\pass1,catgt_MGS3_g0}{D:\Wenqing\040125\raw\pass1,catgt_FV1_g0} ^
-ap -ni -prb=0 -supercat_trim_edges ^
-dest=D:\Wenqing\040125\raw\pass2


%~dp0CatGT %LOCALARGS%


echo Done, see CatGT.log file for details
pause