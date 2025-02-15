import os
import tempfile
from collections import namedtuple
from subprocess import check_output, run, CalledProcessError
from typing import List, Optional, Tuple

import psutil
from rich.markdown import Markdown

from llms import run_cohere, Prompts

MAX_CHARS = 10000
MAX_COMMANDS = 3
SHELLS = ['bash', 'powershell', 'zsh']

Shell = namedtuple("Shell", ['path', 'name', 'prompt'])
Command = namedtuple("Command", ['text', 'output'])

def count_chars(text: str) -> int:
    return len(text)

def truncate_chars(text: str, reverse=False):
    return text[-MAX_CHARS:] if reverse else text[:MAX_CHARS]

def get_shell_name(shell_path):
    if not shell_path:
        return None
    if os.path.splitext(shell_path)[-1].lower() in SHELLS:
        return os.path.splitext(shell_path)[-1].lower()
    if os.path.splitext(shell_path)[0].lower() in SHELLS:
        return os.path.splitext(shell_path)[0].lower()
    if shell_path.lower() in SHELLS:
        return shell_path.lower()
    
def get_shell_name_and_path():
    path = os.environ.get("SHELL", None) or os.environ.get("TF_SHELL", None)
    if shell_name := get_shell_name(path):
        return shell_name, path
    
    proc = psutil.Process(os.getpid())
    while proc is not None and proc.pid > 0:

        try:
            _path = proc.name()
        except TypeError:
            _path = proc.name
        
        if shell_name := get_shell_name(_path):
            return shell_name, path

        try:
            proc = proc.parent()
        except TypeError:
            proc = proc.parent

    return None, path

def get_shell_prompt(shell_name, shell_path):
    shell_prompt = None

    try: 
        if shell_name == 'zsh':
            cmd = [
                shell_path, '-i', '-c', 'echo $PROMPT'
            ]
            shell_prompt = check_output(cmd, text=True)
        elif shell_name == 'bash':
            cmd = [
                shell_path, 'echo', '${PS1@P}'
            ]
            shell_prompt = check_output(cmd, text=True)
        elif shell_name == 'powershell':
            cmd = [
                shell_path, '-c', 'Write-Host $prompt'
            ]
            shell_prompt = check_output(cmd, text=True)
    except:
        pass

    return shell_prompt.strip() if shell_prompt else None

def get_pane_output():
    output = ""
    debug_logs = []

    try:
        # Debug: Check which shell is detected
        if os.getenv("TMUX"):
            debug_logs.append("Detected TMUX environment.")
            cmd = ['tmux', 'capture-pane', '-p']
            output = check_output(cmd, text=True)
        elif os.getenv("STY"):
            debug_logs.append("Detected screen environment.")
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.close()
                cmd = ['screen', '-X', 'hardcopy', temp_file.name]
                run(cmd, check=True)
                with open(temp_file.name, 'r') as file:
                    output = file.read()
                os.remove(temp_file.name)
        elif os.name == 'nt':  # PowerShell
            debug_logs.append("Detected Windows PowerShell environment.")
            try:
                debug_logs.append("Attempting PowerShell Get-History command.")
                cmd = ['powershell', '-Command', 'Get-History | Select-Object -ExpandProperty CommandLine']
                output = check_output(cmd, text=True)
            except CalledProcessError as e:
                debug_logs.append(f"Primary PowerShell command failed: {e}")
                debug_logs.append("Attempting fallback PowerShell history command.")
                try:
                    cmd = ['powershell', '-Command', '$host.UI.RawUI.History.GetCommands() | ForEach-Object {$_.CommandLine}']
                    output = check_output(cmd, text=True)
                except CalledProcessError as fallback_error:
                    debug_logs.append(f"Fallback PowerShell command failed: {fallback_error}")
        else:
            debug_logs.append("Fallback to normal shell environment.")
            history_file = os.path.expanduser('~/.bash_history')
            if os.path.exists(history_file):
                with open(history_file, 'r') as file:
                    output = file.read()
            else:
                output = "No history file found or unsupported shell."

    except CalledProcessError as e:
        debug_logs.append(f"Subprocess error: {e}")
        output = f"Error capturing pane output: {e}"
    except Exception as e:
        debug_logs.append(f"Unexpected error: {e}")
        output = f"Unexpected error: {e}"

    # Print debug logs for troubleshooting
    if debug_logs:
        print("\n".join(debug_logs))

    return output.strip()


def get_commands(pane_output:str, shell:Shell):
    commands = [] # order: newest to oldest
    buffer = []

    for line in reversed(pane_output.splitlines()):
        if not line.strip():
            continue

        if shell.prompt.lower() in line.lower():
            command_text = line.split(shell.prompt, 1)[1].strip()
            command = Command(command_text, '\n'.join(reversed(buffer)).strip())
            commands.append(command)
            buffer = []
            continue

        buffer.append(line)

    return commands[1:]

def truncate_commands(commands):
    num_chars = 0
    truncated_cmd = []
    for command in commands:
        command_chars = count_chars(command.text)
        if command_chars + num_chars > MAX_CHARS:
            break
        num_chars += command_chars

        output = []
        for line in reversed(command.output.splitlines()):
            if count_chars('\n'.join(output)) + count_chars(line) > MAX_CHARS:
                break
            output.append(line)
            num_chars += count_chars(line)

        output = '\n'.join(reversed(output))
        command = Command(command.text, output)
        truncated_cmd.append(command)

    return truncated_cmd

def truncate_pane_output(output):
    hit_non_empty_line = False
    lines = []
    for line in reversed(output.splitlines()):
        if line and line.strip():
            hit_non_empty_line = True

        if hit_non_empty_line:
            lines.append(line)

    lines = lines[1:]
    output = '\n'.join(reversed(lines))
    output = truncate_chars(output, reverse=True)
    
    return output.strip()

def command_to_string(command, shell_prompt):
    shell_prompt = shell_prompt if shell_prompt else '$'
    command_str = f'{shell_prompt} {command.text}'
    command_str += f'\n{command.output}' if command.output.strip() else ''
    return command_str

def format_output(output):
    return Markdown(
        output, 
        inline_code_lexer='python'
    )

def get_shell():
    name, path = get_shell_name_and_path()
    prompt = get_shell_prompt(name, path)
    return Shell(path, name, prompt)

def get_terminal_context(shell):
    pane_output = get_pane_output()
    if not pane_output:
        return "<terminal_history> No Terminal History Found. </terminal_history>"
    
    if not shell.prompt:
        pane_output = truncate_pane_output(pane_output)
        context = f'<terminal_history> {pane_output} </terminal_history>'
    else:
        commands = get_commands(pane_output, shell)
        commands = truncate_commands(commands)
        commands = list(reversed(commands))

        previous_commands = commands[:-1]
        last_command = commands[-1]

        context = "<terminal_history>"
        context += "<previous_commands>\n"
        context += "\n".join(
            command_to_string(c, shell.prompt) for c in previous_commands
        )
        context += "\n</previous_commands>\n"
        context += "\n<last_command>\n"
        context += command_to_string(last_command, shell.prompt)
        context += "\n</last_command>"
        context += "\n</terminal_history>"

    return context

def build_query(context, query):
    if not (query and query.strip()):
        query = "Explain the last command's output. Use the previous commands as context, if relevant, but focus on the last command."
    return f'{context}\n\n{query}'


def explain(context, query):
    system_message = Prompts.EXPLAIN_PROMPT.value if not query else Prompts.ANSWER_PROMPT
    user_message = build_query(context, query)
    output = run_cohere(system_message, user_message)
    return format_output(output)
    



