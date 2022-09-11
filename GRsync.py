#!/usr/bin/env python -u
# -*- coding: utf-8 -*-

try:
  import urllib.request as urllib2
except:
  import urllib2

import sys
import json
import argparse
from argparse import RawTextHelpFormatter
import socket
import re
import os

# remember the ending "/"
# eg: PHOTO_DEST_DIR = "/home/user/photos/"
PHOTO_DEST_DIR = ""

# GR_HOST is FIXED. DO NOT CHANGE!!
GR_HOST = "http://192.168.0.1/"
PHOTO_LIST_URI = "v1/photos"
GR_PROPS = "v1/props"
STARTDIR = ""
STARTFILE = ""
SUPPORT_DEVICE = ['RICOH GR II', 'RICOH GR III', 'RICOH GR IIIx']
DEVICE = "RICOH GR IIIx"

def getDeviceModel():
    req = urllib2.Request(GR_HOST + GR_PROPS)
    try:
        resp = urllib2.urlopen(req)
        data = resp.read()
        props = json.loads(data)
        if props['errCode'] != 200:
            print("Error code: %d, Error message: %s" % (photoDict['errCode'], photoDict['errMsg']))
            sys.exit(1)
        else:
            return props['model']
    except Exception as e:
        print("Unable to fetch device props from device")
        sys.exit(1)

def getBatteryLevel():
    req = urllib2.Request(GR_HOST + GR_PROPS)
    try:
        resp = urllib2.urlopen(req)
        data = resp.read()
        props = json.loads(data)
        if props['errCode'] != 200:
            print("Error code: %d, Error message: %s" % (photoDict['errCode'], photoDict['errMsg']))
            sys.exit(1)
        else:
            return props['battery']
    except Exception as e:
        print("Unable to fetch device props from %s" % DEVICE)
        sys.exit(1)

def getPhotoList():
    req = urllib2.Request(GR_HOST + PHOTO_LIST_URI)
    try:
        resp = urllib2.urlopen(req)
        data = resp.read()
        photoDict = json.loads(data)
        if photoDict['errCode'] != 200:
            print("Error code: %d, Error message: %s" % (photoDict['errCode'], photoDict['errMsg']))
            sys.exit(1)
        else:
            photoList = []
            for dic in photoDict['dirs']:
                # check if this directory already exist in local PHOTO_DEST_DIR
                # if not, create one
                if not os.path.isdir(PHOTO_DEST_DIR+dic['name']):
                    os.makedirs(PHOTO_DEST_DIR+dic['name'])
                
                # generate the full photo list
                for file in dic['files']:
                    photoList.append("%s/%s" % (dic['name'], file ))
            return photoList
    except Exception as e:
        print("Unable to fetch photo list from %s" % DEVICE)
        sys.exit(1)
    
def getLocalFiles():
    fileList = []
    for (dir, _, files) in os.walk(PHOTO_DEST_DIR):
        for f in files:
            fileList.append(os.path.join(dir, f).replace(PHOTO_DEST_DIR, ""))
            
    return fileList

def fetchPhoto(photouri):
    try:
        if 'GR2' in DEVICE.upper():
            f = urllib2.urlopen(GR_HOST+photouri)
        else: 
            f = urllib2.urlopen(GR_HOST+PHOTO_LIST_URI+'/'+photouri)
        with open(PHOTO_DEST_DIR+photouri, "wb") as localfile:
            localfile.write(f.read())
        return True
    except Exception as e:
        return False

def shutdownGR():
    req = urllib2.Request("http://192.168.0.1/v1/device/finish")
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, b"{}")

