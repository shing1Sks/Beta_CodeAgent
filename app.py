import os
import subprocess
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SANDBOX_DIR = "agent_sandbox"
os.makedirs(SANDBOX_DIR, exist_ok=True)

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def get_folder_tree(path):
    """Return folder structure."""
    try:
        return subprocess.check_output(["tree", path], text=True)
    except Exception:
        return subprocess.check_output(["ls", "-R", path], text=True)


def run_command(command):
    """Run shell command inside sandbox."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=SANDBOX_DIR,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {str(e)}"


def call_llm(prompt):
    """Ask Groq LLM for next command."""
    response = groq_client.chat.completions.create(
        model=os.getenv("MODEL_ID", "gpt-4"),
        messages=[
            {"role": "system", "content": "You are a coding agent."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def ask_llm(task, folder_tree, last_output):
    """Construct LLM prompt."""
    prompt = f"""
You are an autonomous coding agent that can only run non-interactive terminal commands inside the 'agent_sandbox' directory.

### RULES:
1. **NO interactive commands** like `nano`, `vi`, `less`, `top`, etc.
2. **Use echo or printf** to create or update files.  
   Example:  
     echo "print('Hello')" > main.py
3. Always create minimal, functional code in as few commands as possible.
4. **Do not explain your commands**, only output the command itself.
5. If the task is done, return `exit` to stop.

### CONTEXT:
Task: {task}

Current folder structure:
{folder_tree}

Last command output:
{last_output}

### QUESTION:
What single non-interactive command should be executed next?
"""
    return call_llm(prompt)


def clean_command(cmd):
    """Remove markdown formatting and extra text."""
    cmd = cmd.strip()
    if cmd.startswith("```"):
        cmd = cmd.split("```")[1]  # remove first ```
        cmd = cmd.replace("bash", "").replace("python", "")  # remove language tags
    cmd = cmd.replace("```", "").strip()
    return cmd


def main():
    task = input("Enter the coding task for the agent: ")
    last_output = "None"

    for step in range(10):  # safety steps
        folder_tree = get_folder_tree(SANDBOX_DIR)
        command = clean_command(ask_llm(task, folder_tree, last_output))

        print(f"\n[Agent Step {step + 1}] Command: {command}")
        last_output = run_command(command)
        print(f"[Terminal Output]:\n{last_output}")


if __name__ == "__main__":
    main()
