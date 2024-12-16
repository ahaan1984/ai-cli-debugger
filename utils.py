import os
import tempfile
from collections import namedtuple
from subprocess import check_output, run, CalledProcessError
from typing import List, Optional, Tuple

import psutil
from rich.markdown import Markdown

MAX_CHARS = 10000
MAX_COMMANDS = 3
SHELLS = ['bash', 'powershell', 'zsh']

Shell = namedtuple("Shell", ['path', 'name', 'prompt'])
Command = namedtuple("Command", ['text', 'output'])

def count_chars(text: str) -> int:
    return len(text)

def truncate_chars(text: str, reverse=False):
    return text[-MAX_CHARS:] if reverse else text[:MAX_CHARS]

def get_shell(shell_path):
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
    if shell_name := get_shell(path):
        return shell_name, path
    
    proc = psutil.Process(os.getpid())
    while proc is not None and proc.pid > 0:

        try:
            _path = proc.name()
        except TypeError:
            _path = proc.name
        
        if shell_name := get_shell(_path):
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
    output_file = None
    output = ''

    try:
        with tempfile.NamedTemporaryFile(delete=False) as output_file:
            output_file = tempfile.name

            if os.getenv("TMUX"):
                cmd = [
                    'tmux', 'capture_pane', '-p', '-s', '-'
                ]
                with open(output_file, 'w') as f:
                    run(cmd, stdout=f, text=True)
            elif os.getenv("STY"):
                cmd = [
                    'screen', '-X', 'hardcopy', '-h', output_file
                ]
                check_output(cmd, text=True)
            else:
                return ""
            
    except CalledProcessError as e:
        pass

    if output_file:
        os.remove(output_file)

    return output

def get_commands(pane_output:str, shell:Shell):
    commands = [] # order: newest to oldest
    buffer = []

    for line in reversed(pane_output.splitline()):
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




