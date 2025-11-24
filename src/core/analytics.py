"""Analytics module for performance tracking and analysis"""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from collections import defaultdict

from .memory import load_state, save_state
from .logger import logger
import hashlib


def register_file(filename: str, username: Optional[str] = None) -> str:
    """
    Register a file and create a mapping from file hash to filename.
    
    Args:
        filename: The actual filename
        username: Username for user-specific state (optional)
        
    Returns:
        File hash (8-character hex string)
    """
    state = load_state(username)
    
    # Ensure file_mapping exists
    if not hasattr(state, 'file_mapping') or state.file_mapping is None:
        state.file_mapping = {}
    
    # Create hash from filename
    file_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
    
    # Store mapping if not already present
    if file_hash not in state.file_mapping:
        state.file_mapping[file_hash] = filename
        save_state(state, username)
        logger.get_logger().info(f"Registered file: {filename} -> {file_hash}")
    
    return file_hash


def record_quiz_answer(
    chunk_id: str,
    source_reference: str,
    is_correct: bool,
    question_text: str = "",
    username: Optional[str] = None,
    filename: Optional[str] = None
) -> None:
    """
    Record a quiz answer performance for a specific chunk.
    
    Args:
        chunk_id: Identifier for the chunk (e.g., "chunk_0", "chunk_1")
        source_reference: Reference to source content (e.g., "Chunk 1 - Introduction")
        is_correct: Whether the answer was correct
        question_text: The question text (optional, for reference)
        username: Username for user-specific state (optional)
    """
    state = load_state(username)
    
    # Handle case where chunk_performance might not exist (for old state files)
    if not hasattr(state, 'chunk_performance') or state.chunk_performance is None:
        state.chunk_performance = {}
    
    # Use source_reference as key if chunk_id is not available
    key = chunk_id if chunk_id else source_reference
    
    if key not in state.chunk_performance:
        state.chunk_performance[key] = {
            "correct": 0,
            "incorrect": 0,
            "attempts": 0,
            "last_attempt": None,
            "source_reference": source_reference,
            "filename": filename,  # Store filename for display
            "questions": []
        }
    # Update filename if not set (for existing chunks)
    elif filename and not state.chunk_performance[key].get("filename"):
        state.chunk_performance[key]["filename"] = filename
    
    # Update performance
    state.chunk_performance[key]["attempts"] += 1
    if is_correct:
        state.chunk_performance[key]["correct"] += 1
    else:
        state.chunk_performance[key]["incorrect"] += 1
    
    state.chunk_performance[key]["last_attempt"] = datetime.now().isoformat()
    
    # Store question for reference
    if question_text:
        state.chunk_performance[key]["questions"].append({
            "question": question_text[:200],  # Truncate for storage
            "correct": is_correct,
            "timestamp": datetime.now().isoformat()
        })
        # Keep only last 10 questions per chunk
        if len(state.chunk_performance[key]["questions"]) > 10:
            state.chunk_performance[key]["questions"] = state.chunk_performance[key]["questions"][-10:]
    
    save_state(state, username)
    
    logger.get_logger().info(
        f"Recorded quiz answer for {key}: {'correct' if is_correct else 'incorrect'}"
    )


def get_chunk_performance(chunk_id: str, username: Optional[str] = None) -> Dict[str, Any]:
    """
    Get performance statistics for a specific chunk.
    
    Args:
        chunk_id: Identifier for the chunk
        username: Username for user-specific state (optional)
        
    Returns:
        Dictionary with performance metrics
    """
    state = load_state(username)
    
    # Handle case where chunk_performance might not exist (for old state files)
    if not hasattr(state, 'chunk_performance') or state.chunk_performance is None:
        return {
            "correct": 0,
            "incorrect": 0,
            "attempts": 0,
            "accuracy": 0.0,
            "source_reference": ""
        }
    
    perf = state.chunk_performance.get(chunk_id, {})
    attempts = perf.get("attempts", 0)
    correct = perf.get("correct", 0)
    
    accuracy = (correct / attempts * 100) if attempts > 0 else 0.0
    
    return {
        "correct": correct,
        "incorrect": perf.get("incorrect", 0),
        "attempts": attempts,
        "accuracy": accuracy,
        "source_reference": perf.get("source_reference", ""),
        "last_attempt": perf.get("last_attempt")
    }


