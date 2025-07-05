import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document as LangchainDocument
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from app.core.config import settings
from app.models.document import DocumentChunk

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """
    A class for managing vector store operations including document indexing and similarity search.
    """
    
    def __init__(self, persist_directory: str = None):
        """
        Initialize the vector store manager.
        
        Args:
            persist_directory: Directory to persist the vector store (defaults to settings.CHROMA_DB_PATH)
        """
        self.persist_directory = persist_directory or settings.CHROMA_DB_PATH
        os.makedirs(self.persist_directory, exist_ok=True)
        self.embeddings = self._get_embeddings()
        self.vector_store = self._get_vector_store()
    
    def _get_embeddings(self) -> Embeddings:
        """
        Get the embeddings model.
        
        Returns:
            An instance of a LangChain Embeddings class
        """
        model_name = settings.EMBEDDING_MODEL
        logger.info(f"Loading embeddings model: {model_name}")
        
        # Configure device based on availability
        device = "cuda"  # Default to CUDA if available
        try:
            import torch
            if not torch.cuda.is_available():
                device = "cpu"
                logger.warning("CUDA not available, using CPU for embeddings")
        except ImportError:
            device = "cpu"
            logger.warning("PyTorch not available, using CPU for embeddings")
        
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': device},
            encode_kwargs={'normalize_embeddings': True}
        )
    
    def _get_vector_store(self) -> VectorStore:
        """
        Get or create a vector store instance.
        
        Returns:
            A VectorStore instance (ChromaDB)
        """
        return Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_metadata={"hnsw:space": "cosine"}  # Optimize for cosine similarity
        )
    
    def add_documents(
        self, 
        documents: List[LangchainDocument],
        ids: Optional[List[str]] = None,
        **kwargs
    ) -> List[str]:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of Langchain Document objects
            ids: Optional list of document IDs
            **kwargs: Additional arguments to pass to the vector store
            
        Returns:
            List of document IDs
        """
        if not documents:
            return []
            
        logger.info(f"Adding {len(documents)} documents to vector store")
        
        # If no IDs provided, generate them
        if ids is None:
            import hashlib
            ids = [
                hashlib.sha256(doc.page_content.encode()).hexdigest()
                for doc in documents
            ]
        
        # Add documents to the vector store
        doc_ids = self.vector_store.add_documents(
            documents=documents,
            ids=ids,
            **kwargs
        )
        
        # Persist the changes
        self.vector_store.persist()
        
        return doc_ids
    
    def add_document_chunks(
        self, 
        chunks: List[DocumentChunk],
        document_id: int,
        **kwargs
    ) -> List[str]:
        """
        Add document chunks to the vector store.
        
        Args:
            chunks: List of DocumentChunk objects
            document_id: ID of the parent document
            **kwargs: Additional arguments to pass to the vector store
            
        Returns:
            List of document IDs
        """
        if not chunks:
            return []
            
        # Convert DocumentChunk objects to Langchain Document objects
        documents = []
        ids = []
        
        for chunk in chunks:
            # Create metadata for the chunk
            metadata = {
                'document_id': document_id,
                'chunk_id': chunk.id,
                'chunk_index': chunk.chunk_index,
            }
            
            if chunk.page_number is not None:
                metadata['page_number'] = chunk.page_number
                
            if chunk.section_title:
                metadata['section_title'] = chunk.section_title
            
            # Create a Langchain Document
            doc = LangchainDocument(
                page_content=chunk.content,
                metadata=metadata
            )
            
            documents.append(doc)
            ids.append(f"doc_{document_id}_chunk_{chunk.chunk_index}")
        
        # Add to vector store
        return self.add_documents(documents, ids=ids, **kwargs)
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Tuple[LangchainDocument, float]]:
        """
        Perform a similarity search.
        
        Args:
            query: The query string
            k: Number of results to return
            filter: Optional filter to apply to the search
            **kwargs: Additional arguments to pass to the vector store
            
        Returns:
            List of (document, score) tuples
        """
        logger.debug(f"Performing similarity search for query: {query[:100]}...")
        
        # Perform the search
        results = self.vector_store.similarity_search_with_score(
            query=query,
            k=k,
            filter=filter,
            **kwargs
        )
        
        return results
    
    def get_document_chunks(
        self,
        document_id: int,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get chunks for a specific document from the vector store.
        
        Args:
            document_id: ID of the document
            limit: Maximum number of chunks to return
            offset: Number of chunks to skip
            
        Returns:
            List of chunk data dictionaries
        """
        # This is a simplified implementation that would need to be adapted
        # based on how you're storing chunks in your vector store
        
        # In a real implementation, you might query the vector store with a filter
        # to get chunks for a specific document
        logger.warning("get_document_chunks is not fully implemented")
        return []
    
    def delete_document(self, document_id: int) -> bool:
        """
        Delete all chunks for a document from the vector store.
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get all chunk IDs for this document
            # This is a simplified example - in practice, you'd need to query
            # the vector store to find all chunks with document_id=document_id
            
            # For ChromaDB, we can use the delete method with a filter
            if hasattr(self.vector_store, 'delete') and hasattr(self.vector_store, '_collection'):
                # This is ChromaDB specific
                from chromadb import QueryBuilder
                
                # Create a filter to match the document_id
                filter_condition = {"document_id": {"$eq": document_id}}
                
                # Delete all chunks matching the filter
                self.vector_store.delete(where=filter_condition)
                self.vector_store.persist()
                
                logger.info(f"Deleted all chunks for document {document_id} from vector store")
                return True
            else:
                logger.warning("Vector store does not support deletion by filter")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting document {document_id} from vector store: {str(e)}")
            return False
    
    def clear(self) -> bool:
        """
        Clear the entire vector store.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if hasattr(self.vector_store, '_collection'):
                # ChromaDB specific
                self.vector_store._collection.delete(where={})
                self.vector_store.persist()
                logger.info("Cleared vector store")
                return True
            else:
                logger.warning("Vector store does not support clearing")
                return False
        except Exception as e:
            logger.error(f"Error clearing vector store: {str(e)}")
            return False

# Create a singleton instance
vector_store_manager = VectorStoreManager()
