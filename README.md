# AdaptixC2 MCP Server
---
## ✨ Overview

**AdaptixC2 MCP Server** enables LLM agents to interact with and automate operations with the **[AdaptixC2](https://github.com/Adaptix-Framework/AdaptixC2)** framework via the MCP protocol.

It allows AI-driven red teaming, automation of post-exploitation tasks, and controlled tool execution within a C2 environment.

![AdaptixC2 MCP](img/image_2026-03-24_19-12-29.png)
![AdaptixC2 MCP](img/image_2026-03-24_19-01-52.png)
![AdaptixC2 MCP](img/image_2026-03-24_19-08-54.png)


---

## 🚀 Installation and Setup

Python 3.10+ and the `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`) are required.

1. Clone the repository:
```bash
git clone https://github.com/Faceless0x7/AdaptixC2-MCP-Server
cd AdaptixC2-MCP-Server
```

2. Create an isolated virtual environment and install dependencies:
```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

3. Configure connection parameters:
Copy the configuration template and edit it with your details (IP, port, C2 credentials, endpoint):
```bash
cp .env.example .env
```

---

## 🤖 Connecting to LLMs

Add the server startup parameters to your MCP client configuration.
### Example: Gemini CLI

Create the configuration file:

```bash
mkdir -p .gemini
nano .gemini/settings.json
```

**Example configuration for Gemini CLI:**
```json
{
  "mcpServers": {
    "adaptixc2": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/kali/Desktop/AdaptixC2-MCP-Server",
        "run",
        "server.py"
      ]
    }
  }
}
```

---

## 🛡️ BOF Integration (Optional)

The server supports BOFs. To activate this functionality, additional setup steps are required on both the Teamserver and the MCP side. 

### 1. Build and Install Extension-Kit
Clone and compile the modules from the official **[Extension-Kit](https://github.com/Adaptix-Framework/Extension-Kit)** repository:
```bash
git clone https://github.com/Adaptix-Framework/Extension-Kit
cd Extension-Kit
make
```

### 2. Configure profile.yaml in AdaptixC2
In the `profile.yaml` configuration file of your AdaptixC2 Teamserver, you must specify the path to the compiled file from the first step (it is important to use an absolute path):
```yaml
axscripts:
  - "/full/path/to/Extension-Kit/extension-kit.axs"
```
For more details about the main C2 server: [AdaptixC2 Documentation](https://adaptix-framework.gitbook.io/adaptix-framework/adaptix-c2/getting-starting/installation-server)

### 3. Restricting AI Access via bofs.yaml
To minimize risk and avoid excessive tool exposure, the server enforces a strict **default-deny** model for BOF modules.

Edit the `bofs.yaml` file in the root directory of `AdaptixC2 MCP Server`. You must explicitly list which commands the AI is allowed to leverage:
```yaml
# Example: Granting access only to two required BOFs in AD
AD-BOF:
  - dcsync single
  - adwssearch

# Or allowing the entire category
ADCS-BOF: all 
```
*If a category is commented out or the config is left entirely commented out — no BOF tools will be loaded.*

---
### Built-in Tools (no BOF required)
  - agent_info
  - change_directory
  - copy_file
  - download_file
  - execute_powershell
  - execute_raw
  - execute_shell
  - get_downloaded_file
  - get_uid
  - get_working_directory
  - jobs_kill
  - jobs_list
  - kill_agent
  - kill_process
  - list_agents
  - list_credentials
  - adaptix__list_directory
  - list_disks
  - list_downloads
  - list_listeners
  - list_processes
  - list_targets
  - list_task_history
  - list_tunnels
  - log_finding
  - make_directory
  - move_file
  - port_forward
  - adaptix__read_file
  - remove_file
  - reverse_port_forward
  - run_process
  - save_writeup
  - set_agent_sleep
  - start_socks4
  - start_socks5
  - stop_tunnel
  - tag_agent
  - view_session_notes

### BOF-based Tools
  - bof_adbof
  - bof_adcsbof
  - bof_credsbof
  - bof_elevationbof
  - bof_executionbof
  - bof_injectionbof
  - bof_kerbeusbof
  - bof_lateralmovement
  - bof_ldapbof
  - bof_mssqlbof
  - bof_postexbof
  - bof_processbof
  - bof_relayinformerbof
  - bof_salbof
  - bof_sarbof



## ⚠️ Disclaimer

This project is intended for authorized security testing and research purposes only.

Do not use this software on systems you do not own or have explicit permission to test.