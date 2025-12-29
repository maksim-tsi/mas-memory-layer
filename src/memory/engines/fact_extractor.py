"""
Fact extraction engine for promoting information from L1 to L2.

This module implements the FactExtractor class, which uses LLMs (with fallback)
to extract structured facts from raw text turns.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import uuid4

from pydantic import ValidationError

from src.memory.models import Fact, FactType, FactCategory
from src.memory.schemas.fact_extraction import (
    FACT_EXTRACTION_SYSTEM_INSTRUCTION,
    FACT_EXTRACTION_SCHEMA,
)
from src.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class FactExtractionError(Exception):
    """Raised when fact extraction fails."""
    pass


class FactExtractor:
    """
    Extracts structured facts from raw text using LLMs with rule-based fallback.
    
    Attributes:
        llm_client: Client for LLM interactions.
        model_name: Name of the LLM model to use.
    """

    def __init__(self, llm_client: LLMClient, model_name: Optional[str] = None):
        self.llm_client = llm_client
        self.model_name = model_name or "gemini-3-flash-preview"

    async def extract_facts(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Fact]:
        """
        Extract facts from text using LLM with fallback to rules.

        Args:
            text: The raw text to process.
            metadata: Optional metadata to attach to facts (e.g., session_id, source_uri).

        Returns:
            List[Fact]: List of extracted Fact objects.
        """
        if not text or not text.strip():
            return []

        try:
            return await self._extract_with_llm(text, metadata)
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}. Falling back to rules.")
            return self._extract_with_rules(text, metadata)

    async def _extract_with_llm(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Fact]:
        """Extract facts using LLM with native structured output."""
        prompt = f"Extract significant facts from the following conversation:\n\n{text}"
        
        response = await self.llm_client.generate(
            prompt=prompt,
            model=self.model_name,
            system_instruction=FACT_EXTRACTION_SYSTEM_INSTRUCTION,
            response_schema=FACT_EXTRACTION_SCHEMA,
            temperature=0.0,
            max_output_tokens=8192,
        )

        try:
            # Parse JSON response (no markdown cleanup needed with structured output)
            data = json.loads(response.text)
            raw_facts = data.get("facts", [])
            
            facts = []
            for rf in raw_facts:
                try:
                    # Create Fact object
                    # Note: Fact requires many fields, we fill defaults for missing ones
                    fact = Fact(
                        fact_id=str(uuid4()),
                        session_id=metadata.get("session_id", "unknown") if metadata else "unknown",
                        content=rf.get("content"),
                        fact_type=rf.get("type", FactType.MENTION),
                        fact_category=rf.get("category", FactCategory.OPERATIONAL),
                        certainty=float(rf.get("certainty", 0.5)),
                        impact=float(rf.get("impact", 0.5)),
                        source_uri=metadata.get("source_uri") if metadata else None,
                        source_type="llm_extraction",
                        extracted_at=datetime.now(timezone.utc),
                        ciar_score=0.0, # Will be calculated later
                        age_decay=1.0,
                        recency_boost=1.0
                    )
                    facts.append(fact)
                except ValidationError as ve:
                    logger.warning(f"Skipping invalid fact from LLM: {ve}")
                    continue
            
            return facts

        except json.JSONDecodeError as e:
            raise FactExtractionError(f"Failed to parse LLM JSON response: {e}")

    def _extract_with_rules(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Fact]:
        """Fallback extraction using regex rules."""
        facts = []
        
        # Simple rule: Extract email addresses as entities
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        for email in emails:
            facts.append(Fact(
                fact_id=str(uuid4()),
                session_id=metadata.get("session_id", "unknown") if metadata else "unknown",
                content=f"Email address: {email}",
                fact_type=FactType.ENTITY,
                fact_category=FactCategory.PERSONAL,
                certainty=1.0,
                impact=0.5,
                source_uri=metadata.get("source_uri") if metadata else None,
                source_type="rule_fallback",
                extracted_at=datetime.now(timezone.utc),
                ciar_score=0.0,
                age_decay=1.0,
                recency_boost=1.0
            ))

        # Simple rule: Extract "I like/love/prefer" as preferences
        preferences = re.findall(r'\b(I (?:like|love|prefer) .+?)(?:[.!?;]|$)', text, re.IGNORECASE)
        for pref in preferences:
            facts.append(Fact(
                fact_id=str(uuid4()),
                session_id=metadata.get("session_id", "unknown") if metadata else "unknown",
                content=pref,
                fact_type=FactType.PREFERENCE,
                fact_category=FactCategory.PERSONAL,
                certainty=0.8,
                impact=0.7,
                source_uri=metadata.get("source_uri") if metadata else None,
                source_type="rule_fallback",
                extracted_at=datetime.now(timezone.utc),
                ciar_score=0.0,
                age_decay=1.0,
                recency_boost=1.0
            ))

        return facts
