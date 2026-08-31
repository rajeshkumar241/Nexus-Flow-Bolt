"""
MongoDB Connection Manager with Graceful Fallback

Provides a robust MongoDB connection with:
- Connection timeout handling
- Graceful fallback to in-memory mock collections when MongoDB is unavailable
- Clear logging for connected vs offline mode
- Environment-based configuration
"""

import os
import logging
from typing import Optional, Any, Dict, List
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError
from pymongo.database import Database
from pymongo.collection import Collection
from bson.objectid import ObjectId
from datetime import datetime

logger = logging.getLogger(__name__)


class MockCollection:
    """In-memory mock collection for offline mode."""
    
    def __init__(self, name: str):
        self.name = name
        self._data: List[Dict] = []
        self._id_counter = 0
    
    def _generate_id(self):
        self._id_counter += 1
        return ObjectId()
    
    def find_one(self, filter_dict: Dict = None, *args, **kwargs) -> Optional[Dict]:
        if filter_dict is None:
            filter_dict = {}
        # Handle sort param (e.g., sort=[("analyzed_at", -1)])
        sort_spec = kwargs.get("sort")
        matched = [doc.copy() for doc in self._data if self._match(doc, filter_dict)]
        if sort_spec:
            try:
                # sort is list of (key, direction) tuples
                for key, direction in reversed(sort_spec):
                    reverse = direction == -1
                    matched.sort(key=lambda x: x.get(key, ""), reverse=reverse)
            except Exception:
                pass
        return matched[0] if matched else None
    
    def find(self, filter_dict: Dict = None, *args, **kwargs):
        if filter_dict is None:
            filter_dict = {}
        return MockCursor([doc.copy() for doc in self._data if self._match(doc, filter_dict)])
    
    def insert_one(self, document: Dict) -> Any:
        doc = document.copy()
        if "_id" not in doc:
            doc["_id"] = self._generate_id()
        self._data.append(doc)
        return MockInsertResult(doc["_id"])
    
    def insert_many(self, documents: List[Dict]) -> Any:
        ids = []
        for doc in documents:
            doc = doc.copy()
            if "_id" not in doc:
                doc["_id"] = self._generate_id()
            ids.append(doc["_id"])
            self._data.append(doc)
        return MockInsertManyResult(ids)
    
    def update_one(self, filter_dict: Dict, update: Dict, *args, **kwargs) -> Any:
        matched = 0
        modified = 0
        for doc in self._data:
            if self._match(doc, filter_dict):
                matched = 1
                if "$set" in update:
                    doc.update(update["$set"])
                    modified = 1
                if "$unset" in update:
                    for key in update["$unset"]:
                        doc.pop(key, None)
                        modified = 1
                if "$inc" in update:
                    for key, val in update["$inc"].items():
                        doc[key] = doc.get(key, 0) + val
                        modified = 1
                break
        # Handle upsert
        if matched == 0 and kwargs.get("upsert"):
            new_doc = {}
            # copy filter (non-operator keys) into doc
            for k, v in filter_dict.items():
                if not k.startswith("$"):
                    new_doc[k] = v
            if "$set" in update:
                new_doc.update(update["$set"])
            if "$setOnInsert" in update:
                for k, v in update["$setOnInsert"].items():
                    if k not in new_doc:
                        new_doc[k] = v
            if "_id" not in new_doc:
                new_doc["_id"] = self._generate_id()
            self._data.append(new_doc)
            return MockUpdateResult(0, 1)
        return MockUpdateResult(matched, modified)
    
    def update_many(self, filter_dict: Dict, update: Dict, *args, **kwargs) -> Any:
        matched = 0
        modified = 0
        for doc in self._data:
            if self._match(doc, filter_dict):
                matched += 1
                if "$set" in update:
                    doc.update(update["$set"])
                    modified += 1
                if "$unset" in update:
                    for key in update["$unset"]:
                        doc.pop(key, None)
                        modified += 1
        return MockUpdateResult(matched, modified)
    
    def delete_one(self, filter_dict: Dict, *args, **kwargs) -> Any:
        for i, doc in enumerate(self._data):
            if self._match(doc, filter_dict):
                self._data.pop(i)
                return MockDeleteResult(1)
        return MockDeleteResult(0)
    
    def delete_many(self, filter_dict: Dict, *args, **kwargs) -> Any:
        initial_len = len(self._data)
        self._data = [doc for doc in self._data if not self._match(doc, filter_dict)]
        return MockDeleteResult(initial_len - len(self._data))
    
    def count_documents(self, filter_dict: Dict = None, *args, **kwargs) -> int:
        if filter_dict is None:
            return len(self._data)
        return sum(1 for doc in self._data if self._match(doc, filter_dict))
    
    def aggregate(self, pipeline: List[Dict], *args, **kwargs):
        return []
    
    def create_index(self, *args, **kwargs):
        pass
    
    def _match(self, doc: Dict, filter_dict: Dict) -> bool:
        for key, value in filter_dict.items():
            if key.startswith("$"):
                continue
            if key not in doc:
                return False
            if isinstance(value, dict):
                for op, op_value in value.items():
                    if op == "$regex":
                        import re
                        if not re.search(op_value, str(doc[key]), re.IGNORECASE if "$options" in value and "i" in value["$options"] else 0):
                            return False
                    elif op == "$in":
                        if doc[key] not in op_value:
                            return False
                    elif op == "$ne":
                        if doc[key] == op_value:
                            return False
                    elif op == "$gte":
                        if doc[key] < op_value:
                            return False
                    elif op == "$lte":
                        if doc[key] > op_value:
                            return False
            else:
                if doc[key] != value:
                    return False
        return True


