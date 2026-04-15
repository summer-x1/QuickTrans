# QuickTrans

macOS 系统级划词翻译工具。在任意应用中选中文字，点击浮动图标，即刻获得翻译结果。

## 功能特性

- 在任意应用中选中文字 → 出现浮动「译」触发图标
- 点击图标 → 显示翻译弹窗
- 基于 DeepL API（支持免费版）
- 支持自定义目标语言、字体大小、弹窗停留时间等
- 轻量后台守护进程
- 支持无障碍 API 直接获取文字（避免剪贴板污染）
- 米色护眼背景，自动适配深色/浅色模式

## 系统要求

- macOS 12+
- Python 3.9+
- DeepL API Key（[免费注册](https://www.deepl.com/pro-api)）

## 安装

```bash
git clone https://github.com/summer-x1/QuickTrans.git
cd QuickTrans
bash install.sh
```

安装脚本会自动完成：
1. 安装 Python 依赖（PyObjC）
2. 创建 `quicktrans` 启动命令
3. 在 shell 配置文件中添加开机自启

### macOS 权限设置

QuickTrans 需要以下两项权限：

**输入监听**（必须）：
> 系统设置 → 隐私与安全性 → 输入监听 → 开启你的终端应用

**辅助功能**（推荐，用于直接获取选中文字）：
> 系统设置 → 隐私与安全性 → 辅助功能 → 开启你的终端应用

## 使用方法

```bash
# 启动守护进程
quicktrans

# 首次运行会启动配置向导
# 输入 DeepL API Key 并选择目标语言
```

启动后：
1. 在任意应用中**拖选文字**
2. 光标附近出现蓝色**「译」**图标
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
  "api_key": "你的-deepl-api-key",
  "api_url": "https://api-free.deepl.com/v2/translate",
  "engine": "deepl",
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
| `api_key` | — | DeepL API Key |
| `api_url` | `https://api-free.deepl.com/v2/translate` | API 地址（配置向导自动填写）|
| `target_lang` | `ZH` | 目标语言（ZH、EN、JA、KO、DE、FR、ES、RU 等）|
| `min_drag_distance` | `10` | 触发选词检测的最小拖拽距离（px）|
| `popup_duration` | `12` | 弹窗基础停留时间（秒），实际时间随文字长度动态增加 |
| `font_size` | `16` | 翻译弹窗字体大小 |
| `icon_size` | `32` | 触发图标大小（px）|
| `icon_dismiss_delay` | `5` | 触发图标自动消失时间（秒）|

修改后重启守护进程生效。

## 常见问题

**提示「Another QuickTrans instance is already running」**
```bash
pkill -f quicktrans
rm -f ~/.config/quicktrans/quicktrans.pid
quicktrans
```

**选中文字后没有出现「译」图标**
- 检查终端应用是否已获得「输入监听」权限
- 查看运行日志：`cat ~/.config/quicktrans/quicktrans.log`

**翻译失败或报错**
- 检查 API Key 是否正确：`cat ~/.config/quicktrans/config.json`
- 免费版 Key 以 `:fx` 结尾，对应 `api-free.deepl.com`
- 查看日志获取详细错误信息

## 卸载

```bash
cd QuickTrans
bash uninstall.sh
```

## 开源协议

MIT
