"""Message splitter utility for splitting long messages into chunks."""
import re
from typing import List


class MessageSplitter:
    """Splits long messages into sentence-based chunks for better readability.

    Designed for WhatsApp messages where shorter chunks are easier to read
    on mobile devices.
    """

    def __init__(
        self,
        max_length: int = 1000,
        min_split_length: int = 500,
    ):
        """Initialize the message splitter.

        Args:
            max_length: Maximum characters per chunk (default: 1000).
            min_split_length: Minimum length before attempting to split (default: 500).
        """
        self.max_length = max_length
        self.min_split_length = min_split_length

    def split_into_chunks(self, text: str) -> List[str]:
        """Split text into chunks at sentence boundaries.

        Args:
            text: The text to split.

        Returns:
            List of text chunks, each within max_length.
        """
        if not text:
            return []

        # If message is short enough, return as single chunk
        if len(text) <= self.min_split_length:
            return [text.strip()]

        # Split into sentences
        sentences = self._split_into_sentences(text)

        # Group sentences into chunks
        chunks = self._group_into_chunks(sentences)

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences, preserving delimiters.

        Args:
            text: The text to split.

        Returns:
            List of sentences with their ending punctuation.
        """
        # Pattern matches sentence endings: . ! ? followed by space or end
        # Also handles Indonesian/Malay text which may use different punctuation
        pattern = r'(?<=[.!?])\s+'

        # Split by sentence boundaries
        parts = re.split(pattern, text)

        # Clean up and filter empty sentences
        sentences = []
        for part in parts:
            part = part.strip()
            if part:
                sentences.append(part)

        return sentences

    def _group_into_chunks(self, sentences: List[str]) -> List[str]:
        """Group sentences into chunks within max_length.

        Args:
            sentences: List of sentences to group.

        Returns:
            List of chunked text.
        """
        if not sentences:
            return []

        chunks = []
        current_chunk = []

        for sentence in sentences:
            sentence_length = len(sentence)

            # If a single sentence is longer than max_length, we need to force split
            if sentence_length > self.max_length:
                # First, save any accumulated chunk
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []

                # Force split the long sentence
                forced_chunks = self._force_split_sentence(sentence)
                chunks.extend(forced_chunks)
                continue

            # Check if adding this sentence would exceed max_length
            current_length = sum(len(s) for s in current_chunk) + len(current_chunk)  # + spaces

            if current_chunk and (current_length + 1 + sentence_length) > self.max_length:
                # Save current chunk and start new one
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
            else:
                current_chunk.append(sentence)

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _force_split_sentence(self, text: str) -> List[str]:
        """Force split a very long sentence at word boundaries.

        Args:
            text: Text to force split.

        Returns:
            List of text chunks.
        """
        chunks = []
        words = text.split()
        current_chunk = []

        for word in words:
            current_length = sum(len(w) for w in current_chunk) + len(current_chunk)

            if current_chunk and (current_length + 1 + len(word)) > self.max_length:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
            else:
                current_chunk.append(word)

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks
