import logging
from typing import List, Optional, Union

from sqlalchemy import URL

from derisk.component import SystemApp
from derisk.storage.metadata import DatabaseManager
from derisk_serve.core import BaseServe

from .api.endpoints import init_endpoints, router
from .config import (  # noqa: F401
    APP_NAME,
    SERVE_APP_NAME,
    SERVE_APP_NAME_HUMP,
    SERVE_CONFIG_KEY_PREFIX,
    ServeConfig,
)

logger = logging.getLogger(__name__)


class Serve(BaseServe):
    """Serve component for DERISK
    
    Examples:

        Register the serve component in your system app
        .. code-block:: python
        
        from fastapi import FastAPI
        from derisk import SystemApp
        from derisk.core import PromptTemplate
        from derisk_serve.prompt.serve import Serve, SERVE_APP_NAME
        
        app = FastAPI()
        system_app = SystemApp(app)
        system_app.register(Serve, api_prefix="/api/v1/prompt")
        system_app.init()
        
        # Run before start hook
        system_app.before_start()
        
        prompt_serve = system_app.get_component(SERVE_APP_NAME, Serve)

        # Get the prompt manager
        prompt_manager = prompt_serve.get_prompt_manager()
        prompt_manager.save(
            PromptTemplate(templat"Hello {name}", input_variables=["name"]),
            prompt_name="prompt_name",
        )

    With your database url
   
    .. code-block:: python

        from fastapi import FastAPI
        from derisk import SystemApp
        from derisk.core import PromptTemplate
        from derisk_serve.prompt.serve import Serve, SERVE_APP_NAME

        app = FastAPI()
        system_app = SystemApp(app)
        system_app.register(
            Serve,
            api_prefix="/api/v1/prompt",
            db_url_or_db="sqlite:///:memory:",
            try_create_tables=True,
        )
        system_app.on_init()
        # Run before start hook
        system_app.before_start()

        prompt_serve = system_app.get_component(SERVE_APP_NAME, Serve)

        # Get the prompt manager
        prompt_manager = prompt_serve.prompt_manager
        prompt_manager.save(
            PromptTemplate(template="Hello {name}", input_variables=["name"]),
            prompt_name="prompt_name",
        )
    """

    name = SERVE_APP_NAME

    def __init__(
        self,
        system_app: SystemApp,
        config: Optional[ServeConfig] = None,
        api_prefix: Optional[str] = None,
        api_tags: Optional[List[str]] = None,
        db_url_or_db: Union[str, URL, DatabaseManager] = None,
        try_create_tables: Optional[bool] = False,
    ):
        if api_prefix is None:
            api_prefix = [f"/api/v1/{APP_NAME}", f"/api/v2/serve/{APP_NAME}"]
        if api_tags is None:
            api_tags = [SERVE_APP_NAME_HUMP]
        super().__init__(
            system_app, api_prefix, api_tags, db_url_or_db, try_create_tables
        )
        self._db_manager: Optional[DatabaseManager] = None
        self._config = config

    def init_app(self, system_app: SystemApp):
        if self._app_has_initiated:
            return
        self._system_app = system_app
        self._system_app.app.include_router(
            router, prefix=self._api_prefix, tags=self._api_tags
        )
        self._config = self._config or ServeConfig.from_app_config(
            system_app.config, SERVE_CONFIG_KEY_PREFIX
        )
        init_endpoints(self._system_app, self._config)
        self._app_has_initiated = True

    def on_init(self):
        """Called when init the application.

        You can do some initialization here. You can't get other components here
        because they may be not initialized yet
        """
        # import your own module here to ensure the module is loaded before the
        # application starts
        from .models.models import ServeEntity as _  # noqa: F401

    def after_init(self):
        """Called after init the application."""
        # TODO: Your code here
        self._db_manager = self.create_or_get_db_manager()
