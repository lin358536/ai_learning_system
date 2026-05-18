# 智途校园 - Agent模块初始化
from app.agent.tools.generate_plan import GeneratePlanTool
from app.agent.tools.query_plans import QueryPlansTool
from app.agent.tools.generate_resume import GenerateResumeTool
from app.agent.tools.query_resumes import QueryResumesTool
from app.agent.tools.query_profile import QueryProfileTool
from app.agent.tools.query_points import QueryPointsTool
from app.agent.tools.registry import tool_registry

# 注册所有工具
tool_registry.register(GeneratePlanTool())
tool_registry.register(QueryPlansTool())
tool_registry.register(GenerateResumeTool())
tool_registry.register(QueryResumesTool())
tool_registry.register(QueryProfileTool())
tool_registry.register(QueryPointsTool())

__all__ = ["tool_registry"]