class MockCursor:
    def __init__(self, data: List[Dict]):
        self._data = data
        self._skip = 0
        self._limit = None
        self._sort = None
    
    def skip(self, n: int):
        self._skip = n
        return self
    
    def limit(self, n: int):
        self._limit = n
        return self
    
    def sort(self, key: str, direction: int = 1):
        self._sort = (key, direction)
        return self
    
    def __iter__(self):
        data = self._data
        if self._sort:
            key, direction = self._sort
            data = sorted(data, key=lambda x: x.get(key, ""), reverse=(direction == -1))
        if self._skip:
            data = data[self._skip:]
        if self._limit:
            data = data[:self._limit]
        return iter(data)
    
    def __list__(self):
        return list(self.__iter__())
    
    def to_list(self, length=None):
        data = list(self.__iter__())
        if length:
            return data[:length]
        return data


class MockInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id
        self.acknowledged = True


class MockInsertManyResult:
    def __init__(self, inserted_ids):
        self.inserted_ids = inserted_ids
        self.acknowledged = True


class MockUpdateResult:
    def __init__(self, matched_count: int, modified_count: int):
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.acknowledged = True


class MockDeleteResult:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count
        self.acknowledged = True


class MockDatabase:
    """Mock database for offline mode."""
    
    def __init__(self):
        self._collections: Dict[str, MockCollection] = {}
    
    def __getattr__(self, name: str) -> MockCollection:
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]
    
    def __getitem__(self, name: str) -> MockCollection:
        return self.__getattr__(name)
    
    def list_collection_names(self):
        return list(self._collections.keys())


class MongoConnectionManager:
    """Manages MongoDB connection with graceful fallback."""
    
    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._mock_db: Optional[MockDatabase] = None
        self._is_connected = False
        self._connection_attempted = False
        self._uri: Optional[str] = None
        self._timeout_ms: int = 5000
    
    def initialize(self, uri: Optional[str] = None, timeout_ms: int = 5000) -> bool:
        """Initialize MongoDB connection with timeout.
        
        Args:
            uri: MongoDB connection URI (defaults to MONGO_URI env var)
            timeout_ms: Connection timeout in milliseconds
            
        Returns:
            True if connected to real MongoDB, False if using fallback
        """
        self._uri = uri or os.getenv("MONGO_URI")
        self._timeout_ms = timeout_ms
        self._connection_attempted = True
        
        if not self._uri:
            self._enable_offline_mode()
            return False
        
        try:
            self._client = MongoClient(
                self._uri,
                serverSelectionTimeoutMS=self._timeout_ms,
                connectTimeoutMS=self._timeout_ms,
                socketTimeoutMS=self._timeout_ms,
            )
            
            self._client.admin.command("ping")
            
            self._db = self._client.get_default_database()
            if self._db is None:
                from urllib.parse import urlparse
                parsed = urlparse(self._uri)
                db_name = parsed.path.lstrip("/") or "nexus_flow"
                self._db = self._client[db_name]
            
            self._is_connected = True
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError, Exception):
            # Normal offline state - no stack trace, no noisy error
            logger.debug("MongoDB ping failed - switching to offline mode", exc_info=False)
            self._enable_offline_mode()
            return False
    
    def _enable_offline_mode(self):
        """Enable offline mode with mock collections."""
        self._is_connected = False
        self._mock_db = MockDatabase()
        self._db = self._mock_db
    
    @property
    def db(self) -> Database:
        """Get the database instance (real or mock)."""
        if self._db is None:
            self.initialize()
        return self._db
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to real MongoDB."""
        return self._is_connected
    
    @property
    def is_offline(self) -> bool:
        """Check if running in offline mode."""
        return not self._is_connected
    
    def get_collection(self, name: str) -> Collection:
        """Get a collection (real or mock)."""
        return self.db[name]
    
    def close(self):
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._is_connected = False


# Global instance
_mongo_manager: Optional[MongoConnectionManager] = None


def get_mongo_manager() -> MongoConnectionManager:
    """Get the global MongoDB connection manager."""
    global _mongo_manager
    if _mongo_manager is None:
        _mongo_manager = MongoConnectionManager()
    return _mongo_manager


def init_mongo(uri: Optional[str] = None, timeout_ms: int = 5000) -> bool:
    """Initialize MongoDB connection (convenience function)."""
    manager = get_mongo_manager()
    return manager.initialize(uri, timeout_ms)


def get_db() -> Database:
    """Get the database instance (real or mock)."""
    return get_mongo_manager().db


def is_mongo_connected() -> bool:
    """Check if connected to real MongoDB."""
    return get_mongo_manager().is_connected


def is_mongo_offline() -> bool:
    """Check if running in offline mode."""
    return get_mongo_manager().is_offline