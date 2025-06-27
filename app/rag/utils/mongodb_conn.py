from pymongo import MongoClient


class MongoDBManager:
    def __init__(self, host='192.168.0.103',
                 port=27017,
                 db_name='langchain_rag',
                 collection_name='kb',
                 username=None,
                 password=None):
        """
        初始化 MongoDB 连接，并自动创建默认数据库和集合（如果不存在）
        :param host: MongoDB 服务器地址
        :param port: MongoDB 端口
        :param db_name: 数据库名称
        :param collection_name: 集合名称
        :param username: 用户名（用于认证）
        :param password: 密码（用于认证）
        """
        # 初始化连接
        if username and password:
            self.client = MongoClient(
                host=host,
                port=port,
                username=username,
                password=password,
            )
        else:
            self.client = MongoClient(host, port)
        self.db = self.client[db_name]
        self.collection_name = collection_name

        # 获取集合对象
        self.collection = self.db[self.collection_name]

    def list_collection_names(self):
        return self.db.list_collection_names()

    def insert_one(self, document):
        """插入单条文档"""
        result = self.collection.insert_one(document)
        print(f"Inserted document ID: {result.inserted_id}")
        return result.inserted_id

    def insert_many(self, documents):
        """批量插入多条文档"""
        result = self.collection.insert_many(documents)
        print(f"Inserted {len(result.inserted_ids)} documents")
        return result.inserted_ids

    def find_one(self, query=None):
        """查询单条文档"""
        return self.collection.find_one(query)

    def find_all(self, query=None, page=1, page_size=10):
        """分页查询所有文档"""
        skip = (page - 1) * page_size
        cursor = self.collection.find(query).skip(skip).limit(page_size)
        return list(cursor)

    def update_one(self, filter, update_data):
        """更新单条文档"""
        result = self.collection.update_one(filter, {"$set": update_data})
        print(f"Matched {result.matched_count}, Modified {result.modified_count} documents")
        return result.modified_count

    def update_many(self, filter, update_data):
        """更新多条文档"""
        result = self.collection.update_many(filter, {"$set": update_data})
        print(f"Matched {result.matched_count}, Modified {result.modified_count} documents")
        return result.modified_count

    def delete_one(self, filter):
        """删除单条文档"""
        result = self.collection.delete_one(filter)
        print(f"Deleted {result.deleted_count} document")
        return result.deleted_count

    def delete_many(self, filter):
        """删除多条文档"""
        result = self.collection.delete_many(filter)
        print(f"Deleted {result.deleted_count} documents")
        return result.deleted_count

    def close(self):
        """关闭连接"""
        self.client.close()
        print("MongoDB connection closed")


mongo = MongoDBManager(
    host="192.168.0.103",
    port=27017,
    db_name="langchain_rag",
    collection_name="kb",
    username="root",
    password="root",
)
# ✅ 示例：使用 MongoDBManager 类
if __name__ == "__main__":
    # 1. 初始化连接
    mongo = MongoDBManager(
        host="192.168.0.103",
        port=27017,
        db_name="langchain_rag",
        collection_name="kb",
        username="root",
        password="root",
    )
    # print(mongo.list_collection_names())
    # 2. 插入数据
    # doc1 = {"name": "Alice", "age": 25, "city": "New York"}
    # doc2 = {"name": "Bob", "age": 30, "city": "San Francisco"}
    # doc3 = {"name": "Charlie", "age": 22, "city": "Los Angeles"}
    # mongo.insert_one(doc1)
    # mongo.insert_many([doc2, doc3])

    # 3. 查询数据
    # print("\nAll students:")
    # for student in mongo.find_all():
    #     print(student)
    #
    # mongo.find_one()

    # print("\nFind Alice:")
    print(mongo.find_one({"content_ltks": "excel"}))

    # # 4. 更新数据
    # mongo.update_one({"name": "Alice"}, {"age": 26})
    # print("\nAfter updating Alice's age:")
    # print(mongo.find_one({"name": "Alice"}))
    #
    # # 5. 删除数据
    # mongo.delete_one({"name": "Alice"})
    # print("\nAfter deleting Alice:")
    # for student in mongo.find_all():
    #     print(student)

    # 6. 关闭连接
    mongo.close()
