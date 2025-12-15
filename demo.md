这是一个非常棒的思路转换！引入 **HTTP Wrapper (中间件)** 模式是解决复杂的鉴权、Session 保持和接口标准化的最佳实践。

根据你提供的 GitHub 代码 (`codeinterpreter-wrapper.py`)，这个 Wrapper 将复杂的 AgentCube/SDK 操作封装成了简单的 **无状态/弱状态 HTTP 接口**。

*   **变化点 1 (鉴权)**：Wrapper 代码本身看起来没有强制鉴权逻辑（开放接口），或者鉴权下沉到了网络层。Dify 只需要配置 Wrapper 的地址即可，极大简化了 Header 配置。
*   **变化点 2 (接口)**：我们将不再直接调用 AgentCube，而是调用 Wrapper 的标准接口：`/create_sandbox` 和 `/run_code`。

以下是基于 **Wrapper 模式** 更新后的完整端到端方案。

---

### 🏛️ 新核心架构图解

*   **大脑 (Dify)**：负责业务编排。
*   **中间件 (Wrapper)**：你提供的 Python FastAPI 服务。它负责持有 Session、管理 SDK 实例。
*   **手脚 (AgentCube)**：实际的沙箱环境（由 Wrapper 管理）。

### ✅ 准备工作

1.  **部署 Wrapper**：确保 `codeinterpreter-wrapper.py` 已经运行，并且 Dify 可以访问到该服务（例如 `http://192.168.1.100:8000`）。
2.  **API 定义 (基于 Wrapper 代码)**：
    *   **创建沙箱**: `POST /create_sandbox`
    *   **执行代码**: `POST /run_code`
    *   **清理资源**: `POST /stop_sandbox` (建议加上，保持环境卫生)

---

### 🛠️ Dify 实施步骤 (Wrapper 版)

#### 第一阶段：全局配置

1.  打开 Dify 应用 -> **环境变量 (Environment Variables)**。
2.  配置 Wrapper 地址，不再需要复杂的 Token：
    *   `WRAPPER_URL`: 你的中间件地址 (例如 `http://<your-ip>:8000`)

#### 第二阶段：任务分发 (Dispatcher)

*(保持不变)* 在 `Start` 节点后，添加 **代码节点 (Code)**。

*   **节点名称**：`Task Generator`
*   **功能**：定义模拟次数。
*   **语言**：Python 3
*   **代码**：
    ```python
    def main(arg1: str) -> dict:
        # 模拟 3 个平行宇宙
        count = 3 
        seeds = list(range(101, 101 + count))
        return {"seeds": seeds}
    ```

#### 第三阶段：并发核心 (The Swarm)

添加 **迭代节点 (Iteration)**。

1.  **输入变量**：选择 `Task Generator` 的 `seeds`。
2.  **迭代变量名**：`item`。
3.  **并发模式**：**✅ 开启**。

**⚠️ 以下步骤 4-8 全部在【迭代节点内部】配置：**

#### 步骤 4：初始化沙箱 (Middleware Call)

在迭代内部添加 **HTTP 请求节点**。

*   **节点名称**：`Init Sandbox`
*   **API URL**: `{{#env.WRAPPER_URL#}}/create_sandbox`
*   **Method**: `POST`
*   **Body (JSON)**:
    ```json
    {
      "conversation_id": "dify-sim-{{#sys.conversation_id#}}" 
    }
    ```
*   **输出校验**：确保获取到 `body.sandbox_id`。

#### 步骤 5：构建任务代码 (Payload Builder)

在迭代内部添加 **代码节点 (Code)**。

