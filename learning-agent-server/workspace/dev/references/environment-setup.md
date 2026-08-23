# 环境搭建参考（Python / Go）

> 原则：每一步都有「验证命令」，装完立刻验证，再进下一步。国内网络优先给镜像源。

---

## 通用：先选编辑器

推荐 **VS Code**（免费、Python/Go 插件完善）：<https://code.visualstudio.com/>
装两个扩展：Python（微软官方）、Go（golang.go）。**扩展不是必须**，纯命令行也能学，但对新手看报错、点运行更友好。

---

## Python 3

### macOS
- 推荐方式一（Homebrew，若已装 brew）：
  ```bash
  brew install python@3.12
  ```
- 方式二：官网安装包 <https://www.python.org/downloads/>（macOS 下 .pkg 双击装）。
- 验证：
  ```bash
  python3 --version     # 期望 Python 3.12.x 或 3.13.x
  python3 -c "print('ok')"   # 期望输出 ok
  ```

### Windows
1. 官网下载 64 位安装包 <https://www.python.org/downloads/windows/>。
2. 安装第一步**勾选 “Add python.exe to PATH”**（关键，漏了后面 `python` 命令找不到）。
3. 验证（新开 PowerShell 或 CMD）：
   ```powershell
   python --version
   python -c "print('ok')"
   ```

### Linux (Debian/Ubuntu)
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
python3 --version
```

### 国内镜像（pip）
```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### 虚拟环境（入门必学，避免污染系统）
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

---

## Go

### macOS
```bash
brew install go
```
### Windows
官网 <https://go.dev/dl/> 下载 .msi 双击装（自动配 PATH）。

### Linux
```bash
# 或用官方 tar 包：https://go.dev/dl/
sudo apt install golang-go
```

### 验证
```bash
go version          # 期望 go version go1.2x.x darwin/amd64（或 arm64）
```

### 国内镜像（GOPROXY，国内必配，否则拉依赖超时）
```bash
go env -w GOPROXY=https://goproxy.cn,direct
go env -w GO111MODULE=on
```

### 第一个程序（验证整条链路）
```bash
mkdir -p ~/hello && cd ~/hello
go mod init hello
# 写 main.go：package main / import "fmt" / func main(){ fmt.Println("Hello, Go!") }
go run main.go        # 期望输出 Hello, Go!
```

---

## 常见坑速查

| 现象 | 原因 | 解决 |
|---|---|---|
| `python` 命令找不到（Windows） | 没勾 Add to PATH | 重装并勾选，或手动加 PATH |
| `pip install` 超时 | 国外源慢 | 换清华源（见上） |
| `go: module ... not found` / 拉依赖卡住 | GOPROXY 没配 | `go env -w GOPROXY=https://goproxy.cn,direct` |
| `go run` 报 `no required module` | 没 `go mod init` | 先 `go mod init <名字>` |
| macOS 报 `command not found: go` | brew 装了但 PATH 没刷新 | 重开终端，或 `echo $PATH` 确认 |
| `python3` 能用但版本很老 | 系统自带旧版 | 用 brew / 官网装新版并确认 `python3` 指向新版 |
