# file: memory_system.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional, Callable
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime
import uuid
import redis
import json

# --- Data Schemas for Operating Memory (Data Contracts) ---

class PersonalMemoryState(BaseModel):
    """
    Schema for an agent's private scratchpad.
    This entire object is serialized to JSON and stored under a single Redis key.
    """
    agent_id: str
    current_task_id: Optional[str] = None
    # Intermediate thoughts, calculations, or API results
    scratchpad: Dict[str, Any] = Field(default_factory=dict)
    # Data being evaluated for promotion according to the CIAR model
    promotion_candidates: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class SharedWorkspaceState(BaseModel):
    """
    Schema for the shared workspace, representing a collaborative event.
    This entire object is serialized to JSON and stored under a single Redis key.
    """
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex}")
    status: Literal["active", "resolved", "cancelled"] = "active"
    # The core, shared facts and state data for the event
    shared_data: Dict[str, Any] = Field(default_factory=dict)
    # Log of agents who have contributed to this event
    participating_agents: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

# --- Abstract Interface for the Memory System ---

class HybridMemorySystem(ABC):
    """
    Abstract base class defining the contract for our hybrid memory system.
    Agents will interact with this interface, not the raw Redis client.
    """

    @abstractmethod
    def get_personal_state(self, agent_id: str) -> PersonalMemoryState:
        """Retrieves the full personal state for a given agent."""
        pass

    @abstractmethod
    def update_personal_state(self, state: PersonalMemoryState) -> None:
        """Overwrites the personal state for a given agent."""
        pass

    @abstractmethod
    def get_shared_state(self, event_id: str) -> SharedWorkspaceState:
        """Retrieves the full state of a shared event."""
        pass

    @abstractmethod
    def update_shared_state(self, state: SharedWorkspaceState) -> None:
        """Overwrites the state of a shared event."""
        pass
    
    @abstractmethod
    def publish_update(self, event_id: str, update_summary: Dict) -> None:
        """Publishes a notification that a shared event has been updated."""
        pass

# --- Concrete Redis Implementation ---

class RedisHybridMemorySystem(HybridMemorySystem):
    """
    A concrete implementation of the HybridMemorySystem using Redis as the backend.
    """
    
    def __init__(self, redis_client: redis.StrictRedis):
        """
        Initializes the memory system with a connected Redis client.

        Args:
            redis_client: An instance of redis.StrictRedis.
        """
        self.client = redis_client
        try:
            # Verify the connection is alive
            if not self.client.ping():
                raise ConnectionError("Could not connect to Redis.")
        except redis.exceptions.ConnectionError as e:
            print(f"Error connecting to Redis: {e}")
            raise

    def _get_personal_key(self, agent_id: str) -> str:
        return f"personal_state:{agent_id}"

    def _get_shared_key(self, event_id: str) -> str:
        return f"shared_state:{event_id}"

    def _get_channel_key(self, event_id: str) -> str:
        return f"channel:shared_state:{event_id}"

    def get_personal_state(self, agent_id: str) -> PersonalMemoryState:
        key = self._get_personal_key(agent_id)
        raw_state = self.client.get(key)
        
        if raw_state is None:
            # If no state exists, create a new default state
            return PersonalMemoryState(agent_id=agent_id)
        
        try:
            return PersonalMemoryState.model_validate_json(raw_state)
        except ValidationError as e:
            print(f"Data validation error for agent '{agent_id}': {e}")
            # In a production system, you might want to handle this corruption
            # (e.g., by archiving the bad data and returning a fresh state).
            return PersonalMemoryState(agent_id=agent_id)

    def update_personal_state(self, state: PersonalMemoryState) -> None:
        key = self._get_personal_key(state.agent_id)
        state.last_updated = datetime.utcnow()
        # Use Pydantic's method for safe JSON serialization
        serialized_state = state.model_dump_json()
        self.client.set(key, serialized_state)

    def get_shared_state(self, event_id: str) -> SharedWorkspaceState:
        key = self._get_shared_key(event_id)
        raw_state = self.client.get(key)
        
        if raw_state is None:
            # Unlike personal state, a request for a non-existent shared event
            # is typically an error.
            raise KeyError(f"No shared workspace found for event_id: {event_id}")
            
        try:
            return SharedWorkspaceState.model_validate_json(raw_state)
        except ValidationError as e:
            print(f"Data validation error for event '{event_id}': {e}")
            raise ValueError(f"Corrupted data for event_id: {event_id}") from e

    def update_shared_state(self, state: SharedWorkspaceState) -> None:
        key = self._get_shared_key(state.event_id)
        state.last_updated = datetime.utcnow()
        serialized_state = state.model_dump_json()
        self.client.set(key, serialized_state)
        
        # After updating state, publish a notification
        update_summary = {
            "event_id": state.event_id,
            "status": state.status,
            "last_updated_by": state.participating_agents[-1] if state.participating_agents else "system"
        }
        self.publish_update(state.event_id, update_summary)


    def publish_update(self, event_id: str, update_summary: Dict) -> None:
        channel = self._get_channel_key(event_id)
        message = json.dumps(update_summary)
        self.client.publish(channel, message)


