import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Milvus
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from pymilvus import connections, utility
import streamlit as st
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class MilvusRAGSystem:
    def __init__(self):
        # 初始化配置
        self.milvus_host = os.getenv("MILVUS_HOST", "localhost")
        self.milvus_port = os.getenv("MILVUS_PORT", "19530")
        self.collection_name = os.getenv("MILVUS_COLLECTION", "rag_collection")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        # 初始化模型
        self.embedding_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=self.openai_api_key
        )

        # 初始化LLM
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0.3,
            openai_api_key=self.openai_api_key
        )

        # 连接Milvus
        self._connect_to_milvus()

        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )

    def _connect_to_milvus(self):
        """连接到Milvus数据库"""
        try:
            connections.connect(
                alias="default",
                host=self.milvus_host,
                port=self.milvus_port
            )
            st.success(f"成功连接到Milvus: {self.milvus_host}:{self.milvus_port}")
        except Exception as e:
            st.error(f"连接Milvus失败: {str(e)}")
            raise

    def create_collection(self):
        """创建集合（如果不存在）"""
        if not utility.has_collection(self.collection_name):
            # Milvus集合将通过LangChain的Milvus类自动创建
            st.info(f"集合 '{self.collection_name}' 不存在，将在首次插入时创建")
            return False
        else:
            st.success(f"集合 '{self.collection_name}' 已存在")
            return True

    def load_and_split_documents(self, file_path):
        """加载并分割文档"""
        file_extension = os.path.splitext(file_path)[1].lower()

        try:
            if file_extension == ".pdf":
                loader = PyPDFLoader(file_path)
            elif file_extension in [".txt", ".md"]:
                loader = TextLoader(file_path)
            else:
                raise ValueError(f"不支持的文件类型: {file_extension}")

            documents = loader.load()
            st.info(f"已加载 {len(documents)} 页文档")

            # 分割文档
            split_docs = self.text_splitter.split_documents(documents)
            st.info(f"文档分割为 {len(split_docs)} 个片段")

            return split_docs
        except Exception as e:
            st.error(f"文档加载失败: {str(e)}")
            return None

    def store_documents(self, documents):
        """将文档存储到Milvus"""
        try:
            # 使用LangChain的Milvus集成
            vector_db = Milvus.from_documents(
                documents=documents,
                embedding=self.embedding_model,
                collection_name=self.collection_name,
                connection_args={
                    "host": self.milvus_host,
                    "port": self.milvus_port
                },
                drop_old=True  # 删除现有集合（谨慎使用）
            )

            st.success(f"已将 {len(documents)} 个文档片段存储到Milvus集合 '{self.collection_name}'")
            return vector_db
        except Exception as e:
            st.error(f"文档存储失败: {str(e)}")
            return None

    def initialize_retriever(self, search_kwargs=None):
        """初始化检索器"""
        if search_kwargs is None:
            search_kwargs = {"k": 5}  # 默认返回前5个结果

        try:
            vector_db = Milvus(
                embedding_function=self.embedding_model,
                collection_name=self.collection_name,
                connection_args={
                    "host": self.milvus_host,
                    "port": self.milvus_port
                },
                search_params={"metric_type": "IP", "params": {"nprobe": 16}},
            )

            retriever = vector_db.as_retriever(search_kwargs=search_kwargs)
            return retriever
        except Exception as e:
            st.error(f"检索器初始化失败: {str(e)}")
            return None

    def create_rag_chain(self, retriever):
        """创建RAG链"""
        # 定义提示模板
        template = """你是一个知识渊博的AI助手，使用以下上下文信息回答问题。
        如果不知道答案，请诚实回答不知道，不要编造答案。

        上下文:
        {context}

        问题: {question}

        请提供详细、准确的回答:"""

        prompt = ChatPromptTemplate.from_template(template)

        # 创建RAG链
        chain = (
                {"context": retriever, "question": RunnablePassthrough()}
                | prompt
                | self.llm
                | StrOutputParser()
        )

        return chain

    def search_documents(self, query, k=5):
        """直接在Milvus中搜索文档"""
        try:
            vector_db = Milvus(
                embedding_function=self.embedding_model,
                collection_name=self.collection_name,
                connection_args={
                    "host": self.milvus_host,
                    "port": self.milvus_port
                },
                search_params={"metric_type": "IP", "params": {"nprobe": 16}},
            )

            results = vector_db.similarity_search(query, k=k)
            return results
        except Exception as e:
            st.error(f"文档搜索失败: {str(e)}")
            return []

    def get_collection_stats(self):
        """获取集合统计信息"""
        try:
            stats = utility.get_collection_stats(self.collection_name)
            return stats
        except Exception as e:
            st.error(f"获取集合统计失败: {str(e)}")
            return None

    def delete_collection(self):
        """删除集合"""
        try:
            utility.drop_collection(self.collection_name)
            st.success(f"已删除集合 '{self.collection_name}'")
            return True
        except Exception as e:
            st.error(f"删除集合失败: {str(e)}")
            return False


