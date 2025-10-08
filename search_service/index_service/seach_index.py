import os
import mimetypes
from collections import defaultdict
from typing import Any, Tuple, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dotenv import load_dotenv
load_dotenv()
#-------------Libraries utilize in setting Vector Search Index----------------
from pymilvus import connections, Collection
from llama_index.core.schema import NodeWithScore
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.vector_stores.milvus.utils import BGEM3SparseEmbeddingFunction
from llama_index.core.vector_stores.types import VectorStoreQueryMode
from llama_index.core import VectorStoreIndex, Document, StorageContext, SimpleDirectoryReader
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter, MetadataFilter, FilterOperator
from llama_index.core.extractors import DocumentContextExtractor, QuestionsAnsweredExtractor,  SummaryExtractor
#------------Libraries utilized for custom functionalities---------------------
from index_service.schemas import SourceNode, SourceMetadata
from index_service.utilities import TextProcessor as txtprocessor
from index_service.config import IndexConfig as settings
from index_service.image_processor import ImageProcessor as imgprocessor
from index_service.extract_content import DataExtractor as contentprocessor

#-----Paths for data storage locations--------
MILVUS_DB_URI: Any = os.getenv('MILVUS_DB_URI')
DOCS_DIR: Any = os.getenv('DOCS_DIR')
IMG_DIR: Any = os.getenv('IMG_DIR')
TEMP_IMG_DIR: Any = os.getenv('TEMP_IMG_DIR')
DEFAULT_COLLECTION: Any = os.getenv('VECTOR_COLLECTION')