if __name__ == '__main__':
    # --- Example Usage ---
    
    print("--- Phase 3: Implementation & Prototyping Demo ---")
    
    # 1. Connect to a local Redis instance (ensure Redis is running)
    try:
        redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
        redis_client.ping()
        print("Successfully connected to Redis.")
    except redis.exceptions.ConnectionError as e:
        print(f"Could not connect to Redis. Please ensure it is running on localhost:6379. Error: {e}")
        exit()
        
    # 2. Instantiate the memory system
    memory = RedisHybridMemorySystem(redis_client)
    
    # 3. Simulate an Agent's Personal Workflow
    agent_id = "port_agent_007"
    print(f"\n--- Simulating workflow for agent: {agent_id} ---")

    # Get initial state (will be created on the fly)
    personal_state = memory.get_personal_state(agent_id)
    print(f"Initial personal state retrieved: {personal_state.model_dump_json(indent=2)}")
    
    # Update the scratchpad
    personal_state.scratchpad["congestion_level"] = 0.85
    personal_state.scratchpad["berth_availability"] = {"B7": "free", "B8": "occupied"}
    personal_state.promotion_candidates["delay_hypothesis"] = {"vessel_id": "V-123", "confidence": 0.7}
    
    # Save the updated state
    memory.update_personal_state(personal_state)
    print("Personal state updated in Redis.")

    # Retrieve and verify the state
    retrieved_state = memory.get_personal_state(agent_id)
    print(f"Retrieved updated state: {retrieved_state.model_dump_json(indent=2)}")
    assert retrieved_state.scratchpad["congestion_level"] == 0.85

    # 4. Simulate a Collaborative Workflow
    print("\n--- Simulating collaborative workflow ---")
    
    # An agent decides to promote a hypothesis, creating a new shared event
    new_event = SharedWorkspaceState() # Pydantic model creates default event_id
    new_event.shared_data["initial_alert"] = "Potential 6-hour delay for Vessel V-123"
    new_event.participating_agents.append(agent_id)

    # Note: A real system would have CIAR/EPDL logic here. We simulate the outcome.
    print(f"Agent {agent_id} created a new shared event: {new_event.event_id}")
    
    # Update state (which also publishes an update)
    memory.update_shared_state(new_event)
    print("Shared event created and update published.")

    # Another agent contributes
    event_id = new_event.event_id
    shared_state = memory.get_shared_state(event_id)
    
    customs_agent_id = "customs_agent_001"
    shared_state.shared_data["customs_hold"] = True
    shared_state.shared_data["reason"] = "Secondary inspection required"
    shared_state.participating_agents.append(customs_agent_id)

    memory.update_shared_state(shared_state)
    print(f"Agent {customs_agent_id} contributed to the event.")
    
    # Retrieve and verify final shared state
    final_shared_state = memory.get_shared_state(event_id)
    print(f"Final shared state: {final_shared_state.model_dump_json(indent=2)}")
    assert final_shared_state.shared_data["customs_hold"] is True
    
    # (Optional) To see pub/sub in action, you would need a separate script
    # running a subscriber loop on the channel: "channel:shared_state:<event_id>"