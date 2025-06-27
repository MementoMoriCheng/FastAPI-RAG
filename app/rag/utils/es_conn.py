import os
import json
import re

import jieba
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.helpers import parallel_bulk

# Elasticsearch 配置
ES_HOSTS = ["http://192.168.0.103:9200"]
ES_AUTH = ("elastic", "elastic123.")
ES_INDEX = "kb_index"


class ElasticSearchSystem:
    def __init__(self):
        self.es = Elasticsearch(
            hosts=ES_HOSTS,
            http_auth=ES_AUTH,
            verify_certs=False,
            timeout=30
        )
        if not self.es.ping():
            raise ConnectionError("无法连接到Elasticsearch集群")

        self.create_index()

    def create_index(self):
        """创建Elasticsearch索引并配置映射"""
        if not self.es.indices.exists(index=ES_INDEX):
            mapping = json.load(open(os.path.join("mapping.json"), "r"))
            self.es.indices.create(index=ES_INDEX, body=mapping)
            print(f"索引 {ES_INDEX} 创建成功")
        else:
            print(f"索引 {ES_INDEX} 已存在")

    def index_documents(self, documents, batch_size=1000, threads=4):
        """索引文档到Elasticsearch"""
        actions = [
            {
                "_index": ES_INDEX,
                "_source": {
                    **doc,
                    "timestamp": datetime.now().isoformat()
                }
            }
            for doc in documents
        ]

        success_count = 0
        failed_count = 0

        # 使用并行批量操作提高性能
        for result in parallel_bulk(
                self.es,
                actions,
                chunk_size=batch_size,
                thread_count=threads,
                raise_on_error=False
        ):
            if result[0]:
                success_count += 1
            else:
                failed_count += 1
                print(f"文档索引失败: {result[1]}")

        print(f"文档索引完成: 成功 {success_count}, 失败 {failed_count}")
        return success_count, failed_count

    def search(self, query, fields=["title_tks", "content_ltks"], size=10):
        """执行搜索"""
        # 使用jieba对中文查询进行分词
        query_tokens = " ".join(jieba.cut_for_search(query))

        search_body = {
            "query": {
                "multi_match": {
                    "query": query_tokens,
                    "fields": fields,
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "highlight": {
                "fields": {
                    "content_with_weight": {"fragment_size": 150}
                }
            },
            "size": size
        }

        results = self.es.search(index=ES_INDEX, body=search_body)
        return self._process_results(results)


    def _process_results(self, es_response):
        """处理搜索结果"""
        processed = {
            "total": es_response["hits"]["total"]["value"],
            "took": es_response["took"],
            "hits": []
        }

        for hit in es_response["hits"]["hits"]:
            source = hit["_source"]
            highlight = hit.get("highlight", {})
            explanation = hit.get("_explanation", {})

            # 提取评分细节
            score_details = self._extract_score_details(explanation)

            processed["hits"].append({
                "id": hit["_id"],
                "docnm_kwd": source.get("docnm_kwd", ""),
                "title_tks": source.get("title_tks", ""),
                "content_snippet": self._extract_snippet(highlight, source),
                "score": hit["_score"],
                "score_details": score_details,
                "timestamp": source.get("@timestamp", "")
            })

        return processed

    def _extract_snippet(self, highlight, source):
        """提取内容摘要"""
        if "content_with_weight" in highlight:
            return " ... ".join(highlight["content_with_weight"])

        # 回退到分词内容
        content = source.get("content_ltks", "") or source.get("content_sm_ltks", "")
        return content[:200] + "..." if content else "无内容"

    def _extract_score_details(self, explanation):
        """从解释中提取评分细节"""
        if not explanation:
            return {}

        details = {}

        # 递归提取评分细节
        def extract(exp, level=0):
            if "description" in exp:
                # 提取IDF值
                if "idf" in exp["description"]:
                    if "idf" not in details:
                        details["idf"] = []
                    details["idf"].append({
                        "value": exp["value"],
                        "description": exp["description"]
                    })

                # 提取文档频率
                if "docFreq" in exp["description"]:
                    match = re.search(r'docFreq=(\d+)', exp["description"])
                    if match:
                        details["docFreq"] = int(match.group(1))

                # 提取字段统计
                if "field" in exp["description"]:
                    match = re.search(r'field=([\w_]+)', exp["description"])
                    if match:
                        field = match.group(1)
                        if "fields" not in details:
                            details["fields"] = {}
                        details["fields"][field] = exp["value"]

            # 处理子解释
            if "details" in exp:
                for detail in exp["details"]:
                    extract(detail, level + 1)

        extract(explanation)
        return details

    def export_index(self, file_path, batch_size=1000):
        """导出索引中的所有文档"""
        all_docs = []
        scroll_id = None

        try:
            # 初始滚动请求
            scroll_response = self.es.search(
                index=ES_INDEX,
                scroll='5m',
                size=batch_size,
                body={"query": {"match_all": {}}}
            )
            scroll_id = scroll_response['_scroll_id']
            hits = scroll_response['hits']['hits']
            all_docs.extend(hits)

            # 继续滚动直到没有更多结果
            while len(hits) > 0:
                scroll_response = self.es.scroll(
                    scroll_id=scroll_id,
                    scroll='5m'
                )
                scroll_id = scroll_response['_scroll_id']
                hits = scroll_response['hits']['hits']
                all_docs.extend(hits)

        finally:
            # 清理滚动资源
            if scroll_id:
                self.es.clear_scroll(scroll_id=scroll_id)

        # 提取文档内容
        documents = [hit["_source"] for hit in all_docs]

        # 保存到文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)

        print(f"导出 {len(documents)} 个文档到 {file_path}")
        return len(documents)

    def optimize_index(self):
        """优化索引性能"""
        # 强制合并段
        self.es.indices.forcemerge(index=ES_INDEX, max_num_segments=1)

        # 刷新缓存
        self.es.indices.clear_cache(index=ES_INDEX)

        print("索引优化完成")



# 示例数据（根据您提供的结构）
SAMPLE_DATA = [
    {
        'docnm_kwd': 'D:\\rag-files\\example\\EMS智能助手.docx',
        'title_tks': 'd rag file exampl em 智能 助手',
        'title_sm_tks': 'd rag file exampl em 智能 助手',
        'content_with_weight': '<table><caption>Table Location: D:\\rag-files\\example\\EMS智能助手 > EMS系统智能助手 > 4、接口设计 > 4.1. 知识库管理 > 4.1.1 创建知识库</caption><tr><td>参数名 </td><td>类型 </td><td>必填</td><td>描述</td></tr><tr><td>name</td><td>字符串</td><td>是</td><td>唯一名称</td></tr><tr><td>description</td><td>字符串</td><td></td><td>简短描述</td></tr><tr><td>language</td><td>字符串</td><td></td><td>语言设置</td></tr><tr><td>embedding_model</td><td>字符串</td><td></td><td>嵌入模型名称</td></tr><tr><td>permission</td><td>字符串</td><td></td><td>指定谁可以访问</td></tr></table>',
        'content_ltks': 'tabl locat d rag file exampl em 智能 助手 em 系统 智能 助手 4 接口 设计 4 1 知识库 管理 4 11 创建 知识库 参数 名 类型 必填 描述 name 字符串 是 唯一 名称 descript 字符串 简短 描述 languag 字符串 语言 设置 embed _ model 字符串 嵌入 模型 名称 permiss 字符串 指定 谁 可以 访问',
        'content_sm_ltks': 'tabl locat d rag file exampl em 智能 助手 em 系统 智能 助手 4 接口 设计 4 1 知识 库 管理 4 11 创建 知识 库 参数 名 类型 必填 描述 name 字符 串 是 唯一 名称 descript 字符 串 简短 描述 languag 字符 串 语言 设置 emb _ model 字符 串 嵌入 模型 名称 permiss 字符 串 指定 谁 可以 访问'
    },
    {
        'docnm_kwd': 'D:\\rag-files\\example\\EMS智能助手.docx',
        'title_tks': 'd rag file exampl em 智能 助手',
        'title_sm_tks': 'd rag file exampl em 智能 助手',
        'content_with_weight': 'EMS系统智能助手1、项目背景1.1 业务痛点文档切分手段单一，只支持按最大 Token 数切分对文档中的图片信息未作处理检索相关度低1.2 知识库现状：培训文档（PDF 格式）：1 份设备指导手册（Word/Excel）：7份经验案例（txt）：2 份1.3 项目启动前考量1.3.1 使用场景评估',
        'content_ltks': 'em 系统 智能 助手 1 项目 背景 11 业务 痛点 文档 切分 手段 单一 只 支持 按 最大 token 数 切分 对 文档 中的 图片 信息 未 作 处理 检索 相关度 低 12 知识库 现状 培训 文档 pdf 格式 1 份 设备 指导 手册 word excel 7 份 经验 案例 txt 2 份 13 项目 启动 前 考量 131 使用 场景 评估',
        'content_sm_ltks': 'em 系统 智能 助手 1 项目 背景 11 业务 痛点 文档 切分 手段 单一 只 支持 按 最大 token 数 切分 对 文档 中的 图片 信息 未 作 处理 检索 相关 度 低 12 知识 库 现状 培训 文档 pdf 格式 1 份 设备 指导 手册 word excel 7 份 经验 案例 txt 2 份 13 项目 启动 前 考量 131 使用 场景 评估'
    },
    {
        'docnm_kwd': 'D:\\rag-files\\example\\EMS智能助手.docx',
        'title_tks': 'd rag file exampl em 智能 助手',
        'title_sm_tks': 'd rag file exampl em 智能 助手',
        'content_with_weight': '主要用户群体：技术人员、新接触EMS平台的人员等日常使用频次：平台操作指导、技术培训等并发使用规模：日常并发 5-10 人1.3.2 系统要求明确答案准确性：操作指导、查询等场景要求高准确性响应速度：常规查询 5 秒内响应知识溯源：需要显示信息来源，便于验证2、技术架构设计',
        'content_ltks': '主要 用户 群体 技术人员 新接 触 em 平台 的 人员 等 日常 使用 频次 平台 操作 指导 技术培训 等 并发 使用 规模 日常 并发 510 人 13 2 系统 要求 明确 答案 准确性 操作 指导 查询 等 场景 要求 高 准确性 响应速度 常规 查询 5 秒 内 响应 知识 溯源 需要 显示信息 来源 便于 验证 2 技术 架构设计',
        'content_sm_ltks': '主要 用户 群体 技术 人员 新接 触 em 平台 的 人员 等 日常 使用 频次 平台 操作 指导 技术 培训 等 并发 使用 规模 日常 并发 510 人 13 2 系统 要求 明确 答案 准确 性 操作 指导 查询 等 场景 要求 高 准确 性 响应 速度 常规 查询 5 秒 内 响应 知识 溯源 需要 显示 信息 来源 便于 验证 2 技术 架构 设计'
    },
    {
        'docnm_kwd': 'D:\\rag-files\\example\\EMS智能助手.docx',
        'title_tks': 'd rag file exampl em 智能 助手',
        'title_sm_tks': 'd rag file exampl em 智能 助手',
        'content_with_weight': '2.1 技术栈Python 3.11+：开发语言LangChain：提供RAG系统构建的核心组件FastAPI：后端框架2.2 代码结构-project\n    -readme.md 项目说明\n    -requirements.txt 使用依赖包的版本 \n    -llm LLM调用封装\n        -self_llm.py 自定义 LLM 基类\n        -**_llm.py 自定义 LLM\n        -call_llm.py 将各个 LLM 的原生接口封装在一起\n        -test.ipynb 使用示例\n    -embedding embedding调用封装\n        -**_embedding.py 自定义 embedding\n        -call_embedding.py 调用 embedding 模型 \n    -document_loaders 文档加载器调用封装\n        -ocr.py\n        -pdfloader.py\n        -docloader.py\n        -txtloader.py\n        -markdownloader.py\n        -excelloader.py\n    -text_splitter 文档分割器调用封装              \n    -data 源数据路径\n    -prompt_template.py 维护prompt 模板\n    -database 数据库层封装\n        -create_db.py 处理源数据及初始化数据库封装\n    -qa_chain 应用层封装\n        -qa_chain.py 封装检索问答链，返回一个检索问答链对象\n        -chat_qa_chian.py：封装对话检索链，返回一个带有历史记录的对话检索链对象\n        -get_vectordb.py 返回向量数据库对象\n        -model_to_llm.py 调用模型        \n    -serve 服务层封装\n        -run_gradio.py 启动 Gradio 界面\n        -api.py 封装 FastAPI\n        -run_api.sh 启动 API',
        'content_ltks': '21 技术 栈 python 3 11 开发 语言 langchain 提供 rag 系统 构建 的 核心 组件 fastapi 后端 框架 2 2 代码 结构 project readm md 项目 说明 requir txt 使用 依赖 包 的 版本 llm llm 调用 封装 self _ llm py 自定义 llm 基类 _ llm py 自定义 llm call _ llm py 将 各个 llm 的 原生 接口 封装 在 一起 test ipynb 使用 示例 embed embed 调用 封装 _ embed py 自定义 embed call _ embed py 调用 embed 模型 document _ loader 文档 加载 器 调用 封装 ocr py pdfloader py docload py txtloader py markdownload py excelload py text _ splitter 文档 分割器 调用 封装 data 源 数据 路径 prompt _ templat py 维护 prompt 模板 databas 数据库 层 封装 creat _ db py 处理 源 数据 及 初始化 数据库 封装 qa _ chain 应用层 封装 qa _ chain py 封装 检索 问答 链 返回 一个 检索 问答 链 对象 chat _ qa _ chian py 封装 对话 检索 链 返回 一个 带有 历史记录 的 对话 检索 链 对象 get _ vectordb py 返回 向量 数据库 对象 model _ to _ llm py 调用 模型 serv 服务 层 封装 run _ gradio py 启动 gradio 界面 api py 封装 fastapi run _ api sh 启动 api',
        'content_sm_ltks': '21 技术 栈 python 3 11 开发 语言 langchain 提供 rag 系统 构建 的 核心 组件 fastapi 后端 框架 2 2 代码 结构 project readm md 项目 说明 requir txt 使用 依赖 包 的 版本 llm llm 调用 封装 self _ llm py 自 定义 llm 基类 _ llm py 自 定义 llm call _ llm py 将 各个 llm 的 原生 接口 封装 在 一起 test ipynb 使用 示例 emb emb 调用 封装 _ emb py 自 定义 emb call _ emb py 调用 emb 模型 document _ loader 文档 加载 器 调用 封装 ocr py pdfloader py docload py txtloader py markdownload py excelload py text _ splitter 文档 分割 器 调用 封装 data 源 数据 路径 prompt _ templat py 维护 prompt 模板 databa 数据 库 层 封装 creat _ db py 处理 源 数据 及 初始 化 数据 库 封装 qa _ chain 应用 层 封装 qa _ chain py 封装 检索 问答 链 返回 一个 检索 问答 链 对象 chat _ qa _ chian py 封装 对话 检索 链 返回 一个 带有 历史 记录 的 对话 检索 链 对象 get _ vectordb py 返回 向量 数据 库 对象 model _ to _ llm py 调用 模型 serv 服务 层 封装 run _ gradio py 启动 gradio 界面 api py 封装 fastapi run _ api sh 启动 api'
    },
{
    'docnm_kwd': 'D:\\rag-files\\example\\EMS智能助手.docx',
    'title_tks': 'd rag file exampl em 智能 助手',
    'title_sm_tks': 'd rag file exampl em 智能 助手',
    'content_with_weight': '3.5 增强模块功能描述：增强模块负责整合检索结果，通过构建优化的上下文，使用应用提示词工程技术、查询转换、RAG Fusion 技术，达到提升整体的搜索效率和准确性的效果3.5.1 提示词使用模板构建最终提示template ="""你是一个问答机器人助手，请使用以下检索到的上下文来回答问题，如果你不知道答案，就说你不知道。问题是：{question},上下文:{context},答案是:"""',
    'content_ltks': '35 增强 模块 功能 描述 增强 模块 负责 整合 检索 结果 通过 构建 优化 的 上下文 使用 应用 提示 词 工程技术 查询 转换 rag fusion 技术 达到 提升 整体 的 搜索 效率 和 准确性 的 效果 35 1 提示 词 使用 模板 构建 最终 提示 templat 你 是 一个 问答 机器人 助手 请 使用 以下 检索 到 的 上下文 来 回答 问题 如果 你 不 知道 答案 就 说 你 不 知道 问题 是 question 上下文 context 答案 是',
    'content_sm_ltks': '35 增强 模块 功能 描述 增强 模块 负责 整合 检索 结果 通过 构建 优化 的 上 下文 使用 应用 提示 词 工程 技术 查询 转换 rag fusion 技术 达到 提升 整体 的 搜索 效率 和 准确 性 的 效果 35 1 提示 词 使用 模板 构建 最终 提示 templat 你 是 一个 问答 机器 人 助手 请 使用 以下 检索 到 的 上 下文 来 回答 问题 如果 你 不 知道 答案 就 说 你 不 知道 问题 是 question 上 下文 context 答案 是'
  },
  {
    'docnm_kwd': 'D:\\rag-files\\example\\EMS智能助手.docx',
    'title_tks': 'd rag file exampl em 智能 助手',
    'title_sm_tks': 'd rag file exampl em 智能 助手',
    'content_with_weight': '3.5.2 查询转换方案利用大型语言模型(LLM)的能力，通过某种提示将原来的用户问题转换或重写为更合适的、能够更准确地返回所需结果的查询。LLM的能力确保了转换后的查询更有可能从文档或数据中获取相关和准确的答案。3.5.3 RAG Fusion 优化策略当接收用户 query时，让大模型生成5-10个相似的query，然后每个query去匹配5-10个文本块，接着对所有返回的文本块 再做个倒序融合排序',
    'content_ltks': '352 查询 转换 方案 利用 大型 语言 模型 llm 的 能力 通过 某种 提示 将 原来 的 用户 问题 转换 或 重写 为 更 合适 的 能够 更 准确 地 返回 所需 结果 的 查询 llm 的 能力 确保 了 转换 后 的 查询 更 有 可能 从 文档 或 数据 中 获取 相关 和 准确 的 答案 35 3 rag fusion 优化 策略 当 接收 用户 queri 时 让 大 模型 生成 510 个 相似 的 queri 然后 每个 queri 去 匹配 510 个 文本 块 接着 对 所有 返回 的 文本 块 再 做 个 倒序 融合 排序',
    'content_sm_ltks': '352 查询 转换 方案 利用 大型 语言 模型 llm 的 能力 通过 某种 提示 将 原来 的 用户 问题 转换 或 重写 为 更 合适 的 能够 更 准确 地 返回 所需 结果 的 查询 llm 的 能力 确保 了 转换 后 的 查询 更 有 可能 从 文档 或 数据 中 获取 相关 和 准确 的 答案 35 3 rag fusion 优化 策略 当 接收 用户 queri 时 让 大 模型 生成 510 个 相似 的 queri 然后 每个 queri 去 匹配 510 个 文本 块 接着 对 所有 返回 的 文本 块 再 做 个 倒序 融合 排序'
  },
  {
    'docnm_kwd': 'D:\\rag-files\\example\\EMS智能助手.docx',
    'title_tks': 'd rag file exampl em 智能 助手',
    'title_sm_tks': 'd rag file exampl em 智能 助手',
    'content_with_weight': '3.6 生成模块功能描述：生成模块负责调用大型语言模型，生成回答，并进行后处理。实现：定义llm包，包中存放以主流大模型名称命名的自定义 .py文件，以及一个基类文件。基类实现以下功能：基础初始化：创建客户端实例配置超时、重试策略等参数从环境变量加载配置错误处理：实现错误分类机制，区分不同类型的API错误针对特定错误（速率限制/服务器错误）实现指数退避重试策略',
    'content_ltks': '36 生成 模块 功能 描述 生成 模块 负责 调用 大型 语言 模型 生成 回答 并 进行 后处理 实现 定义 llm 包 包 中 存放 以 主流 大 模型 名称 命名 的 自定义 py 文件 以及 一个 基类 文件 基类 实现 以下 功能 基础 初始化 创建 客户端 实例 配置 超时 重试 策略 等 参数 从 环境变量 加载 配置 错误处理 实现 错误 分类 机制 区分 不同 类型 的 api 错误 针对 特定 错误 速率 限制 服务器 错误 实现 指数 退避 重试 策略',
    'content_sm_ltks': '36 生成 模块 功能 描述 生成 模块 负责 调用 大型 语言 模型 生成 回答 并 进行 后 处理 实现 定义 llm 包 包 中 存放 以 主流 大 模型 名称 命名 的 自 定义 py 文件 以及 一个 基类 文件 基类 实现 以下 功能 基础 初始 化 创建 客户 端 实例 配置 超时 重试 策略 等 参数 从 环境 变量 加载 配置 错误 处理 实现 错误 分类 机制 区分 不同 类型 的 api 错误 针对 特定 错误 速率 限制 服务 器 错误 实现 指数 退避 重试 策略'
  },
  {
    'docnm_kwd': 'D:\\rag-files\\example\\EMS智能助手.docx',
    'title_tks': 'd rag file exampl em 智能 助手',
    'title_sm_tks': 'd rag file exampl em 智能 助手',
    'content_with_weight': '在达到最大重试次数后返回错误信息聊天功能：同步聊天接口（chat）：返回完整响应内容和token数流式聊天接口（chat_streamly）：以生成器形式逐步返回响应内容和最终token数处理输出长度限制情况，附加相应提示信息上下文管理：实现动态上下文窗口计算简单的token计数方法（ASCII/非ASCII字符不同权重）根据内容长度自动调整上下文窗口大小',
    'content_ltks': '在 达到 最大 重试 次数 后 返回 错误信息 聊天 功能 同步 聊天 接口 chat 返回 完整 响应 内容 和 token 数 流式 聊天 接口 chat _ streamli 以 生成器 形式 逐步 返回 响应 内容 和 最终 token 数 处理 输出 长度 限制 情况 附加 相应 提示信息 上下文 管理 实现 动态 上下文 窗口 计算 简单 的 token 计数 方法 ascii 非 ascii 字符 不同 权重 根据 内容 长度 自动 调整 上下文 窗口 大小',
    'content_sm_ltks': '在 达到 最大 重试 次数 后 返回 错误 信息 聊天 功能 同步 聊天 接口 chat 返回 完整 响应 内容 和 token 数 流式 聊天 接口 chat _ streamli 以 生成 器 形式 逐步 返回 响应 内容 和 最终 token 数 处理 输出 长度 限制 情况 附加 相应 提示 信息 上 下文 管理 实现 动态 上 下文 窗口 计算 简单 的 token 计数 方法 ascii 非 ascii 字符 不同 权重 根据 内容 长度 自动 调整 上 下文 窗口 大小'
  },
  {
    'docnm_kwd': 'D:\\rag-files\\example\\EMS智能助手.docx',
    'title_tks': 'd rag file exampl em 智能 助手',
    'title_sm_tks': 'd rag file exampl em 智能 助手',
    'content_with_weight': '工具方法：获取重试延迟时间提取总token数自定义的模型文件可以继承基类后按厂商要求实现不同的方法及功能。4、接口设计4.1. 知识库管理4.1.1 创建知识库URL: <base_url>/knowledge_base/create_knowledge_base描述: 创建新的知识库容器请求方式: POST请求参数:4.1.2 删除知识库URL: <base_url>/knowledge_base/delete_knowledge_base描述: 删除指定知识库及其所有文件请求方式: DELETE请求参数:',
    'content_ltks': '工具 方法 获取 重试 延迟时间 提取 总 token 数 自定义 的 模型 文件 可以 继承 基类 后 按 厂商 要求 实现 不同 的 方法 及 功能 4 接口 设计 4 1 知识库 管理 4 11 创建 知识库 url base _ url knowledg _ base creat _ knowledg _ base 描述 创 建新 的 知识库 容器 请求 方式 post 请求 参数 4 12 删除 知识库 url base _ url knowledg _ base delet _ knowledg _ base 描述 删除 指定 知识库 及其 所有 文件 请求 方式 delet 请求 参数',
    'content_sm_ltks': '工具 方法 获取 重试 延迟 时间 提取 总 token 数 自 定义 的 模型 文件 可以 继承 基类 后 按 厂商 要求 实现 不同 的 方法 及 功能 4 接口 设计 4 1 知识 库 管理 4 11 创建 知识 库 url base _ url knowledg _ base creat _ knowledg _ base 描述 创 建新 的 知识 库 容器 请求 方式 post 请求 参数 4 12 删除 知识 库 url base _ url knowledg _ base delet _ knowledg _ base 描述 删除 指定 知识 库 及其 所有 文件 请求 方式 delet 请求 参数'
  },
  {
    'docnm_kwd': 'D:\\rag-files\\example\\EMS智能助手.docx',
    'title_tks': 'd rag file exampl em 智能 助手',
    'title_sm_tks': 'd rag file exampl em 智能 助手',
    'content_with_weight': '4.1.3 更新知识库信息URL: <base_url>/knowledge_base/{kb_id}/update_info描述: 修改知识库描述信息请求方式: PUT请求参数:4.1.4. 获取知识库列表URL: <base_url>/knowledge_base/list_knowledge_bases描述: 查询所有知识库请求方式: GET请求参数: 无4.2 知识库文件管理4.2.1 文件上传URL: <base_url>/knowledge_base/upload_docs描述: 上传文件到知识库并自动向量化存储请求方式: POST请求格式: multipart/form-data请求参数:',
    'content_ltks': '4 13 更新 知识库 信息 url base _ url knowledg _ base kb _ id updat _ info 描述 修改 知识库 描述 信息 请求 方式 put 请求 参数 4 1 4 获取 知识库 列表 url base _ url knowledg _ base list _ knowledg _ base 描述 查询 所有 知识库 请求 方式 get 请求 参数 无 42 知识库 文件 管理 42 1 文件 上传 url base _ url knowledg _ base upload _ doc 描述 上传 文件 到 知识库 并 自动 向 量化 存储 请求 方式 post 请求 格式 multipart form data 请求 参数',
    'content_sm_ltks': '4 13 更新 知识 库 信息 url base _ url knowledg _ base kb _ id updat _ info 描述 修改 知识 库 描述 信息 请求 方式 put 请求 参数 4 1 4 获取 知识 库 列表 url base _ url knowledg _ base list _ knowledg _ base 描述 查询 所有 知识 库 请求 方式 get 请求 参数 无 42 知识 库 文件 管理 42 1 文件 上传 url base _ url knowledg _ base upload _ doc 描述 上传 文件 到 知识 库 并 自动 向 量化 存储 请求 方式 post 请求 格式 multipart form data 请求 参数'
  },
  {
    'docnm_kwd': 'D:\\rag-files\\example\\EMS智能助手.docx',
    'title_tks': 'd rag file exampl em 智能 助手',
    'title_sm_tks': 'd rag file exampl em 智能 助手',
    'content_with_weight': '4.2.2 获取文件列表URL: <base_url>/knowledge_base/{kb_id}/list_files描述: 获取知识库内所有文件的元数据请求方式: GET请求参数:4.2.3 删除知识文件URL: <base_url>/knowledge_base/{kb_id}/delete_docs描述: 删除知识库内指定文件请求方式: DELETE请求参数:4.2.4 解析文档URL: <base_url>/knowledge_base/{kb_id}/chunks描述: 创建新的知识库容器请求方式: POST请求参数:4.3. 聊天助手管理',
    'content_ltks': '42 2 获取 文件 列表 url base _ url knowledg _ base kb _ id list _ file 描述 获取 知识库 内 所有 文件 的 元数据 请求 方式 get 请求 参数 42 3 删除 知识 文件 url base _ url knowledg _ base kb _ id delet _ doc 描述 删除 知识库 内 指定 文件 请求 方式 delet 请求 参数 42 4 解析 文档 url base _ url knowledg _ base kb _ id chunk 描述 创 建新 的 知识库 容器 请求 方式 post 请求 参数 43 聊天 助手 管理',
    'content_sm_ltks': '42 2 获取 文件 列表 url base _ url knowledg _ base kb _ id list _ file 描述 获取 知识 库 内 所有 文件 的 元 数据 请求 方式 get 请求 参数 42 3 删除 知识 文件 url base _ url knowledg _ base kb _ id delet _ doc 描述 删除 知识 库 内 指定 文件 请求 方式 delet 请求 参数 42 4 解析 文档 url base _ url knowledg _ base kb _ id chunk 描述 创 建新 的 知识 库 容器 请求 方式 post 请求 参数 43 聊天 助手 管理'
  }
    ]

if __name__ == "__main__":
    # 1. 初始化系统
    search_system = ElasticSearchSystem()

    # 2. 创建索引
    # search_system.create_index()

    # 3. 索引示例数据
    # search_system.index_documents(SAMPLE_DATA)

    # 4. 执行搜索测试
    results = search_system.search("提示词工程")
    print(f"找到 {results['total']} 个结果 (耗时 {results['took']}ms):")
    for i, hit in enumerate(results["hits"], 1):
        print(f"{i}. {hit['title_tks']} (得分: {hit['score']:.4f})")
        if hit['score_details']:
            print("   评分细节:", hit['score_details'])

    # 5. 测试搜索建议
    # suggestions = search_system.suggest("智能")
    # print("搜索建议:", suggestions)

    # 6. 导出/导入测试
    # search_system.export_index("kb_export.json")
    # search_system.import_index("kb_export.json")
