import os
import argparse

from rich.console import Console

from utils import get_shell, get_terminal_context, explain

def main():
    parser = argparse.ArgumentParser(
        description="Understand the output of your latest terminal command"
    )
    parser.add_argument(
        "--query", type=str, required=False, default=None, help="A question about what's on your terminal." 
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print debug information."
    )
    args = parser.parse_args()
    console = Console()
    debug = lambda text: console.print(f'huh | {text}') if args.debug else None

    # if not os.environ.get("TMUX") and not os.environ.get("STY"):
    #     console.print("huh | This script must be run inside a tmux session.")
    #     return
    
    # if not os.getenv("COHERE_API_KEY", None):
    #     console.print("huh | Please set the COHERE_API_KEY environment variable.")
    #     print(os.getenv("COHERE_API_KEY"))
    #     return
    
    with console.status("huh | Getting terminal context..."):
        shell = get_shell()
        context = get_terminal_context(shell)

        debug(f'Retrieved Shell Information: \n{shell}')
        debug(f'Retrieved Terminal Context: \n{context}')
        debug('Sending request to LLM....')

        response = explain(context, args.query)

    console.print(response)