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
现在，您已决定完成推理过程。现在您应该提供问题的最终分析报告。系统会向您提供可能的根本原因组件和原因的候选。您必须从提供的候选组件和原因中选择根本原因组件和原因。

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

请首先回顾你之前的推理过程，推断出该问题的确切答案。然后生成你的分析报告，确保你的分析报告保护如下三部分内容，同时请确保语言专业简洁，格式有条理，方便人类用户阅读：
1.根因定位信息，包含发生时间、发生的根因组件、根本原因
2.分析思路，把你的分析推理过程整理成如下格式的数据进行输出(注意markdown标签和json之间一定要输出换行符)：
```vis-chart
{
  "type": "flow-diagram",
  "data": {
    "nodes": [
      { "name": "诊断步骤1" },
      { "name": "诊断步骤2" },

    ],
    "edges": [
      { "source": "诊断步骤1", "target": "诊断步骤1" },
      { "source": "诊断步骤x", "target": "诊断步骤y" },
      { "source": "诊断步骤x", "target": "诊断步骤y", "name": "诊断步骤链接逻辑原因"}
    ]
  }
}
```
3.根因推断证据链，包含推导出根因的关键证据和数据信息，确保数据来源于提供的数据.不要自行构造和篡改，但是可以对数据进行合并和精简。同时对于时序、比例等结构化的可以图表展示的数据可以考虑使用如下格式的图表进行展示,不适合如下图表类型展示的数据直接使用文本展示:
     可用图表类型:
          response_line_chart: 折线图;
          response_pie_chart: 饼图;
          response_table:表格;
          response_heatmap:热力图;
     数据输出格式:
          ```vis-db-chart\n{"type":"这里输出选择的图表类型",   "data":"这里是数据的json列表内容,数据格式请参考[{"数据字段名":"数据值"}]的数据规范"}\n```

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


class RcaRportAssistantAgent(ReportAssistantAgent):
    """Ipython Code Assistant Agent."""

    profile: ProfileConfig = ProfileConfig(
        name=DynConfig(
            "Kevin",
            category="agent",
            key="derisk_agent_expand_diag_reporter_agent_profile_name",
        ),
        role=DynConfig(
            "Diagnose Reporter",
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

