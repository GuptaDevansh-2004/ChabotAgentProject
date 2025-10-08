import os
import time
from typing import Any, List, Optional
from dotenv import load_dotenv
load_dotenv()
#-----Libraries utilized for live monitoring------
from collections import deque
from threading import Thread, Event, Lock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
#---Custom functionality utilization libraries----
from index_service.seach_index import SearchIndex

#--------Path for data storage location-----------
DOCS_DIR: Any = os.getenv('DOCS_DIR')


class IndexServiceMonitor:
    """Provide utilities to perform operation corresponding to change in database of search index"""

    def __init__(self) -> None:
        self.monitor = None # store the monitor of index service
        self.IS_MONITORING = Event() # store the monitoring signal for index monitoring service
        self._STOP_MONITORING = Event() # send stop signal to observer of index moniyor
        
        self._INSERT_FILE = Lock() # create thread locker for new data file(s) to be indexed
        self._INSERT_QUEUE = deque() # create a queue to handle new data file(s) in directory
        self._DELETE_FILE = Lock() # create thread locker for handling data file(s) deleted
        self._DELETE_QUEUE = deque() # create a queue to handle deleted data file(s) in directory
        self._MODIFY_FILE = Lock() # create thread locker for handling data file(s) modified
        self._MODIFY_QUEUE = deque() # create a queue to handle modified data file(s) in directory
        
        self._DEBOUNCE_DELAY = 5  # time(in seconds) to wait before processing next batch
        self._file_change_handler = self.FileChangeHandler(self)
        

    def start(self) -> None:
        """Execute monitoring of changes in database for upsertion in search index"""
        assert os.path.isdir(DOCS_DIR), f"[Index Service Monitor] database to be monitored not found: {DOCS_DIR}"
        IS_MONITORING = Event()
        self.monitor = Thread(target=self._start_index_monitoring, daemon=True, args=(IS_MONITORING,))
        self.monitor.start()
        self.IS_MONITORING = IS_MONITORING


    def stop(self) -> Event:
        """Evoke execution of index serive monitoring instance. Returns True on safe termination"""
        self._STOP_MONITORING.set() # Signal all the indexing processes to terminate 
        return self.IS_MONITORING


    def _start_index_monitoring(self, MONITORED: Event) -> None:
        """Keep watching for addition of new documents in knowledge base and update search index with their content."""
        IS_WORKING = Event() # Set a flag for indexing operation by worker

        thread = Thread(target=self._debounce_index_worker, daemon=True, args=(IS_WORKING,))
        thread.start()
        # Start a monitoring instance for monitoring change in database
        observer = Observer()
        observer.schedule(self._file_change_handler, DOCS_DIR, recursive=False)
        observer.start()
        print(f"[Index Service Monitor][Observer] Running. Monitoring '{DOCS_DIR}' for updates...")

        while not IS_WORKING.is_set():
            time.sleep(1)

        print(f"[Index Service Monitor][Observer] Shutting down. Cannot monitor for more updates in knowledge base {DOCS_DIR}...")
        thread.join()
        observer.stop()
        observer.join()
        MONITORED.set() # indicated main thread about safe termination of index service monitor


    def _debounce_index_worker(self, EXECUTED: Event) -> None:
        """Sets the new/updated files in database for indexing in batches"""
        print("[Index Service Monitor][Worker] Handling of updates in database initiated......")
        sub_workers: List[Event] = [] # stores the completeion signal send by the indexing workers
        threads: List[Thread] = [] 

        while not self._STOP_MONITORING.is_set():
            time.sleep(self._DEBOUNCE_DELAY)

            # Checks for documents to be inserted in search index
            with self._INSERT_FILE:
                # Take all queued files for indexing
                files_to_insert = list(set(self._INSERT_QUEUE))
                self._INSERT_QUEUE.clear()
            # Process the entire file batch in separate thread
            if files_to_insert:
                IS_INSERTED = Event()
                sub_workers.append(IS_INSERTED)
                thread = Thread(target=self._process_index_insertion_batch, args=(files_to_insert, IS_INSERTED), daemon=True)
                threads.append(thread)
                thread.start()

            # Checks for documents to be deleted from search index
            with self._DELETE_FILE:
                # Take all queued files to delete from indexing
                files_to_delete = list(set(self._DELETE_QUEUE))
                self._DELETE_QUEUE.clear()
            # Process the entire file batch in separate thread
            if files_to_delete:
                IS_DELETED = Event()
                sub_workers.append(IS_DELETED)
                thread = Thread(target=self._process_index_deletion_batch, args=(files_to_delete, IS_DELETED), daemon=True)
                threads.append(thread)
                thread.start()

             # Checks for documents to be modified in search index
            with self._MODIFY_FILE:
                # Take all queued modified files for indexing
                files_to_modify = list(set(self._MODIFY_QUEUE))
                self._MODIFY_QUEUE.clear()
            # Process the entire file batch in separate thread
            if files_to_modify:
                IS_MODIFIED = Event()
                sub_workers.append(IS_MODIFIED)
                thread = Thread(target=self._process_index_modification_batch, args=(files_to_modify, IS_MODIFIED), daemon=True)
                threads.append(thread)
                thread.start()

        # Terminates all the sub working thread before exiting the main index worker
        while True:
            all_indexed: bool  = True
            for sub_worker in sub_workers:
                all_indexed = all_indexed and sub_worker.is_set()
            if all_indexed:
                break
            time.sleep(1)

        # Wait for safe termination of all indexing sub workers
        for thread in threads:
            thread.join()
        print("[Index Service Monitor][Worker] All current process terminated successfully.....")
        EXECUTED.set() # Signal's observer thread about completion of all indexing 


    def _process_index_insertion_batch(self, files_to_insert: list, COMPLETED: Event) -> None:
        """Execute the indexing of new documents recieved in database to include in search index"""
        print(f"[Index Service Monitor][Processor] Received file insertion batch of {len(files_to_insert)} files :", [file for file in files_to_insert])

        # Initialize a search index for updating vector store
        index = SearchIndex()
        documents = index.load_data(input_files=files_to_insert)
        index.insert_docs_index(documents)  
        index.update_index_insertion(files_path=files_to_insert)

        time.sleep(1)  # simulate work
        print("[Index Service Monitor][Processor] Batch processing completed for extracting data and indexing new documents.....")
        print("[Index Service Monitor][Processor] Searching in files :", os.listdir(DOCS_DIR))
        COMPLETED.set() # indicates work complete by a indexing batch

    
    def _process_index_deletion_batch(self, files_to_delete: list, COMPLETED: Event) -> None:
        """Execute the deletion of given documents of database from search index"""
        print(f"[Index Service Monitor][Processor] Received files deletion batch of {len(files_to_delete)} files :", [file for file in files_to_delete])

        # Initialize a search index for updating vector store
        index = SearchIndex()  
        index.update_index_deletion(files_path=files_to_delete)

        time.sleep(1)  # simulate work
        print("[Index Service Monitor][Processor] Batch processing completed for deleting documents from search index.....")
        print("[Index Service Monitor][Processor] Searching in files :", os.listdir(DOCS_DIR))
        COMPLETED.set() # indicates work complete by a indexing batch


    def _process_index_modification_batch(self, files_to_modify: list, COMPLETED: Event) -> None:
        """Execute the modification of given documents of database in search index"""
        print(f"[Index Service Monitor][Processor] Received files modification batch of {len(files_to_modify)} files :", [file for file in files_to_modify])

        # Initialize a search index for updating vector store
        index = SearchIndex()  
        # Delete existing data of modified files from search index
        index.update_index_deletion(files_path=files_to_modify)
        # insert modified data of files in search index
        index.update_index_insertion(files_path=files_to_modify)

        time.sleep(1)  # simulate work
        print("[Index Service Monitor][Processor] Batch processing completed for modifying documents in search index.....")
        print("[Index Service Monitor][Processor] Searching in files :", os.listdir(DOCS_DIR))
        COMPLETED.set() # indicates work complete by a indexing batch


    class FileChangeHandler(FileSystemEventHandler):
        """Handles the monitor response on changes in directory data"""

        def __init__(self, index_montior) -> None:
            self._INSERT_FILE = index_montior._INSERT_FILE
            self._INSERT_QUEUE = index_montior._INSERT_QUEUE
            self._DELETE_FILE = index_montior._DELETE_FILE
            self._DELETE_QUEUE = index_montior._DELETE_QUEUE
            self._MODIFY_FILE = index_montior._MODIFY_FILE
            self._MODIFY_QUEUE = index_montior._MODIFY_QUEUE

        def on_created(self, event) -> None:
            """Executes if new file created in directory"""
            if not event.is_directory:
                with self._INSERT_FILE:
                    self._INSERT_QUEUE.append(event.src_path)
        
        def on_deleted(self, event) -> None:
            """Executes if existing file deletes from directory"""
            if not event.is_directory:
                with self._DELETE_FILE:
                    self._DELETE_QUEUE.append(event.src_path)

        def on_modified(self, event) -> None:
            """Executes if existing file modifies in directory"""
            if not event.is_directory:
                with self._MODIFY_FILE:
                    self._MODIFY_QUEUE.append(event.src_path)