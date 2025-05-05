import zipfile
import os
from pathlib import Path

def zip_folders(folders, output_filename, exclude_dirs=None, include_exts=None):
    if exclude_dirs is None:
        exclude_dirs = set()
    if include_exts is None:
        include_exts = {'.py', '.pb', '.c'}

    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for folder in folders:
            for root, dirs, files in os.walk(folder):
                # Ignorujemy katalogi, które podaliśmy
                dirs[:] = [d for d in dirs if d not in exclude_dirs]

                for file in files:
                    if Path(file).suffix in include_exts:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, start=folder.parent)
                        zipf.write(file_path, arcname)
                        print(f"[+] Dodano: {arcname}")

if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent

    folders_to_zip = [
        root_dir / 'src',
        root_dir / 'tests',
        root_dir / 'ref'
    ]

    output_zip = root_dir / 'lang.zip'

    exclude_dirs = {'__pycache__'}
    include_exts = {'.py', '.pb', '.c'}

    print(f"Pakuję do {output_zip}...")
    zip_folders(folders_to_zip, output_zip, exclude_dirs, include_exts)
    print(f"Gotowe! Spakowano projekt, pominięto katalogi: {exclude_dirs}, uwzględniono pliki: {include_exts}")
