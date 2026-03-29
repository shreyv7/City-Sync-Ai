def get_file_size_kb(file_obj) -> float:
    """
    Calculate the size of a file object in kilobytes.
    
    Args:
        file_obj: The file object (e.g., from st.file_uploader)
        
    Returns:
        float: File size in KB
    """
    # Move pixel to end to get size
    pos = file_obj.tell()
    file_obj.seek(0, 2)  # Seek to end
    size_bytes = file_obj.tell()
    file_obj.seek(pos)  # Reset position
    return size_bytes / 1024.0
