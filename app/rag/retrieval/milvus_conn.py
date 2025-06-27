import time
import random
import numpy as np
from pymilvus import (
    connections,
    FieldSchema, CollectionSchema, DataType,
    Collection, utility, MilvusClient
)


class MilvusCRUD:
    def __init__(self, uri="http://localhost:19530", token="root:Milvus"):
        """
        初始化 Milvus 连接
        :param host: Milvus 服务器地址
        :param port: Milvus 端口
        :param user: 用户名
        :param password: 密码
        """
        self.uri = uri
        self.token = token
        self.client = None
        # 连接 Milvus
        self.connect()

        # 当前操作的集合
        self.collection = None

    def connect(self):
        """连接到 Milvus 服务器"""
        try:
            self.client = MilvusClient(
                uri=self.uri,
                token=self.token
            )
            print(f"✅ 成功连接到 Milvus: {self.uri}")
        except Exception as e:
            print(f"❌ 连接失败: {str(e)}")
            raise

    def disconnect(self):
        """断开 Milvus 连接"""
        connections.disconnect("default")
        print("✅ 已断开 Milvus 连接")

    def create_collection(self, collection_name, dim=128, description="Book collection"):
        """
        创建新的集合
        :param collection_name: 集合名称
        :param dim: 向量维度
        :param description: 集合描述
        """
        # 检查集合是否存在
        if self.client.has_collection(collection_name):
            print(f"⚠️ 集合 '{collection_name}' 已存在")
            self.collection = Collection(collection_name)
            return

        # 定义字段
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="docnm_kwd", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="kwd_embedding", dtype=DataType.FLOAT16_VECTOR, dim=dim),

            FieldSchema(name="content_with_weight", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="content_embedding", dtype=DataType.FLOAT16_VECTOR, dim=dim),
            FieldSchema(name="sparse_content_embedding", dtype=DataType.SPARSE_FLOAT_VECTOR, dim=dim)
        ]

        # 创建集合模式
        schema = CollectionSchema(
            fields=fields,
            description=description,
            enable_dynamic_field=True  # 允许动态字段
        )

        # 创建集合
        try:
            self.collection = Collection(
                name=collection_name,
                schema=schema,
                using="default",
                shards_num=2
            )
            print(f"✅ 成功创建集合 '{collection_name}'")

            # 创建索引
            self.create_index()

        except Exception as e:
            print(f"❌ 创建集合失败: {str(e)}")
            raise

    def create_index(self, index_type="IVF_FLAT", metric_type="L2", nlist=1024):
        """
        为向量字段创建索引
        :param index_type: 索引类型
        :param metric_type: 距离度量类型
        :param nlist: 聚类中心数量
        """
        if not self.collection:
            print("❌ 请先选择或创建一个集合")
            return

        # 检查索引是否已存在
        if self.collection.has_index():
            print(f"⚠️ 集合 '{self.collection.name}' 已有索引")
            return

        index_params = self.client.prepare_index_params()
        # 定义索引参数
        index_params = {
            "index_type": index_type,
            "metric_type": metric_type,
            "params": {"nlist": nlist}
        }

        # 创建索引
        try:
            self.collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            print(f"✅ 成功为字段 'embedding' 创建 {index_type} 索引")
        except Exception as e:
            print(f"❌ 创建索引失败: {str(e)}")
            raise

    def load_collection(self, collection_name):
        """
        加载已存在的集合
        :param collection_name: 集合名称
        """
        try:
            self.collection = Collection(collection_name)
            print(f"✅ 已加载集合 '{collection_name}'")
        except Exception as e:
            print(f"❌ 加载集合失败: {str(e)}")
            raise

    def insert_data(self, data):
        """
        插入数据到集合
        :param data: 要插入的数据字典
        """
        if not self.collection:
            print("❌ 请先选择或创建一个集合")
            return 0

        # 准备数据
        entities = []
        for field in self.collection.schema.fields:
            if field.name in data and field.name != "id":  # 跳过自动生成的ID
                entities.append(data[field.name])

        # 插入数据
        try:
            # 加载集合到内存
            self.collection.load()

            # 执行插入
            insert_result = self.collection.insert(entities)

            # 刷新使数据可搜索
            self.collection.flush()

            print(f"✅ 成功插入 {len(insert_result.primary_keys)} 条数据")
            return insert_result.primary_keys
        except Exception as e:
            print(f"❌ 插入数据失败: {str(e)}")
            return []
        finally:
            # 释放内存
            self.collection.release()

    def batch_insert(self, data_list):
        """
        批量插入数据
        :param data_list: 数据字典列表
        """
        if not self.collection:
            print("❌ 请先选择或创建一个集合")
            return 0

        # 准备批量数据
        entities_dict = {field.name: [] for field in self.collection.schema.fields if field.name != "id"}

        for data in data_list:
            for field in entities_dict:
                if field in data:
                    entities_dict[field].append(data[field])

        # 转换为列表格式
        entities = [entities_dict[field] for field in entities_dict]

        # 插入数据
        try:
            # 加载集合到内存
            self.collection.load()

            # 执行插入
            insert_result = self.collection.insert(entities)

            # 刷新使数据可搜索
            self.collection.flush()

            print(f"✅ 成功批量插入 {len(insert_result.primary_keys)} 条数据")
            return insert_result.primary_keys
        except Exception as e:
            print(f"❌ 批量插入失败: {str(e)}")
            return []
        finally:
            # 释放内存
            self.collection.release()

    def search(self, query_vector, limit=5, output_fields=["title", "author", "year"]):
        """
        执行向量搜索
        :param query_vector: 查询向量
        :param limit: 返回结果数量
        :param output_fields: 返回的字段列表
        """
        if not self.collection:
            print("❌ 请先选择或创建一个集合")
            return []

        # 搜索参数
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 16}  # 搜索的聚类中心数
        }

        try:
            # 加载集合到内存
            self.collection.load()

            # 执行搜索
            start_time = time.time()
            results = self.collection.search(
                data=[query_vector],
                anns_field="embedding",
                param=search_params,
                limit=limit,
                output_fields=output_fields
            )
            search_time = time.time() - start_time

            # 处理结果
            search_results = []
            for hits in results:
                for hit in hits:
                    result = {
                        "id": hit.id,
                        "distance": hit.distance,
                        "entity": hit.entity.to_dict()
                    }
                    search_results.append(result)

            print(f"🔍 搜索完成，耗时 {search_time:.4f} 秒")
            return search_results
        except Exception as e:
            print(f"❌ 搜索失败: {str(e)}")
            return []
        finally:
            # 释放内存
            self.collection.release()

    def query_by_id(self, ids, output_fields=["title", "author", "year", "embedding"]):
        """
        按ID查询实体
        :param ids: 实体ID列表
        :param output_fields: 返回的字段列表
        """
        if not self.collection:
            print("❌ 请先选择或创建一个集合")
            return []

        # 构建查询表达式
        expr = f"id in {ids}" if isinstance(ids, list) else f"id == {ids}"

        try:
            # 加载集合到内存
            self.collection.load()

            # 执行查询
            results = self.collection.query(
                expr=expr,
                output_fields=output_fields
            )

            print(f"✅ 找到 {len(results)} 条匹配记录")
            return results
        except Exception as e:
            print(f"❌ 查询失败: {str(e)}")
            return []
        finally:
            # 释放内存
            self.collection.release()

    def update(self, id, update_data):
        """
        更新实体
        :param id: 实体ID
        :param update_data: 更新数据字典
        """
        if not self.collection:
            print("❌ 请先选择或创建一个集合")
            return False

        # 检查实体是否存在
        entity = self.query_by_id(id)
        if not entity:
            print(f"❌ ID {id} 的实体不存在")
            return False

        # 构建更新表达式
        set_expr = ", ".join([f"{key} = {repr(value)}" for key, value in update_data.items()])
        expr = f"id == {id}"

        try:
            # 加载集合到内存
            self.collection.load()

            # 执行更新
            result = self.collection.update(
                expr=expr,
                set_expr=set_expr
            )

            # 刷新使更改生效
            self.collection.flush()

            print(f"✅ 成功更新 ID {id} 的实体")
            return True
        except Exception as e:
            print(f"❌ 更新失败: {str(e)}")
            return False
        finally:
            # 释放内存
            self.collection.release()

    def delete(self, ids):
        """
        删除实体
        :param ids: 要删除的实体ID或ID列表
        """
        if not self.collection:
            print("❌ 请先选择或创建一个集合")
            return 0

        # 构建删除表达式
        if isinstance(ids, list):
            expr = f"id in {ids}"
        else:
            expr = f"id == {ids}"

        try:
            # 加载集合到内存
            self.collection.load()

            # 执行删除
            result = self.collection.delete(expr)

            # 刷新使删除生效
            self.collection.flush()

            deleted_count = result.delete_count
            print(f"✅ 成功删除 {deleted_count} 条记录")
            return deleted_count
        except Exception as e:
            print(f"❌ 删除失败: {str(e)}")
            return 0
        finally:
            # 释放内存
            self.collection.release()

    def drop_collection(self, collection_name=None):
        """
        删除集合
        :param collection_name: 要删除的集合名称，默认为当前集合
        """
        target_name = collection_name or (self.collection.name if self.collection else None)
        if not target_name:
            print("❌ 请指定要删除的集合名称")
            return False

        # 检查集合是否存在
        if not self.client.has_collection(target_name):
            print(f"⚠️ 集合 '{target_name}' 不存在")
            return False

        try:
            # 删除集合
            self.client.drop_collection(target_name)
            print(f"✅ 成功删除集合 '{target_name}'")

            # 如果删除的是当前集合，则重置引用
            if self.collection and self.collection.name == target_name:
                self.collection = None

            return True
        except Exception as e:
            print(f"❌ 删除集合失败: {str(e)}")
            return False

    def get_collection_stats(self):
        """获取集合统计信息"""
        # if not self.collection:
        #     print("❌ 请先选择或创建一个集合")
        #     return {}

        try:
            # stats = self.client.get_collection_stats(self.collection.name)
            stats = self.client.describe_collection("kb_collection")
            return stats
        except Exception as e:
            print(f"❌ 获取统计信息失败: {str(e)}")
            return {}

    def list_collections(self):
        """列出所有集合"""
        try:
            collections = self.client.list_collections()
            return collections
        except Exception as e:
            print(f"❌ 获取集合列表失败: {str(e)}")
            return []


