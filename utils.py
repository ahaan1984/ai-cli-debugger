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
                shell_path, "echo", "${PS1@P}"
            ]
            shell_prompt = check_output(cmd, text=True)
        elif shell_name == 'powershell':
            cmd = [
                shell_path, "-c", "Write-Host $prompt"
            ]
            shell_prompt = check_output(cmd, text=True)
    except:
        pass

    return shell_prompt.strip() if shell_prompt else None

# def get_pane_output():
#     output_file = None
#     output = ''
#     try:
#         with tempfile.NamedTemporaryFile(delete=False) as output_file:
#             output_file = tempfile.name

#             if os.getenv("TMUX"):

