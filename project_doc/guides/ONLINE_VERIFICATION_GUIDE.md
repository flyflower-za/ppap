# 在线防伪比对模块配置指南

在线防伪比对模块可以通过提取 PDF 文件中二维码的内容（如 URL），解析出关键参数（如报告编号、防伪验证码），然后向第三方检测机构的 API 发送请求拉取原件进行文本差异比对。

为了方便配置，系统提供了三种二维码参数提取语法，从易到难，适合不同技术背景的用户。

---

## 1. 参数提取语法说明

在配置该模块时，需要填写 **正则表达式 (Regex Pattern)**。系统支持以下三种写法，会自动检测并转换。

### 方式 A：简化占位符语法（推荐）
适合参数在二维码中**紧密相连**的场景。用户只需用 `{变量名}` 标记需要提取的部分，其余部分按原样书写。

*   **二维码 URL 示例**：
    `https://mycti.com/query?reportno=A225097&randomno=198641`
*   **提取规则填写**：
    `reportno={report_id}&randomno={verify_code}`
*   **系统自动转换后的正则**：
    `reportno=(?P<report_id>[^&\s]+)&randomno=(?P<verify_code>[^&\s]+)`

### 方式 B：占位符 + `*` 通配符语法
适合提取的参数**不相邻**、中间夹杂了其他无关参数的场景。使用 `*` 来代表“跳过中间任意字符”（系统会自动将其转换为 `.*?` 非贪婪匹配）。

*   **二维码 URL 示例**：
    `https://example.com/verify?reportno=A225097&type=pdf&lang=zh&randomno=198641`
*   **提取规则填写**：
    `reportno={report_id}*randomno={verify_code}`
*   **系统自动转换后的正则**：
    `reportno=(?P<report_id>[^&\s]+).*?randomno=(?P<verify_code>[^&\s]+)`

### 方式 C：原生正则表达式（高级）
如果您熟悉正则表达式，可以直接编写包含命名捕获组 `(?P<name>...)` 的原生正则。当检测到输入包含 `(?P<` 时，系统会跳过转换，直接将其作为正则表达式编译。

*   **提取规则填写**：
    `reportno=(?P<report_id>[^&]+)&randomno=(?P<verify_code>[^\s&]+)`

---

## 2. 支持提取的预设变量

提取出的变量将用于构造“目标 URL (Target URL)”。系统支持且**必须**提取出以下两个变量：

1.  `{report_id}`：报告编号/证书编号。
2.  `{verify_code}`：验证码/随机码/查询码。

---

## 3. 目标 URL 构造示例

提取出上述变量后，您可以在“目标 URL”输入框中，使用 `{report_id}` 和 `{verify_code}` 占位符来动态构造请求地址。

*   **配置的目标 URL**：
    `https://myctiapi.cti-soft.com:58443/api/HomeQuery/PreviewReportH5?ReportNo={report_id};{verify_code}`
*   **解析生成的真实 URL**（以华测为例）：
    `https://myctiapi.cti-soft.com:58443/api/HomeQuery/PreviewReportH5?ReportNo=A225097;198641`

---

## 4. 常见问题 (FAQ)

#### Q1: 如果匹配失败会怎样？
如果二维码内容与填写的提取规则不匹配，算子会标记为 `fail` 并输出：
`在线防伪失败：二维码内容未匹配提取规则。内容: ... 正则: ...`

#### Q2: 简化占位符如何识别？
系统在后台会自动检测规则中是否包含 `(?P<`。
*   如果**包含**，则认为是原生正则，不做任何修改。
*   如果**不包含**且含有 `{report_id}` 或 `{verify_code}`，则启动自动转换机制，将 `{var_name}` 替换为命名捕获组 `(?P<var_name>[^&\s]+)`，并将 `*` 替换为 `.*?`。