*   **节点名称**：`Code Builder`
*   **输入变量**：`seed` (来自 `item`)
*   **代码**：
    *(逻辑不变，我们依然利用 `print` 输出 JSON，因为 Wrapper 会捕获 `stdout`)*
    ```python
    def main(seed: int) -> dict:
        py_code = f"""
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import json

# 1. 物理法则
np.random.seed({seed})

# 2. 模拟市场
days = 100
price = 100 + np.cumsum(np.random.randn(days))
volatility = np.std(price)

# 3. 绘图
plt.figure(figsize=(6, 4))
plt.plot(price, color='red', linewidth=1.5)
plt.title('Sim-{seed} | Vol: {{:.2f}}'.format(volatility))
plt.grid(True, alpha=0.3)

buf = io.BytesIO()
plt.savefig(buf, format='png')
buf.seek(0)
img_b64 = base64.b64encode(buf.read()).decode('utf-8')
plt.close()

# 4. 关键：将结果打印到 stdout，Wrapper 会捕获它
print(json.dumps({{"seed": {seed}, "vol": volatility, "image": img_b64}}))
"""
        return {"payload": py_code}
    ```

#### 步骤 6：执行代码 (Middleware Call)

在迭代内部添加 **HTTP 请求节点**。这就是 Wrapper 简化的威力所在。

*   **节点名称**：`Run Simulation`
*   **API URL**: `{{#env.WRAPPER_URL#}}/run_code`
*   **Method**: `POST`
*   **Headers**: `Content-Type: application/json`
*   **Body (JSON)**:
    ```json
    {
      "sandbox_id": "{{#Init Sandbox.body.sandbox_id#}}",
      "code": "{{#Code Builder.payload#}}",
      "language": "py"
    }
    ```
*   **Timeout**: `60` 秒。

#### 步骤 7：解析结果 (Result Parser)

在迭代内部添加 **代码节点 (Code)**。

*   **节点名称**：`Parser`
*   **输入变量**：`wrapper_resp` (来自 `Run Simulation` 的 body)
*   **代码**：
    ```python
    import json
    
    def main(wrapper_resp: dict) -> dict:
        # Wrapper 的返回结构是 {"output": "..."}
        # 里面的 output 才是我们的 Python print 的内容
        try:
            raw_stdout = wrapper_resp.get('output', '')
            # 清理可能的额外换行符
            data = json.loads(raw_stdout.strip())
            
            md = f"**模拟 #{data['seed']} (波动率: {data['vol']:.2f})**\n"
            md += f"![Chart](data:image/png;base64,{data['image']})"
            
            return {"markdown": md}
        except Exception as e:
            return {"markdown": f"⚠️ 计算失败: {str(e)} | Raw: {wrapper_resp}"}
    ```

#### 步骤 8：清理沙箱 (Garbage Collection)

为了不耗尽 Wrapper 服务器的内存/连接数，建议在迭代结束前释放沙箱。
添加 **HTTP 请求节点**。

*   **节点名称**：`Teardown`
*   **API URL**: `{{#env.WRAPPER_URL#}}/stop_sandbox`
*   **Method**: `POST`
*   **Body (JSON)**:
    ```json
    {
      "sandbox_id": "{{#Init Sandbox.body.sandbox_id#}}"
    }
    ```

---

#### 第四阶段：汇总报告 (Reducer)

跳出迭代节点，在主流程上添加 **代码节点**。

*   **节点名称**：`Report Generator`
*   **输入变量**：`results` (选择 **Iteration 节点** 的输出)
*   **代码**：
    ```python
    def main(results: list) -> dict:
        html = "### 📊 模拟完成 (Via Wrapper)\n\n"
        for item in results:
            # 这里的 item 对应 Parser 的输出
            html += item['markdown'] + "\n\n---\n\n"
        return {"content": html}
    ```

#### 第五阶段：输出

添加 **Answer** 节点，输出 `{{#Report Generator.content#}}`。

---

### 💡 方案优势总结

1.  **架构更稳健**：Dify 不直接依赖复杂的第三方鉴权逻辑，而是依赖自己可控的 Wrapper。
2.  **调试更简单**：Wrapper 提供了标准的 API (`/run_code`)，你可以在 Postman 里轻松测试 Wrapper 是否工作，排查问题时可以明确是 Dify 的问题还是后端的问题。
3.  **状态管理**：Wrapper 在内存中维护了 `SANDBOX_STORE`，这意味着在一个 Session 期间（Init -> Run -> Stop），文件和变量是持久的。虽然我们这个 Demo 是一次性执行，但未来你可以扩展成“多轮对话修改代码”的模式。