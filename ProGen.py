import os
import pty
import subprocess
import sys
import psutil
import time
import re
from colorama import Fore, Style, init

processes = {}


def process_details(pid):
    if pid in processes:
        try:
            proc = psutil.Process(pid)
            status = proc.status()
            cpu_times = proc.cpu_times()
            cpu_percent = proc.cpu_percent(interval=0.1)
            cpu_affinity = proc.cpu_affinity()
            memory_info = proc.memory_info()

            print(f"PID: {pid}")
            print(f"Status: {status}")
            print(f"CPU Times: {cpu_times}")
            print(f"CPU Percent: {cpu_percent}%")
            print(f"CPU Affinity (CPUs it can run on): {cpu_affinity}")
            print(f"Memory Info: {memory_info}")
            print(f"Elapsed Time Since Creation (seconds): {time.time() - proc.create_time()}")
        except psutil.NoSuchProcess:
            print(f"Process with PID {pid} does not exist.")
    else:
        print(f"No process found with PID {pid}.")

def list_processes():
    if processes:
        print("List of processes and their states:")
        for pid, (process, master_fd) in processes.items():
            try:
                proc = psutil.Process(pid)
                status = proc.status()
                print(f"PID: {pid}, Status: {status}")
            except psutil.NoSuchProcess:
                print(f"PID: {pid}, Status: dead")
    else:
        print("No processes spawned yet.")


def spawn_process(timeout: int=None):
    command = ['./a.out'] if not timeout else ['./a.out', str(timeout)]
    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(command, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd)
    
    pid = process.pid
    processes[pid] = (process, master_fd)
    print(f"Spawned process with PID {pid}.")


def open_terminal(pid):
    if pid in processes:
        process, master_fd = processes[pid]
        print(f"Opening terminal for process {pid}. Type 'exit' to detach.")

        try:
            while True:
                output = os.read(master_fd, 1024).decode('utf-8')  
                while output:
                    sys.stdout.write(output)
                    sys.stdout.flush()
                    output = os.read(master_fd, 1024).decode('utf-8')  

                input_command = input()
                if input_command.lower() == 'exit':
                    break
                os.write(master_fd, (input_command + "\n").encode('utf-8'))
                
        except KeyboardInterrupt:
            print("\nExiting terminal.")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"No process found with PID {pid}.")


init(autoreset=True)

def show_help():
    help_text = f"""
    {Fore.CYAN}Available Commands:
    {Fore.GREEN}- generate [timeout]     {Fore.WHITE}: Spawn a process with an optional timeout (in seconds).
    {Fore.GREEN}- terminal <pid>         {Fore.WHITE}: Open a terminal for the process with the given PID.
    {Fore.GREEN}- show <pid>             {Fore.WHITE}: Show details of the process with the given PID.
    {Fore.GREEN}- list                   {Fore.WHITE}: List all running processes.
    {Fore.GREEN}- exit                   {Fore.WHITE}: Exit the program.
    {Fore.GREEN}- help                   {Fore.WHITE}: Show this help text.
    """
    print(help_text)


def main():
    generate_pattern = re.compile(r"^generate(?:\s+(\d+))?$")
    terminal_pattern = re.compile(r"^terminal\s+(\d+)$")
    show_pattern = re.compile(r"^show\s+(\d+)$")
    
    print(f"{Fore.YELLOW}Welcome! Type '{Fore.GREEN}help{Fore.YELLOW}' to see available commands.")
    show_help()
    
    while True:
        user_input = input(f"{Fore.LIGHTBLUE_EX}Enter command: {Style.RESET_ALL}").strip()

        match = generate_pattern.match(user_input)
        if match:
            timeout = match.group(1)
            if timeout:
                print(f"{Fore.GREEN}Spawning a process with timeout {timeout} seconds...")
                spawn_process(timeout=int(timeout))
            else:
                print(f"{Fore.GREEN}Spawning a process with default timeout...")
                spawn_process()
            continue

        match = terminal_pattern.match(user_input)
        if match:
            try:
                pid = int(match.group(1))
                print(f"{Fore.GREEN}Opening terminal for PID {pid}...")
                open_terminal(pid)
            except ValueError:
                print(f"{Fore.RED}Invalid PID. Please enter a valid integer.")
            continue

        match = show_pattern.match(user_input)
        if match:
            try:
                pid = int(match.group(1))
                print(f"{Fore.GREEN}Showing details for PID {pid}...")
                process_details(pid)
            except ValueError:
                print(f"{Fore.RED}Invalid PID. Please enter a valid integer.")
            continue

        if user_input == "list":
            print(f"{Fore.CYAN}Listing all processes...")
            list_processes()
            continue

        if user_input == "exit":
            print(f"{Fore.MAGENTA}Exiting... Goodbye!")
            exit(0)

        if user_input == "help":
            show_help()
            continue

        print(f"{Fore.RED}Unknown command. Type '{Fore.GREEN}help{Fore.RED}' for available commands.")

if __name__ == "__main__":
    main()
