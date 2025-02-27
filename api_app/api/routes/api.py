from collections import defaultdict
from typing import Any, DefaultDict, Dict, Optional

from fastapi import APIRouter, Request, Depends
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.openapi.utils import get_openapi

from api.dependencies.database import get_repository
from db.repositories.workspaces import WorkspaceRepository
from api.routes import health, workspaces, workspace_templates, workspace_service_templates, user_resource_templates, \
    shared_services, shared_service_templates
from core import config

core_tags_metadata = [
    {"name": "health", "description": "Verify that the TRE is up and running"},
    {"name": "workspace templates", "description": "**TRE admin** registers and can access templates"},
    {"name": "workspace service templates", "description": "**TRE admin** registers templates and can access templates"},
    {"name": "user resource templates", "description": "**TRE admin** registers templates and can access templates"},
    {"name": "workspaces", "description": "**TRE admin** administers workspaces, **TRE Users** can view their own workspaces"},
]

workspace_tags_metadata = [
    {"name": "workspaces", "description": " **Workspace Owners and Researchers** can view their own workspaces"},
    {"name": "workspace services", "description": "**Workspace Owners** administer workspace services, **Workspace Owners and Researchers** can view services in the workspaces they belong to"},
    {"name": "user resources", "description": "**Researchers** administer and can view their own researchers, **Workspace Owners** can view/update/delete all user resources in their workspaces"},
    {"name": "shared services", "description": "**TRE administratiors** administer shared services"},
]

router = APIRouter()

# Core API
core_router = APIRouter(prefix=config.API_PREFIX)
core_router.include_router(health.router, tags=["health"])
core_router.include_router(workspace_templates.workspace_templates_admin_router, tags=["workspace templates"])
core_router.include_router(workspace_service_templates.workspace_service_templates_core_router, tags=["workspace service templates"])
core_router.include_router(user_resource_templates.user_resource_templates_core_router, tags=["user resource templates"])
core_router.include_router(shared_service_templates.shared_service_templates_core_router, tags=["shared service templates"])
core_router.include_router(shared_services.shared_services_router, tags=["shared services"])
core_router.include_router(workspaces.workspaces_core_router, tags=["workspaces"])
core_router.include_router(workspaces.workspaces_shared_router, tags=["workspaces"])

core_swagger_router = APIRouter()

openapi_definitions: DefaultDict[str, Optional[Dict[str, Any]]] = defaultdict(lambda: None)


@core_swagger_router.get("/openapi.json", include_in_schema=False, name="core_openapi")
async def core_openapi(request: Request):
    global openapi_definitions

    if openapi_definitions["core"] is None:
        openapi_definitions["core"] = get_openapi(
            title=f"{config.PROJECT_NAME}",
            description=config.API_DESCRIPTION,
            version=config.VERSION,
            routes=core_router.routes,
            tags=core_tags_metadata
        )

    return openapi_definitions["core"]


@core_swagger_router.get("/docs", include_in_schema=False, name="core_swagger")
async def get_swagger(request: Request):
    swagger_ui_html = get_swagger_ui_html(
        openapi_url="openapi.json",
        title=request.app.title + " - Swagger UI",
        oauth2_redirect_url="/api/docs/oauth2-redirect",
        init_oauth={
            "usePkceWithAuthorizationCodeGrant": True,
            "clientId": config.SWAGGER_UI_CLIENT_ID,
            "scopes": ["openid", "offline_access", f"api://{config.API_CLIENT_ID}/user_impersonation"]
        }
    )

    return swagger_ui_html


@core_swagger_router.get('/docs/oauth2-redirect', include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()

core_router.include_router(core_swagger_router)
router.include_router(core_router)

# Workspace API
workspace_router = APIRouter(prefix=config.API_PREFIX)
workspace_router.include_router(workspaces.workspaces_shared_router, tags=["workspaces"])
workspace_router.include_router(workspaces.workspace_services_workspace_router, tags=["workspace services"])
workspace_router.include_router(workspaces.user_resources_workspace_router, tags=["user resources"])

workspace_swagger_router = APIRouter()


@workspace_swagger_router.get("/workspaces/{workspace_id}/openapi.json", include_in_schema=False, name="openapi_definitions")
async def get_openapi_json(workspace_id: str, request: Request, workspace_repo=Depends(get_repository(WorkspaceRepository))):
    global openapi_definitions

    if openapi_definitions[workspace_id] is None:

        openapi_definitions[workspace_id] = get_openapi(
            title=f"{config.PROJECT_NAME} - Workspace {workspace_id}",
            description=config.API_DESCRIPTION,
            version=config.VERSION,
            routes=workspace_router.routes,
            tags=workspace_tags_metadata
        )

        workspace = workspace_repo.get_workspace_by_id(workspace_id)
        ws_app_reg_id = workspace.properties['app_id']
        workspace_scopes = {
            f"api://{ws_app_reg_id}/user_impersonation": "List and Get TRE Workspaces"
        }
        openapi_definitions[workspace_id]['components']['securitySchemes']['oauth2']['flows']['authorizationCode']['scopes'] = workspace_scopes

    return openapi_definitions[workspace_id]


@workspace_swagger_router.get("/workspaces/{workspace_id}/docs", include_in_schema=False, name="workspace_swagger")
async def get_workspace_swagger(workspace_id, request: Request, workspace_repo=Depends(get_repository(WorkspaceRepository))):

    workspace = workspace_repo.get_workspace_by_id(workspace_id)
    ws_app_reg_id = workspace.properties['app_id']
    swagger_ui_html = get_swagger_ui_html(
        openapi_url="openapi.json",
        title=request.app.title + " - Swagger UI",
        oauth2_redirect_url="/api/docs/oauth2-redirect",
        init_oauth={
            "usePkceWithAuthorizationCodeGrant": True,
            "clientId": config.SWAGGER_UI_CLIENT_ID,
            "scopes": ["openid", "offline_access", f"api://{ws_app_reg_id}/user_impersonation"]
        }
    )

    return swagger_ui_html

workspace_router.include_router(workspace_swagger_router)
router.include_router(workspace_router)