def main():
    # 设置页面标题和图标
    st.set_page_config(
        page_title="LangChain + Milvus RAG 系统",
        page_icon="🔍",
        layout="wide"
    )

    # 标题和说明
    st.title("🔍 LangChain + Milvus RAG 系统")
    st.markdown("""
    这是一个使用 LangChain 框架和 Milvus 向量数据库实现的检索增强生成 (RAG) 系统。
    上传文档，将其存储在 Milvus 中，然后使用自然语言提问获取答案。
    """)

    # 初始化系统
    if "rag_system" not in st.session_state:
        st.session_state.rag_system = MilvusRAGSystem()
        st.session_state.rag_system.create_collection()

    # 侧边栏配置
    with st.sidebar:
        st.header("配置")
        st.subheader("Milvus 连接")
        st.info(f"主机: {st.session_state.rag_system.milvus_host}")
        st.info(f"端口: {st.session_state.rag_system.milvus_port}")
        st.info(f"集合: {st.session_state.rag_system.collection_name}")

        # 显示集合统计信息
        if st.button("显示集合统计"):
            stats = st.session_state.rag_system.get_collection_stats()
            if stats:
                st.json(stats)

        # 删除集合选项
        if st.button("删除集合", type="secondary"):
            if st.session_state.rag_system.delete_collection():
                st.rerun()

        st.divider()
        st.subheader("文档上传")

        # 文件上传器
        uploaded_file = st.file_uploader(
            "上传文档 (PDF 或 TXT)",
            type=["pdf", "txt", "md"]
        )

        if uploaded_file is not None:
            # 保存上传的文件
            file_path = f"./uploads/{uploaded_file.name}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # 加载并分割文档
            split_docs = st.session_state.rag_system.load_and_split_documents(file_path)

            if split_docs:
                # 存储文档到Milvus
                vector_db = st.session_state.rag_system.store_documents(split_docs)

                if vector_db:
                    # 初始化检索器
                    st.session_state.retriever = st.session_state.rag_system.initialize_retriever()

                    # 创建RAG链
                    st.session_state.rag_chain = st.session_state.rag_system.create_rag_chain(
                        st.session_state.retriever
                    )

    # 主界面
    tab1, tab2 = st.tabs(["问答系统", "文档检索"])

    with tab1:
        st.subheader("基于文档的问答")

        if "rag_chain" not in st.session_state:
            st.warning("请先上传文档以初始化问答系统")
        else:
            question = st.text_input(
                "输入您的问题：",
                placeholder="文档中提到了哪些关键概念？"
            )

            if question:
                with st.spinner("正在检索并生成答案..."):
                    try:
                        # 使用RAG链生成答案
                        answer = st.session_state.rag_chain.invoke(question)

                        # 显示答案
                        st.subheader("答案:")
                        st.markdown(answer)

                        # 显示上下文来源
                        st.divider()
                        st.subheader("来源文档:")

                        # 检索相关文档
                        context_docs = st.session_state.rag_system.search_documents(question, k=3)

                        for i, doc in enumerate(context_docs, 1):
                            st.markdown(f"**来源 {i}:**")
                            st.caption(
                                f"文档: {doc.metadata.get('source', '未知')} | 页码: {doc.metadata.get('page', 'N/A')}")
                            st.markdown(doc.page_content[:500] + ("..." if len(doc.page_content) > 500 else ""))
                            st.divider()

                    except Exception as e:
                        st.error(f"生成答案时出错: {str(e)}")

    with tab2:
        st.subheader("文档语义搜索")

        if "retriever" not in st.session_state:
            st.warning("请先上传文档以启用文档搜索")
        else:
            search_query = st.text_input(
                "输入搜索查询：",
                placeholder="搜索相关文档片段",
                key="search_query"
            )

            if search_query:
                with st.spinner("正在搜索相关文档..."):
                    try:
                        # 搜索相关文档
                        results = st.session_state.rag_system.search_documents(search_query, k=5)

                        if not results:
                            st.info("未找到相关文档")
                        else:
                            st.success(f"找到 {len(results)} 个相关文档片段")

                            for i, doc in enumerate(results, 1):
                                st.markdown(f"### 结果 #{i}")
                                st.caption(
                                    f"文档: {doc.metadata.get('source', '未知')} | 页码: {doc.metadata.get('page', 'N/A')}")
                                st.markdown(doc.page_content)
                                st.divider()

                    except Exception as e:
                        st.error(f"文档搜索失败: {str(e)}")

#
# if __name__ == "__main__":
#     # 检查环境变量
#     if not os.getenv("OPENAI_API_KEY"):
#         st.error("未找到 OPENAI_API_KEY 环境变量。请在 .env 文件中设置或在环境中提供。")
#     else:
#         main()

# 4. 连接 Milvus 数据库
milvus_connection = {
    "host": "192.168.0.104",
    "port": "19530",
    "user": "root",
    "password": "S1nexcel123.",
    "db_name": "sinexcel_ai_vector"
}


def get_collection_stats():
    """获取集合统计信息"""
    try:
        stats = utility.get_collection_stats(collection_name)
        return stats
    except Exception as e:
        st.error(f"获取集合统计失败: {str(e)}")
        return None