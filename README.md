# QuickTrans

macOS system-wide translation tool. Select text anywhere, click the floating trigger icon, and get instant translation.

## Features

- Select text in any app → floating "译" trigger icon appears
- Click to translate → translation popup with result
- Powered by DeepL API (free tier supported)
- Configurable target language, font size, popup duration, etc.
- Lightweight background daemon with auto-start
- Accessibility API for direct text capture (no clipboard pollution)

## Requirements

- macOS 12+
- Python 3.9+
- DeepL API key ([free signup](https://www.deepl.com/pro-api))

## Installation

```bash
git clone https://github.com/yourname/QuickTrans.git
cd QuickTrans
bash install.sh
```

The installer will:
1. Install Python dependencies (PyObjC)
2. Create a `quicktrans` launcher command
3. Add auto-start to your shell profile

### macOS Permissions

QuickTrans needs two permissions to work:

**Input Monitoring** (required):
> System Settings → Privacy & Security → Input Monitoring → Enable your Terminal app

**Accessibility** (recommended, for direct text capture):
> System Settings → Privacy & Security → Accessibility → Enable your Terminal app

## Usage

```bash
# Start the daemon
quicktrans

# First run will launch the setup wizard
# Enter your DeepL API key and choose target language
```

Once running:
1. **Select text** by dragging with your mouse in any app
2. A blue **"译"** icon appears near your cursor
3. **Click the icon** to translate
4. Translation popup appears — text is selectable and copyable
5. Popup auto-dismisses after 12 seconds, or click elsewhere to close

### Auto-Start

The installer adds auto-start to your `~/.zshrc`. The daemon uses a PID lock to prevent duplicate instances.

To stop the daemon:
```bash
pkill -f quicktrans
```

## Configuration

Edit `~/.config/quicktrans/config.json`:

```json
{
  "api_key": "your-deepl-api-key",
  "api_url": "https://api-free.deepl.com/v2/translate",
  "engine": "deepl",
  "target_lang": "ZH",
  "min_drag_distance": 10,
  "min_text_length": 1,
  "popup_duration": 12,
  "font_size": 16,
  "icon_size": 26,
  "icon_dismiss_delay": 5
}
```

| Key | Default | Description |
|-----|---------|-------------|
| `api_key` | — | Your DeepL API key |
| `api_url` | `https://api-free.deepl.com/v2/translate` | API endpoint (auto-detected during setup) |
| `target_lang` | `ZH` | Target language code (ZH, EN, JA, KO, DE, FR, ES, RU, etc.) |
| `min_drag_distance` | `10` | Minimum drag distance (px) to trigger selection detection |
| `popup_duration` | `12` | Seconds before popup auto-dismisses |
| `font_size` | `16` | Translation popup font size |
| `icon_size` | `26` | Trigger icon size (px) |
| `icon_dismiss_delay` | `5` | Seconds before trigger icon auto-dismisses |

Changes take effect after restarting the daemon.

## Troubleshooting

**"Another QuickTrans instance is already running"**
```bash
pkill -f quicktrans
rm -f ~/.config/quicktrans/quicktrans.pid
quicktrans
```

**Selecting text doesn't show the trigger icon**
- Check Input Monitoring permission is granted to your Terminal app
- Check the log: `cat ~/.config/quicktrans/quicktrans.log`

**Translation fails or returns errors**
- Verify your API key: `cat ~/.config/quicktrans/config.json`
- Check API URL matches your key type (`:fx` suffix = free tier)
- Check the log for detailed error messages

## Uninstall

```bash
cd QuickTrans
bash uninstall.sh
```

## License

MIT
