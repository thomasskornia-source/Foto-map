#!/usr/bin/env python3
"""Local-only server and anonymous importer for public iCloud Shared Albums."""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from PIL import ExifTags, Image

ROOT = Path(__file__).resolve().parent
MAX_BODY = 8192
MAX_PHOTOS = 500
MAX_IMAGE = 32 * 1024 * 1024
BASE = "https://ckdatabasews.icloud.com/database/1/com.apple.photos.cloud/production"
UA = "FotoMapLocal/1.0"

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            p = urllib.parse.urlsplit(newurl)
            host = (p.hostname or "").lower()
            if p.scheme != "https" or p.port not in (None, 443) or not (host.endswith(".icloud.com") or host.endswith(".apple.com")):
                return None
        except ValueError:
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)

opener = urllib.request.build_opener(SafeRedirect())

class AlbumError(ValueError):
    pass

def token_from_url(value):
    try:
        p = urllib.parse.urlsplit(value.strip())
    except ValueError:
        raise AlbumError("Der Link ist ungültig.")
    if p.scheme != "https" or (p.hostname or "").lower() not in ("photos.icloud.com", "icloud.com", "www.icloud.com"):
        raise AlbumError("Bitte einen öffentlichen iCloud-Link von photos.icloud.com einfügen.")
    parts = [urllib.parse.unquote(x) for x in p.path.split("/") if x]
    token = parts[2] if len(parts) >= 3 and parts[:2] == ["shared", "album"] else None
    if not token or not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", token):
        raise AlbumError("Der Link enthält keinen unterstützten öffentlichen Album-Schlüssel.")
    return token

def post_json(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type":"application/json", "Accept":"application/json", "User-Agent":UA, "Origin":"https://www.icloud.com"}, method="POST")
    try:
        with opener.open(req, timeout=20) as res:
            data = res.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024: raise AlbumError("Apple hat eine unerwartet große Antwort geliefert.")
            return json.loads(data.decode()), res.headers
    except urllib.error.HTTPError as e:
        raise AlbumError("Apple konnte das Album nicht abrufen. Prüfe die öffentliche Freigabe.")
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError):
        raise AlbumError("Apple ist nicht erreichbar oder hat eine ungültige Antwort geliefert.")

def value(fields, key, default=None):
    item = fields.get(key) if isinstance(fields, dict) else None
    return item.get("value", default) if isinstance(item, dict) else (item if item is not None else default)

def coordinates(fields):
    lat = lng = None
    for key, item in (fields or {}).items():
        v = item.get("value") if isinstance(item, dict) else item
        k = key.lower()
        if k in ("latitude", "lat", "gpslatitude"): lat = v
        if k in ("longitude", "lon", "lng", "gpslongitude"): lng = v
        if k in ("location", "gpslocation") and isinstance(v, dict):
            lat = v.get("latitude", v.get("lat", lat)); lng = v.get("longitude", v.get("lng", lng))
    try:
        lat, lng = float(lat), float(lng)
        return (lat, lng) if -90 <= lat <= 90 and -180 <= lng <= 180 and (lat or lng) else (None, None)
    except (TypeError, ValueError): return None, None

def iso_date(value_):
    try:
        stamp = float(value_); stamp = stamp / 1000 if stamp > 10_000_000_000 else stamp
        return datetime.fromtimestamp(stamp, timezone.utc).isoformat().replace("+00:00", "Z") if stamp > 0 else None
    except (TypeError, ValueError, OSError, OverflowError): return None

def asset_url(fields):
    for key in ("resJPEGFullRes", "resOriginalRes", "resOriginalAltRes"):
        res = value(fields, key)
        if isinstance(res, dict):
            url = res.get("downloadURL")
            try:
                p = urllib.parse.urlsplit(url or "")
                if p.scheme == "https" and p.port in (None, 443) and ((p.hostname or "").endswith(".icloud-content.com") or (p.hostname or "").endswith(".apple.com")): return url
            except ValueError: pass
    return None

def exif(url):
    if not url: return None, None, None
    try:
        with opener.open(urllib.request.Request(url, headers={"User-Agent":UA}), timeout=15) as res: data = res.read(MAX_IMAGE + 1)
        if len(data) > MAX_IMAGE: return None, None, None
        from io import BytesIO
        with Image.open(BytesIO(data)) as im:
            tags = im.getexif(); gps = tags.get_ifd(ExifTags.IFD.GPSInfo); gps = {ExifTags.GPSTAGS.get(k,k):v for k,v in gps.items()}
            def deg(v, ref):
                if not v: return None
                def rat(x): return float(x.numerator)/float(x.denominator) if hasattr(x,"numerator") else float(x[0])/float(x[1])
                n=rat(v[0])+rat(v[1])/60+rat(v[2])/3600
                return -n if str(ref).upper() in ("S","W") else n
            lat, lng = deg(gps.get("GPSLatitude"),gps.get("GPSLatitudeRef")),deg(gps.get("GPSLongitude"),gps.get("GPSLongitudeRef"))
            raw=tags.get(36867) or tags.get(306); taken=None
            if raw:
                try: taken=datetime.strptime(str(raw),"%Y:%m:%d %H:%M:%S").replace(tzinfo=timezone.utc).isoformat().replace("+00:00","Z")
                except ValueError: pass
            return lat,lng,taken
    except (OSError, ValueError, TimeoutError, urllib.error.URLError):
        return None,None,None

