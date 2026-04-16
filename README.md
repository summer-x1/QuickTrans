# QuickTrans

macOS 系统级划词翻译工具。在任意应用中选中文字，点击浮动图标，即刻获得翻译结果。

## 功能特性

- 在任意应用中选中文字 → 出现贴近文本右下角的浮动触发气泡
- 点击图标 → 显示翻译弹窗
- 支持 DeepL、OpenAI、DeepSeek、Gemini、Qwen 以及其他 OpenAI 兼容大模型
- 支持自定义目标语言、字体大小、弹窗停留时间等
- 轻量后台守护进程
- 支持无障碍 API 直接获取文字（避免剪贴板污染）
- 米色护眼背景，自动适配深色/浅色模式

## 系统要求

- macOS 12+
- Python 3.9+
- 任一可用翻译 API Key：DeepL / OpenAI / DeepSeek / Gemini / DashScope(Qwen) / 其他兼容模型

## 安装

```bash
git clone https://github.com/summer-x1/QuickTrans.git
cd QuickTrans
bash install.sh
```

安装脚本会自动完成：
1. 安装 Python 依赖（PyObjC）
2. 创建 `quicktrans` 启动命令
3. 保留仓库根目录的 `QuickTrans.command` 供 Finder 双击启动

### macOS 权限设置

QuickTrans 需要以下两项权限：

**输入监听**（必须）：
> 系统设置 → 隐私与安全性 → 输入监听 → 开启你的终端应用

**辅助功能**（推荐，用于直接获取选中文字）：
> 系统设置 → 隐私与安全性 → 辅助功能 → 开启你的终端应用

## 使用方法

启动方式：

1. Finder 中双击仓库根目录的 `QuickTrans.command`
2. 或在终端运行：

```bash
quicktrans
```

首次运行会启动配置向导，选择 provider、输入 API Key / model，并选择目标语言。

默认不会写入 shell 自动启动。如果你需要打开终端时自动拉起，可以手动把下面这行加到 `~/.zshrc` 或 `~/.bashrc`：

```bash
(quicktrans &) 2>/dev/null
```

启动后：
1. 在任意应用中**拖选文字**
2. 选中文本右下角出现一个小型浮动触发气泡
3. **点击图标**开始翻译
4. 弹窗显示翻译结果，可选中复制
5. 弹窗根据文字长度自动消失，或点击其他地方关闭

### 停止守护进程

```bash
pkill -f quicktrans
```

## 配置

编辑 `~/.config/quicktrans/config.json`：

```json
{
  "provider": "deepl",
  "engine": "deepl",
  "api_key": "你的-api-key",
  "api_url": "https://api-free.deepl.com/v2/translate",
  "model": "",
  "target_lang": "ZH",
  "min_drag_distance": 10,
  "min_text_length": 1,
  "popup_duration": 12,
  "font_size": 16,
  "icon_size": 32,
  "icon_dismiss_delay": 5
}
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `provider` | `deepl` | 翻译后端：`deepl` / `openai` / `deepseek` / `gemini` / `qwen` / `openai_compatible` |
| `engine` | `deepl` | 兼容旧版本配置的别名，会自动与 `provider` 同步 |
| `api_key` | — | 对应 provider 的 API Key |
| `api_url` | provider 默认值 | 接口地址；`openai_compatible` 建议填写完整的 `chat/completions` 地址 |
| `model` | provider 默认值或空 | LLM 模型名；DeepL 不使用该字段 |
| `target_lang` | `ZH` | 目标语言（ZH、EN、JA、KO、DE、FR、ES、RU 等）|
| `min_drag_distance` | `10` | 触发选词检测的最小拖拽距离（px）|
| `popup_duration` | `12` | 弹窗基础停留时间（秒），实际时间随文字长度动态增加 |
| `font_size` | `16` | 翻译弹窗字体大小 |
| `icon_size` | `32` | 触发图标大小（px）|
| `icon_dismiss_delay` | `5` | 触发图标自动消失时间（秒）|

### Provider 说明

- `deepl`：沿用原始翻译接口，免费版 Key 以 `:fx` 结尾
- `openai`：默认使用 `https://api.openai.com/v1/chat/completions` + `gpt-4.1-mini`
- `deepseek`：默认使用 `https://api.deepseek.com/chat/completions` + `deepseek-chat`
- `gemini`：默认使用 `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- `qwen`：默认使用 DashScope 兼容接口 `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
- `openai_compatible`：用于 Kimi、智谱、豆包、百川、零一万物、SiliconFlow、OpenRouter 等兼容 `chat/completions` 的模型，只需填写它们官方提供的接口地址和模型名

### 配置示例

DeepSeek:

```json
{
  "provider": "deepseek",
  "engine": "deepseek",
  "api_key": "YOUR_DEEPSEEK_API_KEY",
  "api_url": "https://api.deepseek.com/chat/completions",
  "model": "deepseek-chat",
  "target_lang": "ZH"
}
```

Gemini:

```json
{
  "provider": "gemini",
  "engine": "gemini",
  "api_key": "YOUR_GEMINI_API_KEY",
  "api_url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
  "model": "gemini-2.5-flash",
  "target_lang": "ZH"
}
```

OpenAI 兼容国产模型（示例：自定义接口）:

```json
{
  "provider": "openai_compatible",
  "engine": "openai_compatible",
  "api_key": "YOUR_API_KEY",
  "api_url": "https://your-provider.example.com/v1/chat/completions",
  "model": "your-model-name",
  "target_lang": "ZH"
}
```

修改后重启守护进程生效。

## 常见问题

**提示「Another QuickTrans instance is already running」**
```bash
pkill -f quicktrans
quicktrans
```

正常退出时会自动清理 `~/.config/quicktrans/quicktrans.pid`。即使文件偶尔残留，真正控制单实例的是文件锁，不是文件是否存在本身。

**选中文字后没有出现触发气泡**
- 检查终端应用是否已获得「输入监听」权限
- 查看运行日志：`cat ~/.config/quicktrans/quicktrans.log`

**翻译失败或报错**
- 检查 API Key、`provider`、`api_url`、`model` 是否匹配：`cat ~/.config/quicktrans/config.json`
- DeepL 免费版 Key 以 `:fx` 结尾，对应 `api-free.deepl.com`
- `openai_compatible` 需要使用供应商官方提供的 `chat/completions` 地址
- 查看日志获取详细错误信息

## 卸载

```bash
cd QuickTrans
bash uninstall.sh
```

## 开源协议

MIT
