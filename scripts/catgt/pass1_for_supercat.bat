:: This is a demo script to do CatGT 'pass 1' runs on two recordings.
:: 
:: The companion script, pass2_for_supercat.bat, runs supercat on these outputs to join them.
::  


@echo off
@setlocal enableextensions
@cd /d "%~dp0"


:: INPUT PARAMS -- EDIT TO MATCH YOUR DATA
::
set dir1=D:\Wenqing\040125\raw\
set dir2=D:\Wenqing\040125\raw\
set run1=MGS3
set run2=FV1
set g=0
set dest=D:\Wenqing\040125\raw\pass1


:: PROCESSING PARAMS -- EDIT TO MATCH YOUR DATA 
:: check probe string (e.g. change to probe=0:1 if you have two probes)
:: if you took your data without probe folders, remove -prb_fld
:: add lffilter if needed
:: if you have no ni, remove the line starting with -ni
:: if you have ni, change edge extractions -- these are just examples
::
set process_params=-t=0,0 ^
-ap -prb=0 ^
-apfilter=butter,12,300,10000 -gblcar -gfix=0.40,0.10,0.02 ^
-out_prb_fld ^
-ni -pass1_force_ni_ob_bin ^
-dest=%dest%


echo Starting CatGT runs
set LOCALARGS=-dir=%dir1% -run=%run1% -g=%g% %process_params%
%~dp0CatGT %LOCALARGS%


set LOCALARGS=-dir=%dir2% -run=%run2% -g=0 %process_params%
%~dp0CatGT %LOCALARGS%


echo Done, see CatGT.log file for details
pause