def import_album(url):
    token=token_from_url(url)
    resolve=BASE+"/public/records/resolve?"+urllib.parse.urlencode({"remapEnums":"true","getCurrentSyncToken":"true","sharing_url_key":token})
    data,_=post_json(resolve,{"shortGUIDs":[{"value":token,"shouldFetchRootRecord":True}]})
    item=(data.get("results") or [{}])[0]; access=item.get("anonymousPublicAccess") or {}; zone=item.get("zoneID")
    part=access.get("databasePartition"); auth=access.get("token")
    if not isinstance(zone,dict) or not isinstance(part,str) or not isinstance(auth,str): raise AlbumError("Album privat, abgelaufen oder mit Apple nicht kompatibel.")
    p=urllib.parse.urlsplit(part if "://" in part else "https://"+part); host=(p.hostname or "").lower()
    if p.scheme!="https" or not re.fullmatch(r"p\d+-ckdatabasews\.icloud\.com",host): raise AlbumError("Apple lieferte einen nicht unterstützten Albumserver.")
    params={"remapEnums":"true","getCurrentSyncToken":"true","sharing_url_key":token,"publicAccessAuthToken":auth}
    endpoint="https://"+host+"/database/1/com.apple.photos.cloud/production/shared/records/query?"
    records=[]; marker=None; seen=set()
    for _ in range(30):
        body={"zoneID":zone,"query":{"recordType":"CPLAssetAndMasterByAddedDate","filterBy":[{"fieldName":"direction","comparator":"EQUALS","fieldValue":{"value":"ASCENDING","type":"STRING"}}]},"resultsLimit":200}
        if marker: body["continuationMarker"]=marker
        page,headers=post_json(endpoint+urllib.parse.urlencode(params),body); records.extend(page.get("records") or [])
        refreshed=headers.get("X-CloudKit-PublicAccess-AuthToken")
        if refreshed: params["publicAccessAuthToken"]=refreshed
        marker=page.get("continuationMarker")
        if not marker: break
        if not isinstance(marker,str) or marker in seen: raise AlbumError("Apple lieferte eine fehlerhafte Albumseite.")
        seen.add(marker)
    else: raise AlbumError("Das Album ist für einen einzelnen Import zu groß.")
    masters={}; assets=[]
    for rec in records:
        fields=rec.get("fields") or {}
        if rec.get("recordType")=="CPLMaster": masters[rec.get("recordName")]=fields
        elif rec.get("recordType")=="CPLAsset":
            ref=value(fields,"masterRef") or {}; assets.append((rec,fields,ref.get("recordName") if isinstance(ref,dict) else None))
    photos=[]
    for i,(rec,fields,master_id) in enumerate(assets[:MAX_PHOTOS]):
        master=masters.get(master_id,{})
        image=asset_url(master) or asset_url(fields)
        if not image: continue
        lat,lng=coordinates(fields)
        if lat is None: lat,lng=coordinates(master)
        captured=iso_date(value(fields,"assetDate"))
        if lat is None or not captured:
            exlat,exlng,exdate=exif(image)
            if lat is None: lat,lng=exlat,exlng
            captured=captured or exdate
        photos.append({"id":rec.get("recordName",str(i)),"title":"Foto {}".format(i+1),"lat":lat,"lng":lng,"capturedAt":captured,"image":image})
    root=item.get("rootRecord") or {}; fields=root.get("fields") or {}; title=value(fields,"title") or value(fields,"name") or "iCloud Fotoalbum"
    if not photos: raise AlbumError("Apple lieferte keine abrufbaren Fotos für dieses Album.")
    return {"title":title,"photos":photos,"truncated":len(assets)>MAX_PHOTOS}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): print("{} - {}".format(self.address_string(),fmt%args))
    def send_json(self,status,data):
        body=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.path not in ("/","/index.html"): return self.send_json(404,{"error":"Nicht gefunden."})
        try: body=(ROOT/"Index.html").read_bytes()
        except OSError: return self.send_json(500,{"error":"Webseite konnte nicht gelesen werden."})
        self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def do_POST(self):
        if self.path!="/api/import": return self.send_json(404,{"error":"Nicht gefunden."})
        try: length=int(self.headers.get("Content-Length","0"))
        except ValueError: length=0
        if not 1<=length<=MAX_BODY: return self.send_json(413,{"error":"Ungültige Anfrage."})
        try:
            req=json.loads(self.rfile.read(length).decode());url=req.get("url","") if isinstance(req,dict) else ""
            if not isinstance(url,str): raise AlbumError("Bitte einen gültigen Albumlink einfügen.")
            return self.send_json(200,import_album(url))
        except AlbumError as e: return self.send_json(400,{"error":str(e)})
        except (UnicodeDecodeError,json.JSONDecodeError,AttributeError): return self.send_json(400,{"error":"Die Anfrage enthält keine gültigen Albumdaten."})

def main():
    port=int(sys.argv[1]) if len(sys.argv)>1 else 8765
    if not 1024<=port<=65535: raise SystemExit("Port muss zwischen 1024 und 65535 liegen.")
    server=ThreadingHTTPServer(("127.0.0.1",port),Handler);print("Foto Map: http://127.0.0.1:{}/".format(port))
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
if __name__=="__main__": main()
