import os

# Directories to include
INCLUDE_DIRS = ['src', 'tests', 'ref', 'utils']

# Directories to exclude
EXCLUDE_DIRS = ['venv', '.venv', '__pycache__', 'build']

# File extensions and specific filenames to include
INCLUDE_EXTENSIONS = ['.py', '.pb', '.c', '.bnf', '.ebnf', '.grammar']
INCLUDE_FILENAMES = ['ref_lang.c']

# Output file
OUTPUT_FILE = 'all_in_one_dump.txt'

def should_include_dir(path):
    return any(path.startswith(d + os.sep) or path == d for d in INCLUDE_DIRS)

def should_exclude_dir(path):
    return any(part in EXCLUDE_DIRS for part in path.split(os.sep))

def should_include_file(file_name):
    _, ext = os.path.splitext(file_name)
    return (
        ext in INCLUDE_EXTENSIONS or
        file_name in INCLUDE_FILENAMES
    )

def collect_files(base_dir='.'):
    collected_files = []
    for root, dirs, files in os.walk(base_dir):
        # Normalize relative path
        rel_root = os.path.relpath(root, base_dir)
        
        if rel_root == '.':
            continue  # Skip root itself

        if should_exclude_dir(rel_root):
            print(f"Skipping directory: {rel_root}")
            dirs[:] = []  # Don’t walk subdirs here
            continue

        if not should_include_dir(rel_root):
            print(f"Skipping (not in include list): {rel_root}")
            dirs[:] = []  # Don’t walk subdirs here
            continue

        for file in files:
            if should_include_file(file):
                full_path = os.path.join(root, file)
                print(f"Including: {full_path}")
                collected_files.append(full_path)
            else:
                print(f"Skipping file: {os.path.join(rel_root, file)}")

    return collected_files

def write_combined_file(file_list, output_file):
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for file_path in file_list:
            out_f.write(f"{'#' * 80}\n")
            out_f.write(f"# FILE: {file_path}\n")
            out_f.write(f"{'#' * 80}\n\n")
            try:
                with open(file_path, 'r', encoding='utf-8') as in_f:
                    content = in_f.read()
                    out_f.write(content)
            except Exception as e:
                out_f.write(f"[ERROR reading {file_path}: {e}]\n")
            out_f.write('\n\n')  # Add spacing between files

def main():
    files_to_include = collect_files()
    print(f"\nFound {len(files_to_include)} files to include.\n")
    write_combined_file(files_to_include, OUTPUT_FILE)
    print(f"Combined file written to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