def downloadPhotos(isAll, jpeg_only=False, raw_only=False, download_last_n_pictures=None):
    print("Fetching photo list from %s ..." % DEVICE)
    photoLists = getPhotoList()
    localFiles = getLocalFiles()
    count = 0
    if (isAll == True) or download_last_n_pictures or jpeg_only or raw_only:
        totalPhoto = len(photoLists)
    else:
        starturi = "%s/%s" % (STARTDIR, STARTFILE)
        if starturi not in photoLists:
            print("Unable to find %s in Ricoh %s" % (starturi, DEVICE))
            sys.exit(1)
        else:
            while True:
                if photoLists[0] != starturi:
                    photoLists.pop(0)
                else:
                    totalPhoto = len(photoLists)
                    break
                    
    print("Start to download photos ..."    )
    if download_last_n_pictures:
        if (jpeg_only and raw_only) or (isAll) or (not jpeg_only and not raw_only):
                totalPhoto = download_last_n_pictures * 2
        else:
            totalPhoto = download_last_n_pictures
    
    elif (jpeg_only and not raw_only) or (not jpeg_only and raw_only):
        totalPhoto = totalPhoto / 2

    while True:
        if not photoLists:
            print("\nAll photos are downloaded.")
            shutdownGR()
            break
        else:
            photouri = photoLists.pop(0)
            count += 1
            if photouri in localFiles:
                print("(%d/%d) Skip %s, already have it on local drive!!" % (count, totalPhoto, photouri))
            else:
                should_download = not(jpeg_only or raw_only) or (jpeg_only and photouri.upper().endswith(".JPG")) or (raw_only and photouri.upper().endswith(".DNG"))
                if not should_download:
                    continue
                print("(%d/%d) Downloading %s now ... " % ((count / 2 if (jpeg_only or raw_only) else count), totalPhoto, photouri),)
                if fetchPhoto(photouri) == True:
                    print("done!!")
                else:
                    print("*** FAILED ***")

            if download_last_n_pictures:
                if download_last_n_pictures > 0:
                    download_last_n_pictures = download_last_n_pictures - 1
                    #print("Photo left to download: %s" % str(download_last_n_pictures))
                else:
                    #print("Downloaded photo(s): %s" % str(count))
                    break
    
if __name__ == "__main__":
    # set connection timeout to 2 seconds
    socket.setdefaulttimeout(2)
    
    # setting up argument parser
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description='''
GRsync is a handy Python script, which allows you to sync photos from Ricoh GR
II or III via Wifi. It has been tested on Mac OS X and Ubuntu. It should be able to
run on any platform that has a Python environment.

It automatically checks if photos already exists in your local drive. Duplicated
photos will be skipped and only sync needed photos for you.

Simple usage - Download ALL photos from Ricoh GR II or III:

    ./GRsync -a

Advanced usage - Download photos after specific directory and file:

    ./GRsync -d 100RICOH -f R0000005.JPG
    
    All photos after 100RICOH/R0000005.JPG will be downloaded, including all
    following directories (eg. 101RICOH, 102RICOH)

''')
    parser.add_argument("-a", "--all", action="store_true", help="Download all photos")
    parser.add_argument("-d", "--dir", help="Assign directory (eg. -d 100RICOH). MUST use with -f")
    parser.add_argument("-f", "--file", help="Start to download photos from specific file \n(eg. -f R0000005.JPG). MUST use with -d")
    parser.add_argument("-j", "--jpg", action="store_true", help="Download jpg files only")
    parser.add_argument("-r", "--raw", action="store_true", help="Download raw files only")
    parser.add_argument("-l", "--last",dest="last", default=0, type=int, help="Download last N pictures from the end")


    
    download_last_n_pictures = None
    if parser.parse_args().last:
        try:
            download_last_n_pictures = int(parser.parse_args().last)
            print("Only downloading last %s picture(s)" % str(download_last_n_pictures))
        except:
            pass

    model = getDeviceModel()

    if model not in SUPPORT_DEVICE:
        print("Your source device '%s' is unknown or not supported!" % model)
        sys.exit(1)
    else:
        DEVICE = model

    if getBatteryLevel() < 15:
        print("Your battery level is less than 15%, please charge it before sync operation!")
        sys.exit(1)
    
    isAll = (parser.parse_args().all == True)
    jpeg_only = (parser.parse_args().jpg == True)
    raw_only = (parser.parse_args().raw == True)

    if not ((parser.parse_args().dir is None)):
        match = re.match(r"^[1-9]\d\dRICOH$", parser.parse_args().dir)
        if match:
            STARTDIR = parser.parse_args().dir
        else:
            print("Incorrect directory name. It should be something like 100RICOH")
            sys.exit(1)
    else:
        STARTDIR = "100RICOH"

    if not (parser.parse_args().file is None):
        match = re.match(r"^R0\d{6}\.JPG$", parser.parse_args().file)
        if not match:
            match = re.match(r"^R0\d{6}\.RAW$", parser.parse_args().file)
        if match:
            STARTFILE = parser.parse_args().file
        else :
            print("Incorrect file name. It should be something like R0999999.JPG. (all in CAPITAL)")
            sys.exit(1)

    if not (isAll or jpeg_only or raw_only):
        parser.print_help()
        sys.exit(1)

    downloadPhotos(isAll=isAll, jpeg_only=jpeg_only, raw_only=raw_only, download_last_n_pictures=download_last_n_pictures)
