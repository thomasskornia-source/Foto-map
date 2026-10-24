# Foto Map

Interaktive Reisekarte aus einem öffentlichen iCloud-Fotoalbum oder lokal ausgewählten Fotos. Zeigt GPS-Route, Foto-Zeitleiste, geschätzte Aufenthalte und nahe Wikipedia-Ortsinfos.

## Lokal starten

Python 3.9 oder neuer:

```sh
python3 -m pip install -r requirements.txt
python3 server.py
```

Öffne `http://127.0.0.1:8765`. Beenden mit Ctrl+C. Der Server lauscht nur auf localhost.

## Hinweise

- Unterstütztes iCloud-Format: `https://photos.icloud.com/shared/album/<Schlüssel>` mit aktivierter öffentlicher Freigabe. Apples anonyme CloudKit-Schnittstelle ist nicht offiziell dokumentiert und kann sich ändern. Ältere `sharedalbum`-Links werden derzeit nicht unterstützt.
- Der Server speichert weder Fotos noch Album-Schlüssel. Albumlinks in „Meine Alben“ liegen im Browser-localStorage. Kurzlebige Bildlinks können ablaufen; importiere dann erneut.
- Lokale Fotos werden im Browser analysiert und nicht hochgeladen. Wikipedia erhält die erkannten Ortskoordinaten für die Umkreissuche.
- Aufenthaltszeiten sind nur die Fotospanne zwischen Aufnahmen in einer Nähe, keine exakten Ankunfts- oder Abfahrtszeiten. Bilder ohne GPS erscheinen in Galerie und Zeitleiste, aber nicht auf der Karte.
- Karten und Bibliotheken werden über OpenStreetMap/CARTO und öffentliche CDNs geladen.

## Tests

```sh
python3 -m unittest
```
