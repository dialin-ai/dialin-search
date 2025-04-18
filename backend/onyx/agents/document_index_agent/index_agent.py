"""
Document Index Agent - An agentic environment for LLM interaction with document index.

This module defines an agent-based interface for LLMs to interact with the document index.
It provides a structured way for LLMs to query, retrieve, and analyze documents without
modifying existing code.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from onyx.auth.users import current_user
from onyx.context.search.enums import LLMEvaluationType, SearchType
from onyx.context.search.models import IndexFilters, RetrievalDetails, SearchRequest
from onyx.context.search.pipeline import SearchPipeline
from onyx.context.search.types import InferenceChunk, InferenceSection
from onyx.db.models import User
from onyx.document_index.factory import get_default_document_index
from onyx.document_index.interfaces import DocumentIndex, VespaChunkRequest
from onyx.llm.interfaces import LLM, ToolChoiceOptions
from onyx.llm.factory import get_default_llms
from onyx.natural_language_processing.utils import get_tokenizer
from onyx.prompts.prompt_utils import build_doc_context_str
from onyx.utils.logger import setup_logger
from onyx.utils.timing import log_function_time

logger = setup_logger()


class ToolName(str, Enum):
    """Enum of available tools for the document index agent."""
    SEARCH = "search"
    GET_DOCUMENT = "get_document"
    GET_RELATED_DOCUMENTS = "get_related_documents"
    SUMMARIZE_DOCUMENTS = "summarize_documents"
    EXTRACT_ENTITIES = "extract_entities"


@dataclass
class DocumentInfo:
    """Simplified document information for use in the agent."""
    document_id: str
    content: str
    title: str
    source_type: Optional[str] = None
    link: Optional[str] = None
    score: Optional[float] = None
    update_time: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentState:
    """
    Manages the state for the document index agent.
    Tracks conversation history, retrieved documents, and current context.
    """
    
    def __init__(self):
        self.conversation_history: List[BaseMessage] = []
        self.retrieved_documents: List[DocumentInfo] = []
        self.current_context: Dict[str, Any] = {}
        self.tool_results: Dict[str, Any] = {}
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the conversation history."""
        self.conversation_history.append(message)
    
    def add_retrieved_document(self, document: DocumentInfo) -> None:
        """Add a document to the retrieved documents list."""
        self.retrieved_documents.append(document)
    
    def set_context(self, key: str, value: Any) -> None:
        """Set a value in the current context."""
        self.current_context[key] = value
    
    def record_tool_result(self, tool_name: str, result: Any) -> None:
        """Record the result of a tool execution."""
        timestamp = datetime.now().isoformat()
        if tool_name not in self.tool_results:
            self.tool_results[tool_name] = []
        self.tool_results[tool_name].append({
            "timestamp": timestamp,
            "result": result
        })


