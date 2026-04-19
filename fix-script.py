import xml.etree.ElementTree as ET
from urllib.parse import unquote
import sys
import re

def parse_xml_library(xml_filepath):
    """
    Reads an XML file and builds a dictionary where:
    - Key: first 44 characters of the decoded filename
    - Value: full decoded filename (just the filename, not the full path)
    
    Only processes lines/elements with Location attributes matching:
    Location="file://localhost/V:/MyFiles/Music/..."
    """
    library = {}
    prefix = "file://localhost/V:/MyFiles/Music/"

    location_pattern = re.compile(r'Location="([^"]+)"')

    with open(xml_filepath, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            match = location_pattern.search(stripped)
            if match:
                raw_location = match.group(1)
                if raw_location.startswith(prefix):
                    decoded_location = unquote(raw_location)
                    filename = decoded_location.split("/")[-1]
                    extension = filename.split(".")[-1]

                    if len(filename) - len(extension) <= 44:
                        key = filename
                    else:
                        key = filename[:44] + "." + extension
                    library[key] = filename

    return library


def rename_files_from_library(library, folder_path, dry_run=True):
    """
    Scans all files in folder_path and renames any file whose name matches a key
    in the library.

    Parameters:
        library     : dict returned by parse_xml_library()
        folder_path : path to the folder containing files to rename
        dry_run     : if True, only prints what WOULD be renamed without doing it
    """
    import os

    folder = os.path.abspath(folder_path)
    print("folder " + folder)
    if not os.path.isdir(folder):
        print(f"ERROR: '{folder}' is not a valid directory.")
        return

    files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]

    if not files:
        print("No files found in the specified folder.")
        return

    matched_files   = []
    unmatched_files = []

    for filename in sorted(files):
        key = filename
        if key in library:
            matched_files.append((filename, library[key]))
        else:
            unmatched_files.append(filename)

    # --- Matched files ---
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Scanning {len(files)} file(s) in: {folder}\n")
    print(f"{'CURRENT FILENAME':<50}  {'NEW FILENAME'}")
    print("-" * 120)

    for filename, new_full_name in matched_files:
        print(f"{filename:<50}  ->  {new_full_name}")
        if not dry_run:
            src = os.path.join(folder, filename)
            dst = os.path.join(folder, new_full_name)
            if os.path.exists(dst):
                print(f"  [SKIPPED] Destination already exists: {new_full_name}")
            else:
                os.rename(src, dst)

    # --- Unmatched files ---
    print("-" * 120)
    print(f"\nMatched: {len(matched_files)}  |  Unmatched: {len(unmatched_files)}")

    if unmatched_files:
        print(f"\nUNMATCHED FILES (no library entry found):")
        print("-" * 60)
        for filename in unmatched_files:
            print(f"  {filename}")
        print("-" * 60)

    if dry_run:
        print("\nThis was a DRY RUN — no files were renamed.")
        print("Re-run with --rename flag to apply changes.")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Build library only:")
        print("    python parse_xml_library.py <xml_file>")
        print()
        print("  Preview renames (dry run):")
        print("    python parse_xml_library.py <xml_file> <folder_to_rename>")
        print()
        print("  Apply renames:")
        print("    python parse_xml_library.py <xml_file> <folder_to_rename> --rename")
        print()
        print("Running demo...\n")

        demo_line = '    Location="file://localhost/V:/MyFiles/Music/DJ/UKG/M-Dubs%20-%20Bump%20%27N%27%20Grind%20(feat.%20Lady%20Saw)%20(Sunship%20Edit).flac"'
        pattern = re.compile(r'Location="([^"]+)"')
        prefix = "file://localhost/V:/MyFiles/Music/"
        match = pattern.search(demo_line)
        if match:
            raw = match.group(1)
            if raw.startswith(prefix):
                decoded = unquote(raw)
                filename = decoded.split("/")[-1]
                key = filename[:44]
                print(f"Demo entry:")
                print(f"  Key   : '{key}'")
                print(f"  Value : '{filename}'")
        return

    xml_filepath = sys.argv[1]
    folder_path  = sys.argv[2] if len(sys.argv) >= 3 else None
    do_rename    = "--rename" in sys.argv

    print(f"Parsing: {xml_filepath}\n")
    library = parse_xml_library(xml_filepath)

    if not library:
        print("No matching Location entries found.")
        return

    print(f"Found {len(library)} entries in library.\n")

    # Save library to text file
    output_path = xml_filepath.rsplit(".", 1)[0] + "_library.txt"
    with open(output_path, "w", encoding="utf-8") as out:
        out.write(f"{'KEY (first 44 chars)':<44} VALUE\n")
        out.write("-" * 120 + "\n")
        for key, value in library.items():
            out.write(f"{key:<44} {value}\n")
    print(f"Library saved to: {output_path}")

    # Rename files if a folder was provided
    if folder_path:
        rename_files_from_library(library, folder_path, dry_run=not do_rename)
    else:
        print("\nTip: Pass a folder path as a second argument to preview or apply renames.")


if __name__ == "__main__":
    main()