from fastapi import APIRouter

from coding_assistant.api.routes import auth_routes, evals, health, mcp_routes, orgs, repos, routing, runs, tools

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth_routes.router)
api_router.include_router(orgs.router)
api_router.include_router(runs.router)
api_router.include_router(tools.router)
api_router.include_router(routing.router)
api_router.include_router(repos.router)
api_router.include_router(evals.router)
api_router.include_router(mcp_routes.router)
