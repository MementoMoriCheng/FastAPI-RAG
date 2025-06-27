import logging
from minio import Minio as MinioClient
from minio.error import S3Error
from io import BytesIO

logger = logging.getLogger(__name__)


class MinioStorage:
    def __init__(self, endpoint, access_key, secret_key, secure=False):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.client = None
        self.connect()

    def connect(self):
        """建立 MinIO 客户端连接"""
        try:
            self.client = MinioClient(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
            logger.info("Connected to MinIO")
        except Exception as e:
            logger.error(f"Failed to connect to MinIO: {e}")

    def health(self) -> bool:
        """检查 MinIO 是否可用"""
        if not self.client:
            return False
        try:
            self.client.list_buckets()
            return True
        except Exception as e:
            logger.error(f"MinIO health check failed: {e}")
            return False

    def put(self, bucket: str, filename: str, data: bytes) -> bool:
        """上传字节流到 MinIO"""
        for i in range(3):  # 尝试重试3次
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                self.client.put_object(bucket, filename, BytesIO(data), len(data))
                return True
            except S3Error as e:
                logger.warning(f"MinIO put error (retry {i + 1}/3): {e}")
                self.connect()
                # time.sleep(1)
        return False

    def get(self, bucket: str, filename: str) -> bytes | None:
        """从 MinIO 获取对象内容"""
        for i in range(3):  # 尝试重试3次
            try:
                response = self.client.get_object(bucket, filename)
                return response.read()
            except S3Error as e:
                logger.warning(f"MinIO get error (retry {i + 1}/3): {e}")
                self.connect()
                # time.sleep(1)
        return None

    def obj_exists(self, bucket: str, filename: str) -> bool:
        """检查对象是否存在"""
        try:
            self.client.stat_object(bucket, filename)
            return True
        except S3Error as e:
            if e.code in ["NoSuchKey", "NoSuchBucket"]:
                return False
            raise

    def list_buckets_with_info(self):
        try:
            buckets = self.client.list_buckets()
            return [{"name": b.name, "created": b.creation_date} for b in buckets]
        except Exception as e:
            logging.error(f"Failed to list buckets with info: {e}")
            return []

    def rm_file(self, bucket, filename):
        """删除对象文件"""
        try:
            self.client.remove_object(bucket, filename)
        except Exception:
            logging.exception(f"Fail to remove {bucket}/{filename}:")

    def rm_bucket(self, bucket):
        """删除对象"""
        try:
            self.client.remove_bucket(bucket)
        except Exception:
            logging.exception(f"Fail to remove {bucket}")


if __name__ == "__main__":
    # 初始化 MinioStorage 对象
    minio_storage = MinioStorage(
        endpoint="192.168.0.104:9000",
        access_key="miniouser",
        secret_key="miniouser123.",
        secure=False
    )

    # 检查健康状态
    print("Health Check:", "Passed" if minio_storage.health() else "Failed")
    # buckets = minio_storage.list_buckets_with_info()
    # print("连接成功！可用存储桶:")
    # for bucket in buckets:
    #     print(f"- {bucket}")

    test_bucket = "rag-kb"
    test_file = "testfile.txt"
    test_content = b"Hello, MinIO!"

    # 测试上传
    # if minio_storage.put(test_bucket, test_file, test_content):
    #     print(f"Successfully uploaded {test_file} to {test_bucket}")
    # else:
    #     print(f"Failed to upload {test_file} to {test_bucket}")

    test_file1 = "testfile.txt"
    test_content1 = b"Hello, MinIO!hahha"
    # 测试上传
    if minio_storage.put(test_bucket, test_file1, test_content1):
        print(f"Successfully uploaded {test_file1} to {test_bucket}")
    else:
        print(f"Failed to upload {test_file1} to {test_bucket}")
    # 测试对象是否存在
    # if minio_storage.obj_exists(test_bucket, test_file):
    #     print(f"{test_file} exists in {test_bucket}")
    # else:
    #     print(f"{test_file} does not exist in {test_bucket}")

    # 测试下载
    # downloaded_data = minio_storage.get(test_bucket, test_file)
    # print(downloaded_data)
    # if downloaded_data:
    #     print(f"Downloaded content matches: {downloaded_data == test_content}")
    # else:
    #     print("Failed to download file.")

    # 删除文件
    # minio_storage.rm_file(test_bucket, test_file)

    # 删除bucket
    # minio_storage.rm_bucket(test_bucket)