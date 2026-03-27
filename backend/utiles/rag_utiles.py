# RubyRAG class for document processing and retrieval using FAISS.
import os
from dotenv import load_dotenv
from typing import List, Optional

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

load_dotenv()

class RubyRAG:
    """
    RubyRAG class for document processing and retrieval using FAISS.
    Updated to use Free Google Gemini Embeddings.
    """
    def __init__(
        self,
        db_path: str = "ruby_rag/db",
        embedding_model: str = "models/embedding-001",
        chunk_size: int = 600,
        chunk_overlap: int = 80,
    ):
        self.db_path = db_path 
        google_api_key = os.getenv("GOOGLE_API_KEY")
        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model=embedding_model, 
            google_api_key=google_api_key
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap)
        
        self.vectorstore = None
        # Load existing DB if present
        if os.path.exists(db_path):
            print(f"Loading FAISS DB from {db_path}")
            self.vectorstore = FAISS.load_local(
                db_path,
                self.embedding_model,
                allow_dangerous_deserialization=True,
            )
        else:
            print("No existing DB found. New DB will be created.")
    


    def _load_documents(self, file_path: str) -> List[Document]:
        """
        Load documents from a file.

        Args:
            file_path (str): Path to the document file.

        Returns:
            List[Document]: List of documents loaded from the file.
        """
        ext = os.path.splitext(file_path)[-1].lower()

        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding="utf-8")

        docs = loader.load()
        return self.text_splitter.split_documents(docs)
    
    def add_documents(self, file_path: str):
        """
        Add documents to the FAISS vector store.

        Args:
            file_path (str): Path to the document file.
        """
        docs = self._load_documents(file_path)
        if self.vectorstore is None:
            print("Creating new FAISS DB")
            self.vectorstore = FAISS.from_documents(
                docs,
                self.embedding_model,
            )
        else:
            print("Adding documents to existing FAISS DB")
            self.vectorstore.add_documents(docs)
        
        self.vectorstore.save_local(self.db_path)
        print(f"Documents added to FAISS DB at {self.db_path}")

    def query(self, query: str, k: int = 3, use_hf_rerank: bool = True) -> str:
        """
        Query the FAISS vector store.
        If use_hf_rerank is True, fetches more results and reranks them using Hugging Face model.

        Args:
            query (str): Query to search for.
            k (int): Number of documents to return.
            use_hf_rerank (bool): Whether to use HF model for reranking.

        Returns:
            str: Query response.
        """
        if self.vectorstore is None:
            raise RuntimeError("No existing DB found.")

        # If reranking, fetch more candidates
        fetch_k = k * 3 if use_hf_rerank else k
        docs = self.vectorstore.similarity_search(query, k=fetch_k)

        if use_hf_rerank and len(docs) > 1:
            hf_token = os.getenv("HF_TOKEN")
            if hf_token and "hf_" in hf_token and "your_" not in hf_token:
                try:
                    from huggingface_hub import InferenceClient
                    client = InferenceClient(provider="hf-inference", api_key=hf_token)
                    
                    sentences = [doc.page_content for doc in docs]
                    similarities = client.sentence_similarity(
                        {
                            "source_sentence": query,
                            "sentences": sentences
                        },
                        model="Mike0307/text2vec-base-chinese-rag",
                    )
                    
                    # Sort docs by similarity scores
                    scored_docs = sorted(zip(docs, similarities), key=lambda x: x[1], reverse=True)
                    docs = [doc for doc, score in scored_docs[:k]]
                    print(f"RAG: Reranked using HF model. Top score: {scored_docs[0][1]}")
                except Exception as e:
                    print(f"RAG: HF Reranking Error: {e}")
                    docs = docs[:k]
            else:
                docs = docs[:k]
        else:
            docs = docs[:k]

        context = []
        for i, doc in enumerate(docs, 1):
            context.append(
                f"[Context {i}]\n{doc.page_content}"
            )

        return "\n\n---\n\n".join(context)
