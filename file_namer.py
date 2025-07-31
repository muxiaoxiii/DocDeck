import os
from datetime import datetime

def get_unique_filename(output_dir, base_name):
    """
    Return a unique file name by appending (1), (2), etc., if a file already exists.
    """
    name, ext = os.path.splitext(base_name)
    candidate = base_name
    i = 1
    while os.path.exists(os.path.join(output_dir, candidate)):
        candidate = f"{name} ({i}){ext}"
        i += 1
    return candidate

def suggest_output_filename(input_path, suffix="_header"):
    """
    Suggest an output filename based on input file path and suffix.
    e.g., "/path/doc.pdf" + "_header" -> "doc_header.pdf"
    """
    base_name = os.path.basename(input_path)
    name, ext = os.path.splitext(base_name)
    return f"{name}{suffix}{ext}"

def get_merged_output_filename(prefix="merged", ext=".pdf"):
    """
    Generate a merged output filename with timestamp.
    e.g., merged_20250730_153000.pdf
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}{ext}"

def resolve_output_filename(input_path, output_dir, suffix="_header", user_defined_name=None):
    """
    Determine the output filename for a given input file.
    Priority:
    1. user_defined_name (if provided)
    2. default naming based on input_path and suffix
    3. ensure uniqueness in output_dir
    """
    if user_defined_name:
        base_name = user_defined_name if user_defined_name.endswith(".pdf") else f"{user_defined_name}.pdf"
    else:
        base_name = suggest_output_filename(input_path, suffix)

    return get_unique_filename(output_dir, base_name)
def batch_resolve_output_filenames(input_paths, output_dir, suffix="_header", user_defined_names=None):
    """
    Generate a list of unique output filenames for a list of input paths.
    user_defined_names: Optional dict mapping input_path to custom name (without extension or with .pdf)
    Returns a dict mapping input_path to output filename.
    """
    output_map = {}
    for path in input_paths:
        custom_name = None
        if user_defined_names and path in user_defined_names:
            custom_name = user_defined_names[path]
        output_name = resolve_output_filename(path, output_dir, suffix, custom_name)
        output_map[path] = output_name
    return output_map