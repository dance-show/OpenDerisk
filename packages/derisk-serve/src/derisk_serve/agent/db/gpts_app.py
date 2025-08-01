import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from itertools import groupby
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    or_,
)

from derisk._private.pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_to_json,
    model_validator,
)
from derisk.agent.core.plan import AWELTeamContext
from derisk.agent.core.plan.base import SingleAgentContext
from derisk.agent.core.plan.react.team_react_plan import AutoTeamContext
from derisk.agent.resource.base import AgentResource, ResourceType
from derisk.storage.metadata import BaseDao, Model
from derisk_app.openapi.api_view_model import ConversationVo
from derisk_app.scene import ChatScene

from derisk_serve.agent.model import NativeTeamContext
from derisk_serve.agent.team.base import TeamMode

logger = logging.getLogger(__name__)


class BindAppRequest(BaseModel):
    team_app_code: str
    bin_app_codes: List[str]


class GptsAppDetail(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    app_code: Optional[str] = None
    app_name: Optional[str] = None
    type: Optional[str] = None
    agent_name: Optional[str] = None
    agent_role: Optional[str] = None
    agent_describe: Optional[str] = None
    node_id: Optional[str] = None
    resources: Optional[list[AgentResource]] = None
    prompt_template: Optional[str] = None
    llm_strategy: Optional[str] = None
    llm_strategy_value: Union[Optional[str], Optional[List[Any]]] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    def to_dict(self):
        return {k: self._serialize(v) for k, v in self.__dict__.items()}

    def _serialize(self, value):
        if isinstance(value, BaseModel):
            return value.to_dict()
        elif isinstance(value, list):
            return [self._serialize(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._serialize(v) for k, v in value.items()}
        else:
            return value

    @classmethod
    def from_dict(cls, d: Dict[str, Any], parse_llm_strategy: bool = False):
        lsv = d.get("llm_strategy_value")
        if parse_llm_strategy and lsv:
            strategies = json.loads(lsv)
            llm_strategy_value = ",".join(strategies)
        else:
            llm_strategy_value = d.get("llm_strategy_value", None)

        return cls(
            app_code=d["app_code"],
            app_name=d["app_name"],
            type=d["type"],
            agent_name=d["agent_name"],
            agent_role=d["agent_role"],
            agent_describe=d.get("agent_describe", None),
            node_id=d["node_id"],
            resources=AgentResource.from_json_list_str(d.get("resources", None)),
            prompt_template=d.get("prompt_template", None),
            llm_strategy=d.get("llm_strategy", None),
            llm_strategy_value=llm_strategy_value,
            created_at=d.get("created_at", None),
            updated_at=d.get("updated_at", None),
        )

    @classmethod
    def from_entity(cls, entity):
        resources = AgentResource.from_json_list_str(entity.resources)
        return cls(
            app_code=entity.app_code,
            app_name=entity.app_name,
            type=entity.type,
            agent_name=entity.agent_name,
            agent_role=entity.agent_role,
            agent_describe=entity.agent_describe,
            node_id=entity.node_id,
            resources=resources,
            prompt_template=entity.prompt_template,
            llm_strategy=entity.llm_strategy,
            llm_strategy_value=entity.llm_strategy_value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class GptsApp(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    app_code: Optional[str] = None
    app_name: Optional[str] = None
    app_describe: Optional[str] = None
    team_mode: Optional[str] = None
    language: Optional[str] = None
    team_context: Optional[
        Union[
            str, AutoTeamContext, SingleAgentContext, AWELTeamContext, NativeTeamContext
        ]
    ] = None
    user_code: Optional[str] = None
    sys_code: Optional[str] = None
    is_collected: Optional[str] = None
    icon: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    details: List[GptsAppDetail] = []
    published: Optional[str] = None
    user_name: Optional[str] = None
    user_icon: Optional[str] = None
    hot_value: Optional[int] = None
    param_need: Optional[List[dict]] = []
    owner_name: Optional[str] = None
    owner_avatar_url: Optional[str] = None
    recommend_questions: Optional[List] = []
    admins: List[str] = Field(default_factory=list)

    # By default, keep the last two rounds of conversation records as the context
    keep_start_rounds: int = 1
    keep_end_rounds: int = 1

    def to_dict(self):
        return {k: self._serialize(v) for k, v in self.__dict__.items()}

    def _serialize(self, value):
        if isinstance(value, BaseModel):
            return value.to_dict()
        elif isinstance(value, list):
            return [self._serialize(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._serialize(v) for k, v in value.items()}
        else:
            return value

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        return cls(
            app_code=d.get("app_code", None),
            app_name=d["app_name"],
            language=d["language"],
            app_describe=d["app_describe"],
            team_mode=d["team_mode"],
            team_context=d.get("team_context", None),
            user_code=d.get("user_code", None),
            sys_code=d.get("sys_code", None),
            icon=d.get("icon", None),
            is_collected=d.get("is_collected", None),
            created_at=d.get("created_at", None),
            updated_at=d.get("updated_at", None),
            details=d.get("details", None),
            published=d.get("published", None),
            param_need=d.get("param_need", None),
            hot_value=d.get("hot_value", None),
            owner_name=d.get("owner_name", None),
            owner_avatar_url=d.get("owner_avatar_url", None),
            recommend_questions=d.get("recommend_questions", []),
            admins=d.get("admins", []),
            keep_start_rounds=d.get("keep_start_rounds", 0),
            keep_end_rounds=d.get("keep_end_rounds", 2),
        )

    @model_validator(mode="before")
    @classmethod
    def pre_fill(cls, values):
        if not isinstance(values, dict):
            return values
        is_collected = values.get("is_collected")
        if is_collected is not None and isinstance(is_collected, bool):
            values["is_collected"] = "true" if is_collected else "false"
        return values


class GptsAppQuery(GptsApp):
    page_size: int = 100
    page: int = 1
    is_collected: Optional[str] = None
    is_recent_used: Optional[str] = None
    published: Optional[str] = None
    ignore_user: Optional[str] = None
    app_codes: Optional[List[str]] = []
    hot_map: Optional[Dict[str, int]] = {}
    need_owner_info: Optional[str] = "true"


class GptsAppResponse(BaseModel):
    total_count: Optional[int] = 0
    total_page: Optional[int] = 0
    current_page: Optional[int] = 0
    app_list: Optional[List[GptsApp]] = Field(
        default_factory=list, description="app list"
    )


class GptsAppCollection(BaseModel):
    app_code: Optional[str] = None
    user_code: Optional[str] = None
    sys_code: Optional[str] = None

    def to_dict(self):
        return {k: self._serialize(v) for k, v in self.__dict__.items()}

    def _serialize(self, value):
        if isinstance(value, BaseModel):
            return value.to_dict()
        elif isinstance(value, list):
            return [self._serialize(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._serialize(v) for k, v in value.items()}
        else:
            return value

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        return cls(
            app_code=d.get("app_code", None),
            user_code=d.get("user_code", None),
            sys_code=d.get("sys_code", None),
            created_at=d.get("created_at", None),
            updated_at=d.get("updated_at", None),
        )


class UserRecentApps(BaseModel):
    app_code: Optional[str] = None
    user_code: Optional[str] = None
    sys_code: Optional[str] = None
    last_accessed: datetime = None
    gmt_create: datetime = None
    gmt_modified: datetime = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        return cls(
            app_code=d.get("app_code", None),
            user_code=d.get("user_code", None),
            sys_code=d.get("sys_code", None),
            gmt_create=d.get("gmt_create", None),
            gmt_modified=d.get("gmt_modified", None),
            last_accessed=d.get("last_accessed", None),
        )


class UserRecentAppsEntity(Model):
    __tablename__ = "user_recent_apps"
    id = Column(Integer, primary_key=True, comment="autoincrement id")
    app_code = Column(String(255), nullable=False, comment="Current AI assistant code")
    user_code = Column(String(255), nullable=True, comment="user code")
    sys_code = Column(String(255), nullable=True, comment="system app code")
    gmt_create = Column(DateTime, default=datetime.utcnow, comment="create time")
    gmt_modified = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="last update time",
    )
    last_accessed = Column(DateTime, default=None, comment="last access time")
    __table_args__ = (
        Index("idx_user_r_app_code", "app_code"),
        Index("idx_user_code", "user_code"),
        Index("idx_last_accessed", "last_accessed"),
    )


class GptsAppCollectionEntity(Model):
    __tablename__ = "gpts_app_collection"
    id = Column(Integer, primary_key=True, comment="autoincrement id")
    app_code = Column(String(255), nullable=False, comment="Current AI assistant code")
    user_code = Column(String(255), nullable=True, comment="user code")
    sys_code = Column(String(255), nullable=True, comment="system app code")
    created_at = Column(
        DateTime, name="gmt_create", default=datetime.utcnow, comment="create time"
    )
    updated_at = Column(
        DateTime,
        name="gmt_modified",
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="last update time",
    )


class GptsAppEntity(Model):
    __tablename__ = "gpts_app"
    id = Column(Integer, primary_key=True, comment="autoincrement id")
    app_code = Column(String(255), nullable=False, comment="Current AI assistant code")
    app_name = Column(String(255), nullable=False, comment="Current AI assistant name")
    icon = Column(String(1024), nullable=True, comment="app icon, url")
    app_describe = Column(
        String(2255), nullable=False, comment="Current AI assistant describe"
    )
    language = Column(String(100), nullable=False, comment="gpts language")
    team_mode = Column(String(255), nullable=False, comment="Team work mode")
    team_context = Column(
        Text,
        nullable=True,
        comment="The execution logic and team member content that teams with different"
                " working modes rely on",
    )

    user_code = Column(String(255), nullable=True, comment="user code")
    sys_code = Column(String(255), nullable=True, comment="system app code")
    published = Column(String(64), nullable=True, comment="published")

    param_need = Column(
        Text,
        nullable=True,
        comment="Parameters required for application",
    )

    created_at = Column(
        DateTime, name="gmt_create", default=datetime.utcnow, comment="create time"
    )
    updated_at = Column(
        DateTime,
        name="gmt_modified",
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="last update time",
    )
    admins = Column(Text, nullable=True, comment="administrators")

    __table_args__ = (UniqueConstraint("app_name", name="uk_gpts_app"),)


class GptsAppDetailEntity(Model):
    __tablename__ = "gpts_app_detail"
    id = Column(Integer, primary_key=True, comment="autoincrement id")
    app_code = Column(String(255), nullable=False, comment="Current AI assistant code")
    app_name = Column(String(255), nullable=False, comment="Current AI assistant name")
    type = Column(
        String(255),
        nullable=False,
        comment="bind detail agent type. 'app' or 'agent', default 'agent'",
    )
    agent_name = Column(String(255), nullable=False, comment=" Agent name")
    agent_role = Column(String(255), nullable=False, comment=" Agent role")
    agent_describe = Column(Text, nullable=True, comment=" Agent describe")
    node_id = Column(
        String(255), nullable=False, comment="Current AI assistant Agent Node id"
    )
    resources = Column(Text, nullable=True, comment="Agent bind  resource")
    prompt_template = Column(Text, nullable=True, comment="Agent bind  template")
    llm_strategy = Column(String(25), nullable=True, comment="Agent use llm strategy")
    llm_strategy_value = Column(
        Text, nullable=True, comment="Agent use llm strategy value"
    )
    created_at = Column(
        DateTime, name="gmt_create", default=datetime.utcnow, comment="create time"
    )
    updated_at = Column(
        DateTime,
        name="gmt_modified",
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="last update time",
    )

    __table_args__ = (
        UniqueConstraint(
            "app_name", "agent_name", "node_id", name="uk_gpts_app_agent_node"
        ),
    )

    def to_dict(self):
        return {k: self._serialize(v) for k, v in self.__dict__.items()}

    def _serialize(self, value):
        if isinstance(value, BaseModel):
            return value.to_dict()
        elif isinstance(value, list):
            return [self._serialize(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._serialize(v) for k, v in value.items()}
        else:
            return value


class UserRecentAppsDao(BaseDao):
    def query(
            self,
            user_code: Optional[str] = None,
            sys_code: Optional[str] = None,
            app_code: Optional[str] = None,
    ):
        with self.session() as session:
            recent_app_qry = session.query(UserRecentAppsEntity)
            if user_code:
                recent_app_qry = recent_app_qry.filter(
                    UserRecentAppsEntity.user_code == user_code
                )
            if sys_code:
                recent_app_qry = recent_app_qry.filter(
                    UserRecentAppsEntity.sys_code == sys_code
                )
            if app_code:
                recent_app_qry = recent_app_qry.filter(
                    UserRecentAppsEntity.app_code == app_code
                )
            recent_app_qry.order_by(UserRecentAppsEntity.last_accessed.desc())
            apps = []
            results = recent_app_qry.all()
            for result in results:
                apps.append(
                    UserRecentApps.from_dict(
                        {
                            "app_code": result.app_code,
                            "sys_code": result.sys_code,
                            "user_code": result.user_code,
                            "last_accessed": result.last_accessed,
                            "gmt_create": result.gmt_create,
                            "gmt_modified": result.gmt_modified,
                        }
                    )
                )
            return apps

    def upsert(
            self,
            user_code: Optional[str] = None,
            sys_code: Optional[str] = None,
            app_code: Optional[str] = None,
    ):
        with self.session() as session:
            try:
                existing_app = (
                    session.query(UserRecentAppsEntity)
                    .filter(
                        UserRecentAppsEntity.user_code == user_code,
                        UserRecentAppsEntity.sys_code == sys_code,
                        UserRecentAppsEntity.app_code == app_code,
                    )
                    .first()
                )

                last_accessed = datetime.utcnow()
                if existing_app:
                    existing_app.last_accessed = last_accessed
                    existing_app.gmt_modified = datetime.utcnow()
                    session.commit()
                else:
                    new_app = UserRecentAppsEntity(
                        user_code=user_code,
                        sys_code=sys_code,
                        app_code=app_code,
                        last_accessed=last_accessed,
                        gmt_create=datetime.utcnow(),
                        gmt_modified=datetime.utcnow(),
                    )
                    session.add(new_app)
                    session.commit()

                return UserRecentApps.from_dict(
                    {
                        "app_code": app_code,
                        "sys_code": sys_code,
                        "user_code": user_code,
                        "last_accessed": last_accessed,
                        "gmt_create": (
                            existing_app.gmt_create
                            if existing_app
                            else new_app.gmt_create
                        ),
                        "gmt_modified": last_accessed,
                    }
                )
            except Exception as ex:
                logger.error(f"recent use app upsert error: {ex}")


class GptsAppCollectionDao(BaseDao):
    def collect(
            self,
            app_code: str,
            user_code: Optional[str] = None,
            sys_code: Optional[str] = None,
    ):
        with self.session() as session:
            app_qry = session.query(GptsAppCollectionEntity)
            if user_code:
                app_qry = app_qry.filter(GptsAppCollectionEntity.user_code == user_code)
            if sys_code:
                app_qry = app_qry.filter(GptsAppCollectionEntity.sys_code == sys_code)
            if app_code:
                app_qry = app_qry.filter(GptsAppCollectionEntity.app_code == app_code)
            app_entity = app_qry.one_or_none()
            if app_entity is not None:
                raise "current app has been collected!"
            app_entity = GptsAppCollectionEntity(
                app_code=app_code,
                user_code=user_code,
                sys_code=sys_code,
            )
            session.add(app_entity)

    def uncollect(
            self,
            app_code: str,
            user_code: Optional[str] = None,
            sys_code: Optional[str] = None,
    ):
        with self.session() as session:
            app_qry = session.query(GptsAppCollectionEntity)
            if user_code:
                app_qry = app_qry.filter(GptsAppCollectionEntity.user_code == user_code)
            if sys_code:
                app_qry = app_qry.filter(GptsAppCollectionEntity.sys_code == sys_code)
            if app_code:
                app_qry = app_qry.filter(GptsAppCollectionEntity.app_code == app_code)
            app_entity = app_qry.one_or_none()
            if app_entity:
                session.delete(app_entity)
                session.commit()

    def list(self, query: GptsAppCollection):
        with self.session() as session:
            app_qry = session.query(GptsAppCollectionEntity)
            if query.user_code:
                app_qry = app_qry.filter(
                    GptsAppCollectionEntity.user_code == query.user_code
                )
            if query.sys_code:
                app_qry = app_qry.filter(
                    GptsAppCollectionEntity.sys_code == query.sys_code
                )
            if query.app_code:
                app_qry = app_qry.filter(
                    GptsAppCollectionEntity.app_code == query.app_code
                )
            res = app_qry.all()
            session.close()
            return res


class GptsAppDao(BaseDao):
    def list_all(self):
        with self.session() as session:
            app_qry = session.query(GptsAppEntity)
            app_entities = app_qry.all()
            apps = [
                GptsApp.from_dict(
                    {
                        "app_code": app_info.app_code,
                        "app_name": app_info.app_name,
                        "language": app_info.language,
                        "app_describe": app_info.app_describe,
                        "team_mode": app_info.team_mode,
                        "team_context": app_info.team_context,
                        "user_code": app_info.user_code,
                        "sys_code": app_info.sys_code,
                        "created_at": app_info.created_at,
                        "updated_at": app_info.updated_at,
                        "published": app_info.published,
                        "details": [],
                        "admins": [],
                        # "keep_start_rounds": app_info.keep_start_rounds,
                        # "keep_end_rounds": app_info.keep_end_rounds,
                    }
                )
                for app_info in app_entities
            ]
            return apps

    def list_hot_apps(self, query: GptsAppQuery):
        from derisk.storage.chat_history.chat_history_db import ChatHistoryDao

        chat_history_dao = ChatHistoryDao()
        hot_app_map = chat_history_dao.get_hot_app_map(query.page - 1, query.page_size)
        logger.info(f"hot_app_map = {hot_app_map}")
        hot_map = {}
        for hp in hot_app_map:
            hot_map[hp.get("app_code")] = hp.get("sz")
        app_codes = [hot_app.get("app_code") for hot_app in hot_app_map]
        if len(app_codes) == 0:
            return []
        apps = self.app_list(
            GptsAppQuery(app_codes=app_codes, hot_map=hot_map, need_owner_info="true")
        ).app_list
        return apps

    def app_list(self, query: GptsAppQuery, parse_llm_strategy: bool = False):
        recent_app_codes = []
        collection_dao = GptsAppCollectionDao()
        gpts_collections = collection_dao.list(
            GptsAppCollection.from_dict(
                {"sys_code": query.sys_code, "user_code": query.user_code}
            )
        )
        app_codes = [gc.app_code for gc in gpts_collections]
        if query.is_recent_used and query.is_recent_used.lower() == "true":
            recent_app_dao = UserRecentAppsDao()
            recent_apps = recent_app_dao.query(
                user_code=query.user_code,
                sys_code=query.sys_code,
                app_code=query.app_code,
            )
            recent_app_codes = [ra.app_code for ra in recent_apps]

        session = self.get_raw_session()
        try:
            app_qry = session.query(GptsAppEntity)
            if query.app_name:
                app_qry = app_qry.filter(
                    GptsAppEntity.app_name.like(f"%{query.app_name}%")
                )
            if not (query.ignore_user and query.ignore_user.lower() == "true"):
                if query.user_code:
                    app_qry = app_qry.filter(
                        or_(
                            GptsAppEntity.user_code == query.user_code,
                            GptsAppEntity.admins.like(f"%{query.user_code}%"),
                        )
                    )
                if query.sys_code:
                    app_qry = app_qry.filter(GptsAppEntity.sys_code == query.sys_code)
            if query.team_mode:
                app_qry = app_qry.filter(GptsAppEntity.team_mode == query.team_mode)
            if query.is_collected and query.is_collected.lower() in ("true", "false"):
                app_qry = app_qry.filter(GptsAppEntity.app_code.in_(app_codes))
            if query.is_recent_used and query.is_recent_used.lower() == "true":
                app_qry = app_qry.filter(GptsAppEntity.app_code.in_(recent_app_codes))
            if query.published and query.published.lower() in ("true", "false"):
                app_qry = app_qry.filter(
                    GptsAppEntity.published == query.published.lower()
                )
            if query.app_codes:
                app_qry = app_qry.filter(GptsAppEntity.app_code.in_(query.app_codes))
            total_count = app_qry.count()
            app_qry = app_qry.order_by(GptsAppEntity.id.desc())
            app_qry = app_qry.offset((query.page - 1) * query.page_size).limit(
                query.page_size
            )
            results = app_qry.all()
        finally:
            session.close()
        if results is not None:
            result_app_codes = [res.app_code for res in results]
            app_details_group = self._group_app_details(result_app_codes, session)
            app_question_group = self._group_app_questions(result_app_codes, session)
            apps = []
            app_resp = GptsAppResponse()

            for app_info in results:
                app_details = app_details_group.get(app_info.app_code, [])
                recommend_questions = app_question_group.get(app_info.app_code, [])
                if ((app_info.team_mode and app_info.team_mode == "auto_plan"
                     and app_info.team_context and app_info.team_context.find("reasoning_engine") > 0)):
                    team_context = json.loads(str(app_info.team_context))
                    app_detail = GptsAppDetailEntity()
                    app_detail.agent_describe = None
                    app_detail.agent_name = "ReasoningPlanner"
                    app_detail.agent_role = "ReasoningPlanner"
                    app_detail.app_code = app_info.app_code
                    app_detail.app_name = app_info.app_name
                    app_detail.created_at = app_info.created_at
                    app_detail.llm_strategy = team_context["llm_strategy"]
                    app_detail.llm_strategy_value = json.dumps(team_context["llm_strategy_value"], ensure_ascii=False)
                    app_detail.node_id = app_info.app_code
                    app_detail.prompt_template = None
                    app_detail.resources = json.dumps(team_context["resources"], ensure_ascii=False)
                    app_detail.type = None
                    app_detail.updated_at = app_info.updated_at
                    app_details = [app_detail]
                try:
                    apps.append(
                        GptsApp.from_dict(
                            self._entity_to_app_dict(
                                app_info,
                                app_details,
                                query.hot_map,
                                app_codes,
                                parse_llm_strategy,
                                None,
                                None,
                                recommend_questions,
                            )
                        )
                    )
                except Exception as e:
                    logger.warning(str(e), e)

            apps = sorted(
                apps,
                key=lambda obj: (
                    float("-inf") if obj.hot_value is None else obj.hot_value
                ),
                reverse=True,
            )
            app_resp.total_count = total_count
            app_resp.app_list = apps
            app_resp.current_page = query.page
            app_resp.total_page = (total_count + query.page_size - 1) // query.page_size
            return app_resp


    def get_gpts_apps_by_knowledge_id(self, knowledge_id: Optional[str] = None):
        session = self.get_raw_session()
        try:
            apps = session.query(GptsAppEntity)
            if knowledge_id is not None:
                apps = apps.filter(GptsAppEntity.team_context.like("%" + knowledge_id + "%"))

            apps = apps.order_by(GptsAppEntity.id.asc())

            results = apps.all()
            return results

        finally:
            session.close()


    def _entity_to_app_dict(
            self,
            app_info: GptsAppEntity,
            app_details: List[GptsAppDetailEntity],
            hot_app_map: dict = None,
            app_collects: List[str] = [],
            parse_llm_strategy: bool = False,
            owner_name: str = None,
            owner_avatar_url: str = None,
            recommend_questions: List = None,
    ):
        return {
            "app_code": app_info.app_code,
            "app_name": app_info.app_name,
            "language": app_info.language,
            "app_describe": app_info.app_describe,
            "team_mode": app_info.team_mode,
            "team_context": _load_team_context(
                app_info.team_mode, app_info.team_context
            ),
            "user_code": app_info.user_code,
            "icon": app_info.icon,
            "sys_code": app_info.sys_code,
            "is_collected": "true" if app_info.app_code in app_collects else "false",
            "created_at": app_info.created_at,
            "updated_at": app_info.updated_at,
            "details": [
                GptsAppDetail.from_dict(item.to_dict(), parse_llm_strategy)
                for item in app_details
            ],
            "published": app_info.published,
            "param_need": (
                json.loads(app_info.param_need) if app_info.param_need else None
            ),
            "hot_value": (
                hot_app_map.get(app_info.app_code, 0) if hot_app_map is not None else 0
            ),
            "owner_name": app_info.user_code,
            "owner_avatar_url": owner_avatar_url,
            "recommend_questions": (
               [] 
            ),
            "admins": [],
        }

    def _group_app_details(self, app_codes, session):
        app_detail_qry = session.query(GptsAppDetailEntity).filter(
            GptsAppDetailEntity.app_code.in_(app_codes)
        )
        app_details = app_detail_qry.all()
        app_details.sort(key=lambda x: x.app_code)
        app_details_group = {
            key: list(group)
            for key, group in groupby(app_details, key=lambda x: x.app_code)
        }
        return app_details_group

    def _group_app_questions(self, app_codes, session):
        return {} 

    def native_app_detail(self, app_name: str):
        with self.session() as session:
            app_qry = (
                session.query(GptsAppEntity)
                .filter(GptsAppEntity.app_name == app_name)
                .filter(GptsAppEntity.team_mode == "native_app")
            )
            app_info = app_qry.first()
            if not app_info:
                logger.warning(f"Not found native app {app_name}!")
                return None
            app_detail_qry = session.query(GptsAppDetailEntity).filter(
                GptsAppDetailEntity.app_code == app_info.app_code
            )
            app_details = app_detail_qry.all()

            if app_info:
                app = GptsApp.from_dict(self._entity_to_app_dict(app_info, app_details))
                return app
            else:
                return app_info

    async def auto_team_bin_apps(self, team_app_code: str, bind_apps: List[str]):
        logger.info(f"auto_team_bin_apps:{team_app_code},{bind_apps}")
        ### 把应用转换为当前应用的子agent，
        team_app: GptsApp = self.app_detail(team_app_code)
        if not team_app:
            raise ValueError(f"{team_app} is not a app!")
        if team_app.team_mode != TeamMode.AUTO_PLAN.value:
            raise ValueError(f"{team_app.app_name} is not a multi agents app!")

        gpt_apps: List[GptsApp] = []
        err_app_codes: List[str] = []
        for bind_app in bind_apps:
            gpt_app: GptsApp = self.app_detail(bind_app)
            if not gpt_app:
                err_app_codes.append(bind_app)
            gpt_apps.append(gpt_app)
        if len(err_app_codes) > 0:
            raise ValueError(
                f"There is a problem with the app codes to be bound！[{err_app_codes}]"
            )
        for gpt_app in gpt_apps:
            ## 暂时线只支持绑定单agent应用，多Agent应用绑定要把多Agent的子Agent资源提到绑定的TL Agent上，可能需要产品测来定义
            if gpt_app.team_mode == TeamMode.SINGLE_AGENT.value:
                new_detail: GptsAppDetail = gpt_app.details[0].copy()
                new_detail.app_name = team_app.app_name
                new_detail.app_code = team_app.app_code
                strategy_values = json.loads(gpt_app.details[0].llm_strategy_value)
                # 恢复模拟前端的数据
                new_detail.llm_strategy_value = ",".join(strategy_values)
                new_detail.agent_describe = gpt_app.app_describe
                new_detail.agent_role = (
                    new_detail.agent_role
                    if new_detail.agent_role
                    else new_detail.agent_name
                )
                new_detail.agent_name = gpt_app.app_name
                team_app.details.append(new_detail)
                self.edit(team_app)

    def app_detail(self, app_code: str, user_code: str = None, sys_code: str = None):
        with self.session() as session:
            app_qry = session.query(GptsAppEntity).filter(
                GptsAppEntity.app_code == app_code
            )
            return app_qry.first()
         
    def delete(
            self,
            app_code: str,
            user_code: Optional[str] = None,
            sys_code: Optional[str] = None,
    ):
        """
        To delete the application, you also need to delete the corresponding plug-ins
        and collections.
        """
        if app_code is None:
            raise "cannot delete app when app_code is None"
        with self.session() as session:
            app_qry = session.query(GptsAppEntity)
            app_qry = app_qry.filter(GptsAppEntity.app_code == app_code)
            app_qry.delete()

            app_detail_qry = session.query(GptsAppDetailEntity).filter(
                GptsAppDetailEntity.app_code == app_code
            )
            app_detail_qry.delete()

            app_collect_qry = session.query(GptsAppCollectionEntity).filter(
                GptsAppCollectionEntity.app_code == app_code
            )
            app_collect_qry.delete()

    def remove_native_app(self, app_code: str):
        with self.session(commit=True) as session:
            app_qry = session.query(GptsAppEntity)
            app_qry = app_qry.filter(GptsAppEntity.team_mode == "native_app").filter(
                GptsAppEntity.app_code == app_code
            )
            app_qry.delete()

    def create(self, gpts_app: GptsApp):
        with self.session() as session:
            app_entity = GptsAppEntity(
                app_code=gpts_app.app_code if gpts_app.app_code else str(uuid.uuid1()),
                app_name=gpts_app.app_name,
                app_describe=gpts_app.app_describe,
                team_mode=gpts_app.team_mode,
                team_context=_parse_team_context(gpts_app.team_context),
                language=gpts_app.language,
                user_code=gpts_app.user_code,
                sys_code=gpts_app.sys_code,
                created_at=gpts_app.created_at,
                updated_at=gpts_app.updated_at,
                icon=gpts_app.icon,
                published="true" if gpts_app.published else "false",
                param_need=(
                    json.dumps(gpts_app.param_need) if gpts_app.param_need else None
                ),
            )
            session.add(app_entity)

            app_details = []
            for item in gpts_app.details:
                resource_dicts = [resource.to_dict() for resource in item.resources]
                if item.agent_name is None:
                    raise "agent name cannot be None"

                app_details.append(
                    GptsAppDetailEntity(
                        app_code=app_entity.app_code,
                        app_name=app_entity.app_name,
                        agent_name=item.agent_name,
                        agent_role=item.agent_role
                        if item.agent_role
                        else item.agent_name,
                        node_id=str(uuid.uuid1()),
                        resources=json.dumps(resource_dicts, ensure_ascii=False),
                        prompt_template=item.prompt_template,
                        llm_strategy=item.llm_strategy,
                        llm_strategy_value=(
                            None
                            if item.llm_strategy_value is None
                            else json.dumps(tuple(item.llm_strategy_value.split(",")))
                        ),
                        created_at=item.created_at,
                        updated_at=item.updated_at,
                    )
                )
            session.add_all(app_details)
            gpts_app.app_code = app_entity.app_code
            return gpts_app

    def edit(self, gpts_app: GptsApp):
        with self.session() as session:
            app_qry = session.query(GptsAppEntity)
            if gpts_app.app_code is None:
                raise Exception("app_code is None, don't allow to edit!")
            app_qry = app_qry.filter(GptsAppEntity.app_code == gpts_app.app_code)
            app_entity = app_qry.one()

            is_reasoning_agent: bool = len(gpts_app.details) == 1 and gpts_app.details[0].agent_name == "ReasoningPlanner"
            if is_reasoning_agent:
                app_entity.team_context = json.dumps(AutoTeamContext(
                    can_ask_user=True,
                    llm_strategy=gpts_app.details[0].llm_strategy,
                    llm_strategy_value=gpts_app.details[0].llm_strategy_value.split(","),
                    prompt_template=None,
                    resources=gpts_app.details[0].resources,
                    teamleader="ReasoningPlanner",
                ).to_dict(), ensure_ascii=False)
            else:
                app_entity.team_context = _parse_team_context(gpts_app.team_context)
            app_entity.app_name = gpts_app.app_name
            app_entity.app_describe = gpts_app.app_describe
            app_entity.language = gpts_app.language
            app_entity.team_mode = gpts_app.team_mode
            app_entity.icon = gpts_app.icon
            app_entity.param_need = json.dumps(gpts_app.param_need)
            app_entity.keep_start_rounds = gpts_app.keep_start_rounds
            app_entity.keep_end_rounds = gpts_app.keep_end_rounds
            session.merge(app_entity)

            old_details = session.query(GptsAppDetailEntity).filter(
                GptsAppDetailEntity.app_code == gpts_app.app_code
            )
            old_details.delete()

            app_details = []
            if not is_reasoning_agent:
                for item in gpts_app.details:
                    resource_dicts = [resource.to_dict() for resource in item.resources]
                    app_details.append(
                        GptsAppDetailEntity(
                            app_code=gpts_app.app_code,
                            app_name=gpts_app.app_name,
                            agent_name=item.agent_name,
                            type=item.type,
                            agent_role=item.agent_role
                            if item.agent_role
                            else item.agent_name,
                            agent_describe=item.agent_describe,
                            node_id=str(uuid.uuid1()),
                            resources=json.dumps(resource_dicts, ensure_ascii=False),
                            prompt_template=item.prompt_template,
                            llm_strategy=item.llm_strategy,
                            llm_strategy_value=(
                                None
                                if item.llm_strategy_value is None
                                else json.dumps(tuple(item.llm_strategy_value.split(",")))
                            ),
                            created_at=item.created_at,
                            updated_at=item.updated_at,
                        )
                    )
                session.add_all(app_details)
            session.commit()

    def update_admins(self, app_code: str, user_nos: Optional[list[str]] = None):
        """
        update admins by app_code
        """
        with self.session() as session:
            app_qry = session.query(GptsAppEntity).filter(
                GptsAppEntity.app_code == app_code
            )
            entity = app_qry.one()
            entity.admins = user_nos
            session.merge(entity)
            session.commit()

    def get_admins(self, app_code: str):
        """
        get admins by app_code
        """
        with self.session() as session:
            app_qry = session.query(GptsAppEntity).filter(
                GptsAppEntity.app_code == app_code
            )
            entity = app_qry.one()
            return entity.admins

    def publish(
            self,
            app_code: str,
            user_code: Optional[str] = None,
            sys_code: Optional[str] = None,
    ):
        """
        To publish the application so that other users and access it.
        """
        if app_code is None:
            raise Exception("cannot publish app when app_code is None")
        with self.session() as session:
            app_qry = session.query(GptsAppEntity)
            app_qry = app_qry.filter(GptsAppEntity.app_code == app_code)
            app_entity = app_qry.one()
            if app_entity is not None:
                app_entity.published = "true"
                session.merge(app_entity)
                app_collect_qry = session.query(GptsAppCollectionEntity).filter(
                    GptsAppCollectionEntity.app_code == app_code
                )
                app_collect_qry.delete()

    def unpublish(
            self,
            app_code: str,
            user_code: Optional[str] = None,
            sys_code: Optional[str] = None,
    ):
        """
        To publish the application so that other users and access it.
        """
        if app_code is None:
            raise Exception("cannot publish app when app_code is None")
        with self.session() as session:
            app_qry = session.query(GptsAppEntity)
            app_qry = app_qry.filter(GptsAppEntity.app_code == app_code)
            app_entity = app_qry.one()
            if app_entity is not None:
                app_entity.published = "false"
                session.merge(app_entity)
                app_collect_qry = session.query(GptsAppCollectionEntity).filter(
                    GptsAppCollectionEntity.app_code == app_code
                )
                app_collect_qry.delete()

    def init_native_apps(self, user_code: Optional[str] = None):
        """
        "Chat Knowledge", "Chat DB", "Chat Data", "Professional DBA", "Dashboard",
        "Chat Excel" "chat_knowledge", "chat_with_db_qa", "chat_with_db_execute",
        "chat_dba", "chat_dashboard", "chat_excel"
        """
        chat_normal_ctx = NativeTeamContext(
            chat_scene="chat_normal",
            scene_name="Chat Normal",
            scene_describe="Native LLM dialogue",
            param_title="",
            show_disable=False,
        )
        chat_knowledge_ctx = NativeTeamContext(
            chat_scene="chat_knowledge",
            scene_name="Chat Knowledge",
            scene_describe="Private knowledge base Q&A",
            param_title="",
            show_disable=False,
        )
        chat_with_db_qa_ctx = NativeTeamContext(
            chat_scene="chat_with_db_qa",
            scene_name="Chat DB",
            scene_describe="Database Metadata Q&A",
            param_title="",
            show_disable=False,
        )
        chat_with_db_execute_ctx = NativeTeamContext(
            chat_scene="chat_with_db_execute",
            scene_name="Chat Data",
            scene_describe="Have a conversation with your private data through natural"
                           " language",
            param_title="",
            show_disable=False,
        )
        chat_dashboard_ctx = NativeTeamContext(
            chat_scene="chat_dashboard",
            scene_name="Chat Dashboard",
            scene_describe="Provide you with professional data analysis reports through"
                           " natural language",
            param_title="",
            show_disable=False,
        )
        chat_excel_ctx = NativeTeamContext(
            chat_scene="chat_excel",
            scene_name="Chat Excel",
            scene_describe="Excel analysis through natural language",
            param_title="",
            show_disable=False,
        )

        gpts_dao = GptsAppDao()

        chat_knowledge_app = GptsApp(
            app_code=chat_knowledge_ctx.chat_scene,
            app_name=chat_knowledge_ctx.scene_name,
            language="zh",
            team_mode="native_app",
            details=[],
            app_describe=chat_knowledge_ctx.scene_describe,
            team_context=chat_knowledge_ctx,
            param_need=[
                {
                    "type": AppParamType.Resource.value,
                    "value": ResourceType.Knowledge.value,
                },
                {"type": AppParamType.Model.value, "value": None},
                {"type": AppParamType.Temperature.value, "value": None},
                {"type": AppParamType.MaxNewTokens.value, "value": None},
            ],
            user_code=user_code,
            published="true",
        )
        try:
            gpts_dao.remove_native_app(chat_knowledge_app.app_code)
            gpts_dao.create(chat_knowledge_app)
        except Exception as ex:
            logger.exception(f"create chat_knowledge_app error: {ex}")

        chat_normal_app = GptsApp(
            app_code=chat_normal_ctx.chat_scene,
            app_name=chat_normal_ctx.scene_name,
            language="zh",
            team_mode="native_app",
            details=[],
            app_describe=chat_normal_ctx.scene_describe,
            team_context=chat_normal_ctx,
            param_need=[
                {"type": AppParamType.Model.value, "value": None},
                {"type": AppParamType.Temperature.value, "value": None},
                {"type": AppParamType.MaxNewTokens.value, "value": None},
            ],
            user_code=user_code,
            published="true",
        )
        try:
            gpts_dao.remove_native_app(chat_normal_app.app_code)
            gpts_dao.create(chat_normal_app)
        except Exception as ex:
            logger.exception(f"create chat_normal_app error: {ex}")

        chat_with_db_qa_app = GptsApp(
            app_code=chat_with_db_qa_ctx.chat_scene,
            app_name=chat_with_db_qa_ctx.scene_name,
            language="zh",
            team_mode="native_app",
            details=[],
            app_describe=chat_with_db_qa_ctx.scene_describe,
            team_context=chat_with_db_qa_ctx,
            param_need=[
                {"type": AppParamType.Resource.value, "value": ResourceType.DB.value},
                {"type": AppParamType.Model.value, "value": None},
                {"type": AppParamType.Temperature.value, "value": None},
                {"type": AppParamType.MaxNewTokens.value, "value": None},
            ],
            user_code=user_code,
            published="true",
        )
        try:
            gpts_dao.remove_native_app(chat_with_db_qa_app.app_code)
            gpts_dao.create(chat_with_db_qa_app)
        except Exception as ex:
            logger.exception(f"create chat_with_db_qa_app error: {ex}")

        chat_with_db_execute_app = GptsApp(
            app_code=chat_with_db_execute_ctx.chat_scene,
            app_name=chat_with_db_execute_ctx.scene_name,
            language="zh",
            team_mode="native_app",
            details=[],
            app_describe=chat_with_db_execute_ctx.scene_describe,
            team_context=chat_with_db_execute_ctx,
            param_need=[
                {"type": AppParamType.Resource.value, "value": ResourceType.DB.value},
                {"type": AppParamType.Model.value, "value": None},
                {"type": AppParamType.Temperature.value, "value": None},
                {"type": AppParamType.MaxNewTokens.value, "value": None},
            ],
            user_code=user_code,
            published="true",
        )
        try:
            gpts_dao.remove_native_app(chat_with_db_execute_app.app_code)
            gpts_dao.create(chat_with_db_execute_app)
        except Exception as ex:
            logger.exception(f"create chat_with_db_execute_app error: {ex}")

        chat_dashboard_app = GptsApp(
            app_code=chat_dashboard_ctx.chat_scene,
            app_name=chat_dashboard_ctx.scene_name,
            language="zh",
            team_mode="native_app",
            details=[],
            app_describe=chat_dashboard_ctx.scene_describe,
            param_need=[
                {"type": AppParamType.Resource.value, "value": ResourceType.DB.value},
                {"type": AppParamType.Model.value, "value": None},
                {"type": AppParamType.Temperature.value, "value": None},
                {"type": AppParamType.MaxNewTokens.value, "value": None},
            ],
            team_context=chat_dashboard_ctx,
            user_code=user_code,
            published="true",
        )
        try:
            gpts_dao.remove_native_app(chat_dashboard_app.app_code)
            gpts_dao.create(chat_dashboard_app)
        except Exception as ex:
            logger.exception(f"create chat_dashboard_app error: {ex}")

        chat_excel_app = GptsApp(
            app_code=chat_excel_ctx.chat_scene,
            app_name=chat_excel_ctx.scene_name,
            language="zh",
            team_mode="native_app",
            details=[],
            app_describe=chat_excel_ctx.scene_describe,
            team_context=chat_excel_ctx,
            param_need=[
                {
                    "type": AppParamType.Resource.value,
                    "value": ResourceType.ExcelFile.value,
                },
                {"type": AppParamType.Model.value, "value": None},
                {"type": AppParamType.Temperature.value, "value": None},
                {"type": AppParamType.MaxNewTokens.value, "value": None},
            ],
            user_code=user_code,
            published="true",
        )
        try:
            gpts_dao.remove_native_app(chat_excel_app.app_code)
            gpts_dao.create(chat_excel_app)
        except Exception as ex:
            logger.exception(f"create chat_excel_app error: {ex}")


def _parse_team_context(
        team_context: Optional[
            Union[
                str, AutoTeamContext, SingleAgentContext, AWELTeamContext, NativeTeamContext
            ]
        ] = None,
):
    """
    parse team_context to str
    """
    if (
            isinstance(team_context, AWELTeamContext)
            or isinstance(team_context, NativeTeamContext)
            or isinstance(team_context, AutoTeamContext)
            or isinstance(team_context, SingleAgentContext)
    ):
        return model_to_json(team_context)
    return team_context


def _load_team_context(
        team_mode: str = None, team_context: str = None
) -> Union[
    str, AWELTeamContext, SingleAgentContext, NativeTeamContext, AutoTeamContext
]:
    """
    load team_context to str or AWELTeamContext
    """
    if team_mode is not None:
        match team_mode:
            case TeamMode.SINGLE_AGENT.value:
                try:
                    if team_context:
                        single_agent_ctx = SingleAgentContext(
                            **json.loads(team_context)
                        )
                        return single_agent_ctx
                    else:
                        return None
                except Exception as ex:
                    logger.warning(
                        f"_load_team_context error, team_mode={team_mode}, "
                        f"team_context={team_context}, {ex}"
                    )
                    return None
            case TeamMode.AWEL_LAYOUT.value:
                try:
                    if team_context:
                        awel_team_ctx = AWELTeamContext(**json.loads(team_context))
                        return awel_team_ctx
                    else:
                        return None
                except Exception as ex:
                    logger.exception(
                        f"_load_team_context error, team_mode={team_mode}, "
                        f"team_context={team_context}, {ex}"
                    )
            case TeamMode.AUTO_PLAN.value:
                try:
                    if team_context:
                        context_obj = json.loads(team_context)
                        if "resources" in context_obj:
                            resource = context_obj["resources"]
                            if isinstance(resource, str):
                                resource_obj = json.loads(context_obj["resources"])
                            else:
                                resource_obj = resource
                            context_obj["resources"] = resource_obj

                        auto_team_ctx = AutoTeamContext(**context_obj)
                        return auto_team_ctx
                    else:
                        return None
                except Exception as ex:
                    logger.exception(
                        f"_load_team_context error, team_mode={team_mode}, "
                        f"team_context={team_context}, {ex}"
                    )
            case TeamMode.NATIVE_APP.value:
                try:
                    if team_context:
                        native_team_ctx = NativeTeamContext(**json.loads(team_context))
                        return native_team_ctx
                    else:
                        return None
                except Exception as ex:
                    logger.exception(
                        f"_load_team_context error, team_mode={team_mode}, "
                        f"team_context={team_context}, {ex}"
                    )
    return team_context


def native_app_params():
    chat_excel = {
        "chat_scene": ChatScene.ChatExcel.value(),
        "scene_name": ChatScene.ChatExcel.scene_name(),
        "param_need": [
            {
                "type": AppParamType.Resource.value,
                "value": ResourceType.ExcelFile.value,
            },
            {"type": AppParamType.Model.value, "value": None},
            {"type": AppParamType.Temperature.value, "value": None},
            {"type": AppParamType.MaxNewTokens.value, "value": None},
        ],
    }
    chat_with_db_qa = {
        "chat_scene": ChatScene.ChatWithDbQA.value(),
        "scene_name": ChatScene.ChatWithDbQA.scene_name(),
        "param_need": [
            {"type": AppParamType.Resource.value, "value": ResourceType.DB.value},
            {"type": AppParamType.Model.value, "value": None},
            {"type": AppParamType.Temperature.value, "value": None},
            {"type": AppParamType.MaxNewTokens.value, "value": None},
        ],
    }
    chat_with_db_execute = {
        "chat_scene": ChatScene.ChatWithDbExecute.value(),
        "scene_name": ChatScene.ChatWithDbExecute.scene_name(),
        "param_need": [
            {"type": AppParamType.Resource.value, "value": ResourceType.DB.value},
            {"type": AppParamType.Model.value, "value": None},
            {"type": AppParamType.Temperature.value, "value": None},
            {"type": AppParamType.MaxNewTokens.value, "value": None},
        ],
    }
    chat_knowledge = {
        "chat_scene": ChatScene.ChatKnowledge.value(),
        "scene_name": ChatScene.ChatKnowledge.scene_name(),
        "param_need": [
            {
                "type": AppParamType.Resource.value,
                "value": ResourceType.Knowledge.value,
            },
            {"type": AppParamType.Model.value, "value": None},
            {"type": AppParamType.Temperature.value, "value": None},
            {"type": AppParamType.MaxNewTokens.value, "value": None},
        ],
    }
    chat_dashboard = {
        "chat_scene": ChatScene.ChatDashboard.value(),
        "scene_name": ChatScene.ChatDashboard.scene_name(),
        "param_need": [
            {"type": AppParamType.Resource.value, "value": ResourceType.DB.value},
            {"type": AppParamType.Model.value, "value": None},
            {"type": AppParamType.Temperature.value, "value": None},
            {"type": AppParamType.MaxNewTokens.value, "value": None},
        ],
    }
    chat_normal = {
        "chat_scene": ChatScene.ChatNormal.value(),
        "scene_name": ChatScene.ChatNormal.scene_name(),
        "param_need": [
            {"type": AppParamType.Model.value, "value": None},
            {"type": AppParamType.Temperature.value, "value": None},
            {"type": AppParamType.MaxNewTokens.value, "value": None},
        ],
    }
    return [
        chat_excel,
        chat_with_db_qa,
        chat_with_db_execute,
        chat_knowledge,
        chat_dashboard,
        chat_normal,
    ]


def adapt_native_app_model(dialogue: ConversationVo):
    """
    Adapt native app chat scene.
    """
    try:
        if dialogue.chat_mode not in [
            ChatScene.ChatKnowledge.value(),
            ChatScene.ChatExcel.value(),
            ChatScene.ChatWithDbQA.value(),
            ChatScene.ChatWithDbExecute.value(),
            ChatScene.ChatDashboard.value(),
            ChatScene.ChatNormal.value,
        ]:
            return dialogue
        gpts_dao = GptsAppDao()
        app_info = gpts_dao.app_detail(
            dialogue.app_code, dialogue.user_name, dialogue.sys_code
        )
        if app_info.team_mode == "native_app":
            if app_info.param_need:
                resource_params = [
                    x
                    for x in app_info.param_need
                    if x["type"] == AppParamType.Resource.value
                ]
                prompt_params = [
                    x
                    for x in app_info.param_need
                    if x["type"] == AppParamType.PromptTemplate.value
                ]
                dialogue.prompt_code = (
                    prompt_params[0].get("value") if prompt_params else None
                )
                if len(resource_params) == 1:
                    resource_param = resource_params[0]
                    if resource_param.get("bind_value"):
                        dialogue.select_param = parse_select_param(
                            app_info.team_context.chat_scene,
                            resource_param.get("bind_value"),
                        )
                        dialogue.chat_mode = app_info.team_context.chat_scene
                    elif (
                            app_info.app_code == ChatScene.ChatKnowledge.value()
                            and not dialogue.select_param.isdigit()
                    ):
                        from derisk_app.knowledge.service import (
                            KnowledgeService,
                            KnowledgeSpaceRequest,
                        )

                        ks_service = KnowledgeService()
                        knowledge_spaces = ks_service.get_knowledge_space(
                            KnowledgeSpaceRequest(name=dialogue.select_param)
                        )
                        if len(knowledge_spaces) == 1:
                            dialogue.select_param = knowledge_spaces[0].name
        return dialogue
    except Exception as e:
        logger.info(f"adapt_native_app_model error: {e}")
        return dialogue


def parse_select_param(chat_scene: str, bind_value: str):
    match chat_scene:
        case _:
            return bind_value


class AppParamType(Enum):
    Resource = "resource"
    Model = "model"
    Temperature = "temperature"
    MaxNewTokens = "max_new_tokens"
    PromptTemplate = "prompt_template"


class TransferSseRequest(BaseModel):
    all: Optional[bool] = False
    app_code_list: Optional[List[str]] = None
    source: Optional[str] = None
    faas_function_pre: Optional[str] = None
    uri: Optional[str] = None


class AllowToolsRequest(BaseModel):
    app_code: str
    mcp_server: str
    allow_tools: List[str]


def mcp_address(source: str, mcp_server: str, uri: str, faas_function_pre: Optional[str] = None):
    if mcp_server == 'mcp-linglongcopilot':
        return None
    if source.lower() == 'df':
        return {
            "name": mcp_server,
            "mcp_servers": f"{uri}/mcp/sse?server_name={mcp_server}"
        }
    elif source.lower() == 'faas':
        def to_camel_case(text):
            words = text.replace('-', ' ').replace('_', ' ').split()
            return words[0] + ''.join(word.capitalize() for word in words[1:])

        return {
            "name": mcp_server,
            "mcp_servers": f"{uri}/sse",
            "headers": json.dumps({
                "x-mcp-server-code": f"{faas_function_pre}.{to_camel_case(mcp_server)}"
            })
        }
    else:
        return None
