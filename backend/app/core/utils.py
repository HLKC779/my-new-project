import hashlib
import os
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import HTTPException, status, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings


def get_file_extension(filename: str) -> str:
    """Extract the file extension from a filename."""
    return Path(filename).suffix.lower()


def validate_file_extension(filename: str) -> bool:
    """Validate that a file has an allowed extension."""
    allowed_extensions = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }
    ext = get_file_extension(filename)
    return ext in allowed_extensions


def get_content_type(filename: str) -> Optional[str]:
    """Get the MIME type for a file based on its extension."""
    ext = get_file_extension(filename)
    content_types = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
    }
    return content_types.get(ext)


def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename to avoid collisions."""
    ext = get_file_extension(original_filename)
    unique_id = str(uuid.uuid4().hex)
    return f"{unique_id}{ext}"


def save_upload_file(upload_file: UploadFile, dest_dir: str = None) -> str:
    """
    Save an uploaded file to the filesystem.
    
    Args:
        upload_file: The uploaded file
        dest_dir: The destination directory (defaults to settings.UPLOAD_DIR)
        
    Returns:
        str: The path to the saved file
    """
    if dest_dir is None:
        dest_dir = settings.UPLOAD_DIR
    
    # Ensure the upload directory exists
    os.makedirs(dest_dir, exist_ok=True)
    
    # Generate a unique filename
    filename = generate_unique_filename(upload_file.filename)
    file_path = os.path.join(dest_dir, filename)
    
    # Save the file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return file_path


def delete_file(file_path: str) -> bool:
    """
    Delete a file from the filesystem.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        bool: True if the file was deleted, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            return True
        return False
    except Exception as e:
        return False


def calculate_file_hash(file_path: str, algorithm: str = 'sha256') -> str:
    """
    Calculate the hash of a file.
    
    Args:
        file_path: Path to the file
        algorithm: The hash algorithm to use (default: 'sha256')
        
    Returns:
        str: The hexadecimal digest of the file's hash
    """
    hash_func = getattr(hashlib, algorithm, hashlib.sha256)
    
    with open(file_path, 'rb') as f:
        file_hash = hash_func()
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            file_hash.update(byte_block)
    
    return file_hash.hexdigest()


def get_file_size(file_path: str) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        int: Size of the file in bytes
    """
    return os.path.getsize(file_path)


def format_file_size(size_in_bytes: int) -> str:
    """
    Format a file size in a human-readable format.
    
    Args:
        size_in_bytes: Size in bytes
        
    Returns:
        str: Formatted file size (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.1f} PB"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to make it safe for storage.
    
    Args:
        filename: The original filename
        
    Returns:
        str: Sanitized filename
    """
    # Remove any path information
    filename = os.path.basename(filename)
    
    # Replace spaces and special characters with underscores
    filename = re.sub(r'[^\w\-_. ]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    return filename


def get_mime_type(file_path: str) -> str:
    """
    Get the MIME type of a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: The MIME type
    """
    import mimetypes
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or 'application/octet-stream'


def send_file(file_path: str, filename: str = None, as_attachment: bool = True):
    """
    Send a file as a response.
    
    Args:
        file_path: Path to the file to send
        filename: The filename to use for the response (defaults to the basename of file_path)
        as_attachment: Whether to send the file as an attachment
        
    Returns:
        FileResponse: A FastAPI FileResponse object
    """
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    if filename is None:
        filename = os.path.basename(file_path)
    
    return FileResponse(
        file_path,
        filename=filename,
        media_type=get_mime_type(file_path),
        headers={"Content-Disposition": f"{'attachment' if as_attachment else 'inline'}; filename={filename}"}
    )
