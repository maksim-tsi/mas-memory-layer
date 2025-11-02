# AgentRouter Integration Guide

**Document Type:** Technical Integration Guide  
**Target Audience:** Developers implementing Phase 2 (Memory Tiers & Lifecycle Engines)  
**Related ADR:** [ADR-005: Multi-Tier LLM Provider Strategy](../ADR/005-multi-tier-llm-provider-strategy.md)  
**Last Updated:** November 2, 2025

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Account Setup](#3-account-setup)
4. [Environment Configuration](#4-environment-configuration)
5. [Code Implementation](#5-code-implementation)
6. [Model Selection Guide](#6-model-selection-guide)
7. [Testing & Validation](#7-testing--validation)
8. [Cost Monitoring](#8-cost-monitoring)
9. [Error Handling](#9-error-handling)
10. [Troubleshooting](#10-troubleshooting)
11. [Production Checklist](#11-production-checklist)

---

## 1. Overview

### What is AgentRouter?

AgentRouter is a unified API gateway that provides access to multiple LLM providers (OpenAI, Anthropic, Google, DeepSeek) through a single OpenAI-compatible interface. This allows cost-optimized multi-model selection without managing multiple API keys or adapting to different API formats.

### Why AgentRouter for This Project?

- ✅ **100% OpenAI API Compatibility** - Works with LangChain/LangGraph without changes
- ✅ **Cost Efficiency** - 85% savings through multi-tier model selection
- ✅ **Single Credential** - One API key for 7 models across 4 providers
- ✅ **Explicit Model Selection** - Aligns with circuit breaker pattern
- ✅ **Trial Credits** - $100-200 for proof-of-concept testing

### Integration Points in Phase 2

| Week | Component | LLM Use Case | Model Tier |
|------|-----------|--------------|------------|
| **Week 4** | CIAR Scorer | Certainty assessment | Tier 1 (GPT-5 Mini) |
| **Week 5** | Fact Extractor | Extract structured facts | Tier 2 (DeepSeek-V3) |
| **Week 7** | Episode Consolidator | Generate summaries | Tier 2-3 (GLM-4.6/Sonnet) |
| **Week 10** | Knowledge Distiller | Synthesize patterns | Tier 3 (GPT-5) |

---

## 2. Prerequisites

### System Requirements

- **Python:** 3.9+ (project requirement)
- **Dependencies:** Listed in `requirements.txt`
- **Infrastructure:** Access to development/staging nodes
- **Network:** Outbound HTTPS to `agentrouter.org`

### Required Python Packages

```bash
# Core dependencies (add to requirements.txt if not present)
langchain>=0.1.0
langchain-openai>=0.1.0
openai>=1.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0

# Testing dependencies (add to requirements-test.txt)
pytest-asyncio>=0.21.0
pytest-vcr>=1.0.0
aioresponses>=0.7.0
```

Install dependencies:

```bash
cd /home/max/code/mas-memory-layer
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### Knowledge Requirements

**Before starting, you should understand:**
- Python async/await patterns
- LangChain ChatOpenAI interface
- Environment variable management
- Basic prompt engineering
- JSON schema validation

---

## 3. Account Setup

### Step 1: Register for AgentRouter

1. **Visit:** https://agentrouter.org
2. **Sign Up:**
   - Use project email or personal academic email
   - Select "Research/Academic" account type
   - Mention "Multi-Agent Memory Systems Research" in purpose field

3. **Verify Email:**
   - Check inbox for verification link
   - Complete email verification

4. **Trial Credits:**
   - You should automatically receive $100-200 in trial credits
   - Check dashboard for credit balance
   - Credits typically valid for 30-90 days

### Step 2: Generate API Key

1. **Navigate to Dashboard:** https://agentrouter.org/dashboard
2. **Go to API Keys section**
3. **Create New Key:**
   - Name: `mas-memory-dev` (for development)
   - Permissions: Full access (default)
   - Expiration: 90 days (recommended)

4. **Copy API Key:**
   - Format: `ar_xxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - ⚠️ **Important:** Store securely, shown only once
   - ⚠️ **Do NOT commit to Git**

5. **Test Key:**
   ```bash
   curl https://agentrouter.org/v1/models \
     -H "Authorization: Bearer ar_your_key_here"
   ```
   
   Expected response: List of available models (GPT-5, Claude, etc.)

### Step 3: Set Up Billing (Optional for Trial)

- **Trial Period:** Use trial credits first (no payment required)
- **Production:** Add payment method when credits depleted
- **Budget Alerts:** Set up $80/month alert in dashboard
- **Cost Tracking:** Enable detailed logging in settings

---

## 4. Environment Configuration

### Step 1: Create Environment File

Create `.env` file in project root (if not already present):

```bash
cd /home/max/code/mas-memory-layer
touch .env
chmod 600 .env  # Restrict permissions
```

Add to `.gitignore` (should already be there):

```bash
# Verify .env is ignored
grep "^\.env$" .gitignore || echo ".env" >> .gitignore
```

### Step 2: Configure API Key

Add to `.env`:

```bash
# AgentRouter LLM Provider
AGENTROUTER_API_KEY=ar_your_actual_key_here

# LLM Configuration
LLM_PROVIDER=agentrouter
LLM_BASE_URL=https://agentrouter.org/v1
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=3

# Cost Monitoring
LLM_DAILY_BUDGET_USD=3.00
LLM_ENABLE_COST_TRACKING=true
LLM_COST_LOG_FILE=logs/llm_costs.json

# Feature Flags (for gradual rollout)
ENABLE_LLM_FACT_EXTRACTION=true
LLM_ROLLOUT_PERCENTAGE=100
```

### Step 3: Create Configuration File

Create `config/llm_config.yaml`:

```yaml
# LLM Provider Configuration
# See ADR-005 for full rationale and model selection strategy

llm:
  provider: "agentrouter"
  api_key_env: "AGENTROUTER_API_KEY"
  base_url: "https://agentrouter.org/v1"
  
  # Timeout and retry settings
  timeout_seconds: 30
  max_retries: 3
  retry_delay_seconds: 2
  
  # Default parameters
  default_temperature: 0.3
  default_max_tokens: 2000

# Model Tier Mappings (aligned with ADR-005)
model_tiers:
  # Tier 1: Budget ($0.26-0.50/1M tokens)
  # Use for: High-frequency, low-complexity operations
  tier_1:
    ciar_scoring: "gpt-5-mini"
    entity_extraction: "claude-3-5-haiku"
    batch_processing: "gemini-2.5-flash"
    simple_classification: "gpt-5-mini"
    default: "gpt-5-mini"
  
  # Tier 2: Balanced ($0.38-0.48/1M tokens)
  # Use for: Primary workload, moderate complexity
  tier_2:
    fact_extraction: "deepseek-v3"
    episode_summary: "glm-4.6"
    relationship_extraction: "deepseek-v3"
    consolidation: "glm-4.6"
    default: "deepseek-v3"
  
  # Tier 3: Premium ($3.44-6.00/1M tokens)
  # Use for: Complex reasoning, critical accuracy
  tier_3:
    knowledge_synthesis: "gpt-5"
    complex_narrative: "claude-3.5-sonnet"
    critical_extraction: "claude-3.5-sonnet"
    pattern_extraction: "gpt-5"
    default: "gpt-5"

# Task-to-Tier Mapping (for convenience)
task_mapping:
  # Week 4-5: CIAR & Promotion
  ciar_certainty_scoring: tier_1
  ciar_impact_scoring: tier_1
  fact_extraction: tier_2
  fact_validation: tier_2
  
  # Week 6-8: Consolidation
  episode_clustering: tier_2
  episode_summarization: tier_2
  relationship_inference: tier_2
  graph_entity_extraction: tier_2
  
  # Week 9-10: Distillation
  pattern_recognition: tier_3
  knowledge_synthesis: tier_3
  knowledge_generalization: tier_3
  
  # Week 11: Orchestration
  context_assembly: tier_1
  response_generation: tier_3

# Cost Monitoring
cost_monitoring:
  enabled: true
  daily_budget_usd: 3.00
  monthly_budget_usd: 80.00
  alert_threshold_percent: 80
  log_file: "logs/llm_costs.json"
  export_interval_hours: 6

# Circuit Breaker Configuration (Week 5)
circuit_breaker:
  failure_threshold: 5
  timeout_seconds: 60
  half_open_max_requests: 2
  enabled: true

# Prompt Templates (extensible)
prompts:
  fact_extraction: "prompts/fact_extraction.txt"
  episode_summary: "prompts/episode_summary.txt"
  knowledge_synthesis: "prompts/knowledge_synthesis.txt"
```

### Step 4: Verify Configuration

Create verification script:

```bash
# scripts/verify_llm_config.py
python3 << 'EOF'
import os
from dotenv import load_dotenv
import yaml

# Load environment
load_dotenv()

# Check API key
api_key = os.getenv('AGENTROUTER_API_KEY')
if api_key:
    print(f"✅ API Key loaded: {api_key[:10]}...{api_key[-4:]}")
else:
    print("❌ API Key not found in environment")
    exit(1)

# Load config
try:
    with open('config/llm_config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    print(f"✅ Config loaded: {len(config)} sections")
    print(f"   - Model tiers: {list(config['model_tiers'].keys())}")
    print(f"   - Task mappings: {len(config['task_mapping'])} tasks")
except Exception as e:
    print(f"❌ Config error: {e}")
    exit(1)

print("\n✅ Configuration verified successfully!")
EOF
```

Run verification:

```bash
cd /home/max/code/mas-memory-layer
python scripts/verify_llm_config.py
```

---

## 5. Code Implementation

### Step 1: Create LLM Client Wrapper

Create `src/utils/llm_client.py`:

```python
"""
LLM client with AgentRouter integration and multi-tier model selection.

This module provides a unified interface for LLM operations across the memory
lifecycle engines. It supports:
- Multi-tier model selection (Budget, Balanced, Premium)
- Circuit breaker pattern for resilience
- Cost tracking and monitoring
- Async operations for performance

See ADR-005 for architecture decisions and model selection strategy.
"""

from typing import Optional, Dict, Any, List, Union
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
import os
import json
import yaml
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class LLMConfig:
    """Configuration loader for LLM settings."""
    
    def __init__(self, config_path: str = "config/llm_config.yaml"):
        self.config_path = config_path
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f)
            logger.info(f"Loaded LLM config from {self.config_path}")
        except FileNotFoundError:
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            self._config = self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Default configuration if file not found."""
        return {
            'llm': {
                'provider': 'agentrouter',
                'base_url': 'https://agentrouter.org/v1',
                'timeout_seconds': 30,
                'max_retries': 3
            },
            'model_tiers': {
                'tier_1': {'default': 'gpt-5-mini'},
                'tier_2': {'default': 'deepseek-v3'},
                'tier_3': {'default': 'gpt-5'}
            }
        }
    
    def get_model_for_task(self, task_type: str) -> str:
        """Get model name for a specific task type."""
        # First check task_mapping for tier
        task_mapping = self._config.get('task_mapping', {})
        tier = task_mapping.get(task_type)
        
        if tier:
            # Get model from tier
            tier_config = self._config['model_tiers'].get(tier, {})
            model = tier_config.get(task_type) or tier_config.get('default')
            if model:
                return model
        
        # Fallback: check all tiers
        for tier_name, tier_config in self._config['model_tiers'].items():
            if task_type in tier_config:
                return tier_config[task_type]
        
        # Ultimate fallback: tier_2 default (balanced)
        return self._config['model_tiers']['tier_2']['default']
    
    def get_llm_settings(self) -> Dict[str, Any]:
        """Get LLM connection settings."""
        return self._config.get('llm', {})


class CostTracker:
    """Track and log LLM usage costs."""
    
    # Pricing per 1M tokens (blended input:output 3:1 ratio)
    PRICING = {
        'gpt-5-mini': 0.325,
        'claude-3-5-haiku': 1.00,
        'gemini-2.5-flash': 0.195,
        'deepseek-v3': 0.38,
        'glm-4.6': 0.31,
        'gpt-5': 3.44,
        'claude-3-5-sonnet': 6.00
    }
    
    def __init__(self, log_file: str = "logs/llm_costs.json"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.daily_costs = {}
    
    def record_usage(
        self,
        model: str,
        task_type: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Record token usage and calculate cost."""
        total_tokens = input_tokens + output_tokens
        cost_per_million = self.PRICING.get(model, 1.0)  # Default if model unknown
        cost = (total_tokens / 1_000_000) * cost_per_million
        
        # Log to file
        today = datetime.now().strftime("%Y-%m-%d")
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'date': today,
            'model': model,
            'task_type': task_type,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'cost_usd': round(cost, 6)
        }
        
        self._append_to_log(log_entry)
        
        # Update daily total
        if today not in self.daily_costs:
            self.daily_costs[today] = 0.0
        self.daily_costs[today] += cost
        
        logger.info(f"LLM usage: {model} | {task_type} | {total_tokens} tokens | ${cost:.6f}")
        
        return cost
    
    def _append_to_log(self, entry: Dict[str, Any]):
        """Append entry to log file."""
        try:
            # Read existing log
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # Append new entry
            logs.append(entry)
            
            # Write back
            with open(self.log_file, 'w') as f:
                json.dump(logs, f, indent=2)
        
        except Exception as e:
            logger.error(f"Error writing cost log: {e}")
    
    def get_daily_cost(self, date: Optional[str] = None) -> float:
        """Get total cost for a specific date."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self.daily_costs.get(date, 0.0)
    
    def check_budget_alert(self, daily_budget: float = 3.0) -> bool:
        """Check if daily budget exceeded."""
        today_cost = self.get_daily_cost()
        if today_cost > daily_budget:
            logger.warning(f"⚠️ Daily budget exceeded: ${today_cost:.2f} > ${daily_budget:.2f}")
            return True
        return False


class LLMClient:
    """
    Unified LLM client with multi-tier model selection and cost tracking.
    
    Usage:
        client = LLMClient()
        
        # Automatic model selection by task
        facts = await client.extract_facts(turns, task_type='fact_extraction')
        
        # Explicit model selection
        score = await client.score_certainty(fact, model='gpt-5-mini')
        
        # Custom prompts
        response = await client.generate(prompt, model='gpt-5')
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        config_path: str = "config/llm_config.yaml"
    ):
        """
        Initialize LLM client.
        
        Args:
            api_key: AgentRouter API key (defaults to env var)
            config_path: Path to configuration file
        """
        self.api_key = api_key or os.getenv("AGENTROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("AGENTROUTER_API_KEY not set in environment")
        
        self.config = LLMConfig(config_path)
        self.cost_tracker = CostTracker()
        self.settings = self.config.get_llm_settings()
        self.base_url = self.settings.get('base_url', 'https://agentrouter.org/v1')
        
        # Cache clients per model
        self._clients: Dict[str, ChatOpenAI] = {}
        
        logger.info(f"Initialized LLMClient with provider: {self.settings.get('provider')}")
    
    def get_client(
        self,
        model: str,
        temperature: float = 0.3,
        **kwargs
    ) -> ChatOpenAI:
        """
        Get or create LangChain ChatOpenAI client for model.
        
        Args:
            model: Model identifier (e.g., 'gpt-5-mini', 'deepseek-v3')
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Additional parameters for ChatOpenAI
        
        Returns:
            Configured ChatOpenAI client
        """
        cache_key = f"{model}_{temperature}"
        
        if cache_key not in self._clients:
            self._clients[cache_key] = ChatOpenAI(
                model=model,
                api_key=self.api_key,
                base_url=self.base_url,
                temperature=temperature,
                timeout=self.settings.get('timeout_seconds', 30),
                max_retries=self.settings.get('max_retries', 3),
                **kwargs
            )
            logger.debug(f"Created new client for {model} (temp={temperature})")
        
        return self._clients[cache_key]
    
    async def generate(
        self,
        prompt: Union[str, List[BaseMessage]],
        model: Optional[str] = None,
        task_type: str = "general",
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = None
    ) -> str:
        """
        Generate text completion.
        
        Args:
            prompt: User prompt (string or list of messages)
            model: Model to use (defaults to task-based selection)
            task_type: Task type for automatic model selection
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            system_message: System message to prepend
        
        Returns:
            Generated text
        """
        # Select model if not specified
        if model is None:
            model = self.config.get_model_for_task(task_type)
        
        # Get client
        client_kwargs = {}
        if max_tokens:
            client_kwargs['max_tokens'] = max_tokens
        
        client = self.get_client(model, temperature, **client_kwargs)
        
        # Build messages
        if isinstance(prompt, str):
            messages = []
            if system_message:
                messages.append(SystemMessage(content=system_message))
            messages.append(HumanMessage(content=prompt))
        else:
            messages = prompt
        
        # Generate
        try:
            response = await client.ainvoke(messages)
            
            # Track cost
            # Note: Actual token counts should come from response.usage
            # This is simplified; LangChain response includes usage metadata
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                self.cost_tracker.record_usage(
                    model=model,
                    task_type=task_type,
                    input_tokens=usage.get('input_tokens', 0),
                    output_tokens=usage.get('output_tokens', 0)
                )
            
            return response.content
        
        except Exception as e:
            logger.error(f"LLM generation failed: {model} | {task_type} | {e}")
            raise
    
    async def extract_facts(
        self,
        turns: List[str],
        model: Optional[str] = None,
        temperature: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Extract structured facts from conversation turns.
        
        Args:
            turns: List of conversation turn contents
            model: Model to use (defaults to fact_extraction task model)
            temperature: Sampling temperature
        
        Returns:
            List of extracted facts as dictionaries
        """
        # Build prompt
        turns_text = "\n".join([f"Turn {i+1}: {t}" for i, t in enumerate(turns)])
        
        prompt = f"""Extract structured facts from these conversation turns. Return JSON array.

{turns_text}

Return JSON array with format:
[
  {{
    "fact_type": "preference|constraint|entity|goal|metric|mention",
    "content": "fact statement in natural language",
    "certainty": 0.0-1.0,
    "entities": ["entity1", "entity2"]
  }}
]

If no facts found, return empty array [].
Extract only clear, significant facts. Avoid noise."""
        
        response = await self.generate(
            prompt=prompt,
            model=model,
            task_type='fact_extraction',
            temperature=temperature,
            system_message="You are a fact extraction assistant. Extract only significant, clear facts from conversations."
        )
        
        # Parse JSON response
        return self._parse_json_response(response)
    
    async def score_certainty(
        self,
        fact: str,
        model: Optional[str] = None
    ) -> float:
        """
        Score certainty of a fact (CIAR component).
        
        Args:
            fact: Fact statement to score
            model: Model to use (defaults to ciar_scoring task model)
        
        Returns:
            Certainty score (0.0-1.0)
        """
        prompt = f"""Rate the certainty/confidence of this fact on a scale of 0.0-1.0.

Fact: "{fact}"

Consider:
- 1.0 = Explicitly stated, definitive
- 0.7-0.9 = Clearly implied, high confidence
- 0.4-0.6 = Inferred, moderate confidence
- 0.0-0.3 = Speculation, low confidence

Return ONLY a number between 0.0 and 1.0, nothing else."""
        
        response = await self.generate(
            prompt=prompt,
            model=model,
            task_type='ciar_certainty_scoring',
            temperature=0.0  # Deterministic for scoring
        )
        
        # Parse float
        try:
            score = float(response.strip())
            return max(0.0, min(1.0, score))  # Clamp to [0, 1]
        except ValueError:
            logger.warning(f"Failed to parse certainty score: {response}, defaulting to 0.6")
            return 0.6  # Default moderate confidence
    
    async def summarize_episode(
        self,
        facts: List[Dict[str, Any]],
        model: Optional[str] = None,
        max_length: int = 500
    ) -> str:
        """
        Generate narrative summary of episode from facts.
        
        Args:
            facts: List of fact dictionaries
            model: Model to use (defaults to episode_summary task model)
            max_length: Maximum summary length in characters
        
        Returns:
            Episode summary text
        """
        # Format facts
        facts_text = "\n".join([
            f"- [{f['fact_type']}] {f['content']}"
            for f in facts
        ])
        
        prompt = f"""Create a coherent narrative summary of these facts (max {max_length} chars):

{facts_text}

Write a concise, natural language summary that connects these facts into a coherent episode.
Focus on the most important information and relationships between facts."""
        
        response = await self.generate(
            prompt=prompt,
            model=model,
            task_type='episode_summarization',
            temperature=0.5,  # Slightly creative for narrative
            system_message="You are a summarization assistant. Create coherent, concise summaries."
        )
        
        # Trim to max length
        return response[:max_length] if len(response) > max_length else response
    
    async def synthesize_knowledge(
        self,
        episodes: List[Dict[str, Any]],
        model: Optional[str] = None
    ) -> str:
        """
        Synthesize general knowledge from multiple episodes.
        
        Args:
            episodes: List of episode dictionaries with 'summary' field
            model: Model to use (defaults to knowledge_synthesis task model)
        
        Returns:
            Synthesized knowledge statement
        """
        episodes_text = "\n\n".join([
            f"Episode {i+1} ({ep.get('session_id', 'unknown')}):\n{ep.get('summary', 'No summary')}"
            for i, ep in enumerate(episodes)
        ])
        
        prompt = f"""Identify common patterns across these episodes and synthesize general knowledge:

{episodes_text}

Generate a concise knowledge statement (2-3 sentences) that captures:
1. Recurring themes or patterns
2. Generalizable insights
3. Actionable knowledge

Focus on what can be learned across all episodes, not specific details."""
        
        response = await self.generate(
            prompt=prompt,
            model=model,
            task_type='knowledge_synthesis',
            temperature=0.5,
            system_message="You are a knowledge synthesis assistant. Identify patterns and generate actionable insights."
        )
        
        return response
    
    def _parse_json_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse JSON from LLM response.
        
        Handles:
        - JSON wrapped in markdown code blocks
        - Malformed JSON with recovery attempts
        - Empty/invalid responses
        
        Args:
            response: Raw LLM response text
        
        Returns:
            Parsed JSON as list of dicts (empty list if parse fails)
        """
        try:
            # Handle markdown code blocks
            content = response.strip()
            
            if "```json" in content:
                # Extract JSON from markdown
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                # Generic code block
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1].strip()
            
            # Parse JSON
            parsed = json.loads(content)
            
            # Ensure it's a list
            if isinstance(parsed, dict):
                return [parsed]
            elif isinstance(parsed, list):
                return parsed
            else:
                logger.warning(f"Unexpected JSON type: {type(parsed)}")
                return []
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e} | Response: {response[:200]}")
            return []
        
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return []
    
    def get_daily_cost(self) -> float:
        """Get total cost for today."""
        return self.cost_tracker.get_daily_cost()
    
    def check_budget(self, daily_budget: float = 3.0) -> bool:
        """Check if daily budget exceeded."""
        return self.cost_tracker.check_budget_alert(daily_budget)


# Convenience function for simple usage
async def extract_facts_simple(turns: List[str]) -> List[Dict[str, Any]]:
    """
    Simple function to extract facts without managing client lifecycle.
    
    Usage:
        facts = await extract_facts_simple(["User prefers Hamburg", "Budget is 50k"])
    """
    client = LLMClient()
    return await client.extract_facts(turns)
```

### Step 2: Test the Implementation

Create test script `scripts/test_llm_client.py`:

```python
"""
Test script for LLM client with AgentRouter.
Run this to verify integration before using in production.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.llm_client import LLMClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_fact_extraction():
    """Test fact extraction with sample turns."""
    print("\n" + "="*60)
    print("TEST 1: Fact Extraction")
    print("="*60)
    
    client = LLMClient()
    
    turns = [
        "User: I need to ship containers to Hamburg port",
        "Agent: Hamburg Port has good capacity this week",
        "User: Great, my budget is 50000 euros",
        "Agent: That should be sufficient for 20 containers"
    ]
    
    print(f"\nInput turns: {len(turns)}")
    for turn in turns:
        print(f"  - {turn}")
    
    print("\nExtracting facts...")
    facts = await client.extract_facts(turns)
    
    print(f"\nExtracted {len(facts)} facts:")
    for i, fact in enumerate(facts, 1):
        print(f"\n  Fact {i}:")
        print(f"    Type: {fact.get('fact_type')}")
        print(f"    Content: {fact.get('content')}")
        print(f"    Certainty: {fact.get('certainty')}")
        print(f"    Entities: {fact.get('entities')}")
    
    print(f"\nDaily cost so far: ${client.get_daily_cost():.4f}")
    
    return facts


async def test_certainty_scoring():
    """Test CIAR certainty scoring."""
    print("\n" + "="*60)
    print("TEST 2: Certainty Scoring")
    print("="*60)
    
    client = LLMClient()
    
    test_facts = [
        ("User explicitly stated preference for Hamburg port", 0.9),
        ("User might prefer morning deliveries", 0.5),
        ("It seems the budget could be flexible", 0.3),
    ]
    
    print("\nScoring facts...")
    for fact, expected in test_facts:
        score = await client.score_certainty(fact)
        status = "✅" if abs(score - expected) < 0.2 else "⚠️"
        print(f"\n  {status} Fact: {fact}")
        print(f"     Score: {score:.2f} (expected ~{expected:.2f})")
    
    print(f"\nDaily cost so far: ${client.get_daily_cost():.4f}")


async def test_episode_summary():
    """Test episode summarization."""
    print("\n" + "="*60)
    print("TEST 3: Episode Summarization")
    print("="*60)
    
    client = LLMClient()
    
    facts = [
        {"fact_type": "entity", "content": "Hamburg Port mentioned"},
        {"fact_type": "preference", "content": "User prefers Hamburg for European shipping"},
        {"fact_type": "constraint", "content": "Budget limit is 50000 euros"},
        {"fact_type": "metric", "content": "Capacity for 20 containers available"}
    ]
    
    print("\nInput facts:")
    for fact in facts:
        print(f"  - [{fact['fact_type']}] {fact['content']}")
    
    print("\nGenerating summary...")
    summary = await client.summarize_episode(facts)
    
    print(f"\nGenerated summary:")
    print(f"  {summary}")
    
    print(f"\nDaily cost so far: ${client.get_daily_cost():.4f}")


async def test_all_models():
    """Test all 7 models to verify availability."""
    print("\n" + "="*60)
    print("TEST 4: Model Availability Check")
    print("="*60)
    
    client = LLMClient()
    
    models = [
        ('gpt-5-mini', 'tier_1'),
        ('claude-3-5-haiku', 'tier_1'),
        ('gemini-2.5-flash', 'tier_1'),
        ('deepseek-v3', 'tier_2'),
        ('glm-4.6', 'tier_2'),
        ('gpt-5', 'tier_3'),
        ('claude-3-5-sonnet', 'tier_3'),
    ]
    
    test_prompt = "Say 'OK' if you can read this."
    
    results = []
    for model, tier in models:
        print(f"\n  Testing {model} ({tier})...", end=" ")
        try:
            response = await client.generate(
                prompt=test_prompt,
                model=model,
                temperature=0.0
            )
            print(f"✅ Response: {response[:50]}")
            results.append((model, True))
        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}")
            results.append((model, False))
    
    print(f"\n  Summary:")
    success_count = sum(1 for _, success in results if success)
    print(f"    {success_count}/{len(results)} models available")
    
    print(f"\nTotal cost for all tests: ${client.get_daily_cost():.4f}")
    
    return all(success for _, success in results)


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("AgentRouter LLM Client Integration Test")
    print("="*60)
    
    try:
        # Test 1: Fact extraction
        await test_fact_extraction()
        
        # Test 2: Certainty scoring
        await test_certainty_scoring()
        
        # Test 3: Episode summary
        await test_episode_summary()
        
        # Test 4: Model availability
        all_success = await test_all_models()
        
        # Final summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        if all_success:
            print("✅ All tests passed!")
            print("✅ All models are available")
            print("✅ Integration is working correctly")
            print("\n🚀 Ready to proceed with Phase 2 implementation")
            return 0
        else:
            print("⚠️ Some tests failed")
            print("⚠️ Check error messages above")
            print("\n🔧 Troubleshooting needed before proceeding")
            return 1
    
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
```

---

## 6. Model Selection Guide

### Quick Reference Table

| Task | Recommended Model | Tier | Cost/1M | Rationale |
|------|------------------|------|---------|-----------|
| **CIAR Certainty** | GPT-5 Mini | 1 | $0.33 | Fast classification, high volume |
| **Entity Extraction** | Claude 3.5 Haiku | 1 | $1.00 | Accurate NER, fast |
| **Fact Extraction** | DeepSeek-V3 | 2 | $0.38 | Best balance cost/quality |
| **Episode Summary** | GLM-4.6 | 2 | $0.31 | Good narrative generation |
| **Relationship Inference** | DeepSeek-V3 | 2 | $0.38 | Structured output |
| **Knowledge Synthesis** | GPT-5 | 3 | $3.44 | Complex reasoning |
| **Critical Accuracy** | Claude 3.5 Sonnet | 3 | $6.00 | Best instruction following |

### Decision Tree

```
Is this a high-frequency operation (>100/day)?
├─ YES: Use Tier 1 (Budget)
│   └─ Simple classification? → GPT-5 Mini
│   └─ Need entity extraction? → Claude 3.5 Haiku
│   └─ Large context (>100K)? → Gemini 2.5 Flash
│
└─ NO: Moderate frequency (<100/day)?
    ├─ YES: Use Tier 2 (Balanced)
    │   └─ Fact extraction? → DeepSeek-V3
    │   └─ Summarization? → GLM-4.6
    │
    └─ NO: Low frequency, high importance?
        └─ Use Tier 3 (Premium)
            └─ Complex reasoning? → GPT-5
            └─ Instruction following? → Claude 3.5 Sonnet
```

### Task-to-Model Examples

```python
# Example model selections in code

# Week 4: CIAR Scoring
certainty = await llm_client.score_certainty(
    fact="User prefers Hamburg",
    model="gpt-5-mini"  # Tier 1: Fast, cheap scoring
)

# Week 5: Fact Extraction  
facts = await llm_client.extract_facts(
    turns=[...],
    model="deepseek-v3"  # Tier 2: Primary workload
)

# Week 7: Episode Summarization
summary = await llm_client.summarize_episode(
    facts=[...],
    model="glm-4.6"  # Tier 2: Good narrative quality
)

# Week 10: Knowledge Synthesis
knowledge = await llm_client.synthesize_knowledge(
    episodes=[...],
    model="gpt-5"  # Tier 3: Complex pattern recognition
)

# Critical extraction (when precision must be >95%)
critical_facts = await llm_client.extract_facts(
    turns=[...],
    model="claude-3.5-sonnet"  # Tier 3: Best accuracy
)
```

---

## 7. Testing & Validation

### Run Integration Tests

```bash
cd /home/max/code/mas-memory-layer

# 1. Verify configuration
python scripts/verify_llm_config.py

# 2. Run comprehensive test
python scripts/test_llm_client.py

# Expected output:
# ✅ All tests passed!
# ✅ All models are available
# Total cost: ~$0.05
```

### Validation Checklist

- [ ] API key loaded correctly
- [ ] Config file parsed successfully
- [ ] Fact extraction returns JSON array
- [ ] Certainty scores in range [0.0, 1.0]
- [ ] Episode summaries are coherent
- [ ] All 7 models respond successfully
- [ ] Cost tracking logs to file
- [ ] Total test cost < $0.10

### Quality Metrics

After running tests, manually review:

**Fact Extraction Quality:**
- Are extracted facts relevant? (>80% should be significant)
- Are fact types correct? (preference vs. entity vs. constraint)
- Are certainty scores reasonable? (should match human judgment ±0.2)

**Summary Quality:**
- Is summary coherent and readable?
- Does it capture main themes?
- Is length appropriate (~200-500 chars)?

---

## 8. Cost Monitoring

### Daily Monitoring Script

Create `scripts/check_llm_costs.py`:

```python
"""
Daily cost monitoring script.
Run this once per day to check LLM spending.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

def analyze_costs(log_file="logs/llm_costs.json"):
    """Analyze LLM costs from log file."""
    
    if not Path(log_file).exists():
        print(f"❌ Cost log not found: {log_file}")
        return
    
    with open(log_file, 'r') as f:
        logs = json.load(f)
    
    # Aggregate by date
    daily_costs = defaultdict(float)
    daily_tasks = defaultdict(lambda: defaultdict(int))
    daily_models = defaultdict(lambda: defaultdict(int))
    
    for entry in logs:
        date = entry['date']
        daily_costs[date] += entry['cost_usd']
        daily_tasks[date][entry['task_type']] += 1
        daily_models[date][entry['model']] += 1
    
    # Print report
    print("\n" + "="*60)
    print("LLM COST REPORT")
    print("="*60)
    
    # Today
    today = datetime.now().strftime("%Y-%m-%d")
    today_cost = daily_costs.get(today, 0.0)
    
    print(f"\nToday ({today}):")
    print(f"  Total: ${today_cost:.2f}")
    print(f"  Budget: $3.00")
    print(f"  Status: {'✅ Within budget' if today_cost < 3.0 else '⚠️ OVER BUDGET'}")
    
    if today in daily_tasks:
        print(f"\n  Tasks:")
        for task, count in daily_tasks[today].items():
            print(f"    - {task}: {count} calls")
    
    # Last 7 days
    print(f"\nLast 7 days:")
    total_week = 0.0
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        cost = daily_costs.get(date, 0.0)
        total_week += cost
        print(f"  {date}: ${cost:.2f}")
    
    print(f"\n  Weekly total: ${total_week:.2f}")
    print(f"  Projected monthly: ${total_week * 4.3:.2f}")
    
    # Monthly projection
    if total_week > 0:
        projected_monthly = total_week * 4.3
        budget_status = "✅ Within budget" if projected_monthly < 80.0 else "⚠️ Over budget"
        print(f"\n  Monthly budget: $80.00")
        print(f"  Status: {budget_status}")
    
    # Top tasks
    print(f"\nMost expensive tasks (last 7 days):")
    task_costs = defaultdict(float)
    for entry in logs:
        if entry['date'] in [
            (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(7)
        ]:
            task_costs[entry['task_type']] += entry['cost_usd']
    
    for task, cost in sorted(task_costs.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  - {task}: ${cost:.2f}")

if __name__ == "__main__":
    analyze_costs()
```

### Set Up Cron Job (Optional)

```bash
# Add to crontab for daily reports
crontab -e

# Add this line (runs daily at 9 AM):
0 9 * * * cd /home/max/code/mas-memory-layer && python scripts/check_llm_costs.py >> logs/daily_cost_reports.txt 2>&1
```

### Budget Alerts

Configure alerts in `config/llm_config.yaml`:

```yaml
cost_monitoring:
  enabled: true
  daily_budget_usd: 3.00
  monthly_budget_usd: 80.00
  alert_threshold_percent: 80  # Alert at 80% of budget
  alert_email: your-email@example.com  # Optional
```

---

## 9. Error Handling

### Common Errors and Solutions

#### Error: "AGENTROUTER_API_KEY not set"

**Cause:** API key not in environment

**Solution:**
```bash
# Check if .env file exists and has key
grep AGENTROUTER_API_KEY .env

# If missing, add it
echo "AGENTROUTER_API_KEY=ar_your_key_here" >> .env

# Reload environment
source .env  # or restart terminal
```

#### Error: "Timeout waiting for response"

**Cause:** LLM request took >30 seconds

**Solution:**
```python
# Increase timeout in config
llm:
  timeout_seconds: 60  # Increase from 30 to 60
```

Or catch and handle:
```python
try:
    response = await llm_client.generate(prompt)
except TimeoutError:
    logger.warning("LLM timeout, using fallback")
    response = fallback_method()
```

#### Error: "Rate limit exceeded"

**Cause:** Too many requests in short time

**Solution:**
```python
import asyncio

# Add delay between requests
for session in sessions:
    facts = await extract_facts(session)
    await asyncio.sleep(1)  # 1 second delay
```

#### Error: "Invalid JSON in response"

**Cause:** LLM didn't return valid JSON

**Solution:**
```python
# Already handled in _parse_json_response()
# Returns empty list [] on parse failure
# Check logs for details:
logger.error(f"JSON parse error: {response[:200]}")
```

#### Error: "Model not found"

**Cause:** Typo in model name or model deprecated

**Solution:**
```python
# Check available models
curl https://agentrouter.org/v1/models \
  -H "Authorization: Bearer $AGENTROUTER_API_KEY"

# Update config with correct model name
```

### Circuit Breaker Integration

When implementing Week 5 circuit breaker:

```python
from src.memory.circuit_breaker import CircuitBreaker

class FactExtractorWithCircuitBreaker:
    def __init__(self, llm_client, circuit_breaker):
        self.llm = llm_client
        self.cb = circuit_breaker
    
    async def extract_facts(self, turns):
        # Check circuit breaker
        if self.cb.is_open():
            logger.warning("Circuit breaker open, using fallback")
            return self._rule_based_extraction(turns)
        
        try:
            # Try LLM extraction
            facts = await self.llm.extract_facts(turns)
            self.cb.record_success()
            return facts
        
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            self.cb.record_failure()
            
            # Fallback to rule-based
            return self._rule_based_extraction(turns)
```

---

## 10. Troubleshooting

### Debug Mode

Enable debug logging:

```python
# At top of your script
import logging
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Check API Connectivity

```bash
# Test API directly
curl https://agentrouter.org/v1/chat/completions \
  -H "Authorization: Bearer $AGENTROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5-mini",
    "messages": [{"role": "user", "content": "Say OK"}]
  }'

# Expected: {"choices":[{"message":{"content":"OK"}}],...}
```

### Inspect Cost Logs

```bash
# View recent costs
tail -n 50 logs/llm_costs.json | python -m json.tool

# Count requests per model
jq '.[] | .model' logs/llm_costs.json | sort | uniq -c
```

### Test Individual Models

```python
# Test specific model in isolation
import asyncio
from src.utils.llm_client import LLMClient

async def test_model(model_name):
    client = LLMClient()
    response = await client.generate(
        prompt="Say 'Working!' if you can read this.",
        model=model_name
    )
    print(f"{model_name}: {response}")

# Run
asyncio.run(test_model("deepseek-v3"))
```

### Common Issues Checklist

- [ ] API key correct and not expired?
- [ ] `.env` file in project root?
- [ ] `config/llm_config.yaml` exists and valid?
- [ ] Internet connectivity working?
- [ ] Python 3.9+ installed?
- [ ] All dependencies installed (`pip install -r requirements.txt`)?
- [ ] Firewall allowing outbound HTTPS?

---

## 11. Production Checklist

### Before Phase 2 Implementation

- [ ] API key obtained and stored securely
- [ ] `.env` file configured and gitignored
- [ ] `config/llm_config.yaml` created
- [ ] All dependencies installed
- [ ] Integration tests passing (`scripts/test_llm_client.py`)
- [ ] All 7 models available and responding
- [ ] Cost tracking working (logs/llm_costs.json created)
- [ ] Test costs < $0.10

### Week 4 (CIAR Scorer)

- [ ] LLMClient integrated into `src/memory/ciar_scorer.py`
- [ ] Certainty scoring using GPT-5 Mini (Tier 1)
- [ ] Impact scoring using GPT-5 Mini (Tier 1)
- [ ] Fallback to heuristics if LLM fails
- [ ] Unit tests with mocked LLM responses

### Week 5 (Fact Extractor & Promotion)

- [ ] LLMClient integrated into `src/memory/fact_extractor.py`
- [ ] Primary extraction using DeepSeek-V3 (Tier 2)
- [ ] Circuit breaker implemented and tested
- [ ] Rule-based fallback working
- [ ] Processing state tracked in Redis
- [ ] Metrics collected (success rate, latency, cost)

### Week 6-11 (Consolidation & Distillation)

- [ ] Episode summarization using GLM-4.6 (Tier 2)
- [ ] Knowledge synthesis using GPT-5 (Tier 3)
- [ ] Batch processing optimized
- [ ] Cost staying within $60-80/month
- [ ] Quality metrics tracked

### Production Deployment

- [ ] Feature flags configured for gradual rollout
- [ ] Monitoring dashboards set up
- [ ] Cost alerts configured
- [ ] Backup/rollback plan documented
- [ ] Error handling tested with all failure modes
- [ ] Documentation updated with lessons learned

---

## 12. Support & Resources

### Documentation

- **ADR-005:** [Multi-Tier LLM Provider Strategy](../ADR/005-multi-tier-llm-provider-strategy.md)
- **Implementation Plan:** [Phase 2 Week 4-5](../plan/implementation-plan-02112025.md)
- **AgentRouter Docs:** https://agentrouter.org/docs
- **LangChain Docs:** https://python.langchain.com/docs

### Code Examples

- **LLM Client:** `src/utils/llm_client.py`
- **Test Script:** `scripts/test_llm_client.py`
- **Cost Monitor:** `scripts/check_llm_costs.py`
- **Configuration:** `config/llm_config.yaml`

### Getting Help

**For AgentRouter Issues:**
- Dashboard: https://agentrouter.org/dashboard
- Support: support@agentrouter.org
- Status page: https://status.agentrouter.org

**For Project Issues:**
- Check implementation plan: `docs/plan/implementation-plan-02112025.md`
- Review ADR-005: `docs/ADR/005-multi-tier-llm-provider-strategy.md`
- Consult Phase 2 spec: `docs/specs/spec-phase2-memory-tiers.md`

---

## Changelog

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-11-02 | 1.0 | Initial integration guide | Development Team |

---

**Next Steps:**
1. Complete account setup (Section 3)
2. Configure environment (Section 4)
3. Run integration tests (Section 7)
4. Begin Week 4 implementation (CIAR Scorer)

Good luck with Phase 2 implementation! 🚀
