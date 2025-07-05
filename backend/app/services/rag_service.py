import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import torch
from datetime import datetime

# LangChain imports
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import VectorStore
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseLLM
from langchain_core.outputs import GenerationChunk, LLMResult

# Document loaders
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredFileLoader,
)

# Embeddings and vector stores
from langchain_community.embeddings import HuggingFaceEmbeddings, HuggingFaceInstructEmbeddings

# LLM models
from langchain_community.llms import HuggingFacePipeline
from transformers import (
    AutoModelForCausalLM,
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    pipeline,
    StoppingCriteria,
    StoppingCriteriaList,
)

# Local imports
from app.core.config import settings
from app.core.vector_store import vector_store_manager
from app.models.document import Document, DocumentChunk
from app.models.query import Query, QueryStatus, QuerySource
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Define a custom stopping criteria for better generation control
class StopOnTokens(StoppingCriteria):
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        stop_ids = [50278, 50279, 50277, 1]  # Common EOS tokens
        for stop_id in stop_ids:
            if input_ids[0][-1] == stop_id:
                return True
        return False

class RAGService:
    """
    A service class for Retrieval-Augmented Generation (RAG) operations.
    Handles document ingestion, retrieval, and generation of responses.
    """
    
    def __init__(self, model_name: str = None, device: str = None):
        """
        Initialize the RAG service.
        
        Args:
            model_name: Name of the HuggingFace model to use
            device: Device to run the model on ('cuda', 'mps', or 'cpu')
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name = model_name or settings.LLM_MODEL_NAME
        
        # Initialize components
        self.embeddings = self._initialize_embeddings()
        self.llm = self._initialize_llm()
        self.vector_store = vector_store_manager.vector_store
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4}
        )
        
        # Initialize QA chain
        self.qa_chain = self._create_qa_chain()
    
    def _initialize_embeddings(self):
        """Initialize the embeddings model."""
        logger.info(f"Initializing embeddings model: {settings.EMBEDDING_MODEL}")
        
        # Use InstructEmbeddings if available, otherwise fall back to standard embeddings
        try:
            return HuggingFaceInstructEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={"device": self.device}
            )
        except Exception as e:
            logger.warning(f"Could not load InstructEmbeddings, falling back to standard embeddings: {e}")
            return HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={"device": self.device}
            )
    
    def _initialize_llm(self):
        """Initialize the language model."""
        logger.info(f"Initializing LLM: {self.model_name}")
        
        try:
            # Load tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                use_fast=True,
                padding_side="left"
            )
            
            # Configure model loading based on device
            model_kwargs = {
                "device_map": "auto",
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
                "low_cpu_mem_usage": True,
            }
            
            # Try to load as a CausalLM first, fall back to Seq2Seq if that fails
            try:
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    **model_kwargs
                )
                task = "text-generation"
            except (ValueError, OSError):
                model = AutoModelForSeq2SeqLM.from_pretrained(
                    self.model_name,
                    **model_kwargs
                )
                task = "text2text-generation"
            
            # Configure generation pipeline
            pipe = pipeline(
                task,
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=1024,
                temperature=0.7,
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.1,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                stopping_criteria=StoppingCriteriaList([StopOnTokens()])
            )
            
            return HuggingFacePipeline(pipeline=pipe)
            
        except Exception as e:
            logger.error(f"Error initializing language model: {e}")
            raise
    
    def _create_qa_chain(self):
        """Create a QA chain with the configured LLM and retriever."""
        # Define a custom prompt template
        template = """Use the following pieces of context to answer the question at the end. 
        If you don't know the answer, just say that you don't know, don't try to make up an answer.
        
        Context:
        {context}
        
        Question: {question}
        Helpful Answer:"""
        
        QA_PROMPT = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )
        
        # Create the QA chain
        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": QA_PROMPT}
        )

    def load_documents(self, file_paths: List[Union[str, Path]]) -> List[Dict[str, Any]]:
        """
        Load and process documents from the given file paths.
        
        Args:
            file_paths: List of file paths to load
            
        Returns:
            List of processed document metadata
        """
        if not file_paths:
            return []
            
        logger.info(f"Loading {len(file_paths)} documents")
        
        results = []
        
        for file_path in file_paths:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue
                
            try:
                if file_path.suffix.lower() == '.pdf':
                    loader = PyPDFLoader(str(file_path))
                elif file_path.suffix.lower() in ['.txt', '.md']:
                    loader = TextLoader(str(file_path))
                elif file_path.suffix.lower() in ['.docx', '.doc']:
                    loader = UnstructuredWordDocumentLoader(str(file_path))
                else:
                    # Try to use the unstructured loader as a fallback
                    loader = UnstructuredFileLoader(str(file_path))
                
                # Load the document
                docs = loader.load()
                
                # Add metadata
                for doc in docs:
                    doc.metadata.update({
                        'source': str(file_path.name),
                        'file_path': str(file_path),
                        'file_type': file_path.suffix.lower(),
                        'load_time': datetime.now().isoformat(),
                    })
                
                results.extend(docs)
                logger.info(f"Loaded {len(docs)} pages from {file_path}")
                
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}", exc_info=True)
                results.append({
                    'file_path': str(file_path),
                    'error': str(e),
                    'success': False
                })
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        return text_splitter.split_documents(results)

    def create_vector_store(self, documents, persist_directory: str = None, recreate: bool = False):
        """Create or load a vector store from documents."""
        persist_directory = persist_directory or settings.CHROMA_DB_PATH
        
        if recreate or not Path(persist_directory).exists():
            self.vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=persist_directory
            )
            self.vector_store.persist()
        else:
            self.vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings
            )
        
        self.retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 4}
        )
        
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=True
        )

    def query(self, question: str) -> Dict[str, Any]:
        """Query the RAG system with a question."""
        if not self.qa_chain:
            raise ValueError("Please load documents and create vector store first.")
        
        result = self.qa_chain({"query": question})
        
        # Format the response
        return {
            "answer": result["result"],
            "sources": [
                {
                    "source": doc.metadata.get("source", "Unknown"),
                    "page": doc.metadata.get("page", "N/A"),
                    "content": doc.page_content[:500] + ("..." if len(doc.page_content) > 500 else "")
                }
                for doc in result["source_documents"]
            ]
        }