class DocumentIndexTools:
    """
    Collection of tools for interacting with the document index.
    These tools are designed to be used by an LLM agent.
    """
    
    def __init__(
        self,
        document_index: DocumentIndex,
        db_session: Session,
        user: Optional[User] = None,
    ):
        self.document_index = document_index
        self.db_session = db_session
        self.user = user
    
    def _chunk_to_doc_info(self, chunk: InferenceChunk) -> DocumentInfo:
        """Convert an InferenceChunk to a DocumentInfo object."""
        return DocumentInfo(
            document_id=chunk.document_id,
            content=chunk.content,
            title=chunk.semantic_identifier or "Unknown",
            source_type=chunk.source_type,
            link=chunk.source_links.get(0) if chunk.source_links else None,
            score=chunk.score,
            update_time=chunk.updated_at,
            metadata=chunk.metadata,
        )
    
    def _section_to_doc_info(self, section: InferenceSection) -> DocumentInfo:
        """Convert an InferenceSection to a DocumentInfo object."""
        return self._chunk_to_doc_info(section.center_chunk)
    
    @log_function_time()
    def search(
        self,
        query: str,
        search_type: str = "semantic",
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[DocumentInfo]:
        """
        Search the document index with the given query and filters.
        
        Args:
            query: The search query
            search_type: Type of search ("semantic", "keyword", or "hybrid")
            filters: Optional filters to apply to the search
            limit: Maximum number of results to return
            
        Returns:
            List of matching documents
        """
        # Convert string search_type to enum
        search_type_enum = SearchType.SEMANTIC
        if search_type.lower() == "keyword":
            search_type_enum = SearchType.KEYWORD
        elif search_type.lower() == "hybrid":
            search_type_enum = SearchType.HYBRID
        
        # Create index filters from the provided filters
        index_filters = IndexFilters()
        if filters:
            # Apply any provided filters
            if "source_type" in filters:
                index_filters.source_type = filters["source_type"]
            if "document_set" in filters:
                index_filters.document_set = filters["document_set"]
            if "time_cutoff" in filters:
                index_filters.time_cutoff = filters["time_cutoff"]
            if "tags" in filters:
                index_filters.tags = filters["tags"]
        
        # Create search request
        retrieval_options = RetrievalDetails(
            filters=index_filters,
            limit=limit,
        )
        
        # Get default LLMs for search pipeline
        llm, fast_llm = get_default_llms()
        
        # Create and execute search pipeline
        search_pipeline = SearchPipeline(
            search_request=SearchRequest(
                query=query,
                search_type=search_type_enum,
                human_selected_filters=index_filters,
                limit=limit,
                evaluation_type=LLMEvaluationType.SKIP,  # Skip evaluation for agent use
            ),
            user=self.user,
            llm=llm,
            fast_llm=fast_llm,
            skip_query_analysis=True,  # Skip analysis since agent is in control
            db_session=self.db_session,
        )
        
        # Get reranked sections from search pipeline
        top_sections = search_pipeline.reranked_sections
        
        # Convert sections to document info objects
        return [self._section_to_doc_info(section) for section in top_sections]
    
    @log_function_time()
    def get_document(
        self,
        document_id: str,
        chunk_index: Optional[int] = None
    ) -> Optional[DocumentInfo]:
        """
        Retrieve a specific document by its ID and optional chunk index.
        
        Args:
            document_id: The ID of the document to retrieve
            chunk_index: Optional specific chunk index to retrieve
            
        Returns:
            Document information if found, None otherwise
        """
        # Create chunk request
        chunk_request = VespaChunkRequest(
            document_id=document_id,
            min_chunk_ind=chunk_index if chunk_index is not None else 0,
            max_chunk_ind=chunk_index if chunk_index is not None else 0,
        )
        
        # Query the document index
        chunks = self.document_index.id_based_retrieval(
            chunk_requests=[chunk_request],
            filters=IndexFilters(),  # Use empty filters, we're querying by ID
        )
        
        # If no chunks found, return None
        if not chunks:
            return None
        
        # Return document info for the first chunk
        return self._chunk_to_doc_info(chunks[0])
    
    @log_function_time()
    def get_related_documents(
        self,
        document_id: str,
        limit: int = 5
    ) -> List[DocumentInfo]:
        """
        Find documents related to the given document.
        
        Args:
            document_id: The ID of the document to find related documents for
            limit: Maximum number of related documents to return
            
        Returns:
            List of related documents
        """
        # First, get the document to use its content for search
        document = self.get_document(document_id)
        if not document:
            return []
        
        # Use the document content as a query to find related documents
        related_docs = self.search(
            query=document.content[:1000],  # Use first 1000 chars as query
            search_type="semantic",
            limit=limit + 1,  # Get one extra to remove the original doc
        )
        
        # Filter out the original document
        related_docs = [doc for doc in related_docs if doc.document_id != document_id]
        
        # Return limited number of related documents
        return related_docs[:limit]
    
    @log_function_time()
    def summarize_documents(
        self,
        document_ids: List[str],
        llm: LLM
    ) -> str:
        """
        Generate a summary of the specified documents.
        
        Args:
            document_ids: List of document IDs to summarize
            llm: LLM instance to use for summarization
            
        Returns:
            Summary of the documents
        """
        documents = []
        for doc_id in document_ids:
            doc = self.get_document(doc_id)
            if doc:
                documents.append(doc)
        
        if not documents:
            return "No documents found to summarize."
        
        # Build context string from documents
        doc_context = "\n\n".join([
            f"Document: {doc.title}\n{doc.content[:2000]}" for doc in documents
        ])
        
        # Create summarization prompt
        summarization_prompt = [
            SystemMessage(content=(
                "You are a document summarization assistant. "
                "Summarize the following documents concisely while preserving key information."
            )),
            HumanMessage(content=f"Please summarize these documents:\n\n{doc_context}")
        ]
        
        # Generate summary using LLM
        response = llm.invoke(summarization_prompt)
        
        return response.content
    
    @log_function_time()
    def extract_entities(
        self,
        text: str,
        llm: LLM
    ) -> Dict[str, List[str]]:
        """
        Extract entities from the provided text.
        
        Args:
            text: Text to extract entities from
            llm: LLM instance to use for entity extraction
            
        Returns:
            Dictionary of entity types and their instances
        """
        # Create entity extraction prompt
        extraction_prompt = [
            SystemMessage(content=(
                "You are an entity extraction assistant. "
                "Extract entities from the text and categorize them. "
                "Return the result as JSON with the following structure: "
                "{'people': [], 'organizations': [], 'locations': [], 'dates': [], 'concepts': []}"
            )),
            HumanMessage(content=f"Extract entities from this text:\n\n{text[:5000]}")
        ]
        
        # Generate entity extraction using LLM
        response = llm.invoke(extraction_prompt)
        
        # Parse the JSON response
        try:
            # Extract JSON from the response content
            content = response.content
            # Look for JSON block if not directly parseable
            if not content.strip().startswith('{'):
                import re
                json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
                else:
                    # Try to find any JSON-like structure
                    json_match = re.search(r'{.*}', content, re.DOTALL)
                    if json_match:
                        content = json_match.group(0)
            
            entities = json.loads(content)
            return entities
        except Exception as e:
            logger.error(f"Error parsing entity extraction response: {e}")
            return {
                "people": [],
                "organizations": [],
                "locations": [],
                "dates": [],
                "concepts": [],
                "error": str(e)
            }


class DocumentIndexAgent:
    """
    Agent for interacting with the document index using natural language.
    Provides a structured interface for LLMs to query and analyze documents.
    """
    
    def __init__(
        self,
        llm: LLM,
        document_index: DocumentIndex,
        db_session: Session,
        user: Optional[User] = None,
    ):
        """
        Initialize the document index agent.
        
        Args:
            llm: LLM instance to use for the agent
            document_index: Document index to interact with
            db_session: Database session
            user: Optional user for authentication and personalization
        """
        self.llm = llm
        self.document_index = document_index
        self.db_session = db_session
        self.user = user
        self.state = AgentState()
        self.tools = DocumentIndexTools(document_index, db_session, user)
        
        # Define tools for the LLM
        self.tool_definitions = [
            {
                "type": "function",
                "function": {
                    "name": ToolName.SEARCH.value,
                    "description": "Search for documents in the index",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "search_type": {
                                "type": "string",
                                "enum": ["semantic", "keyword", "hybrid"],
                                "description": "Type of search to perform"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Optional filters to apply",
                                "properties": {
                                    "source_type": {
                                        "type": "string",
                                        "description": "Filter by source type"
                                    },
                                    "document_set": {
                                        "type": "string",
                                        "description": "Filter by document set"
                                    },
                                    "time_cutoff": {
                                        "type": "string",
                                        "description": "Filter by time cutoff (ISO format)"
                                    },
                                    "tags": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Filter by tags"
                                    }
                                }
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": ToolName.GET_DOCUMENT.value,
                    "description": "Retrieve a specific document by ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "The ID of the document to retrieve"
                            },
                            "chunk_index": {
                                "type": "integer",
                                "description": "Optional specific chunk index to retrieve"
                            }
                        },
                        "required": ["document_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": ToolName.GET_RELATED_DOCUMENTS.value,
                    "description": "Find documents related to a given document",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "The ID of the document to find related documents for"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of related documents",
                                "default": 3
                            }
                        },
                        "required": ["document_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": ToolName.SUMMARIZE_DOCUMENTS.value,
                    "description": "Generate a summary of specified documents",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "document_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of document IDs to summarize"
                            }
                        },
                        "required": ["document_ids"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": ToolName.EXTRACT_ENTITIES.value,
                    "description": "Extract entities from text",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to extract entities from"
                            }
                        },
                        "required": ["text"]
                    }
                }
            }
        ]
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent."""
        return (
            "You are a document index agent with access to a document database. "
            "Your task is to help users find and analyze documents by using the provided tools. "
            "For each user query, think about which tools would be most appropriate to use. "
            "Always provide concise, helpful responses based on the document content. "
            "If you don't know the answer or can't find relevant documents, say so clearly. "
            "Do not make up information that isn't in the documents."
        )
    
    def _serialize_doc_info(self, doc: DocumentInfo) -> Dict[str, Any]:
        """Serialize document info for inclusion in responses."""
        return {
            "document_id": doc.document_id,
            "title": doc.title,
            "content_snippet": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
            "source_type": doc.source_type,
            "link": doc.link,
            "score": doc.score,
            "update_time": doc.update_time.isoformat() if doc.update_time else None,
        }
    
    def run_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """
        Execute a specific tool with the provided arguments.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
            
        Returns:
            Result of the tool execution
        """
        try:
            if tool_name == ToolName.SEARCH.value:
                result = self.tools.search(
                    query=tool_args["query"],
                    search_type=tool_args.get("search_type", "semantic"),
                    filters=tool_args.get("filters"),
                    limit=tool_args.get("limit", 5)
                )
                # Record the documents in the agent state
                for doc in result:
                    self.state.add_retrieved_document(doc)
                
                # Return serialized results
                return [self._serialize_doc_info(doc) for doc in result]
            
            elif tool_name == ToolName.GET_DOCUMENT.value:
                result = self.tools.get_document(
                    document_id=tool_args["document_id"],
                    chunk_index=tool_args.get("chunk_index")
                )
                
                if result:
                    self.state.add_retrieved_document(result)
                    # Return full document info including content
                    return {
                        "document_id": result.document_id,
                        "title": result.title,
                        "content": result.content,
                        "source_type": result.source_type,
                        "link": result.link,
                        "update_time": result.update_time.isoformat() if result.update_time else None,
                        "metadata": result.metadata
                    }
                return None
            
            elif tool_name == ToolName.GET_RELATED_DOCUMENTS.value:
                result = self.tools.get_related_documents(
                    document_id=tool_args["document_id"],
                    limit=tool_args.get("limit", 3)
                )
                
                # Record the documents in the agent state
                for doc in result:
                    self.state.add_retrieved_document(doc)
                
                # Return serialized results
                return [self._serialize_doc_info(doc) for doc in result]
            
            elif tool_name == ToolName.SUMMARIZE_DOCUMENTS.value:
                result = self.tools.summarize_documents(
                    document_ids=tool_args["document_ids"],
                    llm=self.llm
                )
                return result
            
            elif tool_name == ToolName.EXTRACT_ENTITIES.value:
                result = self.tools.extract_entities(
                    text=tool_args["text"],
                    llm=self.llm
                )
                return result
            
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e)}
    
    def process_query(
        self, 
        query: str, 
        stream: bool = False
    ) -> Union[str, Iterator[str]]:
        """
        Process a user query through the agent.
        
        Args:
            query: The user's query
            stream: Whether to stream the response
            
        Returns:
            Response from the agent, either as a complete string or as a stream
        """
        # Add user message to state
        user_message = HumanMessage(content=query)
        self.state.add_message(user_message)
        
        # Create conversation history
        messages = [
            SystemMessage(content=self._create_system_prompt()),
            user_message,
        ]
        
        # Process with LLM
        if stream:
            return self._process_query_stream(messages)
        else:
            return self._process_query_complete(messages)
    
    def _process_query_complete(self, messages: List[BaseMessage]) -> str:
        """Process a complete (non-streaming) query."""
        # Keep processing until we get a final answer (no tool calls)
        while True:
            response = self.llm.invoke(
                messages,
                tools=self.tool_definitions,
                tool_choice=ToolChoiceOptions.AUTO,
            )
            
            # Check if response has tool calls
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    # Execute the tool
                    result = self.run_tool(tool_name, tool_args)
                    self.state.record_tool_result(tool_name, result)
                    
                    # Format tool result
                    tool_results.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result
                    })
                
                # Add results to conversation
                result_message = HumanMessage(
                    content=f"Tool results: {json.dumps(tool_results, default=str)}"
                )
                messages.append(response)
                messages.append(result_message)
            else:
                # No tool calls, we have our answer
                self.state.add_message(response)
                return response.content
    
    def _process_query_stream(self, messages: List[BaseMessage]) -> Iterator[str]:
        """Process a streaming query."""
        # Implementation note: This is a simplified version that doesn't fully stream
        # tool execution results. A more complex implementation would use async and
        # proper streaming.
        
        # Process the query
        final_response = self._process_query_complete(messages)
        
        # Simulate streaming by yielding chunks
        chunk_size = 10  # Characters per chunk
        for i in range(0, len(final_response), chunk_size):
            yield final_response[i:i+chunk_size]


# Example usage
def create_document_index_agent(
    user: Optional[User] = None,
    db_session: Optional[Session] = None,
) -> DocumentIndexAgent:
    """
    Create an instance of the document index agent with default components.
    
    Args:
        user: Optional user for authentication
        db_session: Optional database session (will create if not provided)
        
    Returns:
        Initialized DocumentIndexAgent
    """
    from onyx.db.engine import get_session
    from onyx.db.search_settings import get_current_search_settings
    
    # Get or create database session
    if db_session is None:
        db_session = get_session()
    
    # Get default LLM
    llm, _ = get_default_llms()
    
    # Get document index
    search_settings = get_current_search_settings(db_session)
    document_index = get_default_document_index(search_settings, None)
    
    # Create and return agent
    return DocumentIndexAgent(
        llm=llm,
        document_index=document_index,
        db_session=db_session,
        user=user,
    ) 