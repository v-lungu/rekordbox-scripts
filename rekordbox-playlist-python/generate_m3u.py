import os
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote


LOCATION_PREFIX = "file://localhost/"
INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize(name):
    cleaned = INVALID_CHARS.sub("_", name).strip(" .")
    return cleaned or "_"


def location_to_path(location):
    if not location:
        return None
    if location.startswith(LOCATION_PREFIX):
        location = location[len(LOCATION_PREFIX):]
    path = unquote(location)
    # Windows paths start with a drive letter ("V:/..."); POSIX paths lose
    # their leading "/" when the prefix is stripped, so restore it.
    if not re.match(r"^[A-Za-z]:", path):
        path = "/" + path
    return path.replace("/", os.sep)


def build_collection(root):
    collection = {}
    coll_node = root.find("COLLECTION")
    if coll_node is None:
        return collection
    for track in coll_node.findall("TRACK"):
        track_id = track.get("TrackID")
        path = location_to_path(track.get("Location"))
        if track_id and path:
            collection[track_id] = path
    return collection


def write_m3u(m3u_path, track_paths):
    os.makedirs(os.path.dirname(m3u_path), exist_ok=True)
    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for p in track_paths:
            f.write(p + "\n")


def walk_playlists(node, out_dir, collection, stats):
    for child in node.findall("NODE"):
        name = sanitize(child.get("Name", "Unnamed"))
        node_type = child.get("Type")
        if node_type == "0":
            sub_dir = os.path.join(out_dir, name)
            os.makedirs(sub_dir, exist_ok=True)
            walk_playlists(child, sub_dir, collection, stats)
        elif node_type == "1":
            track_paths = []
            missing = 0
            for t in child.findall("TRACK"):
                key = t.get("Key")
                path = collection.get(key)
                if path:
                    track_paths.append(path)
                else:
                    missing += 1
            m3u_path = os.path.join(out_dir, name + ".m3u8")
            write_m3u(m3u_path, track_paths)
            stats["playlists"] += 1
            stats["tracks"] += len(track_paths)
            stats["missing"] += missing
            print(f"  {m3u_path}  ({len(track_paths)} tracks"
                  + (f", {missing} missing" if missing else "") + ")")


def pick_paths_with_dialog():
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.withdraw()

    xml_path = filedialog.askopenfilename(
        title="Choose your Rekordbox XML file",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
    )
    if not xml_path:
        messagebox.showinfo("Cancelled", "No XML file selected. Exiting.")
        sys.exit(0)

    out_dir = filedialog.askdirectory(title="Choose where to save the playlists")
    if not out_dir:
        messagebox.showinfo("Cancelled", "No output folder selected. Exiting.")
        sys.exit(0)

    return xml_path, out_dir


def main():
    if len(sys.argv) >= 2:
        xml_path = sys.argv[1]
        out_dir = sys.argv[2] if len(sys.argv) >= 3 else "playlists"
    else:
        xml_path, out_dir = pick_paths_with_dialog()

    print(f"Parsing {xml_path} ...")
    tree = ET.parse(xml_path)
    root = tree.getroot()

    collection = build_collection(root)
    print(f"Collection: {len(collection)} tracks")

    playlists_root = root.find("PLAYLISTS")
    if playlists_root is None:
        print("No <PLAYLISTS> section found.")
        sys.exit(1)

    # PLAYLISTS contains a single ROOT NODE — descend into it.
    root_node = playlists_root.find("NODE")
    if root_node is None:
        print("No root playlist node found.")
        sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)
    stats = {"playlists": 0, "tracks": 0, "missing": 0}
    print(f"Writing playlists to {os.path.abspath(out_dir)} ...")
    walk_playlists(root_node, out_dir, collection, stats)

    print(f"\nDone. {stats['playlists']} playlists, {stats['tracks']} tracks"
          + (f", {stats['missing']} missing track refs" if stats["missing"] else ""))


if __name__ == "__main__":
    try:
        main()
    finally:
        # Keep the console open when launched by double-click.
        if sys.stdin and sys.stdin.isatty():
            input("\nPress Enter to exit...")
