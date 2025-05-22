"""Code Assistant Agent."""

import uuid
from typing import Optional, Tuple, List, Type

from derisk.agent import ConversableAgent, ProfileConfig, AgentMessage, Action, Agent
from derisk.core import ModelMessageRoleType
from derisk.util.configure import DynConfig
from derisk.util.string_utils import str_to_bool
from derisk_ext.agent.agents.open_rca.actions.ipython_action import IpythonAction
from IPython.terminal.embed import InteractiveShellEmbed

_IPYTHON_SYSTEM_TEMPLATE = """You are a {{ role }}, {% if name %}named {{ name }}. {% endif %}\
{{ goal }} 

## RULES OF PYTHON CODE WRITING:

1. Reuse variables as much as possible for execution efficiency since the IPython Kernel is stateful, i.e., variables define in previous steps can be used in subsequent steps. 
2. Use variable name rather than `print()` to display the execution results since your Python environment is IPython Kernel rather than Python.exe. If you want to display multiple variables, use commas to separate them, e.g. `var1, var2`.
3. Use pandas Dataframe to process and display tabular data for efficiency and briefness. Avoid transforming Dataframe to list or dict type for display.
4. If you encounter an error or unexpected result, rewrite the code by referring to the given IPython Kernel error message.
5. Do not simulate any virtual situation or assume anything unknown. Solve the real problem.
6. Do not store any data as files in the disk. Only cache the data as variables in the memory.
7. Do not visualize the data or draw pictures or graphs via Python. You can only provide text-based results. Never include the `matplotlib` or `seaborn` library in the code.
8. Do not generate anything else except the Python code block except the instruction tell you to 'Use plain English'. If you find the input instruction is a summarization task (which is typically happening in the last step), you should comprehensively summarize the conclusion as a string in your code and display it directly.
9. Do not calculate threshold AFTER filtering data within the given time duration. Always calculate global thresholds using the entire KPI series of a specific component within a metric file BEFORE filtering data within the given time duration.
10. All issues use **UTC+8** time. However, the local machine's default timezone is unknown. Please use `pytz.timezone('Asia/Shanghai')` to explicityly set the timezone to UTC+8.

{{background}}

Your response should follow the Python block format below:
```python
(YOUR CODE HERE)
```
"""

_IPYTHON_SYSTEM_TEMPLATE_ZH = """您是{{ role }}，{% if name %} 名为 {{ name }}。{% endif %}\
{{ goal }}。请根据下面的规范完成你的目标。
## Python 代码编写规则：
1. 尽可能复用变量以提高执行效率，因为 IPython 内核是有状态的，也就是说，前面步骤中定义的变量可以在后面步骤中使用。
2. 由于您的 Python 环境是 IPython 内核而不是 Python.exe，因此请使用变量名而不是 `print()` 来显示执行结果。如果要显示多个变量，请使用逗号分隔，例如 `var1, var2`。对于输出的变量按如下规则进行数据整理转换:
转换规则：
    a.对于时序、比例等结构化的可以图表展示的数据可以考虑使用如下格式的图表进行展示,可用图表类型:
          response_line_chart: 折线图;
          response_pie_chart: 饼图;
          response_table:表格;
          response_heatmap:热力图;
    数据输出格式:
          ```vis-db-chart\n{"type":"这里输出选择的图表类型",   "data":"这里是数据的json列表内容,数据格式请参考[{"数据字段名":"数据值"}]的数据规范"}\n```
    b.不适合如下图表类型展示的数据直接使用有清晰条理的markdown文本展示
3. 使用 pandas Dataframe 处理和显示表格数据，以提高效率和简洁性。避免将 Dataframe 转换为列表或字典类型进行显示。
4. 如果遇到错误或意外结果，请参考给定的 IPython 内核错误消息重写代码。
5. 不要模拟任何虚拟情况或假设任何未知情况。解决真正的问题。
6. 不要将任何数据存储为磁盘文件。仅将数据缓存为内存变量。
7. 不要使用 Python 可视化数据或绘制图片或图表。您只能提供基于文本的结果。切勿在代码中包含 `matplotlib` 或 `seaborn` 库。
8. 除了指令外，不要生成 Python 代码块以外的任何其他内容。如果您发现输入指令是摘要任务（通常发生在最后一步），则应在代码中将结论全面总结为字符串并直接显示。
9. 不要在给定时间段内过滤数据后计算阈值。始终在给定时间段内过滤数据之前，使用指标文件中特定组件的整个 KPI 系列计算全局阈值。
10. 所有问题均使用 **UTC+8** 时间。但是，本地计算机的默认时区未知。请使用 `pytz.timezone('Asia/Shanghai')` 将时区明确设置为 UTC+8。

{{background}}

您的回复应遵循以下 Python 块格式：
```python
（此处输入您的代码)
```
"""


# Not needed additional user prompt template
_USER_TEMPLATE = """{{ question }}"""

_WRITE_MEMORY_TEMPLATE = """\
{% if question %}Question: {{ question }} {% endif %}
{% if thought %}Thought: {{ thought }} {% endif %}
{% if action %}Action: {{ action }} {% endif %}
{% if action_input %}Action Input: {{ action_input }} {% endif %}
{% if observation %}Observation: {{ observation }} {% endif %}
"""


class IpythonAssistantAgent(ConversableAgent):
    """Ipython Code Assistant Agent."""

    profile: ProfileConfig = ProfileConfig(
        name=DynConfig(
            "Turing",
            category="agent",
            key="derisk_agent_expand_code_assistant_agent_profile_name",
        ),
        role=DynConfig(
            "Python Code Engineer",
            category="agent",
            key="derisk_agent_expand_code_assistant_agent_profile_role",
        ),
        goal=DynConfig(
            " You goal is to write Python code to answer DevOps questions. For each question, you need to write Python code to solve it by retrieving and processing telemetry data of the target system. Your generated Python code will be automatically submitted to a IPython Kernel. The execution result output in IPython Kernel will be used as the answer to the question.",
            category="agent",
            key="derisk_agent_expand_code_assistant_agent_profile_goal",
        ),
        desc=DynConfig(
            "Can independently write and execute python/shell code to solve various"
            " problems",
            category="agent",
            key="derisk_agent_expand_code_assistant_agent_profile_desc",
        ),
        system_prompt_template=_IPYTHON_SYSTEM_TEMPLATE_ZH,
        user_prompt_template=_USER_TEMPLATE,
        write_memory_template=_WRITE_MEMORY_TEMPLATE,
    )

    def __init__(self, **kwargs):
        """Create a new CodeAssistantAgent instance."""
        super().__init__(**kwargs)


        self._init_actions([IpythonAction])

    def _init_actions(self, actions: List[Type[Action]]):
        self.actions = []
        kernel = InteractiveShellEmbed()
        init_code = "import pandas as pd\n" + \
                    "pd.set_option('display.width', 427)\n" + \
                    "pd.set_option('display.max_columns', 10)\n"
        kernel.run_cell(init_code)
        for idx, action in enumerate(actions):
            if issubclass(action, Action):
                self.actions.append(action(language=self.language, kernel=kernel))


    async def init_reply_message(
        self,
        received_message: AgentMessage,
        rely_messages: Optional[List[AgentMessage]] = None,
        sender: Optional[Agent] = None,
    ) -> AgentMessage:
        reply_message = await super().init_reply_message(received_message=received_message, rely_messages=rely_messages, sender=sender)

        from derisk_ext.agent.agents.open_rca.resource.basic_prompt_Bank import schema
        reply_message.context = {
            "background": schema,
        }
        return reply_message