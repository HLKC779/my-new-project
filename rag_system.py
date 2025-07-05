import os
from dotenv import load_dotenv
from typing import List, Dict, Any
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq

class RAGSystem:
    def __init__(self, persist_directory: str = "chroma_db"):
        """Initialize the RAG system with necessary components."""
        load_dotenv()
        self.persist_directory = persist_directory
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2"
        )
        self.llm = ChatGroq(
            temperature=0.1,
            model_name="mixtral-8x7b-32768",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        self.vector_store = None
        self.retriever = None
        self.qa_chain = None

    def load_documents(self, file_paths: List[str]):
        """Load and process documents from the given file paths."""
        documents = []
        
        for file_path in file_paths:
            file_path = Path(file_path)
            if file_path.suffix == '.pdf':
                loader = PyPDFLoader(str(file_path))
            else:
                loader = TextLoader(str(file_path))
            documents.extend(loader.load())
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        return text_splitter.split_documents(documents)

    def create_vector_store(self, documents, recreate: bool = False):
        """Create or load a vector store from documents."""
        if recreate or not Path(self.persist_directory).exists():
            self.vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )
            self.vector_store.persist()
        else:
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
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
        
        return self.qa_chain({"query": question})

def main():
    # Example usage
    rag = RAGSystem()
    
    # Example file paths - replace with your own documents
    document_paths = [
        "data/papers/data_engineering.pdf",
        "data/papers/ai_research.pdf"
    ]
    
    # Load and process documents
    print("Loading documents...")
    documents = rag.load_documents(document_paths)
    
    # Create vector store
    print("Creating vector store...")
    rag.create_vector_store(documents, recreate=True)
    
    # Example query
    while True:
        question = input("\nEnter your question (or 'quit' to exit): ")
        if question.lower() == 'quit':
            break
            
        result = rag.query(question)
        print("\nAnswer:", result["result"])
        print("\nSources:")
        for i, doc in enumerate(result["source_documents"], 1):
            print(f"{i}. {doc.metadata.get('source', 'Unknown source')} - Page {doc.metadata.get('page', 'N/A')}")

if __name__ == "__main__":
    main()
