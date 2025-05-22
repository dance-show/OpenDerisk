"""Code Assistant Agent."""

import uuid
from typing import Optional, Tuple, List, Type

from derisk.agent import ConversableAgent, ProfileConfig, AgentMessage, Action, BlankAction
from derisk.agent.core.plan.report_agent import ReportAssistantAgent
from derisk.core import ModelMessageRoleType
from derisk.util.configure import DynConfig
from derisk.util.string_utils import str_to_bool
from derisk_ext.agent.agents.open_rca.actions.ipython_action import IpythonAction
from IPython.terminal.embed import InteractiveShellEmbed

_SYSTEM_TEMPLATE_ZH = """您是 {{ role }}，{% if name %} 名为 {{ name }}。{% endif %}\
现在，您已决定完成推理过程。现在您应该提供问题的最终答案。系统会向您提供可能的根本原因组件和原因的候选。您必须从提供的候选组件和原因中选择根本原因组件和原因。

## 可能的根本原因:
- CPU 使用率高
- 内存使用率高
- 网络延迟
- 网络丢包
- 磁盘 I/O 读取使用率高
- 磁盘空间使用率高
- JVM CPU 负载高
- JVM 内存溢出 (OOM)

## 可能的根本原因组件：

- apache01
- apache02
- Tomcat01
- Tomcat02
- Tomcat04
- Tomcat03
- MG01
- MG02
- IG01
- IG02
- Mysql01
- Mysql02
- Redis01
- Redis02

回想一下，问题是：{{question}}

请首先回顾你之前的推理过程，推断出该问题的确切答案。然后，在你的回复末尾，使用以下 JSON 格式总结你对根本原因的最终答案：
```json
{
"1": {
"根本原因发生日期时间":（如果问题询问，格式为：'%Y-%m-%d %H:%M:%S'，否则省略），
"根本原因组件":（如果问题询问，则从可能的根本原因组件列表中选择一个，否则省略），
"根本原因原因":（如果问题询问，则从可能的根本原因原因列表中选择一个，否则省略），
},（必填）
"2": {
"根本原因发生日期时间":（如果问题询问，格式为：'%Y-%m-%d %H:%M:%S'，否则省略），
"根本原因组件":（如果问题询问，则从可能的根本原因组件列表中选择一个，否则省略），
"根本原因原因":（如果问题询问，则从可能的根本原因原因列表中选择一个，否则省略），
},（仅当故障编号为“未知”或问题中的“多个”）
...（仅当问题中的故障编号为“未知”或“多个”时）
}
```
（请使用“```json”和“```”标签包装 JSON 对象。您只需提供问题所要求的元素，并省略 JSON 中的其他字段。）
请注意，所有根本原因组件和原因都必须从提供的候选中选择。请勿在 JSON 中回复“未知”、“空”或“未找到”。在选择根本原因组件和原因时不要过于保守。请果断地根据您当前的观察推断出一个可能的答案。
"""

_SYSTEM_TEMPLATE = """You are a {{ role }}, {% if name %}named {{ name }}. {% endif %}\
Now, you have decided to finish your reasoning process. You should now provide the final answer to the issue. The candidates of possible root cause components and reasons are provided to you. The root cause components and reasons must be selected from the provided candidates.

## POSSIBLE ROOT CAUSE REASONS:
        
- high CPU usage
- high memory usage 
- network latency 
- network packet loss
- high disk I/O read usage 
- high disk space usage
- high JVM CPU load 
- JVM Out of Memory (OOM) Heap

## POSSIBLE ROOT CAUSE COMPONENTS:

- apache01
- apache02
- Tomcat01
- Tomcat02
- Tomcat04
- Tomcat03
- MG01
- MG02
- IG01
- IG02
- Mysql01
- Mysql02
- Redis01
- Redis02

Recall the issue is: {{question}}

Please first review your previous reasoning process to infer an exact answer of the issue. Then, summarize your final answer of the root causes using the following JSON format at the end of your response:

```json
{
    "1": {
        "root cause occurrence datetime": (if asked by the issue, format: '%Y-%m-%d %H:%M:%S', otherwise ommited),
        "root cause component": (if asked by the issue, one selected from the possible root cause component list, otherwise ommited),
        "root cause reason": (if asked by the issue, one selected from the possible root cause reason list, otherwise ommited),
    }, (mandatory)
    "2": {
        "root cause occurrence datetime": (if asked by the issue, format: '%Y-%m-%d %H:%M:%S', otherwise ommited),
        "root cause component": (if asked by the issue, one selected from the possible root cause component list, otherwise ommited),
        "root cause reason": (if asked by the issue, one selected from the possible root cause reason list, otherwise ommited),
    }, (only if the failure number is "unknown" or "more than one" in the issue)
    ... (only if the failure number is "unknown" or "more than one" in the issue)
}
```
(Please use "```json" and "```" tags to wrap the JSON object. You only need to provide the elements asked by the issue, and ommited the other fields in the JSON.)
Note that all the root cause components and reasons must be selected from the provided candidates. Do not reply 'unknown' or 'null' or 'not found' in the JSON. Do not be too conservative in selecting the root cause components and reasons. Be decisive to infer a possible answer based on your current observation.
"""


# Not needed additional user prompt template
_USER_TEMPLATE = """"""

_WRITE_MEMORY_TEMPLATE = """\
{% if question %}Question: {{ question }} {% endif %}
{% if thought %}Thought: {{ thought }} {% endif %}
{% if action %}Action: {{ action }} {% endif %}
{% if action_input %}Action Input: {{ action_input }} {% endif %}
{% if observation %}Observation: {{ observation }} {% endif %}
"""


class RcaRportOldAssistantAgent(ReportAssistantAgent):
    """Ipython Code Assistant Agent."""

    profile: ProfileConfig = ProfileConfig(
        name=DynConfig(
            "Kevin",
            category="agent",
            key="derisk_agent_expand_diag_reporter_agent_profile_name",
        ),
        role=DynConfig(
            "Diagnose Reporter(V1)",
            category="agent",
            key="derisk_agent_expand_diag_reporter_agent_profile_role",
        ),
        desc=DynConfig(
            "Now, you have decided to finish your reasoning process. You should now provide the final answer to the issue. The candidates of possible root cause components and reasons are provided to you. The root cause components and reasons must be selected from the provided candidates."
            " problems",
            category="agent",
            key="derisk_agent_expand_code_assistant_agent_profile_desc",
        ),
        system_prompt_template=_SYSTEM_TEMPLATE_ZH,
        # user_prompt_template=_USER_TEMPLATE,
        write_memory_template=_WRITE_MEMORY_TEMPLATE,
    )

    def __init__(self, **kwargs):
        """Create a new CodeAssistantAgent instance."""
        super().__init__(**kwargs)


        self._init_actions([BlankAction])

