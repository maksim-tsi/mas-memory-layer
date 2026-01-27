"""
MAS-specific ToolRuntime wrapper for LangChain agent tools.

Provides convenient access to MAS Memory Layer components via
the LangChain ToolRuntime pattern (ADR-007).
"""

from typing import Optional, Any, Dict, TYPE_CHECKING, TypedDict, Annotated, List
from dataclasses import dataclass
import inspect

from langgraph.graph import add_messages

if TYPE_CHECKING:
    # For type hints only
    from langchain_core.tools import ToolRuntime as LangChainToolRuntime
else:
    LangChainToolRuntime = Any


@dataclass
class MASContext:
    """
    Immutable context for MAS agent tools.
    
    This is passed via ToolRuntime.context and contains
    infrastructure IDs and configuration that should NOT
    be exposed to the LLM.
    """
    session_id: str
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    agent_id: Optional[str] = None
    
    # Memory system reference (injected at runtime)
    memory_system: Optional[Any] = None  # Type: UnifiedMemorySystem
    
    # Configuration flags
    enable_l1_cache: bool = True
    enable_ciar_filtering: bool = True
    default_min_ciar: float = 0.6


class AgentState(TypedDict):
    """LangGraph state for MAS agents."""

    messages: Annotated[List[Dict[str, Any]], add_messages]
    session_id: str
    turn_id: int

    # Memory tier content
    active_context: List[str]
    working_facts: List[Any]
    episodic_chunks: List[str]
    entity_graph: Dict[str, Any]
    semantic_knowledge: List[Any]

    # Agent output
    response: str
    confidence: float


class MASToolRuntime:
    """
    Wrapper around LangChain's ToolRuntime providing MAS-specific helpers.
    
    This class provides convenience methods for accessing common MAS
    components while maintaining compatibility with LangChain's native
    ToolRuntime interface.
    
    Usage:
        @tool
        async def my_tool(arg: str, runtime: ToolRuntime) -> str:
            mas_runtime = MASToolRuntime(runtime)
            session_id = mas_runtime.get_session_id()
            memory = mas_runtime.get_memory_system()
            # ... use memory ...
    """
    
    def __init__(self, runtime: 'LangChainToolRuntime'):
        """
        Initialize MAS runtime wrapper.
        
        Args:
            runtime: LangChain ToolRuntime instance (auto-injected)
        """
        self._runtime = runtime
    
    @property
    def native_runtime(self) -> 'LangChainToolRuntime':
        """Access to underlying LangChain ToolRuntime."""
        return self._runtime
    
    # --- Context Access Methods ---
    
    def get_session_id(self) -> str:
        """
        Get current session ID from context.
        
        Returns:
            Session ID string
            
        Raises:
            KeyError: If session_id not found in context
        """
        context = self._runtime.context
        if isinstance(context, MASContext):
            return context.session_id
        # Fallback for dict-based context
        if hasattr(context, 'session_id'):
            return context.session_id
        raise KeyError("session_id not found in ToolRuntime.context")
    
    def get_user_id(self) -> Optional[str]:
        """
        Get current user ID from context.
        
        Returns:
            User ID string or None if not available
        """
        context = self._runtime.context
        if isinstance(context, MASContext):
            return context.user_id
        if hasattr(context, 'user_id'):
            return context.user_id
        return None
    
    def get_agent_id(self) -> Optional[str]:
        """
        Get current agent ID from context.
        
        Returns:
            Agent ID string or None if not available
        """
        context = self._runtime.context
        if isinstance(context, MASContext):
            return context.agent_id
        if hasattr(context, 'agent_id'):
            return context.agent_id
        return None
    
    def get_organization_id(self) -> Optional[str]:
        """
        Get current organization ID from context.
        
        Returns:
            Organization ID string or None if not available
        """
        context = self._runtime.context
        if isinstance(context, MASContext):
            return context.organization_id
        if hasattr(context, 'organization_id'):
            return context.organization_id
        return None
    
    def get_memory_system(self) -> Optional[Any]:
        """
        Get reference to UnifiedMemorySystem from context.
        
        Returns:
            UnifiedMemorySystem instance or None if not available
        """
        context = self._runtime.context
        if isinstance(context, MASContext):
            return context.memory_system
        if hasattr(context, 'memory_system'):
            return context.memory_system
        return None
    
    def get_config_flag(self, flag_name: str, default: Any = None) -> Any:
        """
        Get configuration flag from context.
        
        Args:
            flag_name: Name of the configuration flag
            default: Default value if flag not found
            
        Returns:
            Configuration value or default
        """
        context = self._runtime.context
        if isinstance(context, MASContext):
            return getattr(context, flag_name, default)
        if hasattr(context, flag_name):
            return getattr(context, flag_name)
        return default
    
    # --- State Access Methods ---
    
    def get_state_value(self, key: str, default: Any = None) -> Any:
        """
        Get value from mutable graph state.
        
        Args:
            key: State key name
            default: Default value if key not found
            
        Returns:
            State value or default
        """
        return self._runtime.state.get(key, default)
    
    def get_messages(self) -> list:
        """
        Get conversation messages from state.
        
        Returns:
            List of messages (typically LangChain message objects)
        """
        return self._runtime.state.get('messages', [])

    # --- Status Streaming ---

    async def stream_status(self, status: str) -> None:
        """Proxy status updates to the underlying runtime when available."""
        status_handler = getattr(self._runtime, 'stream_status', None)
        if status_handler:
            try:
                result = status_handler(status)
                if inspect.isawaitable(result):
                    await result
                return
            except TypeError:
                # Non-awaitable mocks may raise when awaited; treat as best-effort
                return
        # Fallback to stream_writer when stream_status is unavailable
        if hasattr(self._runtime, 'stream_writer') and self._runtime.stream_writer is not None:
            try:
                result = self._runtime.stream_writer({"status": status})
                if inspect.isawaitable(result):
                    await result
            except TypeError:
                return
    
    # --- Store Access Methods ---
    
    async def get_from_store(self, namespace: tuple, key: str) -> Optional[Any]:
        """
        Retrieve value from persistent store.
        
        Args:
            namespace: Store namespace tuple (e.g., ('users',))
            key: Item key
            
        Returns:
            Stored value or None if not found
        """
        if not hasattr(self._runtime, 'store') or self._runtime.store is None:
            return None
        
        item = await self._runtime.store.get(namespace, key)
        return item.value if item else None
    
    async def put_to_store(self, namespace: tuple, key: str, value: Any) -> None:
        """
        Store value in persistent store.
        
        Args:
            namespace: Store namespace tuple (e.g., ('users',))
            key: Item key
            value: Value to store
        """
        if hasattr(self._runtime, 'store') and self._runtime.store is not None:
            await self._runtime.store.put(namespace, key, value)
    
    # --- Streaming Methods ---
    
    async def stream_update(self, update: Dict[str, Any]) -> None:
        """
        Stream custom update to client.
        
        Args:
            update: Dictionary containing update data
        """
        if hasattr(self._runtime, 'stream_writer') and self._runtime.stream_writer is not None:
            await self._runtime.stream_writer(update)
    
    # --- Utility Methods ---
    
    def get_tool_call_id(self) -> Optional[str]:
        """
        Get unique ID for current tool invocation.
        
        Returns:
            Tool call ID or None if not available
        """
        return getattr(self._runtime, 'tool_call_id', None)
    
    def get_config(self) -> Optional[Any]:
        """
        Get RunnableConfig for current execution.
        
        Returns:
            RunnableConfig object or None
        """
        return getattr(self._runtime, 'config', None)
