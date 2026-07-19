from pathlib import Path


def get_single_input_file_path(input_dir: Path, file_extension: str) -> Path:
    """Return the single file with the required extension from the directory."""
    if not input_dir.exists():
        raise FileNotFoundError(f"Directory '{input_dir}' does not exist")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Path '{input_dir}' is not a directory")

    normalized_ext = file_extension.lower()
    if not normalized_ext.startswith("."):
        normalized_ext = f".{normalized_ext}"

    matching_files = [
        file_path
        for file_path in input_dir.iterdir()
        if file_path.is_file() and file_path.name.lower().endswith(normalized_ext)
    ]

    if len(matching_files) != 1:
        raise ValueError(
            f"Expected exactly one '{normalized_ext}' file in '{input_dir}', "
            f"found {len(matching_files)}"
        )

    return matching_files[0]
