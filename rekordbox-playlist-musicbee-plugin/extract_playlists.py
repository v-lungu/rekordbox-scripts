"""
Extract playlists from a Rekordbox XML library export.

For each playlist found under <PLAYLISTS><NODE Type="0" Name="ROOT">, this writes:
  - <playlist>.m3u8   (standard, UTF-8 M3U with file paths)
  - <playlist>.csv    (track metadata: position, title, artist, album, BPM, key, genre, location)

It also writes:
  - playlists_summary.csv : one row per playlist with name + track count

Usage:
  python3 extract_playlists.py [path/to/Library.xml] [output_dir]
Defaults: ./Library.xml and ./playlists_out
"""

import csv
import os
import sys
import re
import urllib.parse
import xml.etree.ElementTree as ET


def safe_filename(name: str) -> str:
    """Strip characters that are illegal on Windows/macOS/Linux filesystems."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip().rstrip(".")
    return cleaned or "untitled"


def location_to_path(location: str) -> str:
    """Convert a Rekordbox `Location` URL to a usable filesystem path."""
    if not location:
        return ""
    # Strip the file://localhost or file:// prefix
    path = re.sub(r"^file://(localhost)?", "", location)
    # Decode percent-encoding (%20 -> space, etc.)
    path = urllib.parse.unquote(path)
    # On Windows the path looks like /V:/MyFiles/... — strip the leading slash
    if re.match(r"^/[A-Za-z]:/", path):
        path = path[1:]
    return path


def extract_playlists(xml_path: str, out_dir: str) -> None:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Build TrackID -> attributes lookup from <COLLECTION>
    collection = {}
    for track in root.iterfind("COLLECTION/TRACK"):
        tid = track.get("TrackID")
        if tid:
            collection[tid] = track.attrib

    print(f"Loaded {len(collection)} tracks from <COLLECTION>")

    os.makedirs(out_dir, exist_ok=True)

    summary_rows = []

    # Walk every Type="1" NODE anywhere under <PLAYLISTS> (handles nested folders)
    for playlist_node in root.iterfind('.//PLAYLISTS//NODE[@Type="1"]'):
        name = playlist_node.get("Name", "untitled")
        declared = int(playlist_node.get("Entries", "0"))
        keys = [t.get("Key") for t in playlist_node.findall("TRACK") if t.get("Key")]

        print(f"\nPlaylist: {name!r}  (declared {declared}, found {len(keys)})")
        summary_rows.append({"playlist": name, "declared_entries": declared, "found_entries": len(keys)})

        base = os.path.join(out_dir, safe_filename(name))

        # --- M3U ---
        with open(base + ".m3u8", "w", encoding="utf-8", newline="\n") as m3u:
            m3u.write("#EXTM3U\n")
            for key in keys:
                meta = collection.get(key)
                if not meta:
                    m3u.write(f"# missing track id {key}\n")
                    continue
                seconds = int(meta.get("TotalTime") or 0)
                title = meta.get("Name", "")
                artist = meta.get("Artist", "")
                m3u.write(f"#EXTINF:{seconds},{artist} - {title}\n")
                m3u.write(location_to_path(meta.get("Location", "")) + "\n")

        # --- CSV ---
        with open(base + ".csv", "w", encoding="utf-8", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow([
                "position", "track_id", "title", "artist", "album", "genre",
                "bpm", "key", "duration_sec", "year", "label", "location",
            ])
            for i, key in enumerate(keys, 1):
                meta = collection.get(key, {})
                writer.writerow([
                    i,
                    key,
                    meta.get("Name", ""),
                    meta.get("Artist", ""),
                    meta.get("Album", ""),
                    meta.get("Genre", ""),
                    meta.get("AverageBpm", ""),
                    meta.get("Tonality", ""),
                    meta.get("TotalTime", ""),
                    meta.get("Year", ""),
                    meta.get("Label", ""),
                    location_to_path(meta.get("Location", "")),
                ])

    # --- Summary ---
    summary_path = os.path.join(out_dir, "playlists_summary.csv")
    with open(summary_path, "w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=["playlist", "declared_entries", "found_entries"])
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nDone. Wrote {len(summary_rows)} playlists to: {out_dir}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    xml_path = sys.argv[1] if len(sys.argv) > 1 else "Library.xml"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "playlists_out"
    extract_playlists(xml_path, out_dir)
