# Dify-Style Workflow variables structured passing system

This implementation plan details the design and changes required to evolve the visual logic graph rule builder (`RuleGraphEditor.vue`) and execution engine (`core.py`) into a structured workflow builder modeled after Dify's variable mapping architecture.

## Goal Description
Currently, variable passing in rules is global and implicit: nodes set variables on a global `shared_state` dictionary, and downstream nodes interpolate them using `{{variable_name}}`. While this works, it leads to namespace collisions, lacks structure, and makes complex multi-step rules hard to visualize and manage.

We propose a structured variables model where:
1. **Explicit Node Outputs**: Each operator defines a structured `output_schema` defining what keys it produces.
2. **Upstream Variable Selection**: When configuring a parameter field in a downstream node, the user can select outputs from any upstream ancestor node using the format `{{#node_id.output_key#}}`.
3. **Execution Context**: The backend engine runs topological node execution, caching outputs per-node, and resolving `{{#node_id.output_key#}}` references on the fly.
4. **Complete Backwards-Compatibility**: Standard `{{variable_name}}` references will continue to be resolved against the global `shared_state` to ensure all existing rules remain 100% functional.

---

## User Review Required

> [!IMPORTANT]
> **Key Architecture Decisions:**
> 1. **Upstream Reachability**: Upstream variables are strictly bounded by reachable ancestor nodes in the directed graph. Downstream or parallel disconnected nodes will not appear in the variable selector.
> 2. **Dot-Notation Path Resolution**: For complex nodes like `http_call` that return arbitrary JSON response bodies, the path resolver will support recursive dot-notation (e.g., `{{#node_http.response_json.data.status#}}`).
> 3. **Interactive Dropdown UX**: Premium inline `{x}` variable selector dropdown trigger integrated next to/inside relevant configuration input boxes in the inspector panel.

---

## Open Questions

> [!NOTE]
> Are there any additional custom operators that require dedicated output schemas beyond the 8 predefined native operators? If yes, their schemas will be registered directly in `operator_registry.py`.

---

## Proposed Changes

### Database & Registry
#### [MODIFY] [operator_registry.py](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/backend/app/models/operator_registry.py)
- Update `INITIAL_OPERATORS` to register structured `output_schema` objects for all core operators:
  - `digital_signature`: `{"signer_cn": "string", "signature_valid": "boolean", "digital_signatures": "object"}`
  - `qr_scanner`: `{"qr_content": "string", "qr_codes": "array"}`
  - `revision_check`: `{"is_tampered": "boolean", "revision_count": "integer"}`
  - `institution_sniffer`: `{"institution": "string"}`
  - `text_llm` / `vision_llm`: `{"passed": "boolean", "reason": "string"}` (plus dynamic output keys when running in extraction mode)
  - `http_call`: `{"status_code": "integer", "response_text": "string", "response_json": "object", "passed": "boolean"}`
  - `variable_extractor`: `{"extracted_value": "string"}` (plus dynamic captured groups parsed from regex)
  - `document_diff`: `{"passed": "boolean", "message": "string", "similarity": "number"}`

---

### Backend Engine
#### [MODIFY] [core.py](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/backend/app/engine/core.py)
- **Nested Variable Resolver**: Implement a helper function `get_nested_val(d: dict, path: str)` to fetch nested dictionary values using dot-notation.
- **Enhanced `interpolate_vars`**:
  - Accept a new `node_outputs` dictionary parameter mapping `node_id` to its outputs.
  - Parse `{{#node_id.output_key#}}` format by splitting the inner path, locating the target node's output, and resolving the nested value.
  - Keep standard `{{variable_name}}` fallback interpolation.
  - Remove duplicate internal `interpolate_vars` re-declarations (e.g. inside `http_call` execution).
- **Node Outputs Caching**:
  - Inside the logic graph BFS traversal loop, initialize `context.node_outputs = {}` if it doesn't exist.
  - After executing each node, construct its `node_outputs_dict` containing its execution results and structured data.
  - Save to `context.node_outputs[node_id] = node_outputs_dict`.
  - Pass `context.node_outputs` into `interpolate_vars` during just-in-time node parameters resolution.

---

### Frontend UI
#### [MODIFY] [RuleGraphEditor.vue](file:///Users/zhouao/Projects/WorkSpace/Enter-Bro/ppap/frontend/src/components/RuleGraphEditor.vue)
- **Graph Ancestry Traversal**:
  - Implement a helper function `getUpstreamNodes(nodeId)` that traverses the graph backwards from `nodeId` along connected incoming edges using a BFS/DFS to build a list of all ancestor nodes.
- **Node Outputs Schema Definition**:
  - Define static `NODE_OUTPUT_SCHEMAS` mapping standard operator keys to their outputs.
  - Add dynamic output logic for `variable_extractor` (parses regex named capture groups `(?P<group_name>...)`) and LLM extraction modes.
- **Inline Variable Selector Component**:
  - Create a premium UI styling for inputs/textareas with an integrated variable selector dropdown:
    - Add a styled `{x}` variable selector button inside/next to configuration inputs (e.g., `prompt` in LLM, `base_document_url` in diff, `url_template` in http).
    - Trigger an Element Plus `<el-popover>` displaying a searchable, structured tree/list of available variables:
      - **System Variables**: global `full_text`, `institution`, etc.
      - **Upstream Outputs**: grouped by ancestor node labels and icons, showing available outputs.
    - Clicking any variable inserts its selector syntax (`{{#node_id.output_key#}}` or `{{system_var}}`) at the cursor position of the input.
- **Dynamic Variable Flow badge cards**:
  - Update the "Node Data Flow" cards in the inspector sidebar.
  - Parse referenced `{{#node_id.output_key#}}` nodes from the node's settings, and display them under "Inputs (Requires)" as node-specific references (e.g., `Node A > Output Key`) instead of flat global names.

---

## Verification Plan

### Automated Tests
- Run `pytest` to verify the backend tests are fully intact.
- Add a new unit test in `tests/engine/test_rule_execution.py` showing that a downstream node can dynamically interpolate parameters from an upstream node's output using `{{#node_id.output_key#}}`.

### Manual Verification
1. Open the rule graph editor.
2. Build a workflow: `📥 Input` -> `📱 二维码识别 (qr_node)` -> `🌐 HTTP 外部验证 (http_node)` -> `📊 最终判定聚合`.
3. In `http_node`, configure the URL template as `https://localhost:31234/health?code={{#qr_node.qr_content#}}` using the new variable selector dropdown.
4. Verify the variable popover displays correct icons, labels, and output options.
5. Trigger a Dry Run simulation.
6. Verify that the backend resolves the variable value correctly and executes the HTTP call, completing the test successfully.