def get_all_chunk_performance(username: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Get performance statistics for all chunks.
    
    Args:
        username: Username for user-specific state (optional)
    
    Returns:
        Dictionary mapping chunk_id to performance metrics
    """
    state = load_state(username)
    
    # Handle case where chunk_performance might not exist (for old state files)
    if not hasattr(state, 'chunk_performance') or state.chunk_performance is None:
        return {}
    
    result = {}
    for chunk_id, perf in state.chunk_performance.items():
        attempts = perf.get("attempts", 0)
        correct = perf.get("correct", 0)
        accuracy = (correct / attempts * 100) if attempts > 0 else 0.0
        
        result[chunk_id] = {
            "correct": correct,
            "incorrect": perf.get("incorrect", 0),
            "attempts": attempts,
            "accuracy": accuracy,
            "source_reference": perf.get("source_reference", ""),
            "filename": perf.get("filename"),  # Include filename
            "last_attempt": perf.get("last_attempt")
        }
    
    return result


def extract_file_name_from_chunks(file_hash: str, chunks: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """
    Try to extract a meaningful file name from chunk source references.
    This is a fallback when filename isn't stored in the mapping.
    
    Args:
        file_hash: The file hash
        chunks: Dictionary of chunks for this file
        
    Returns:
        A suggested file name or None
    """
    # Try to find a filename in any chunk
    for chunk_perf in chunks.values():
        filename = chunk_perf.get("filename")
        if filename and filename != "unknown_file":
            return filename
    
    # If no filename found, try to extract from source references
    # Look for common patterns that might indicate a file/document name
    for chunk_perf in chunks.values():
        source_ref = chunk_perf.get("source_reference", "")
        if source_ref:
            # Try to extract meaningful content
            topic = format_topic_name(source_ref, max_length=100)
            # If it's a substantial topic name (not just "Section X"), use it
            if len(topic) > 15 and not topic.startswith("Section"):
                # Extract first few words as a potential document name
                words = topic.split()[:5]
                if len(words) >= 2:
                    return " ".join(words) + "..."
    
    return None


def backfill_file_mapping_from_chunks(username: Optional[str] = None) -> None:
    """
    Backfill file_mapping by extracting filenames from existing chunk data.
    This helps recover filenames for data created before file registration was implemented.
    """
    state = load_state(username)
    if not hasattr(state, 'chunk_performance') or not state.chunk_performance:
        return
    
    if not hasattr(state, 'file_mapping') or state.file_mapping is None:
        state.file_mapping = {}
    
    updated = False
    for chunk_id, perf in state.chunk_performance.items():
        filename = perf.get("filename")
        if filename and filename != "unknown_file":
            # Extract file hash from chunk_id
            if "_chunk_" in chunk_id:
                file_hash = chunk_id.split("_chunk_")[0]
                # Register this file if not already registered
                if file_hash not in state.file_mapping:
                    state.file_mapping[file_hash] = filename
                    updated = True
                    logger.get_logger().info(f"Backfilled file mapping: {filename} -> {file_hash}")
    
    if updated:
        save_state(state, username)


def group_chunks_by_file(all_perf: Dict[str, Dict[str, Any]], username: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Group chunk performance by file (using file hash from chunk_id).
    
    Args:
        all_perf: Dictionary mapping chunk_id to performance metrics
        username: Username for user-specific state (optional)
        
    Returns:
        Dictionary mapping file_hash to file-level aggregated performance and chunks
    """
    # First, try to backfill file mapping from existing chunk data
    backfill_file_mapping_from_chunks(username)
    
    files = {}
    
    for chunk_id, perf in all_perf.items():
        # Extract file hash from chunk_id (format: {file_hash}_chunk_{chunk_num})
        if "_chunk_" in chunk_id:
            file_hash = chunk_id.split("_chunk_")[0]
            chunk_num = chunk_id.split("_chunk_")[1] if "_chunk_" in chunk_id else "unknown"
        else:
            # Legacy chunks without file hash - group under "unknown"
            file_hash = "unknown"
            chunk_num = chunk_id
        
        if file_hash not in files:
            # Try to get filename from multiple sources:
            # 1. From chunk performance data
            filename = perf.get("filename")
            # 2. From file mapping in state (for existing data)
            if not filename or filename == "unknown_file":
                state = load_state(username=username)  # Get from user-specific state
                if hasattr(state, 'file_mapping') and state.file_mapping:
                    filename = state.file_mapping.get(file_hash)
            
            files[file_hash] = {
                "file_hash": file_hash,
                "filename": filename,  # Store filename for display
                "chunks": {},
                "total_attempts": 0,
                "total_correct": 0,
                "total_incorrect": 0,
                "chunks_with_data": 0
            }
        # Update filename if we find one and it's not set
        elif perf.get("filename") and not files[file_hash].get("filename"):
            filename = perf.get("filename")
            files[file_hash]["filename"] = filename
            # Auto-register this file in the mapping if we found a filename
            if filename and filename != "unknown_file":
                state = load_state(username=username)
                if not hasattr(state, 'file_mapping') or state.file_mapping is None:
                    state.file_mapping = {}
                if file_hash not in state.file_mapping:
                    state.file_mapping[file_hash] = filename
                    save_state(state, username)
                    logger.get_logger().info(f"Auto-registered file from chunk data: {filename} -> {file_hash}")
        # Also check file mapping if filename still not set
        elif not files[file_hash].get("filename") or files[file_hash].get("filename") == "unknown_file":
            state = load_state(username=username)
            if hasattr(state, 'file_mapping') and state.file_mapping:
                mapped_filename = state.file_mapping.get(file_hash)
                if mapped_filename:
                    files[file_hash]["filename"] = mapped_filename
        
        # Add chunk to file
        files[file_hash]["chunks"][chunk_id] = perf
        
        # Aggregate file-level stats
        files[file_hash]["total_attempts"] += perf.get("attempts", 0)
        files[file_hash]["total_correct"] += perf.get("correct", 0)
        files[file_hash]["total_incorrect"] += perf.get("incorrect", 0)
        if perf.get("attempts", 0) > 0:
            files[file_hash]["chunks_with_data"] += 1
    
    # Calculate file-level accuracy
    for file_hash, file_data in files.items():
        total_attempts = file_data["total_attempts"]
        total_correct = file_data["total_correct"]
        file_data["accuracy"] = (total_correct / total_attempts * 100) if total_attempts > 0 else 0.0
        
        # Get most recent attempt across all chunks
        last_attempts = [p.get("last_attempt") for p in file_data["chunks"].values() if p.get("last_attempt")]
        if last_attempts:
            file_data["last_attempt"] = max(last_attempts)
        else:
            file_data["last_attempt"] = None
    
    return files


def get_weak_areas(threshold: float = 60.0, min_attempts: int = 2, username: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Identify weak areas based on performance.
    
    Args:
        threshold: Accuracy threshold below which an area is considered weak (default 60%)
        min_attempts: Minimum number of attempts required to be considered (default 2)
        username: Username for user-specific state (optional)
        
    Returns:
        List of weak areas with performance details, sorted by accuracy (worst first)
    """
    all_perf = get_all_chunk_performance(username)
    weak_areas = []
    
    for chunk_id, perf in all_perf.items():
        if perf["attempts"] >= min_attempts and perf["accuracy"] < threshold:
            weak_areas.append({
                "chunk_id": chunk_id,
                "source_reference": perf["source_reference"],
                "accuracy": perf["accuracy"],
                "correct": perf["correct"],
                "incorrect": perf["incorrect"],
                "attempts": perf["attempts"],
                "last_attempt": perf["last_attempt"]
            })
    
    # Sort by accuracy (worst first)
    weak_areas.sort(key=lambda x: x["accuracy"])
    
    return weak_areas


def get_strong_areas(threshold: float = 80.0, min_attempts: int = 2, username: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Identify strong areas based on performance.
    
    Args:
        threshold: Accuracy threshold above which an area is considered strong (default 80%)
        min_attempts: Minimum number of attempts required to be considered (default 2)
        username: Username for user-specific state (optional)
        
    Returns:
        List of strong areas with performance details, sorted by accuracy (best first)
    """
    all_perf = get_all_chunk_performance(username)
    strong_areas = []
    
    for chunk_id, perf in all_perf.items():
        if perf["attempts"] >= min_attempts and perf["accuracy"] >= threshold:
            strong_areas.append({
                "chunk_id": chunk_id,
                "source_reference": perf["source_reference"],
                "accuracy": perf["accuracy"],
                "correct": perf["correct"],
                "incorrect": perf["incorrect"],
                "attempts": perf["attempts"],
                "last_attempt": perf["last_attempt"]
            })
    
    # Sort by accuracy (best first)
    strong_areas.sort(key=lambda x: x["accuracy"], reverse=True)
    
    return strong_areas


def get_performance_summary(username: Optional[str] = None) -> Dict[str, Any]:
    """
    Get overall performance summary statistics.
    
    Args:
        username: Username for user-specific state (optional)
    
    Returns:
        Dictionary with summary statistics
    """
    all_perf = get_all_chunk_performance(username)
    
    if not all_perf:
        return {
            "total_chunks": 0,
            "total_attempts": 0,
            "total_correct": 0,
            "total_incorrect": 0,
            "overall_accuracy": 0.0,
            "chunks_with_data": 0
        }
    
    total_attempts = sum(p["attempts"] for p in all_perf.values())
    total_correct = sum(p["correct"] for p in all_perf.values())
    total_incorrect = sum(p["incorrect"] for p in all_perf.values())
    chunks_with_data = len([p for p in all_perf.values() if p["attempts"] > 0])
    
    overall_accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0.0
    
    return {
        "total_chunks": len(all_perf),
        "total_attempts": total_attempts,
        "total_correct": total_correct,
        "total_incorrect": total_incorrect,
        "overall_accuracy": overall_accuracy,
        "chunks_with_data": chunks_with_data
    }


def extract_chunk_id_from_reference(source_reference: str, filename: Optional[str] = None) -> str:
    """
    Extract chunk identifier from source reference string.
    Includes filename to make it unique across different files.
    
    Args:
        source_reference: Reference string like "Chunk 1 - Introduction" or "Chunk X - ..."
        filename: Optional filename to make chunk ID unique per file
        
    Returns:
        Chunk identifier (e.g., "file1_chunk_1" or "chunk_1")
    """
    import re
    import hashlib
    
    # Try to extract chunk number
    match = re.search(r'[Cc]hunk\s*(\d+)', source_reference)
    chunk_num = match.group(1) if match else "unknown"
    
    # Create unique identifier using filename if available
    if filename:
        # Create a short hash of filename for uniqueness
        file_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
        return f"{file_hash}_chunk_{chunk_num}"
    
    # Fallback: use first 50 chars as identifier
    return source_reference[:50].replace(" ", "_").lower()


def format_topic_name(source_reference: str, max_length: int = 60) -> str:
    """
    Extract a user-friendly topic name from a source reference string.
    Removes technical jargon and extracts meaningful content.
    
    Args:
        source_reference: Raw source reference like "Chunk 1 - EXACT quote: 'AWS offers...'"
        max_length: Maximum length of the formatted topic name
        
    Returns:
        Clean, user-friendly topic name (e.g., "AWS Foundational Services")
    """
    import re
    
    if not source_reference:
        return "Unknown Topic"
    
    # Remove common technical prefixes
    text = source_reference
    
    # Remove "EXACT quote:" or "quote:" patterns
    text = re.sub(r'[Ee]XACT\s+quote\s*:', '', text)
    text = re.sub(r'quote\s*:', '', text)
    
    # Remove "Chunk X -" pattern but keep the number for reference
    chunk_match = re.search(r'[Cc]hunk\s*(\d+)', text)
    chunk_num = chunk_match.group(1) if chunk_match else None
    text = re.sub(r'[Cc]hunk\s*\d+\s*-\s*', '', text)
    
    # Extract content from quotes if present
    quote_match = re.search(r"['\"]([^'\"]{10,})['\"]", text)
    if quote_match:
        text = quote_match.group(1)
    
    # Clean up the text
    text = text.strip()
    
    # Remove leading/trailing punctuation
    text = re.sub(r'^[^\w]+|[^\w]+$', '', text)
    
    # Capitalize first letter of each word if it's all lowercase
    words = text.split()
    if words and all(w.islower() or not w.isalpha() for w in words[:3]):
        # Capitalize first word
        if words:
            words[0] = words[0].capitalize()
    
    # Join and truncate
    result = ' '.join(words)
    
    # If we have a chunk number, prepend it for context
    if chunk_num and len(result) < max_length - 10:
        result = f"Section {chunk_num}: {result}"
    
    # Truncate if too long, but try to break at word boundary
    if len(result) > max_length:
        truncated = result[:max_length].rsplit(' ', 1)[0]
        if len(truncated) > max_length * 0.7:  # Only truncate if we keep most of it
            result = truncated + "..."
        else:
            result = result[:max_length] + "..."
    
    # Fallback if result is empty or too short
    if not result or len(result.strip()) < 5:
        if chunk_num:
            return f"Section {chunk_num}"
        return "Content Area"
    
    return result

