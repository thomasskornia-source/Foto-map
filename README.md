# Foto Map

Interaktive Reisekarte aus einem öffentlichen iCloud-Fotoalbum oder lokal ausgewählten Fotos. Zeigt GPS-Route, Foto-Zeitleiste, geschätzte Aufenthalte und nahe Wikipedia-Ortsinfos.

## Lokal starten

Python 3.9 oder neuer:

```sh
python3 -m pip install -r requirements.txt
python3 server.py
```

Dann `http://127.0.0.1:8765` öffnen. Der Server ist nur auf diesem Rechner erreichbar; beenden mit Ctrl+C.

## Hinweise und Datenschutz

- Unterstützt wird das aktuelle öffentliche Albumformat `https://photos.icloud.com/shared/album/<Schlüssel>`. Ältere `sharedalbum`-Links werden noch nicht unterstützt. Apple dokumentiert die anonyme iCloud-Schnittstelle nicht als öffentliche API und kann sie ändern.
- Der Server speichert keine Bilder oder Albumlinks. Gespeicherte Links liegen im `localStorage` deines Browsers. Kurzlebige Bildlinks können ablaufen; dann Album erneut importieren.
- Lokale Fotoauswahl wird im Browser verarbeitet und nicht hochgeladen. Wikipedia erhält erkannte Ortskoordinaten für die Umkreissuche.
- Aufenthaltszeiten sind Fotospannen zwischen Aufnahmen am selben Ort, keine exakten Ankunfts- oder Abfahrtszeiten. Fotos ohne GPS erscheinen in Zeitleiste und Galerie, aber nicht auf der Karte.
- Karten, Wikipedia, Tailwind, Leaflet, Lucide und ExifReader laden Daten über das Internet.

## Tests

`python3 -m unittest`
