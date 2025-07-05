import os
from rag_system import RAGSystem

def main():
    # Initialize the RAG system
    print("Initializing RAG system...")
    rag = RAGSystem(persist_directory="chroma_db")
    
    # Path to our sample documents
    document_paths = [
        "data/papers/data_engineering_basics.txt",
        "data/papers/ai_in_data_engineering.txt"
    ]
    
    # Load and process documents
    print("\nLoading documents...")
    documents = rag.load_documents(document_paths)
    print(f"Loaded {len(documents)} document chunks")
    
    # Create vector store
    print("\nCreating vector store...")
    rag.create_vector_store(documents, recreate=True)
    
    # Sample questions to test the system
    questions = [
        "What are the key components of data engineering?",
        "How is AI being used in data engineering?",
        "What are some tools used for data ingestion?",
        "What are the benefits of using AI in data quality management?"
    ]
    
    # Ask questions and get answers
    print("\nTesting the RAG system with some questions:")
    print("-" * 80)
    
    for i, question in enumerate(questions, 1):
        print(f"\nQuestion {i}: {question}")
        try:
            result = rag.query(question)
            print("\nAnswer:", result["result"])
            print("\nSources:")
            for j, doc in enumerate(result["source_documents"], 1):
                source = os.path.basename(doc.metadata.get('source', 'Unknown'))
                print(f"  {j}. {source} - Page {doc.metadata.get('page', 'N/A')}")
        except Exception as e:
            print(f"Error processing question: {e}")
        
        print("-" * 80)

if __name__ == "__main__":
    main()
