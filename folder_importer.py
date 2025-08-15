import os
import logging

# Ensure logging is configured at INFO level if not already set
logging.basicConfig(level=logging.INFO)

def import_from_folder(folder_path, include_hidden=False, sort_by_mtime=False):
    """
    Recursively collect all PDF file paths from a folder.
    Parameters:
        - include_hidden: whether to include hidden files
        - sort_by_mtime: sort result list by file modification time
    Returns:
        List of PDF file paths
    """
    pdf_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if not include_hidden and file.startswith('.'):
                continue
            if file.lower().endswith(".pdf"):
                full_path = os.path.join(root, file)
                pdf_files.append(full_path)

    if sort_by_mtime:
        pdf_files.sort(key=lambda x: os.path.getmtime(x))

    logging.info(f"Found {len(pdf_files)} PDF files in '{folder_path}'")
    return pdf_files

def filter_pdf_files(paths, include_hidden=False, sort_by_mtime=False):
    """
    From a list of file/folder paths, return a flattened list of all PDF file paths.
    Parameters:
        - include_hidden: whether to include hidden files
        - sort_by_mtime: sort result list by file modification time
    """
    all_pdfs = []
    for path in paths:
        if os.path.isfile(path) and path.lower().endswith(".pdf"):
            if not include_hidden and os.path.basename(path).startswith('.'):
                continue
            all_pdfs.append(path)
        elif os.path.isdir(path):
            all_pdfs.extend(import_from_folder(path, include_hidden=include_hidden, sort_by_mtime=sort_by_mtime))

    if sort_by_mtime:
        all_pdfs.sort(key=lambda x: os.path.getmtime(x))

    logging.info(f"Filtered {len(all_pdfs)} PDF files from input paths: {paths}")
    return all_pdfs