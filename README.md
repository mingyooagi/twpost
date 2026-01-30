# twpost - Tweet from Command Line

通过 Chrome CDP 连接发推文的命令行工具。

## Prerequisites

- Google Chrome 已安装
- Twitter/X 账号已在 Chrome 中登录（首次运行时需手动登录）

## Installation

需要 [uv](https://github.com/astral-sh/uv):

```bash
cd ~/tweet
chmod +x twpost
./twpost --help  # 首次运行会自动通过 uv 安装依赖
```

添加到 PATH（可选）:
```bash
echo 'export PATH="$HOME/tweet:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Usage

```bash
# 发新推文
twpost "Hello world!"

# 回复推文
twpost -r "https://x.com/user/status/123456" "Nice post!"

# 带图片发推
twpost -i photo.jpg "Check this out"

# 带图片回复
twpost -r URL -i pic.png "带图回复"
```

## Options

| Option | Description |
|--------|-------------|
| `text` | 推文内容（必填） |
| `-r, --reply URL` | 回复指定推文 |
| `-i, --image FILE` | 附加图片 |

## How It Works

1. 检查 Chrome CDP 端口 (9222) 是否开启
2. 如未开启，自动启动 Chrome（使用 `.chrome/` 作为数据目录）
3. 通过 Playwright 连接 CDP，自动操作 Twitter 页面
4. 输入内容、上传图片（如有）、点击发送

## Notes

- Chrome 数据保存在项目目录下的 `.chrome/` 文件夹
- 首次使用需在自动打开的 Chrome 中登录 Twitter/X
- 如果 CDP 端口被占用，会先关闭现有 Chrome 进程
