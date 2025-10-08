'''
Entry point for indexing serivce. Indexes documents from database in search index along
with Live Monitoring of database for change in documents like insertion or updation of new documents 

Important Points:
1. Execute the program directly from 'search_service' directory (not from parent or sub directories)
   In CLI direct to 'search_service' then execute: 'python -m index_service.indexer'
'''

import time
from threading import Event
from index_service.seach_index import SearchIndex
from index_service.watcher import IndexServiceMonitor


def index_database() -> None:
    """Index all the documents of database in search index"""
    search_index: SearchIndex = SearchIndex(clear_existing_collection=True, index_docs=True)


def start_indexing() -> None:
    """Executes indexing of documents in database in search index with support for live monitoring"""
    # Index all the documents initially
    index_database()
    # Initiate live monitoring of search index
    print("[Main Processor] Live Monitoring the Search Index........")
    index_monitor: IndexServiceMonitor = IndexServiceMonitor()
    index_monitor.start()

    try:
        while True:
            time.sleep(1)
    except BaseException as e:
        print("[Main Processor] Termination of search index monitor initialized.....")

    STOP_MONITOR: Event = index_monitor.stop() # Indicates if search index monitor terminated successfuly 

    while not STOP_MONITOR.is_set():
        try:
            time.sleep(1)
        except BaseException as e:
            print("[Main Processor] Termination of Live Monitor in progress......")

    print("[Main Processor] Search Index Live Monitoring Terminated.......")


if __name__ == '__main__':
    start_indexing()