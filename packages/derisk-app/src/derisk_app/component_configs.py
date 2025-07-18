import logging
from typing import Optional

from derisk.agent.expand.resources.context_tool import store_information
from derisk.agent.expand.resources.math_tool import add_two_numbers
from derisk.component import SystemApp
from derisk.configs.model_config import MODEL_DISK_CACHE_DIR, resolve_root_path
from derisk.util.executor_utils import DefaultExecutorFactory
from derisk_app.config import ApplicationConfig, ServiceWebParameters
from derisk_serve.agent.resource.knowledge_pack import KnowledgePackSearchResource
from derisk_serve.rag.storage_manager import StorageManager

logger = logging.getLogger(__name__)


def initialize_components(
    param: ApplicationConfig,
    system_app: SystemApp,
):
    # Lazy import to avoid high time cost
    from derisk.model.cluster.controller.controller import controller
    from derisk_app.initialization.embedding_component import (
        _initialize_embedding_model,
        _initialize_rerank_model,
    )
    from derisk_app.initialization.scheduler import DefaultScheduler
    from derisk_app.initialization.serve_initialization import register_serve_apps
    from derisk_serve.datasource.manages.connector_manager import ConnectorManager

    web_config = param.service.web
    default_embedding_name = param.models.default_embedding
    default_rerank_name = param.models.default_reranker

    # Register global default executor factory first
    system_app.register(
        DefaultExecutorFactory, max_workers=web_config.default_thread_pool_size
    )
    system_app.register(DefaultScheduler)
    system_app.register_instance(controller)
    system_app.register(ConnectorManager)
    system_app.register(StorageManager)

    from derisk_serve.agent.agents.controller import multi_agents

    system_app.register_instance(multi_agents)

    _initialize_embedding_model(system_app, default_embedding_name)
    _initialize_rerank_model(system_app, default_rerank_name)
    _initialize_model_cache(system_app, web_config)
    _initialize_awel(system_app, web_config.awel_dirs)
    # Initialize resource manager of agent
    _initialize_resource_manager(system_app)
    _initialize_agent(system_app)
    _initialize_openapi(system_app)
    # Register serve apps
    register_serve_apps(system_app, param, web_config.host, web_config.port)
    _initialize_operators()
    _initialize_code_server(system_app)
    _initialize_reasoning(system_app)


def _initialize_model_cache(system_app: SystemApp, web_config: ServiceWebParameters):
    from derisk.storage.cache import initialize_cache

    if not web_config.model_cache or not web_config.model_cache.enable_model_cache:
        logger.info("Model cache is not enable")
        return

    storage_type = web_config.model_cache.storage_type or "memory"
    max_memory_mb = web_config.model_cache.max_memory_mb or 256
    if web_config.model_cache.persist_dir:
        persist_dir = web_config.model_cache.persist_dir
    else:
        persist_dir = f"{MODEL_DISK_CACHE_DIR}_{web_config.port}"
    persist_dir = resolve_root_path(persist_dir)
    initialize_cache(system_app, storage_type, max_memory_mb, persist_dir)


def _initialize_awel(system_app: SystemApp, awel_dirs: Optional[str] = None):
    from derisk.configs.model_config import _DAG_DEFINITION_DIR
    from derisk.core.awel import initialize_awel

    # Add default dag definition dir
    dag_dirs = [_DAG_DEFINITION_DIR]
    if awel_dirs:
        dag_dirs += awel_dirs.strip().split(",")
    dag_dirs = [x.strip() for x in dag_dirs]

    initialize_awel(system_app, dag_dirs)


def _initialize_agent(system_app: SystemApp):
    from derisk.agent import initialize_agent

    initialize_agent(system_app)


def _initialize_resource_manager(system_app: SystemApp):
    from derisk.agent.expand.actions.react_action import Terminate
    from derisk.agent.expand.resources.derisk_tool import list_derisk_support_models
    from derisk.agent.expand.resources.host_tool import (
        get_current_host_cpu_status,
        get_current_host_memory_status,
        get_current_host_system_load,
    )
    from derisk.agent.expand.resources.search_tool import baidu_search
    from derisk.agent.resource.base import ResourceType
    from derisk.agent.resource.manage import get_resource_manager, initialize_resource
    from derisk_serve.agent.resource.app import GptAppResource
    from derisk_serve.agent.resource.datasource import DatasourceResource
    from derisk_serve.agent.resource.knowledge import KnowledgeSpaceRetrieverResource
    from derisk_serve.agent.resource.mcp import MCPSSEToolPack
    from derisk.agent.resource.reasoning_engine import ReasoningEngineResource

    initialize_resource(system_app)
    rm = get_resource_manager(system_app)
    rm.register_resource(DatasourceResource)
    rm.register_resource(KnowledgeSpaceRetrieverResource)
    rm.register_resource(GptAppResource)
    rm.register_resource(resource_instance=Terminate())
    # Register a search tool
    rm.register_resource(resource_instance=baidu_search)
    rm.register_resource(resource_instance=list_derisk_support_models)
    # Register a math tool
    rm.register_resource(resource_instance=add_two_numbers)
    rm.register_resource(resource_instance=store_information)
    # Register host tools
    rm.register_resource(resource_instance=get_current_host_cpu_status)
    rm.register_resource(resource_instance=get_current_host_memory_status)
    rm.register_resource(resource_instance=get_current_host_system_load)
    # Register mcp tool
    rm.register_resource(MCPSSEToolPack, resource_type=ResourceType.Tool)
    rm.register_resource(ReasoningEngineResource)
    rm.register_resource(KnowledgePackSearchResource)


def _initialize_openapi(system_app: SystemApp):
    from derisk_app.openapi.api_v1.editor.service import EditorService

    system_app.register(EditorService)


def _initialize_operators():
    from derisk_app.operators.code import CodeMapOperator  # noqa: F401
    from derisk_app.operators.converter import StringToInteger  # noqa: F401
    from derisk_app.operators.datasource import (  # noqa: F401
        HODatasourceExecutorOperator,
        HODatasourceRetrieverOperator,
    )
    from derisk_app.operators.llm import (  # noqa: F401
        HOLLMOperator,
        HOStreamingLLMOperator,
    )
    from derisk_app.operators.rag import HOKnowledgeOperator  # noqa: F401
    from derisk_serve.agent.resource.datasource import DatasourceResource  # noqa: F401


def _initialize_code_server(system_app: SystemApp):
    from derisk.util.code.server import initialize_code_server

    initialize_code_server(system_app)


def _initialize_reasoning(system_app: SystemApp):
    from derisk.agent.core.reasoning.reasoning_manage import ReasoningManage

    system_app.register(component=ReasoningManage)
