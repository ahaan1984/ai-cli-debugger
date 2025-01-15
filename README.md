### HUH - CLI Tool For Your Terminal

The `huh` is a command-line interface designed to interpret and explain the output of your most recent command. 
By simply typing huh, the tool leverages a language model (LLM) to provide insightful explanations for terminal outputs.

## Configuration

The project uses Cohere's Command R Plus LLM model. To set it up, create a .env file in the project directory and add your API key, as shown below:

`COHERE_API_KEY = 'your-api-key-here'`

To get your API key, go to the following page: https://dashboard.cohere.com/api-keys

## USAGE

`huh` must be run inside a `tmux` or `screen` session. Run the main.py file in `tmux`/`screen` and then just type `huh` after running a command. 
It will return a brief explanation of the issue and briefly explain how to debug the error.
