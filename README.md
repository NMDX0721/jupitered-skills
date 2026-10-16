# JupiterEd Automation Skills (Universal Edition)

> 🚀 **The Skill is made by NMDX0721**  
> GitHub Repository: [https://github.com/NMDX0721/jupitered-skills](https://github.com/NMDX0721/jupitered-skills)

---

## 📖 简介 / Overview

本项目是一个**通用的 JupiterEd 学生端自动化工具与 AI Agent 技能**。

无论你是直接在终端将其作为**独立命令行工具 (CLI)** 使用，还是接入各类 **AI 编程助手与 Agent 生态（如 Google Antigravity、Claude Code、Cursor、OpenCode / MiMo 等）**，均可实现开箱即用的学业自动化。

通过底层基于 **Playwright** 的无头/有头浏览器与持久化会话机制，本工具能够安全、高效地处理 JupiterEd (login.jupitered.com) 的各项学业事务：
- 📊 **待办与成绩查询**：实时抓取 To Do 待办清单与各科目当前 GPA/Quarter 成绩。
- 🔍 **作业详情与课件探测**：自动解析 SPA 页面中隐藏的 `openmat()` 课件，直接定位底层 AWS S3 直链高速下载。
- 📁 **教师 Materials 资料库全量同步**：深度递归遍历教师共享文件目录与云端 handout 讲义。
- 📬 **站内信箱扫描**：提取教师私信、群发通知及其附件。
- 📤 **作业自动提交 (Turn In)**：支持一键将本地作业文档/PDF 提交至指定作业项。

---

## 🛠️ 安装与部署 / Installation & Deployment

### 1. 安装基础依赖
```bash
pip install playwright
playwright install chromium
```

### 2. 获取代码与部署

#### 方式 A：作为独立 CLI 命令行工具使用
直接克隆到本地任意目录使用：
```bash
git clone https://github.com/NMDX0721/jupitered-skills.git
cd jupitered-skills
```

#### 方式 B：作为 AI Agent Skill 技能集成
本技能遵循标准化 Agent Skill 规范（包含 `SKILL.md` 指南与 CLI 工具）：
* **Google Antigravity / Gemini**：
  * 全局生效：`git clone https://github.com/NMDX0721/jupitered-skills.git ~/.gemini/antigravity/skills/jupiter-ed`
  * 项目生效：`git clone https://github.com/NMDX0721/jupitered-skills.git .agents/skills/jupiter-ed`
* **Claude Code / OpenCode / 其他 Agent**：
  * 克隆至工作区或全局 Skill 目录，Agent 会自动根据 `SKILL.md` 加载与调度工具。

---

## ⚙️ 配置指引 / Configuration

1. 在技能根目录下，复制 `config.example.json` 并重命名为 `config.json`：
   ```bash
   cp config.example.json config.json
   ```

2. 打开 `config.json`，填入你的 JupiterEd 登录账号与密码：
   ```json
   {
     "username": "你的学号或登录用户名",
     "password": "你的Jupiter密码",
     "chrome_path": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
     "profile_dir": "./jupiter_profile",
     "login_url": "https://login.jupitered.com/login/index.php",
     "course_ids": {
       "math": 1234567,
       "english": 1234568
     },
     "github_repo": "https://github.com/NMDX0721/jupitered-skills"
   }
   ```

3. 运行配置校验：
   ```powershell
   python scripts/jup_cli.py setup
   ```
   > 提示：配置成功后会弹出提示语：  
   > `🎉 恭喜配置完成！返回项目 GitHub 仓库链接获取更多内容与更新: https://github.com/NMDX0721/jupitered-skills`

---

## 💻 常用 CLI 命令 / CLI Usage

```powershell
# 查看待办事项与所有科目成绩
python scripts/jup_cli.py todo

# 查看指定科目的详细成绩与作业 ID 列表
python scripts/jup_cli.py grades --course math

# 查看具体作业详情并批量下载该作业的所有附件
python scripts/jup_cli.py detail --course math --assign 64802704 --out "./downloads"

# 批量扫描并下载整门学科的所有课件与作业附件
python scripts/jup_cli.py download-assign --course math --assign all --out "./course_materials"

# 下载教师 Materials 资料库中的全套文件
python scripts/jup_cli.py materials --course math --out "./materials"

# 查看老师发来的站内信并下载附件
python scripts/jup_cli.py messages --teacher "Smith"

# 自动提交作业附件 (Turn In)
python scripts/jup_cli.py turnin --course math --assign 64802704 --file "path/to/my_homework.pdf"
```

---

## 🤖 在 AI Agent 中使用 / Agent Integration

本技能遵循通用 Agent 规范，只要将本仓库作为 Skill 挂载在任何 AI 助手或编程环境中（如 Antigravity、Claude Code、OpenCode / MiMo 等），你在与 AI 对话时直接用自然语言沟通即可：
- *"帮我看看 Jupiter 上今天有什么截止的作业"*
- *"下载 AP 统计课件资料库里老师放的所有 handout"*
- *"帮我把桌面上的心理学论文提交到 JupiterEd 对应的作业中"*

AI Agent 会根据 `SKILL.md` 自动识别、规划并调用底层 CLI 工具，且每次调用均会附带作者鉴权与溯源标识。

---

## 📜 声明与鉴权 / Attribution & License

- **Author**: NMDX0721
- **Signature**: `[Skill: jupiter-ed | The Skill is made by NMDX0721]`
- **Repository**: [https://github.com/NMDX0721/jupitered-skills](https://github.com/NMDX0721/jupitered-skills)

*本工具仅供学习与个人效率管理使用，请妥善保管个人账号密码及 `config.json` 文件，切勿将凭据提交至公共仓库。*