class SearchIndex:
    """
    Provides utilities to build and operate upon vector based search index used for querying.
    Args: Requires vectore store collection name to be build and flag to recreate vector store (optional. default: False)
    """

    def __init__(self, *, collection: str = DEFAULT_COLLECTION, clear_existing_collection: bool = False, index_docs: bool = False) -> None:
        self._docstore = SimpleDocumentStore() # Create a docstore to store raw llamaindex documents
        self._node_parser = SentenceSplitter(chunk_size=450, chunk_overlap=20) # Chunker for llama documents
        self._index = self._setup_index(collection, clear_existing_collection) # Stores the index to be used for searching and querying
        self._reranker = settings.RERANKER # reranker model for reranking nodes on basis of query
        if index_docs:   
            self._initialize_indexing()


    def _setup_index(self, collection: str, clear_existing_collection: bool = False) -> VectorStoreIndex:
        """Setup and returns a vector search index with MilvusDB as vector store"""
        print(f"[Search Index] Initializing milvus vector store....")
        
        vector_store = MilvusVectorStore(
            uri = MILVUS_DB_URI,
            collection_name = collection,
            overwrite = clear_existing_collection,
            dim = 768,
            enable_dense = True,
            enable_sparse = True,
            upsert_mode = True,
            sparse_embedding_function = BGEM3SparseEmbeddingFunction(),
            similarity_metric = "IP",
        )

        print(f"[Search Index] Building new search index....")
        index = VectorStoreIndex.from_documents(
            [], storage_context=StorageContext.from_defaults(vector_store=vector_store, docstore=self._docstore)
        )
        print(f"[Search Index] New search index built successfully....")
        return index
    

    def _initialize_indexing(self) -> None:
        """Index the vector store search index with initially existing data in database"""
        docs = self.load_data(DOCS_PATH=DOCS_DIR)
        self.insert_docs_index(docs)
        sources: List[str] = os.listdir(DOCS_DIR)
        source_paths: List[str] = [os.path.join(DOCS_DIR, source) for source in sources]
        self.update_index_insertion(files_path=source_paths)
        print("[Search Index] Initial documents indexed successfully....")
    

    def load_data(self, *, input_files: Optional[List[str]] = None, DOCS_PATH: str = DOCS_DIR) -> List[Document]:
        """Load the data from data source and insert it in search index"""
        # Extract data from input files if given else extract data from whole directory
        docs = SimpleDirectoryReader(
            input_dir=DOCS_PATH, input_files=input_files, filename_as_id=True
        ).load_data()

        if docs:
            # Normalize the content of documents extracted before indexing
            docs = [
                Document(
                    doc_id=doc.doc_id, 
                    text=txtprocessor.normalize_content(doc.text), 
                    metadata=doc.metadata
                ) 
                for doc in docs
            ]
        return docs
    

    def update_index_insertion(self, *, files_path: List[str]) -> None:
        """Update search index's vector store by inserting content of new documents from database"""
        print("[Search Index] Building and updating search index on new data recieved...")
        contentprocessor.clean_temp_dir(TEMP_IMG_DIR, True)

        image_docs: List[Document] = [] # stores the documents which are images from database
        labeled_docs: List[tuple] = [] # stores the documents other than images but contain images

        tasks: List[Future] = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            for path in files_path:
                tasks.append(
                    executor.submit(self._update_index_insertion_helper, path)
                )
            
            for task in as_completed(tasks):
                img_docs_local, labeled_docs_local = task.result()
                image_docs.extend(img_docs_local)
                labeled_docs.extend(labeled_docs_local)
        
        docs_to_update: Dict[str,List[tuple]] = defaultdict(list)
        for label, img_path, filename in labeled_docs:
            docs_to_update[filename].append((label,img_path))
        docs_to_update = dict(docs_to_update)

        modified_image_docs = imgprocessor.get_image_captions_ocr(image_docs)
        if self._update_docs_index(docs_to_update):
            self.insert_docs_index(modified_image_docs)
            print("[Search Index] Search Index is updated on new data successfully...")
            print(f"[Search Index] Searching on '{self._index.vector_store.collection_name if isinstance(self._index.vector_store, MilvusVectorStore) else ""}' with total {len(self._index.docstore.docs)} documents after insertion.")
        else:
            print("[Search Index] Search Index cannot be updated on new data successfully...")


    def update_index_deletion(self, *, files_path: List[str]) -> None:
        """Update search index's vector store by deleting content of existing documents of database"""
        print("[Search Index] Updating search index. Deleting given documents from search index...")
        doc_ids: List[str] = [] # stores documents IDs of all the documents
        
        # Get document IDs prefix for all documents to delete from search index
        for document in files_path:
            doc_name = os.path.basename(document)
            mime_type,_ = mimetypes.guess_file_type(document)
            if mime_type and mime_type.startswith("image/"):
                doc_ids.append(os.path.join(IMG_DIR, f"{doc_name}_.{doc_name.split('.')[-1]}"))
                continue
            doc_ids.append(os.path.join(IMG_DIR, doc_name)) # document ids of all associated images to document
            doc_ids.append(document) # document ids of all related chunks to document in search index  

        # Connect to MilvusDB for deleting documents
        connections.connect(uri=MILVUS_DB_URI)
        milvus_col = Collection(DEFAULT_COLLECTION)

        for doc_id in doc_ids:
            delete_expr = f"doc_id like '{doc_id}%'"
            milvus_col.delete(expr=delete_expr)
            milvus_col.flush()
        milvus_col.compact()

        # Delete all the documents with given document IDs from search index 
        print("[Search Index] Updated search index. Deleted given documents successfully.....")       


    def insert_docs_index(self, docs: List[Document], enable_extractors: bool = False) -> None:
        """Insert and Update search index with documents. Optionally apply extractors like (Context Extractor, Question Extractor, Summary Extractor) if enabled."""
        extractors = self._get_extractors() if enable_extractors else ()
        pipeline = IngestionPipeline(transformations=[self._node_parser, *extractors])
        nodes = pipeline.run(documents=docs, in_place=False)
        self._index.insert_nodes(nodes)
        print("[Search Index] Documents indexed sucessfully......")


    async def fetch_context(self, *, query: str, related_images: List[str]) -> str:
        """Fetches the information corresponding to given query from search index"""
        with ThreadPoolExecutor(max_workers=1) as executor:
            context = executor.submit(self._retrieve_context, query, related_images).result()
        return context

    
    def _retrieve_context(self, query: str, related_images: List[str] = []) -> str:
        """Retrieve context (including images) from search index corresponding to given query"""
        INITIAL_TOP_K = settings.TOP_K * 2

        # Create retriever to fetch nodes corresponding to query
        retriever = self._index.as_retriever(
            similarity_top_k=INITIAL_TOP_K, 
            vector_store_query_mode=VectorStoreQueryMode.HYBRID
        )
        # Intially retrieve the chunks corresponding to query
        nodes: List[NodeWithScore] = retriever.retrieve(query)

        if related_images:
            filters = MetadataFilters(
                filters=[
                    MetadataFilter(key="image_path", value=image, operator=FilterOperator.CONTAINS)
                    for image in related_images
                ]
            )
            retriever = self._index.as_retriever(
                similarity_top_k=INITIAL_TOP_K, 
                vector_store_query_mode=VectorStoreQueryMode.HYBRID,
                filters=filters
            )
            # retrieve the chunks corresponding to query on basis of image paths
            metadata_nodes: List[NodeWithScore] = retriever.retrieve(query)
            nodes_text = [node.get_content() for node in nodes]
            for meta_node in metadata_nodes:
                if not meta_node.get_content() in nodes_text:
                    nodes.append(meta_node)

        print("[Search Index] Source nodes retrieved successfully.....")

        # Store retrieved nodes with custom metadata
        source_nodes: List[SourceNode] = []
        for node in nodes:
            metadata = node.metadata if node.metadata else node.node.metadata
            text = node.text if node.text else node.get_content()
            filtered_metadata = SourceMetadata(IMAGE_PATHS=metadata.get('image_path', "").strip().split())
            source_nodes.append(SourceNode(text=text, metadata=filtered_metadata))
        reranked_nodes: List[SourceNode] = self._get_reranked_nodes(query, source_nodes)

        # Extract context from reranked nodes
        chunks: List[str] = []
        for node in reranked_nodes:
            context: str = node.text
            context += f"[METADATA] RELATED_IMAGE_PATHS: {node.metadata.IMAGE_PATHS} [/METADATA]"
            chunks.append(txtprocessor.normalize_content(context))
        
        print("[Search Index] Context extracted successfully from retrieved nodes.....")
        return '\n-----\n'.join(chunks)
    

    def _update_docs_index(self, update_source_docs: Dict[str,List[tuple]]) -> bool:
        """Updates the documents stored in search index with provided information"""
        updated_docs: List[Document]= []
        top_k = settings.TOP_K * 2

        for filename in update_source_docs:
            filters = MetadataFilters(filters=[ExactMatchFilter(key='file_name', value=filename)])
            retriever = self._index.as_retriever(
                similarity_top_k=top_k, 
                filters=filters, 
                vector_store_query_mode=VectorStoreQueryMode.HYBRID
            )
            
            for label, img_path in update_source_docs[filename]:
                nodes: List[NodeWithScore] = retriever.retrieve(label)
                for node in nodes:
                    node.metadata['image_path'] = node.metadata.get('image_path',"") + f' {img_path} '
                    updated_docs.append(Document(
                        doc_id=list(node.node.relationships.values())[0].__dict__['node_id'],
                        text=node.get_content(),
                        metadata=node.metadata
                    ))
            
        is_updated: bool = all(self._index.refresh_ref_docs(updated_docs))
        print("[Search Index] Documents updated with images successfully....")
        return is_updated
    
    
    def _update_index_insertion_helper(self, file: str) -> Tuple[List[Document], Optional[List[tuple]]]:
        """Helper function. Fetches images from documents in database for indexing"""
        image_docs: List[Document] = []
        labeled_docs: List[tuple] = []

        if os.path.isfile(file):
            image_docs, labels, temp_dir = contentprocessor.extract(file, IMG_DIR, TEMP_IMG_DIR, image_docs)
            if temp_dir and os.listdir(temp_dir):
                selected_labels = imgprocessor.get_image_related_text(labels, temp_dir, IMG_DIR)
                labeled_docs = [(label,selected_labels[label],os.path.basename(file)) for label in selected_labels]
            contentprocessor.clean_temp_dir(temp_dir)

        return image_docs, labeled_docs
    

    def _get_reranked_nodes(self, query: str, nodes: List[SourceNode]) -> List[SourceNode]:
        """Return a sequence[SourceNode] of 'top_k' reranked nodes in sorted order"""
        # Semantic reranking using cross encoder
        pairs = [(query, node.text) for node in nodes]
        scores = self._reranker.predict(pairs)

        scored_nodes = list(zip(nodes, scores))
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        print("[Search Index] Fetched nodes reranked successfully....")
        
        return [node for node, score in scored_nodes[:settings.TOP_K]]
    
    
    def _get_extractors(self) -> Tuple[DocumentContextExtractor,QuestionsAnsweredExtractor,SummaryExtractor]:
        """Return additional extractors (Context, Question, Summary) to be applied on documents before indexing"""
        # create document context retriver
        context_extractor = DocumentContextExtractor(
            docstore=self._docstore,
            max_context_length=1000,
            max_output_tokens=100,
            key="context",
            prompt="""
            You are given a text fragment. Perform the following steps clearly and precisely:\
            1. Disambiguate pronouns and ambiguous terms: Replace any pronouns or vague references with their full, specific referents.\
            2. Extract main topics, entities, and actions, phrasing them as descriptive keywords or short phrases, using comma-separated format.\
            3. Exclude any meta-commentary or instruction about the process itself; only list the contextual phrases.\
            Output in one line as comma-separated phrases.
            """
        )
        # Fetch Possible questions that can be answered by document node
        questions_extractor = QuestionsAnsweredExtractor(
            questions=3, 
            embedding_only=False,
            prompt_template= """\
            Here is the context:
            {context_str}
            Given the contextual information, generate {num_questions} questions this context can provide specific answers to which are unlikely to be found elsewhere.\
            Each query must be of equal length (approximately 30 words), encapsulating the essence of the information, each reflecting a different semantic interpretation while preserving all critical and unique keywords.\
            Higher-level summaries of surrounding context may be provided as well. Try using these summaries to generate better questions that this context can answer.\
            Do not provide meta-commentary of itself.
            """
        )
        # Generate the Summary of document node along
        summary_extractor = SummaryExtractor(
            prompt_template="""\
            Here is the content of the section:
            {context_str}
            Summarize the key topics and entities of the section preserving the essence of information and unquie keywords while providing a new contextual meaning or semantic meaning.\
            Summary: """
        )

        return context_extractor,questions_extractor,summary_extractor