# 示例用法
if __name__ == "__main__":
    from pprint import pprint

    # 1. 初始化 Milvus CRUD
    milvus = MilvusCRUD("http://192.168.0.104:19530", "root:S1nexcel123.")
    # "    sinexcel_ai_vector    ")

    # 2. 创建新集合
    COLLECTION_NAME = "kb_collection"
    milvus.create_collection(COLLECTION_NAME, dim=128)
    #
    # 3. 插入单条数据
    # book_data = {
    #     "title": "The Great Gatsby",
    #     "author": "F. Scott Fitzgerald",
    #     "year": 1925,
    #     "embedding": np.random.rand(128).tolist()  # 128维随机向量
    # }
    # inserted_id = milvus.insert_data(book_data)[0]
    # print(f"插入数据的ID: {inserted_id}")
    #
    # # 4. 批量插入数据
    # books = [
    #     {
    #         "title": "To Kill a Mockingbird",
    #         "author": "Harper Lee",
    #         "year": 1960,
    #         "embedding": np.random.rand(128).tolist()
    #     },
    #     {
    #         "title": "1984",
    #         "author": "George Orwell",
    #         "year": 1949,
    #         "embedding": np.random.rand(128).tolist()
    #     },
    #     {
    #         "title": "Pride and Prejudice",
    #         "author": "Jane Austen",
    #         "year": 1813,
    #         "embedding": np.random.rand(128).tolist()
    #     },
    #     {
    #         "title": "The Hobbit",
    #         "author": "J.R.R. Tolkien",
    #         "year": 1937,
    #         "embedding": np.random.rand(128).tolist()
    #     }
    # ]
    # inserted_ids = milvus.batch_insert(books)
    # print(f"批量插入的ID列表: {inserted_ids}")
    #
    # # 5. 查询数据
    # print("\n查询插入的数据:")
    # queried_data = milvus.query_by_id(inserted_id)
    # print(queried_data)
    #
    # # 6. 执行搜索
    # print("\n执行向量搜索:")
    # query_vec = np.random.rand(128).tolist()  # 随机查询向量
    # search_results = milvus.search(query_vec, limit=3)
    #
    # for i, result in enumerate(search_results):
    #     print(f"结果 #{i + 1}:")
    #     print(f"  ID: {result['id']}")
    #     print(f"  距离: {result['distance']:.4f}")
    #     print(f"  标题: {result['entity']['title']}")
    #     print(f"  作者: {result['entity']['author']}")
    #     print(f"  年份: {result['entity']['year']}")
    #
    # # 7. 更新数据
    # update_id = inserted_ids[0]
    # print(f"\n更新 ID {update_id} 的数据:")
    # update_success = milvus.update(update_id, {"year": 1961})
    # if update_success:
    #     updated_data = milvus.query_by_id(update_id)
    #     print("更新后的数据:", updated_data)
    #
    # # 8. 删除数据
    # print("\n删除数据:")
    # delete_count = milvus.delete(inserted_ids[1])
    # print(f"已删除 {delete_count} 条记录")
    #
    # # 9. 获取集合统计
    # print("\n集合统计信息:")
    # stats = milvus.get_collection_stats()
    # pprint(f"详细信息: {stats}")
    #
    # # 10. 列出所有集合
    print("\n所有集合:")
    collections = milvus.list_collections()
    for col in collections:
        print(f"- {col}")

    # 11. 删除集合 (取消注释以执行)
    # print("\n删除集合:")
    # milvus.drop_collection(COLLECTION_NAME)

    # 12. 断开连接
    # milvus.disconnect()
